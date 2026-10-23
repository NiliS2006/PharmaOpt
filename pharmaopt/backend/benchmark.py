"""Evaluate inventory plans against held-out stochastic demand. Run: python benchmark.py"""
import datetime as dt
import math
import statistics as st
import sys
from pathlib import Path

from app import data, engine

HORIZON = 90
SEEDS = 100
BUDGETS = (300, 800, 2000)
METHODS = ("PharmaOpt", "Reorder point (s,S)", "Order-up-to 30 days")


def _budgeted_plan(meds, stock, budget, target_days, reorder_days=None):
    rows = {row["medicine"]: row for row in engine.analyze(meds, stock)}
    orders, remaining = {}, budget
    for row in sorted(rows.values(), key=lambda item: item["days_cover"]):
        if reorder_days is not None and row["days_cover"] >= row["lead_days"] + reorder_days:
            continue
        usable = max(0, row["in_stock"] - row["at_risk_of_expiry"])
        qty = max(0, round(row["daily_demand"] * target_days(row) - usable))
        qty = min(qty, int(remaining // row["unit_cost"]))
        if qty:
            orders[row["medicine"]] = qty
            remaining -= qty * row["unit_cost"]
    return orders


def plans_for(meds, stock, budget):
    optimizer = {
        order["medicine"]: order["order_qty"]
        for order in engine.recommend(meds, stock, budget)["orders"]
    }
    reorder_point = _budgeted_plan(
        meds, stock, budget,
        lambda row: row["lead_days"] + 30,
        reorder_days=7,
    )
    order_up_to = _budgeted_plan(meds, stock, budget, lambda _row: 30)
    return {
        "PharmaOpt": optimizer,
        "Reorder point (s,S)": reorder_point,
        "Order-up-to 30 days": order_up_to,
    }


def simulate_actual(med, batches, buy_qty, actual_demand, today):
    inventory = [
        [dt.date.fromisoformat(batch["expiry"]), batch["qty"], 0]
        for batch in batches
    ]
    if buy_qty:
        inventory.append([
            today + dt.timedelta(days=HORIZON + 365),
            buy_qty,
            med["lead_days"],
        ])
    expired = unmet = demand_total = stockout_days = 0
    for day, demand in enumerate(actual_demand):
        date = today + dt.timedelta(days=day)
        for batch in inventory:
            if batch[0] <= date and batch[1] > 0 and batch[2] <= day:
                expired += batch[1]
                batch[1] = 0
        remaining = demand
        for batch in sorted(inventory, key=lambda item: item[0]):
            if batch[2] <= day and batch[1] > 0 and remaining > 0:
                used = min(batch[1], remaining)
                batch[1] -= used
                remaining -= used
        demand_total += demand
        unmet += remaining
        stockout_days += remaining > 0
    return demand_total, unmet, expired, stockout_days


def score(meds, stock, plan, seed, today):
    totals = {"demand": 0, "unmet": 0, "expired": 0, "stockout_days": 0,
              "lost_value": 0.0, "expiry_value": 0.0}
    for index, (name, med) in enumerate(meds.items()):
        batches = [batch for batch in stock if batch["medicine"] == name]
        demand = data.future_demand(med, HORIZON, seed * 100 + index)
        demand_total, unmet, expired, stockout_days = simulate_actual(
            med, batches, plan.get(name, 0), demand, today
        )
        totals["demand"] += demand_total
        totals["unmet"] += unmet
        totals["expired"] += expired
        totals["stockout_days"] += stockout_days
        totals["lost_value"] += unmet * med["unit_cost"]
        totals["expiry_value"] += expired * med["unit_cost"]
    totals["fill_rate"] = 1 - totals["unmet"] / totals["demand"] if totals["demand"] else 1
    return totals


def confidence_interval(values):
    mean = st.mean(values)
    if len(values) < 2:
        return mean, mean, mean
    margin = 1.96 * st.stdev(values) / math.sqrt(len(values))
    return mean, max(0, mean - margin), mean + margin


def format_ci(values, decimals=1):
    mean, low, high = confidence_interval(values)
    return f"{mean:.{decimals}f} [{low:.{decimals}f}, {high:.{decimals}f}]"


def run():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    today = dt.date(2026, 1, 1)
    results = {(budget, method): [] for budget in BUDGETS for method in METHODS}
    for seed in range(SEEDS):
        meds, stock = data.build(today=today, seed=seed)
        for budget in BUDGETS:
            for method, plan in plans_for(meds, stock, budget).items():
                results[(budget, method)].append(score(meds, stock, plan, seed, today))

    lines = [
        "| Budget (₹) | Method | Fill rate (%) | Lost demand (units) | Stockout medicine-days | Expired units | Lost-sales value (₹)* | Expiry value (₹) |",
        "|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for budget in BUDGETS:
        for method in METHODS:
            rows = results[(budget, method)]
            lines.append(
                f"| {budget} | {method} | "
                f"{format_ci([row['fill_rate'] * 100 for row in rows], 2)} | "
                f"{format_ci([row['unmet'] for row in rows])} | "
                f"{format_ci([row['stockout_days'] for row in rows])} | "
                f"{format_ci([row['expired'] for row in rows])} | "
                f"{format_ci([row['lost_value'] for row in rows])} | "
                f"{format_ci([row['expiry_value'] for row in rows])} |"
            )

    report = (
        "# Held-out synthetic benchmark\n\n"
        f"Generated by `backend/benchmark.py`: {SEEDS} independently seeded synthetic pharmacies "
        f"per budget, {HORIZON}-day evaluation horizon, and 95% normal confidence intervals "
        "across pharmacies. The planning engine sees only each pharmacy's 42-day sales history "
        "and current stock. Evaluation uses a separate stochastic demand path with weekly "
        "variation, trend, random demand noise, and occasional spikes; the future path is not "
        "used to make the plan.\n\n"
        "Opening stock is generated as 12–35 days of each item's own demand, split into dated "
        "batches. A minority of batches have near-term expiry. Items have item-specific costs, "
        "lead times, and demand levels. Orders arrive after supplier lead time; all methods use "
        "the same FEFO/lost-sales simulation and ₹ budget cap. Each plan places one order at the "
        "start; there is no replenishment or reforecast during the horizon. Baselines are a "
        "reorder-point (s,S) rule and an order-up-to-30-days rule. Results are averages per pharmacy; intervals "
        "are 95% confidence intervals for those means. Stockout medicine-days sums the number "
        "of days each medicine had unmet demand. The unchanged expiry totals reflect current "
        "batches expiring independently of the one-time order decision; the 90-day trial does "
        "not establish that any method reduces expiry.\n\n"
        "*Lost-sales value is unmet units multiplied by acquisition unit cost: a comparable "
        "proxy, not measured retail revenue or profit. Expiry value is expired units multiplied "
        "by acquisition cost. No real pharmacy data is included; this benchmark supports "
        "synthetic comparisons only and is not evidence of real-world impact.*\n\n"
        + "\n".join(lines)
        + "\n\nInterpretation: compare methods within a budget, including their uncertainty "
        "intervals. Do not claim PharmaOpt wins where the measured metrics do not support it.\n"
    )
    print(report)
    destination = Path(__file__).resolve().parents[1] / "docs" / "benchmark.md"
    destination.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    run()
