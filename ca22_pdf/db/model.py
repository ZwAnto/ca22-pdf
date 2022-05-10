from ca22_pdf.db.base import Base

from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, ForeignKeyConstraint
from sqlalchemy.orm import relationship, backref

class Transaction(Base):
    __tablename__ = 'transaction'
    
    op_num = Column(Integer, primary_key=True)
    date_ope = Column(Date())
    date_valeur = Column(Date())
    type = Column(String(50))
    libelle = Column(String(255))
    lib_clean = Column(String(255))
    libelle_ext = Column(String(255))
    debit = Column(Float)
    credit = Column(Float)
    source = Column(String(255), primary_key=True)

    def __repr__(self):
       return f"Transaction(op_num={self.op_num!r}, source={self.source!r}, libelle={self.libelle!r})"


class Categorie(Base):
    __tablename__ = 'categorie'

    id_cat = Column(Integer, primary_key=True)
    id_parent = Column(Integer, ForeignKey('categorie.id_cat'))
    libelle = Column(String(50))
    
    children = relationship("Categorie", backref=backref('parent', remote_side=[id_cat]))
    

class Association(Base):
    __tablename__ = 'association'

    id_cat = Column(Integer, ForeignKey('categorie.id_cat'),  primary_key=True)

    op_num = Column(Integer, primary_key=True)
    source = Column(Integer, primary_key=True)

    ass_cat = relationship("Categorie")
    ass_trx = relationship("Transaction")

    __table_args__ = tuple(ForeignKeyConstraint([op_num, source], ["transaction.op_num", "transaction.source"]))