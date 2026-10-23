"""Synthetic pharmacy data (replace with PostgreSQL later)."""
import random, datetime as dt
MEDS = [("Paracetamol 500mg", 1.2, 40), ("Amoxicillin 250mg", 4.5, 18), ("Metformin 500mg", 2.0, 25),
        ("Atorvastatin 10mg", 3.2, 15), ("Cetirizine 10mg", 1.0, 30), ("Omeprazole 20mg", 2.5, 22),
        ("Insulin Glargine", 420, 2), ("ORS Sachet", 0.8, 12)]

def build(today=None, seed=7):
    rnd = random.Random(seed); today = today or dt.date.today()
    meds, stock = {}, []
    for name, cost, daily in MEDS:
        profile = {
            "daily_mean": daily * rnd.uniform(0.8, 1.2),
            "weekly_amplitude": rnd.uniform(0.05, 0.22),
            "trend_per_day": rnd.uniform(-0.002, 0.003),
            "spike_probability": 0.025,
            "spike_factor": rnd.uniform(1.8, 3.5),
        }
        history = [
            _sample_demand(profile, day, rnd)
            for day in range(-41, 1)
        ]
        lead_days = rnd.randint(2, 7)
        meds[name] = dict(
            unit_cost=cost,
            lead_days=lead_days,
            history=history,
            synthetic_profile=profile,
        )

        total_qty = max(1, round(profile["daily_mean"] * rnd.uniform(12, 35)))
        batch_count = min(rnd.randint(1, 3), total_qty)
        remaining = total_qty
        for batch_index in range(batch_count):
            qty = remaining if batch_index == batch_count - 1 else rnd.randint(
                1, remaining - (batch_count - batch_index - 1)
            )
            remaining -= qty
            expiry_days = rnd.randint(15, 75) if rnd.random() < 0.12 else rnd.randint(120, 360)
            stock.append(dict(
                medicine=name,
                batch=f"B{seed:02d}{len(stock):04d}",
                qty=qty,
                expiry=(today + dt.timedelta(days=expiry_days)).isoformat(),
            ))
    return meds, stock


def _sample_demand(profile, day, rnd):
    weekly = 1 + profile["weekly_amplitude"] * (1 if day % 7 in (5, 6) else -0.5)
    mean = profile["daily_mean"] * max(0.5, 1 + profile["trend_per_day"] * day) * weekly
    if rnd.random() < profile["spike_probability"]:
        mean *= profile["spike_factor"]
    return max(0, round(rnd.gauss(mean, max(0.5, mean ** 0.5))))


def future_demand(med, horizon, seed):
    """Generate held-out demand from the synthetic process, independent of planning."""
    rnd = random.Random(seed)
    profile = med["synthetic_profile"]
    return [_sample_demand(profile, day, rnd) for day in range(1, horizon + 1)]
