"""Detection against tokens on a finer grid of budget caps than the report's, for the orders of the registered
strategies and for three two-line orders that combine the traced dependencies with the text similarity. Every
order runs under the two rules of a run (``selection/base.py``): the tests the model already fails on the original
app are left out, and the run ends at the first failure. Outcomes are each test's majority over its recorded runs.
The adaptive method is printed last, for comparison.

    python scripts/analysis/stop_rule_frontier.py [recording] [--keep-red]   # --keep-red: run the red tests too
"""

import random
import sys

import numpy as np
import pandas as pd
from replaylib import CachedAB, leave_one_out, load, majority_outcome, replay

from traceeval.selection import SelectionContext, get_strategy
from traceeval.selection.base import weighted_affinity
from traceeval.selection.strategies import tfidf_relevance

pd.set_option("display.width", 250)
CAPS = (0.01, 0.02, 0.03, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0)
REGISTERED = ("declared", "observed", "observed_diverse", "cost_aware", "ir_tfidf", "history_ml")

args = [a for a in sys.argv[1:] if not a.startswith("--")]
keep_red = "--keep-red" in sys.argv
h, cat = load(args[0] if args else "runs/gemma7")
variants, tests, full = sorted(h.variants), h.test_ids(), h.total_cost()
revealing = {v: h.revealing_tests(v) for v in variants}
passes = {t: h.baseline_pass_rate(t) >= 0.5 for t in tests}
cost = {t: max(1.0, h.cost(t)) for t in tests}


def context(v):
    return SelectionContext(
        h.changesets[v], cat, h, float("inf"), random.Random(0), train_variants=leave_one_out(variants)(v), options={}
    )


def simple_order(kind, v):
    """Three orders that need no model of the outcomes: the text similarity of ``ir_tfidf`` and whether the test's
    traces touched the change, combined."""
    rel = tfidf_relevance(context(v))
    traced = {t: weighted_affinity(h.changesets[v], h.baseline[t].dep_frequency) > 0 for t in tests}
    if kind == "traced only, by text":
        return sorted((t for t in tests if traced[t]), key=lambda t: (-rel[t], cost[t]))
    if kind == "traced first, by text":
        return sorted(tests, key=lambda t: (not traced[t], -rel[t], cost[t]))
    return sorted(tests, key=lambda t: -(rel[t] + 0.02) * (1 + traced[t]) / cost[t] ** 0.5)  # text x traced per token


def frontier(name, order_of):
    """For each cap: the order run greedily (a test that does not fit is skipped), stopped at the first failure of
    a test that passes on the original app."""
    orders = {v: order_of(v) for v in variants}
    rows = []
    for cap in CAPS:
        found_any, spent_reg, spent_other = [], [], []
        for v in variants:
            remaining, spent, found = cap * full, 0.0, False
            for t in orders[v]:
                if cost[t] > remaining or not (passes[t] or keep_red):
                    continue
                ok, tokens = majority_outcome(h, v, t)
                spent += tokens
                remaining -= tokens
                if not ok and passes[t]:
                    found = True
                    break
                if remaining <= 0:
                    break
            if revealing[v]:
                found_any.append(found)
                spent_reg.append(spent / full)
            else:
                spent_other.append(spent / full)
        rows.append(
            {
                "order": name,
                "cap": cap,
                "detect": np.mean(found_any),
                "cost_all": (sum(spent_reg) + sum(spent_other)) / len(variants),
            }
        )
    return rows


rows = []
for name in REGISTERED:
    strategy = get_strategy(name)
    rows += frontier(name, lambda v, strategy=strategy: strategy.order(context(v)))
for kind in ("traced only, by text", "traced first, by text", "text x traced per token"):
    rows += frontier(kind, lambda v, kind=kind: simple_order(kind, v))
table = pd.DataFrame(rows)
order = list(dict.fromkeys(table.order))
print(f"\nthe tests the model already fails on the original app are {'run' if keep_red else 'skipped'}")
print("\ndetection of the revealed regressions, every order stopped at the first new failure, by budget cap")
print(table.pivot(index="cap", columns="order", values="detect")[order].round(3).to_string())
print("\ntokens spent, mean over all changes (share of the suite)")
print(table.pivot(index="cap", columns="order", values="cost_all")[order].round(3).to_string())

shipped = replay(h, cat, CachedAB(), variants, leave_one_out(variants))
print("\nadaptive_bayes as shipped, by nominal budget")
print(
    shipped.groupby("budget")
    .apply(lambda g: pd.Series({"detect": g[g.is_regression].detected.mean(), "cost_all": g.cost_fraction.mean()}))
    .round(3)
    .to_string()
)
