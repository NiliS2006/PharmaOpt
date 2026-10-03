"""Synthetic pharmacy data (replace with PostgreSQL later)."""
import random, datetime as dt
MEDS = [("Paracetamol 500mg", 1.2, 40), ("Amoxicillin 250mg", 4.5, 18), ("Metformin 500mg", 2.0, 25),
        ("Atorvastatin 10mg", 3.2, 15), ("Cetirizine 10mg", 1.0, 30), ("Omeprazole 20mg", 2.5, 22),
        ("Insulin Glargine", 420, 2), ("ORS Sachet", 0.8, 12)]

def build(today=None, seed=7):
    rnd = random.Random(seed); today = today or dt.date.today()
    meds, stock = {}, []
    for name, cost, daily in MEDS:
        hist = [max(0, round(rnd.gauss(daily, daily * 0.25))) for _ in range(30)]
        meds[name] = dict(unit_cost=cost, lead_days=rnd.randint(2, 7), history=hist)
        for _ in range(rnd.randint(1, 3)):
            stock.append(dict(medicine=name, batch=f"B{rnd.randint(100, 999)}", qty=rnd.randint(20, 400),
                              expiry=(today + dt.timedelta(days=rnd.randint(10, 240))).isoformat()))
    return meds, stock
