"""Compare PharmaOpt's plan with a typical reorder-point rule on synthetic pharmacies. Run: python benchmark.py"""
import statistics as st
from app import data, engine

def baseline(meds, stock, budget):  # refill low lines to 30 days in list order; no urgency ranking or expiry awareness
    left, got = budget, {}
    for r in engine.analyze(meds, stock):
        if r["days_cover"] < r["lead_days"] + engine.SAFETY_DAYS + 7:
            q = min(round(r["daily_demand"] * 30), int(left // r["unit_cost"])); left -= q * r["unit_cost"]; got[r["medicine"]] = q
    return got

def score(meds, stock, got):
    o = [engine.simulate(meds, stock, n, got.get(n, 0)) for n in meds]
    return sum(x["stockout_days"] for x in o), sum(x["unmet_demand_units"] for x in o), sum(x["expired_units"] for x in o)

lines = ["| Budget | Method | Stockout days | Unmet demand (units) | Expired units |", "|---|---|---|---|---|"]
for budget in (300, 800, 2000):
    res = {"Reorder-point rule": [], "PharmaOpt": []}
    for seed in range(50):
        meds, stock = data.build(seed=seed)
        res["Reorder-point rule"].append(score(meds, stock, baseline(meds, stock, budget)))
        plan = {o["medicine"]: o["order_qty"] for o in engine.recommend(meds, stock, budget)["orders"]}
        res["PharmaOpt"].append(score(meds, stock, plan))
    for k, v in res.items(): lines.append(f"| {budget} | {k} | " + " | ".join(f"{st.mean(c):.1f}" for c in zip(*v)) + " |")
out = "\n".join(lines); print(out)
open("../docs/benchmark.md", "w").write("# Benchmark (50 synthetic pharmacies per budget, 60-day horizon, lower is better)\n\n" + out + "\n")
