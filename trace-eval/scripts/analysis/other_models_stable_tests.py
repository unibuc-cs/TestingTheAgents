"""A second model from a recording whose ground truth is not clean: leave out the tests that carry the run-to-run
variation (those that "reveal" one of the benign changes, and those whose own baseline runs disagree), take the
ground truth over the remaining tests, and replay every strategy on them. Indicative only: the unstable tests are
found from the same recording.

    python scripts/analysis/other_models_stable_tests.py [recording]       # default runs/qwen7
"""

import pandas as pd
from replaylib import CachedAB, leave_one_out, load, recording, replay

from traceeval.selection import CORE, get_strategy

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_rows", 400)
STRATEGIES = list(CORE)  # the report's default comparison

h, catalog = load(recording("runs/qwen7"))
meta = h.mutation_meta
variants = sorted(h.variants)
benign = [v for v in variants if meta[v]["category"] == "benign"]
noisy = set().union(*(h.revealing_tests(v) for v in benign))
unsettled = {t for t, stats in h.baseline.items() if len({r["passed"] for r in stats.valid_runs}) > 1}
dropped = noisy | unsettled
print("tests failing on the original app:", sorted(t for t in h.baseline if h.baseline_pass_rate(t) < 0.5))
print(f"tests that 'reveal' a benign change: {len(noisy)} {sorted(noisy)}")
print(f"tests whose baseline runs disagree: {len(unsettled)} {sorted(unsettled)}")


class Stable:
    """The recording with the ground truth taken over the stable tests only."""

    def __init__(self, history, left_out):
        self._history, self._left_out = history, left_out

    def __getattr__(self, name):
        return getattr(self._history, name)

    def revealing_tests(self, variant, threshold=0.5):
        return self._history.revealing_tests(variant, threshold) - self._left_out


stable = Stable(h, dropped)
kept = {t: case for t, case in catalog.items() if t not in dropped}
revealed = {v: len(stable.revealing_tests(v)) for v in variants}
print(
    f"changes a stable test reveals: {sum(n > 0 for n in revealed.values())} of {len(variants)}; "
    f"labelled regressions among them: {sum(revealed[v] > 0 for v in variants if meta[v]['expected_regression'])}; "
    f"benign among them: {sum(revealed[v] > 0 for v in benign)}"
)

runs = []
for name in STRATEGIES:
    strategy = CachedAB() if name == "adaptive_bayes" else get_strategy(name)  # the same method, its model kept
    d = replay(stable, kept, strategy, variants, leave_one_out(variants))
    d["strategy"] = name
    runs.append(d)
table = pd.concat(runs)
# as in the report: detection over the changes a (stable) test reveals, tokens as a mean over all changes
found = table[table.is_regression]
print("\ndetection, stable tests only")
print(found.pivot_table(index="strategy", columns="budget", values="detected").reindex(STRATEGIES).round(3))
print("\ntokens spent, mean over all changes")
print(table.pivot_table(index="strategy", columns="budget", values="cost_fraction").reindex(STRATEGIES).round(3))
adaptive = table[table.strategy == "adaptive_bayes"]
print("\nadaptive_bayes stop reasons")
print(pd.crosstab([adaptive.budget, adaptive.is_regression], adaptive.stop_reason))
false_verdicts = int(((~adaptive.is_regression) & (adaptive.stop_reason == "regression")).sum())
print(
    f"regression verdicts on changes no stable test reveals: {false_verdicts} of {int((~adaptive.is_regression).sum())}"
)
