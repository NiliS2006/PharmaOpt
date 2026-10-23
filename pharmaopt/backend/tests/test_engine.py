import sys, pathlib, datetime as dt; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app import data, engine
def test_plan_respects_budget():
    meds, stock = data.build()
    assert engine.recommend(meds, stock, 500)["spent"] <= 500
def test_buying_reduces_stockouts():
    meds, stock = data.build(); n = next(iter(meds))
    assert engine.simulate(meds, stock, n, 5000)["stockout_days"] <= engine.simulate(meds, stock, n)["stockout_days"]

def test_synthetic_stock_is_scaled_to_each_medicine_demand():
    meds, stock = data.build(today=dt.date(2026, 1, 1), seed=18)
    for name, medicine in meds.items():
        quantity = sum(batch["qty"] for batch in stock if batch["medicine"] == name)
        cover = quantity / medicine["synthetic_profile"]["daily_mean"]
        assert 11.5 <= cover <= 35.5

def test_future_demand_is_seeded_and_not_the_forecast():
    meds, _ = data.build(seed=18)
    name = next(iter(meds))
    first = data.future_demand(meds[name], 30, seed=99)
    assert first == data.future_demand(meds[name], 30, seed=99)
    assert first != data.future_demand(meds[name], 30, seed=100)
    assert first != [engine.forecast(meds[name])] * 30
