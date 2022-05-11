
import os
from pathlib import Path

import pandas as pd
import yaml
from absl import app, flags
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ca22_pdf import conf
from ca22_pdf.db.base import Base
from ca22_pdf.db.model import Association, Categorie, Transaction
from ca22_pdf.parser import parse_single_pdf

FLAGS = flags.FLAGS
flags.DEFINE_string("db", None, "Path to sqlite database")
flags.DEFINE_string("pdf_dir", None, "Path to pdf directory")
                     
# Required flag.
flags.mark_flag_as_required("db")
flags.mark_flag_as_required("pdf_dir")


def main(argv):
    del argv 

    if os.path.isfile(FLAGS.db):
        os.remove(FLAGS.db)

    engine = create_engine(f"sqlite+pysqlite:///{FLAGS.db}", echo=True, future=True)

    Base.metadata.create_all(engine)

    with Session(engine) as session:

        all = list(map(parse_single_pdf, Path(FLAGS.pdf_dir).glob('*/*.pdf')))
        test = pd.concat(all)

        trx = test.apply(lambda x: Transaction(**x), axis=1).values.tolist()

        session.bulk_save_objects(trx)
        session.commit()

        categories = yaml.load(open(Path(conf.__path__._path[0]) / 'categories.yml'), Loader=yaml.BaseLoader)
        
        trx = []
        for parent in categories['categories']:
            trx.append(Categorie(id_cat=parent['id'], libelle=parent['libelle']))
            trx += [Categorie(id_cat=child['id'], libelle=child['libelle'], id_parent=parent['id']) for child in parent.get('sous-categories', [])]

        session.bulk_save_objects(trx)
        session.commit()

if __name__ == '__main__':
    app.run(main)