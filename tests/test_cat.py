
from sqlalchemy.orm import Session
from ca22_pdf.db.base import Base, engine
from ca22_pdf.db.model import Transaction, Association, Categorie
from sqlalchemy import select

def init_base():
    Base.metadata.create_all(engine)

    cat_1 = Categorie(id_cat=1, libelle='parent')
    cat_2 = Categorie(id_cat=2, id_parent=1, libelle='child')

    session = Session(engine)
    session.bulk_save_objects([cat_1, cat_2])
    session.commit()
    session.close()

def test_categories():

    init_base()

    with Session(engine) as session:

        parent = session.execute(select(Categorie).where(Categorie.id_cat==1)).first()
        child = session.execute(select(Categorie).where(Categorie.id_cat==2)).first()
        
        assert parent[0].children[0].libelle == 'child'
        assert child[0].parent.libelle == 'parent'
