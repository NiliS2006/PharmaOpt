from typing import List
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from . import db, engine, llm, invoice

db.init()
app = FastAPI(title="PharmaOpt API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class Chat(BaseModel): question: str
class Sim(BaseModel): medicine: str; buy_qty: int = 0; delay_days: int = 0
class Text(BaseModel): text: str
class Row(BaseModel): medicine: str; batch: str; qty: int; expiry: str; matched: bool = True

@app.get("/api/health")
def health(): return {"ok": True}
@app.get("/api/inventory")
def inventory():
    meds, stock = db.load(); return dict(items=engine.analyze(meds, stock), batches=stock)
@app.get("/api/recommendations")
def recs(budget: float = 1000):
    meds, stock = db.load(); return engine.recommend(meds, stock, budget)
@app.post("/api/simulate")
def sim(s: Sim):
    m, st = db.load()
    return [engine.simulate(m, st, s.medicine, 0, 0), engine.simulate(m, st, s.medicine, s.buy_qty, 0),
            engine.simulate(m, st, s.medicine, s.buy_qty, s.delay_days)]
@app.post("/api/chat")
def chat(c: Chat):
    m, st = db.load(); intent, facts = llm.facts_for(c.question, m, st)
    return dict(intent=intent, answer=llm.explain(c.question, intent, facts), evidence=facts)
@app.post("/api/invoice/parse")
def inv_parse(t: Text): return invoice.parse(t.text, db.load()[0])
@app.post("/api/invoice/upload")
async def inv_upload(file: UploadFile = File(...)):
    return invoice.parse(invoice.read_text(await file.read(), file.filename or ""), db.load()[0])
@app.post("/api/invoice/confirm")
def inv_confirm(rows: List[Row]):
    db.add_batches([r.model_dump(exclude={"matched"}) for r in rows if r.matched]); return {"added": len(rows)}
