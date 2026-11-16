"""The shape of the benchmark behind a recording's results: the suite by kind of test, how many tests reveal each
regression and how many regressions rest on a single test, the cheapest revealing test per regression (what an
oracle would spend), how many hypotheses the adaptive method reasons about per change, and how selective the
dependencies observed in traces are.

    python scripts/analysis/benchmark_structure.py [recording]     # default runs/gemma7
"""

from collections import Counter

import numpy as np
import pandas as pd
from replaylib import load, recording

from traceeval.selection.base import weighted_affinity

pd.set_option("display.width", 250)
h, cat = load(recording())
variants, tests, full = sorted(h.variants), h.test_ids(), h.total_cost()
revealing = {v: h.revealing_tests(v) for v in variants}
regressions = [v for v in variants if revealing[v]]


def kind(test):
    case = cat[test]
    return "dataset item" if case.dataset else ("workflow" if case.workflow else "scenario")


suite = pd.DataFrame(
    {
        "test": tests,
        "kind": [kind(t) for t in tests],
        "cost": [h.cost(t) for t in tests],
        "passes": [h.baseline_pass_rate(t) >= 0.5 for t in tests],
        "reveals": [sum(t in revealing[v] for v in regressions) for t in tests],
    }
)
print("the suite by kind of test")
print(
    suite.groupby("kind")
    .agg(
        tests=("test", "count"),
        token_share=("cost", lambda x: x.sum() / full),
        mean_tokens=("cost", "mean"),
        reveal_a_change=("reveals", lambda x: int((x > 0).sum())),
        fail_on_the_original=("passes", lambda x: int((~x).sum())),
    )
    .round(3)
    .to_string()
)
never = suite[suite.reveals == 0]
print(
    f"\ntests that reveal no change: {len(never)} of {len(suite)} ({never.cost.sum() / full:.0%} of the suite's tokens)"
)
print(f"most expensive test over the cheapest: {suite.cost.max() / suite.cost.min():.0f} times")

sizes = Counter(len(revealing[v]) for v in regressions)
print(f"\nrevealing tests per regression ({len(regressions)} regressions): {dict(sorted(sizes.items()))}")
single = Counter(next(iter(revealing[v])) for v in regressions if len(revealing[v]) == 1)
print(f"regressions one test reveals: {sum(single.values())}, resting on {dict(single)}")
print("regressions at most three tests reveal:", sum(1 for v in regressions if len(revealing[v]) <= 3))
pairs = Counter(kind(t) for v in regressions for t in revealing[v])
print("revealing (change, test) pairs by kind of test:", dict(pairs))

cheapest = [min(h.cost(t) for t in revealing[v]) / full for v in regressions]
print(
    f"\ncheapest revealing test per regression: mean {np.mean(cheapest):.4f} of the suite, max {np.max(cheapest):.4f}"
)

disagree = total = 0
for v in variants:
    for stats in h.variants[v].values():
        runs = stats.valid_runs
        if runs:
            total += 1
            disagree += 0 < sum(r["passed"] for r in runs) < len(runs)
print(f"(change, test) pairs whose runs disagree: {disagree} of {total}")

hypotheses = Counter(
    len({c.id for c in h.changesets[v].components if c.kind not in ("tool", "line")}) for v in variants
)
print("hypotheses per change in the adaptive method (tool: and line: ids folded):", dict(sorted(hypotheses.items())))

rows = []
for v in regressions:
    selected = {t for t in tests if weighted_affinity(h.changesets[v], h.baseline[t].dep_frequency) > 0}
    rows.append(
        {
            "selected": len(selected),
            "revealing": len(revealing[v]),
            "share_revealing": len(revealing[v] & selected) / max(1, len(selected)),
            "cost": sum(h.cost(t) for t in selected) / full,
        }
    )
observed = pd.DataFrame(rows)
print("\nthe tests whose traces touched a regression (the observed selection)")
print(observed.describe().loc[["mean", "50%", "min", "max"]].round(3).to_string())
print("regressions for which that selection is 150 tests or more:", int((observed.selected >= 150).sum()))
