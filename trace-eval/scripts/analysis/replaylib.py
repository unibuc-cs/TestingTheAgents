"""Shared helpers of the analysis scripts: load a recording, replay a strategy offline exactly as the evaluator
does (``experiment/evaluate.py``: same context, same oracle, same seeds), and variants of the adaptive method with
one ingredient changed. Nothing here writes to a recording."""

import random
import sys
import time

import numpy as np
import pandas as pd

from traceeval.catalog import load_catalog
from traceeval.experiment.evaluate import make_oracle
from traceeval.experiment.history import History
from traceeval.experiment.metrics import evaluate_log
from traceeval.experiment.report import CLEAN_STOPS
from traceeval.selection import SelectionContext
from traceeval.selection.adaptive_bayes import DEFAULT_REVEAL, AdaptiveBayes

BUDGETS = (0.02, 0.05, 0.1, 0.2, 0.5, 1.0)


def recording(default: str = "runs/gemma8") -> str:
    """The recording a script works on: its first argument, or ``default``."""
    return sys.argv[1] if len(sys.argv) > 1 else default


def load(workdir):
    """The recording at ``workdir`` and the catalog, as (history, {test id: case})."""
    t0 = time.time()
    history = History.load(workdir)
    catalog = {c.id: c for c in load_catalog()}
    tests, variants = len(history.baseline), len(history.variants)
    print(f"[loaded {workdir}: {tests} tests, {variants} variants, {time.time() - t0:.0f} s]", flush=True)
    return history, catalog


def leave_one_out(variants):
    """The evaluator's training rule: every recorded change but the one under test."""
    return lambda v: [x for x in variants if x != v]


def majority_outcome(history, variant: str, test: str) -> tuple[bool, float]:
    """The majority outcome of ``test`` on ``variant`` and its mean cost there (the baseline's when the variant has
    no valid run of it, as ``History.variant_pass_rate`` does)."""
    stats = history.variants[variant].get(test)
    runs = stats.valid_runs if stats and stats.valid_runs else history.baseline[test].valid_runs
    return sum(r["passed"] for r in runs) / len(runs) >= 0.5, float(np.mean([r["tokens"] for r in runs]))


class CachedAB(AdaptiveBayes):
    """The adaptive method with its outcome-independent model computed once per (change, training set), so that a
    sweep over budgets and seeds does not recompute it."""

    def __init__(self, label="adaptive_bayes", **settings):
        super().__init__(**settings)
        self.name = label
        self._memo = {}

    def model(self, ctx):
        key = (ctx.change.variant, tuple(ctx.train_variants))
        if key not in self._memo:
            self._memo[key] = super().model(ctx)
        model = dict(self._memo[key])
        model["S"] = model["S"].copy()  # run() discounts rows of S in place
        return model


class NoLift(CachedAB):
    """Kind-level reveal ratios only: every test's own record is ignored (a lift of 1)."""

    def calibrate(self, ctx):
        ratios, _record = super().calibrate(ctx)
        return ratios, {}


class NoRatio(CachedAB):
    """The hand-set default reveal ratios (no calibration of the kinds), the tests' own records kept."""

    def calibrate(self, ctx):
        _ratios, record = super().calibrate(ctx)
        return dict(DEFAULT_REVEAL), record


class PFailGreedy(CachedAB):
    """The same model with a simpler policy: the test most likely to newly fail per token, instead of the expected
    information gain."""

    def info_gain(self, post, p_fail):
        return np.maximum(p_fail @ post - p_fail[:, 0], 0.0)  # column 0: nothing is broken


def replay(history, catalog, strategy, variants, train_of, budgets=BUDGETS, seeds=5):
    """One row per (variant, budget, seed), built as ``experiment/evaluate.py`` builds them. ``train_of(variant)``
    gives the changes the strategy may learn from."""
    rows = []
    full = history.total_cost()
    order_cache = {}  # a strategy's order depends on the change (and the seed) only: shared across budgets
    for v in variants:
        change, train = history.changesets[v], train_of(v)
        for b in budgets:
            for seed in range(seeds):
                rng = random.Random(1000 * seed + sum(map(ord, v)))  # the evaluator's seed
                options = {"seed": seed, "order_cache": order_cache}
                ctx = SelectionContext(change, catalog, history, b * full, rng, train_variants=train, options=options)
                log = strategy.run(ctx, make_oracle(history, v, rng))
                row = evaluate_log(log, v, history, catalog, b * full)
                row.update(seed=seed, budget=b, p_broken=log.p_broken)
                # for a run that ended at a failure: the test that failed, and the component the adaptive method
                # then holds most likely broken (the first of its blame list)
                row["failed_test"] = log.executed[-1] if log.stop_reason == "regression" else None
                row["top_blamed"] = log.blame[0][0] if log.blame else None
                rows.append(row)
    return pd.DataFrame(rows)


def summary(df, label=None):
    """Per budget: detection on the revealed regressions, tokens spent on them and on the other changes, and how
    often a clean verdict (the report's ``CLEAN_STOPS``) was given on a regression. Prints the table and returns
    it."""
    out = []
    for b, g in df.groupby("budget"):
        reg, other = g[g.is_regression], g[~g.is_regression]
        clean = g[g.stop_reason.isin(CLEAN_STOPS)]
        out.append(
            {
                "budget": b,
                "detect": reg.detected.mean() if len(reg) else float("nan"),
                "cost_reg": reg.cost_fraction.mean() if len(reg) else float("nan"),
                "cost_unrev": other.cost_fraction.mean() if len(other) else float("nan"),
                "cost_all": g.cost_fraction.mean(),
                "tests": g.tests_run.mean(),
                "clean_n": len(clean),
                "clean_wrong": clean.is_regression.mean() if len(clean) else float("nan"),
                "false_regr": int(((g.stop_reason == "regression") & ~g.is_regression).sum()),
            }
        )
    table = pd.DataFrame(out).set_index("budget").round(3)
    if label:
        print(f"\n--- {label}")
    print(table.to_string(), flush=True)
    return table
