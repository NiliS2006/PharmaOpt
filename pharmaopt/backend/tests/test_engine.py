import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app import data, engine
def test_plan_respects_budget():
    meds, stock = data.build()
    assert engine.recommend(meds, stock, 500)["spent"] <= 500
def test_buying_reduces_stockouts():
    meds, stock = data.build(); n = next(iter(meds))
    assert engine.simulate(meds, stock, n, 5000)["stockout_days"] <= engine.simulate(meds, stock, n)["stockout_days"]
