"""A failure confirmed by running the test again, before it ends a run (``TODO.md`` section 5).

A run ends at the first failure of a test that passes on the original app. Decoding is greedy but not bit-exact,
so on a changed copy a few tests have runs that disagree, and one failing run of such a test is not its majority:
the run then ends with a regression verdict on a test that does not reveal the change. This script replays the
strategies replay-first, with no budget, under three rules for a failure:

- ``one run``: the first failing run ends the run (the rule of ``selection/base.py``);
- ``a second run``: the test is run once more, and only a second failure ends the run;
- ``majority of three``: after a first failure the test is run again, and a third time when the second run
  passes; two failures of three end the run.

The repetitions are other recorded runs of the same (change, test) pair, drawn without replacement, and each is
paid for. Nothing else changes: a strategy sees a test whose failure did not repeat as a test that passed.

    python scripts/analysis/confirm_failures.py [recording ...]     # default runs/gemma8
"""

import random
import sys

import pandas as pd
from replaylib import load

from traceeval.experiment.replay_first import Replays
from traceeval.selection import SelectionContext, get_strategy

RULES = ("one run", "a second run", "majority of three")
STRATEGIES = ("random", "ir_tfidf", "history_ml", "observed", "adaptive_bayes")
SEEDS = 20


def confirming(history, variant: str, rng: random.Random, prefix: dict, rule: str):
    """The evaluator's oracle (``evaluate.make_oracle``) with a failure confirmed as ``rule`` says: a recorded run
    of the test on the changed copy drawn at random and, after a failure, one or two more of its recorded runs."""

    def oracle(test_id: str) -> tuple[bool, float]:
        runs = history.variants[variant][test_id].valid_runs
        first = rng.choice(runs)
        others = [r for r in runs if r is not first]
        rng.shuffle(others)
        drawn = [first]
        if not first["passed"] and rule != "one run" and others:
            drawn.append(others[0])  # the test again
            if others[0]["passed"] and rule == "majority of three" and len(others) > 1:
                drawn.append(others[1])  # one failure and one pass: a third run decides
        # every run made is paid for, from the test's divergence point on
        spent = sum(max(0.0, float(r["tokens"]) - prefix.get(test_id, 0.0)) for r in drawn)
        # one run: its outcome. Otherwise the test failed only if its last run failed too: F F, or F P F
        return (first["passed"] if len(drawn) == 1 else drawn[-1]["passed"]), spent

    return oracle


def measure(workdir: str) -> pd.DataFrame:
    """One row per (strategy, rule, change, seed) of ``workdir``: how the run ended and what it cost."""
    h, catalog = load(workdir)
    replays = Replays.load(workdir)
    if replays is None:
        raise SystemExit(f"{workdir} has not been replayed: run traceeval replay-first --workdir {workdir}")
    full = h.total_cost()
    passes = {t: h.baseline_pass_rate(t) >= 0.5 for t in h.baseline}
    rows = []
    for name in STRATEGIES:
        strategy, shared = get_strategy(name), {"order_cache": {}}
        for variant in h.variants:
            revealing = h.revealing_tests(variant)
            replayed, prefix = replays.replayed(variant), replays.prefix(variant)
            # a replayed test that fails and passes on the original app: the regression is found before any run
            found = [t for t in replays.new_failures(variant) if passes[t]]
            learn, missing = h.training_variants(variant), h.missing(variant)
            for rule in RULES:
                for seed in range(SEEDS):
                    rng = random.Random(1000 * seed + sum(map(ord, variant)))  # the evaluator's seed
                    if found:
                        failed, tokens = found[0], 0.0
                    else:
                        ctx = SelectionContext(
                            h.changesets[variant],
                            catalog,
                            h,
                            float("inf"),
                            rng,
                            learn,
                            dict(shared, seed=seed),
                            replayed,
                            prefix,
                            missing,
                        )
                        log = strategy.run(ctx, confirming(h, variant, rng, prefix, rule))
                        failed = log.executed[-1] if log.stop_reason == "regression" else None
                        tokens = log.cost
                    rows.append(
                        {
                            "strategy": name,
                            "rule": rule,
                            "regression": bool(revealing),
                            # the run ended on a failure, and on a test that reveals the change
                            "verdict": failed is not None,
                            "on a revealing test": failed in revealing,
                            "tokens": tokens / full,
                        }
                    )
    return pd.DataFrame(rows)


def table(rows: pd.DataFrame) -> pd.DataFrame:
    """Per strategy and rule: the regressions found (on a revealing test, on another test, not at all), the
    regression verdicts on the changes no test reveals, and the mean tokens over all changes."""

    def one(g: pd.DataFrame) -> pd.Series:
        regressions, others = g[g.regression], g[~g.regression]
        return pd.Series(
            {
                "regressions: found on a revealing test": regressions["on a revealing test"].mean(),
                "on another test": (regressions.verdict & ~regressions["on a revealing test"]).mean(),
                "called clean": (~regressions.verdict).mean(),
                "other changes: called regression": others.verdict.mean(),
                "tokens, all changes": g.tokens.mean(),
            }
        )

    return rows.groupby(["strategy", "rule"], sort=False)[list(rows.columns[2:])].apply(one)


pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 20)
pd.set_option("display.float_format", "{:.3f}".format)
for workdir in sys.argv[1:] or ["runs/gemma8"]:
    rows = measure(workdir)
    changes = len(rows) // (len(STRATEGIES) * len(RULES) * SEEDS)
    print(
        f"\n{workdir}: {changes} changes, no budget, {SEEDS} seeds; shares of the runs, tokens as shares of the suite"
    )
    print(table(rows).reset_index().to_string(index=False))
