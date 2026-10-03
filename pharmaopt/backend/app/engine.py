"""Deterministic analytics: forecast, FEFO risk, budget optimizer, what-if simulator. No LLM here."""
import datetime as dt
SAFETY_DAYS, COVER_DAYS = 3, 21

def forecast(m):  # mean daily demand of last 14 days
    h = m["history"][-14:]; return sum(h) / len(h)

def batches_of(stock, name):
    return sorted([b for b in stock if b["medicine"] == name], key=lambda b: b["expiry"])

def analyze(meds, stock, today=None):
    today = today or dt.date.today(); rows = []
    for n, m in meds.items():
        d, used, waste, total = forecast(m), 0.0, 0, 0
        for b in batches_of(stock, n):  # FEFO: earliest expiry sold first
            days = (dt.date.fromisoformat(b["expiry"]) - today).days
            sold = min(b["qty"], max(0.0, d * days - used)); used += sold
            waste += round(b["qty"] - sold); total += b["qty"]
        cover = total / d if d else 999
        status = "stockout" if cover < m["lead_days"] + SAFETY_DAYS else ("expiry" if waste > 0.15 * total else "ok")
        rows.append(dict(medicine=n, daily_demand=round(d, 1), in_stock=total, days_cover=round(cover, 1),
                         at_risk_of_expiry=waste, lead_days=m["lead_days"], unit_cost=m["unit_cost"], status=status))
    return rows

def recommend(meds, stock, budget, today=None):
    """Two passes so one medicine can't eat the budget: first a minimum safe cover for every urgent line, then top-ups."""
    rows = {r["medicine"]: r for r in analyze(meds, stock, today)}; left, got = budget, {}
    def need(r, days): return max(0, round(r["daily_demand"] * days - (r["in_stock"] - r["at_risk_of_expiry"])))
    for days_of in (lambda r: r["lead_days"] + SAFETY_DAYS + 4, lambda r: r["lead_days"] + COVER_DAYS):
        for r in sorted(rows.values(), key=lambda r: r["days_cover"]):
            if r["status"] == "expiry": continue  # never add stock to an overstocked line
            qty = min(need(r, days_of(r)) - got.get(r["medicine"], 0), int(left // r["unit_cost"]))
            if qty > 0: left -= qty * r["unit_cost"]; got[r["medicine"]] = got.get(r["medicine"], 0) + qty
    plan = []
    for n, q in got.items():
        r = rows[n]; limited = q < need(r, r["lead_days"] + COVER_DAYS)
        plan.append(dict(medicine=n, order_qty=q, cost=round(q * r["unit_cost"], 2), reason=(
            f"Cover is {r['days_cover']} days vs a {r['lead_days']}-day supplier lead time; forecast {r['daily_demand']}/day."
            + (" Limited by your budget." if limited else ""))))
    return dict(budget=budget, spent=round(budget - left, 2), orders=sorted(plan, key=lambda o: rows[o["medicine"]]["days_cover"]))

def simulate(meds, stock, name, buy_qty=0, delay=0, horizon=60, today=None):
    today = today or dt.date.today(); m = meds[name]; d = forecast(m)
    bs = [[dt.date.fromisoformat(b["expiry"]), b["qty"], 0] for b in batches_of(stock, name)]
    if buy_qty: bs.append([today + dt.timedelta(days=horizon + 365), buy_qty, m["lead_days"] + delay])
    waste = short = stockout_days = 0
    for day in range(horizon):
        for b in bs:
            if b[0] <= today + dt.timedelta(days=day) and b[1] > 0 and b[2] <= day: waste += b[1]; b[1] = 0
        need = d
        for b in sorted(bs, key=lambda b: b[0]):
            if b[2] <= day and b[1] > 0 and need > 0: t = min(b[1], need); b[1] -= t; need -= t
        if need > 0.5: short += need; stockout_days += 1
    return dict(medicine=name, buy_qty=buy_qty, delay_days=delay, expired_units=round(waste),
                unmet_demand_units=round(short), stockout_days=stockout_days, spend=round(buy_qty * m["unit_cost"], 2))
