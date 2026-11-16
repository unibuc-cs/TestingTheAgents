"""Where the adaptive method's result comes from, by offline replay: its stopping threshold swept, each ingredient
removed in turn, the calibration given fewer earlier changes to learn from, and the regressions on which the
shipped method, the method without any history and the method without the tests' own records differ. Takes a few
minutes.

    python scripts/analysis/method_ablations.py [recording]        # default runs/gemma7
"""

import random

import numpy as np
import pandas as pd
from replaylib import (
    CLEAN_STOPS,
    CachedAB,
    NoLift,
    NoRatio,
    PFailGreedy,
    leave_one_out,
    load,
    recording,
    replay,
    summary,
)

from traceeval.selection import SelectionContext
from traceeval.selection.adaptive_bayes import DEFAULT_REVEAL

pd.set_option("display.width", 250)

h, cat = load(recording())
variants = sorted(h.variants)
loo = leave_one_out(variants)


def no_history(_variant):
    return []


# ------------------------------------------------------------ 0. the report's numbers
summary(replay(h, cat, CachedAB(), variants, loo), "0. adaptive_bayes as shipped (the report's numbers)")

# ------------------------------------------------------------ 1. the stopping threshold
print("\n===== 1. eps_clean swept (the method's own dial), nominal budgets of 20% and 100%")
rows = []
for eps in (0.3, 0.2, 0.1, 0.05, 0.02, 0.01, 0.003, 0.001, 0.0):
    d = replay(h, cat, CachedAB(eps_clean=eps), variants, loo, budgets=(0.2, 1.0))
    for b, g in d.groupby("budget"):
        reg, other = g[g.is_regression], g[~g.is_regression]
        clean = g[g.stop_reason.isin(CLEAN_STOPS)]
        rows.append(
            {
                "eps": eps,
                "budget": b,
                "detect": reg.detected.mean(),
                "cost_reg": reg.cost_fraction.mean(),
                "cost_unrev": other.cost_fraction.mean(),
                "cost_all": g.cost_fraction.mean(),
                "clean_n": len(clean),
                "clean_wrong": clean.is_regression.mean() if len(clean) else float("nan"),
            }
        )
sweep = pd.DataFrame(rows).sort_values(["budget", "eps"], ascending=[True, False])
print(sweep.round(3).to_string(index=False), flush=True)

# ------------------------------------------------------------ 2. one ingredient removed at a time
print("\n===== 2. ablations (calibrated on the other changes unless said otherwise)")
summary(replay(h, cat, CachedAB(), variants, no_history), "no earlier change at all: default ratios, no records")
summary(replay(h, cat, NoLift(), variants, loo), "no per-test record (lift of 1), kind ratios calibrated")
summary(replay(h, cat, NoRatio(), variants, loo), "default kind ratios, per-test record kept")
summary(replay(h, cat, CachedAB(duplicate_discount=1.0), variants, loo), "no near-duplicate discount")
summary(replay(h, cat, CachedAB(risk_tilt=0.0), variants, loo), "no risk tilt")
summary(replay(h, cat, CachedAB(text="none"), variants, loo), "no text")
summary(replay(h, cat, CachedAB(text="tfidf"), variants, loo), "TF-IDF text")
summary(replay(h, cat, CachedAB(cover_mandatory=False), variants, loo), "no mandatory rule")
summary(replay(h, cat, PFailGreedy(), variants, loo), "policy: most likely new failure per token (no information gain)")

# ------------------------------------------------------------ 3. how much history the calibration needs
print("\n===== 3. calibrated on n earlier changes drawn at random (three draws), budgets of 20% and 100%")
rows = []
for n in (0, 3, 6, 12, 24, len(variants) - 1):
    for draw in range(3 if 0 < n < len(variants) - 1 else 1):
        rng = random.Random(100 * n + draw)

        def train_of(v, n=n, rng=rng):
            others = [x for x in variants if x != v]
            return sorted(rng.sample(others, n)) if n < len(others) else others

        d = replay(h, cat, CachedAB(), variants, train_of, budgets=(0.2, 1.0))
        for b, g in d.groupby("budget"):
            clean = g[g.stop_reason.isin(CLEAN_STOPS)]
            rows.append(
                {
                    "n_train": n,
                    "budget": b,
                    "detect": g[g.is_regression].detected.mean(),
                    "cost_all": g.cost_fraction.mean(),
                    "clean_wrong": clean.is_regression.mean() if len(clean) else float("nan"),
                }
            )
curve = pd.DataFrame(rows).groupby(["budget", "n_train"])[["detect", "cost_all", "clean_wrong"]]
print(curve.agg(["mean", "min", "max"]).round(3).to_string())

# ------------------------------------------------------------ 4. the regressions behind the differences
print("\n===== 4. regressions on which three versions differ at a 20% budget (share of the five seeds detected)")
runs = {
    "shipped": replay(h, cat, CachedAB(), variants, loo, budgets=(0.2,)),
    "no history": replay(h, cat, CachedAB(), variants, no_history, budgets=(0.2,)),
    "no record": replay(h, cat, NoLift(), variants, loo, budgets=(0.2,)),
}
per_change = pd.DataFrame({k: d[d.is_regression].groupby("variant").detected.mean() for k, d in runs.items()})
per_change["revealing"] = runs["shipped"][runs["shipped"].is_regression].groupby("variant").n_revealing.first()
differ = (per_change["shipped"] != per_change["no history"]) | (per_change["shipped"] != per_change["no record"])
print(per_change[differ].to_string())

example = "code_retry_drop_idempotency" if "code_retry_drop_idempotency" in variants else variants[0]
ctx = SelectionContext(h.changesets[example], cat, h, 1e9, random.Random(0), train_variants=loo(example))
ratios, record = CachedAB().calibrate(ctx)
print(f"\nreveal ratios calibrated without {example}, against the hand-set defaults:")
for kind in sorted(ratios):
    default = DEFAULT_REVEAL.get(kind, DEFAULT_REVEAL.get(kind.split(".", 1)[0], 0.2))
    print(f"  {kind:22s} calibrated {ratios[kind]:.3f}   default {default:.3f}")
lifts = [(revealed + 2) / (expected + 2) for revealed, expected in record.values()]
low, high, median = min(lifts), max(lifts), np.median(lifts)
print(f"lifts of the {len(lifts)} (test, kind) records: {low:.2f} to {high:.2f}, median {median:.2f}")
