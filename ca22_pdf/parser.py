import locale
import os
import re
from itertools import chain

import pandas as pd

locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")

TRESHOLD_DEBIT_CREDIT = 10

partial_date_op = re.compile("^ *([0-9]{2}.[0-9]{2}) +([0-9]{2}.[0-9]{2}) *$")
partial_lib_op = re.compile("^ +\W+(\w+) (.*) ((?:[0-9]{1,3} ){0,4}[0-9]{1,3},[0-9]{2})( +)¨$")
match_op = re.compile("^ *([0-9]{2}.[0-9]{2}) +([0-9]{2}.[0-9]{2})\W+(\w+).? (.*)  ((?:[0-9]{1,3} ){0,4}[0-9]{1,3},[0-9]{2})( +)¨$")

def generate_df_from_pdf(pdf_file):

    os.system(f'pdftotext -layout -x 20 -y 0 -W 600 -H 900 {pdf_file}')
    with open(pdf_file.with_suffix('.txt'), "r") as f:
        data = f.read()
    
    df = pd.DataFrame.from_dict({'text': data.split('\n')})

    # Suppression des lignes vides
    df = df[~df.text.str.match("^ *$")].reset_index()
    df.drop(columns='index', inplace = True)

    return df


def compute_flags(df):

    df['text_lwr'] = df.text.str.lower()

    df["is_ancien_solde"] = df.text_lwr.str.contains("ancien solde")
    df["is_nouveau_solde"] = df.text_lwr.str.contains("nouveau solde")
    df["is_total"] = df.text_lwr.str.contains("total des op.rations")
    df['is_lib'] = df.text_lwr.str.contains("libell. des op.rations")
    df['is_op_type'] = df.text_lwr.str.contains("op.[.] +valeur")
    df['is_heading'] = (df.is_op_type == True) & (df.is_op_type == df.shift().is_lib)
    df['is_page_end'] = df.text_lwr.str.contains("page [0-9]+ / [0-9]+")
    df['is_date'] = df.text_lwr.str.contains("date d'arr.t.")

    df['is_partial_date'] = df.text.str.match(partial_date_op)
    df['is_partial_lib'] = df.text.str.match(partial_lib_op)


def fix_multiline_transaction(df):

    idx_to_drop = []
    for i, r in df.iterrows():
        
        if r.is_partial_date and r.is_partial_date == df.loc[i+1, 'is_partial_lib']:
            df.loc[i, 'text'] += df.loc[i+1, 'text']
            df.loc[i, 'text_lwr'] += df.loc[i+1, 'text_lwr']

            idx_to_drop.append(i+1)
            
    df.drop(idx_to_drop, inplace = True)


def get_transaction_rows(df):

    # Flag des linges d'opérations
    df['is_operation'] = df.text.str.match(match_op)

    op_ranges = [range(i+1,j) for i,j in zip(df[df.is_ancien_solde].index, df[df.is_total].index)]
    inter_table_ranges = [range(i,j+1) for i,j in zip(df[df['is_page_end']].index[:-1], df[df['is_heading']].index[1:])]

    op_ranges = list(chain(*op_ranges))
    inter_table_ranges = list(chain(*inter_table_ranges))
    op_ranges = [i for i in op_ranges if i not in inter_table_ranges and i in df.index]

    return df.loc[op_ranges]


def parse_single_pdf(pdf_file):

    df = generate_df_from_pdf(pdf_file)

    # Ajout des flags
    compute_flags(df)

    # Recupération de la date
    date = df[df.is_date].text_lwr.str.strip().str.extract("date d'arr.t. *: *(.*)").values[0][0]
    date = pd.to_datetime(date, format="%d %B %Y")  

    # Correction des opérations sur plusieurs lignes
    fix_multiline_transaction(df)

    # Filtre sur les opérations
    operations = get_transaction_rows(df)

    # Récupération des libellé complémentaire
    operations['op_num'] = operations.is_operation.cumsum()
    operations = operations.groupby('op_num')
    operations_ext_labels = operations.apply(lambda x: ' | '.join(x.iloc[1:].text.str.strip())).to_frame("libelle_ext")
    operations = operations.apply(lambda x: x.head(1)).set_index("op_num")

    # Extraction des informations
    operations = operations.text.str.extract(match_op)

    # Extraction du débit/credit
    operations['is_debit'] = operations[5].str.len() > TRESHOLD_DEBIT_CREDIT
    operations.loc[operations.is_debit, "debit"] = operations[4]
    operations.loc[~operations.is_debit, "credit"] = operations[4]
    operations = operations.drop(columns= [4, 5, 'is_debit'])
    operations = operations.fillna("0")

    # Renomage des colonnes
    operations.columns = ['date_ope', 'date_valeur', 'type', 'libelle', 'debit', 'credit']

    # Mise en forme
    operations.libelle = operations.libelle.str.strip()
    operations.debit = operations.debit.str.replace(',','.').str.replace(' ','').astype('float')
    operations.credit = operations.credit.str.replace(',','.').str.replace(' ','').astype('float')
    operations['lib_clean'] = operations.libelle.str.replace('[0-9]{2}/[0-9]{2} *$', '', regex=True).str.strip()
    operations = operations.reset_index()

    # Ajout de l'année dans les champs de dates
    operations.date_ope = pd.to_datetime(operations.date_ope + '.' + str(date.year), format='%d.%m.%Y')
    operations.date_valeur = pd.to_datetime(operations.date_valeur + '.' + str(date.year), format='%d.%m.%Y')

    # Correction de l'année lorsque deux année dans le relevé
    minus = (operations.date_ope.dt.month < operations.shift().date_ope.dt.month).cumsum()
    operations.loc[minus == 0,"date_ope"] = operations.date_ope - pd.offsets.DateOffset(years=minus.max())

    minus = (operations.date_valeur.dt.month < operations.shift().date_valeur.dt.month).cumsum()
    operations.loc[minus == 0,"date_valeur"] = operations.date_valeur - pd.offsets.DateOffset(years=minus.max())

    operations.date_ope = operations.date_ope.dt.date
    operations.date_valeur = operations.date_valeur.dt.date

    # Ajoute des libellé complémentaires
    operations = operations.merge(operations_ext_labels, on='op_num')

    # Ajout de la source
    operations['source'] = pdf_file.name

    # Vérification avec le montant total
    debit = operations.debit.sum().round(2)
    credit = operations.credit.sum().round(2)

    if debit == 0 or credit == 0:
        verif = df[df.is_total].text_lwr.str.strip().str.extract("((?:[0-9]{1,3} ){0,4}[0-9]{1,3},[0-9]{2})")
        verif = verif.apply(lambda x: float(x.str.replace(',', '.').str.replace(' ','')))

        assert verif[0] == debit + credit

    else:

        verif = df[df.is_total].text_lwr.str.strip().str.extract("((?:[0-9]{1,3} ){0,4}[0-9]{1,3},[0-9]{2}) +((?:[0-9]{1,3} ){0,4}[0-9]{1,3},[0-9]{2})")
        verif = verif.apply(lambda x: float(x.str.replace(',', '.').str.replace(' ','')))

        assert verif[0] == debit
        assert verif[1] == credit

    return operations
