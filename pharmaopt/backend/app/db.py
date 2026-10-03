"""Persistence: PostgreSQL via DATABASE_URL, SQLite fallback for local dev."""
import os, json
from sqlalchemy import create_engine, Column, Integer, String, Float, Text
from sqlalchemy.orm import declarative_base, Session
from . import data

URL = os.getenv("DATABASE_URL", "sqlite:///pharmaopt.db").replace("postgres://", "postgresql://", 1)
eng = create_engine(URL); Base = declarative_base()

class Med(Base):
    __tablename__ = "meds"
    name = Column(String, primary_key=True); unit_cost = Column(Float); lead_days = Column(Integer); history = Column(Text)
class Batch(Base):
    __tablename__ = "batches"
    id = Column(Integer, primary_key=True); medicine = Column(String); batch = Column(String); qty = Column(Integer); expiry = Column(String)

def init():
    Base.metadata.create_all(eng)
    with Session(eng) as s:
        if not s.query(Med).count():
            meds, stock = data.build()
            s.add_all([Med(name=n, unit_cost=m["unit_cost"], lead_days=m["lead_days"], history=json.dumps(m["history"])) for n, m in meds.items()])
            s.add_all([Batch(**b) for b in stock]); s.commit()

def load():
    with Session(eng) as s:
        meds = {m.name: dict(unit_cost=m.unit_cost, lead_days=m.lead_days, history=json.loads(m.history)) for m in s.query(Med)}
        stock = [dict(medicine=b.medicine, batch=b.batch, qty=b.qty, expiry=b.expiry) for b in s.query(Batch)]
    return meds, stock

def add_batches(rows):
    with Session(eng) as s: s.add_all([Batch(**r) for r in rows]); s.commit()
