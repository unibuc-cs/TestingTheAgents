"""A clean verdict with a bounded miss rate, before every diverged test has run (``TODO.md`` section 5).

Replay-first leaves, for a change, the tests that diverge. Running all of them gives a clean verdict that leaves
nothing untested, and that is what stays expensive: a change that reaches most tests and breaks none costs most
of the suite. This script measures rules that stop earlier and say how often they are wrong:

1. a rule puts the diverged tests of a change in an order and gives each a value, which only goes down along the
   order: how much reason is left to go on;
2. the tests run in that order, and the run ends at the first failure (a regression) or at the first test whose
   value is under a threshold (clean);
3. the threshold comes from other changes with known outcomes, by split conformal prediction: over the
   calibration changes that are regressions, take the value at each one's first revealing test; the threshold is
   the k-th smallest of those, with k = floor(alpha (n + 1)). A new regression is then missed with probability at
   most ``alpha``, whatever the rule, as long as the calibration changes and the new one are exchangeable.

The rules:

- ``random``: the tests in an order drawn at random, the value a random number. What a threshold buys with no
  information at all;
- ``text (TF-IDF)``: the tests by the similarity of their text to the diff (``ir_tfidf``'s order), the value that
  similarity;
- ``learned``: a logistic model of "this diverged test reveals this change" over the features of ``history_ml``,
  fitted on other changes; the value is its probability. ``learned + replay`` adds what the replay says about the
  test: where the change reaches it and how far in;
- ``adaptive_bayes``: the method's own order, the value its probability that the change broke something given
  that every test so far passed. Its clean verdict compares that probability with a constant (``eps_clean``);
  here the calibrated threshold takes the constant's place. ``adaptive_bayes, reached tests`` is the same method
  taught on the tests each past change reaches only, instead of every test whose traces touch the change.

A threshold is set in three ways (``traceeval/experiment/stopping.py`` has the arithmetic):

- ``one``: one for all changes. Its promise is over all changes together, and a rule may keep it by missing most
  regressions of one group and none of another;
- ``per group``: one per group of changes, a group being what the change edits (a skill's steps, text the model
  reads, an agent's tools and skills, the configuration, the starting data, code), which its change set tells
  before any test runs. It promises the miss rate within each group, from fewer past regressions; a group with
  too few has no threshold, and every test its changes reach runs;
- ``one, sure``: one for all changes, lower, so that the miss rate is under its target for nine sets of past
  regressions in ten and not only on average over such sets.

The per-group thresholds are also measured with the change's coverage floor (``coverage.coverage_floor``: the
cheapest diverged tests that, with the replayed ones, cover every changed component and affected mandatory
property), run before a clean verdict (``floor last``) or before the plan (``floor first``). Every table gives the
coverage of the clean verdicts too: the share of what the tests can cover of the change that the tests run and the
replayed ones cover, when the verdict is clean.
On the second recording, for comparison, two selections that never stop on a value: a fixed minimal set of the
whole suite (test-suite minimization, chosen once without the change) and the coverage floor alone.

Three measurements:

- *Within one set of changes.* The changes are split three ways by their ids (``generator.split``): one part is
  what a rule learns from, one calibrates the threshold, and the rule is measured on the third, which neither has
  seen. The split is drawn ``SPLITS`` times and the tables give the means.
- *A kind of change never seen.* The changes of one kind are measured with rules and thresholds that have seen
  the other kinds only; the kinds are then pooled.
- *On other changes* (a second recording of the same original app): the rules learn from one half of the first
  recording's changes, the other half sets the thresholds, and the rules are measured on the second recording's
  changes. Changes written by hand are not exchangeable with generated ones, so this shows what the promise is
  worth when the changes to come are not like those the threshold was set on.

A change the replay already settles (no test diverges, or a replayed test fails) needs no rule and is left out.

    python scripts/analysis/stop_with_guarantee.py [recording [second recording]]   # default runs/gemma8_gen
"""

import math
import random
import sys
from dataclasses import replace
from functools import cached_property

import numpy as np
import pandas as pd
from replaylib import load, recording

from traceeval.catalog import load_properties
from traceeval.experiment.coverage import coverage_floor, floor_items
from traceeval.experiment.replay_first import Replays
from traceeval.experiment.stopping import LearnsOnce, group_of, threshold
from traceeval.mutation.generator import kind_of, split
from traceeval.selection import SelectionContext
from traceeval.selection.adapted import fit_logistic, sigmoid
from traceeval.selection.adaptive_bayes import AdaptiveBayes
from traceeval.selection.extras import _features
from traceeval.selection.strategies import tfidf_relevance

ALPHAS = (0.05, 0.10, 0.20)  # the target miss rates
SPLITS = 20  # how many times the changes are split three ways
BY_GROUP_AT = 0.10  # the target of the tables by group of changes
SURE = 0.9  # "one, sure": the share of the sets of past regressions for which the target is to hold


def replayed(workdir: str):
    """A recording and its replay."""
    history, cases = load(workdir)
    replays = Replays.load(workdir)
    if replays is None:
        raise SystemExit(f"{workdir} has not been replayed: run traceeval replay-first --workdir {workdir}")
    return history, cases, replays


workdir = recording("runs/gemma8_gen")
h, catalog, its_replays = replayed(workdir)
full = h.total_cost()
passes = {t: h.baseline_pass_rate(t) >= 0.5 for t in h.baseline}
props = load_properties()


# ---------------------------------------------------------------------------- the changes, and what the replay leaves
class Change:
    """One recorded change after its replay: the tests left to run, what each costs from its divergence point on,
    and which of them reveal the change. ``source`` and ``replays`` are the recording the change is in, and that
    recording's replay."""

    def __init__(self, variant: str, source, replays):
        self.id = variant
        self.group = group_of(source.changesets[variant])
        prefix, missing = replays.prefix(variant), source.missing(variant)
        # the tests the change reaches that can tell something: they diverge, pass on the original app, and the
        # recording has a valid run of them on this copy
        self.tests = [t for t in replays.diverged(variant) if passes.get(t) and t not in missing]
        # what running one costs: the tokens of its recorded runs on this copy after the divergence point, as the
        # evaluator charges it (``evaluate.make_oracle``)
        runs = {t: source.variants[variant][t].valid_runs for t in self.tests}
        self.cost = {t: sum(max(0.0, r["tokens"] - prefix[t]) for r in runs[t]) / len(runs[t]) for t in self.tests}
        self.revealing = source.revealing_tests(variant) & set(self.tests)
        # a replayed test that fails: the replay alone shows the regression
        self.found_by_replay = any(passes.get(t) for t in replays.new_failures(variant))
        # the replayed tests that pass on the original app: their outcome is known, and they cover what they exercise
        self.known = [t for t in replays.replayed(variant) if passes.get(t)]
        # What a strategy is given for this change (``evaluate.py`` builds the same). Its history is always the
        # first recording, ``h``: that is where the changes a rule learns from are, and the baseline is the same.
        # Who it learns from is set per measurement.
        self.ctx = SelectionContext(
            source.changesets[variant],
            catalog,
            h,
            float("inf"),
            random.Random(0),
            replayed=replays.replayed(variant),
            prefix=prefix,
            missing=missing,
        )
        self.rows = replays.rows[variant]

    @property
    def settled(self) -> bool:
        """Whether the replay leaves nothing to decide: no test to run, or a failure already."""
        return self.found_by_replay or not self.tests

    @cached_property
    def features(self) -> dict[str, list[float]]:
        """Per diverged test, the features of ``history_ml`` (static impact by kind, cost, risk, the shape of the
        test), then the three the replay adds: whether the change first reaches the test in a tool result, the
        share of the test's tokens that replay before that, and the number of requests that do."""
        out = {}
        for t in self.tests:
            row = self.rows[t]
            in_tool_result = float(row["diverged_in"] == "tool result")
            from_replay = [in_tool_result, row["tokens"] / max(1.0, h.cost(t)), float(row["requests"])]
            out[t] = _features(self.ctx, t, self.ctx.change) + from_replay
        return out

    @cached_property
    def text(self) -> dict[str, float]:
        """Per diverged test, the TF-IDF similarity of its text to the diff."""
        relevance = tfidf_relevance(self.ctx)
        return {t: float(relevance.get(t, 0.0)) for t in self.tests}

    @cached_property
    def covers(self) -> dict[str, set[str]]:
        """What each diverged or replayed test covers of what the change touches (``coverage.floor_items``)."""
        return floor_items(self.ctx.change, h, catalog, props, [*self.tests, *self.known])

    @cached_property
    def floor(self) -> list[str]:
        """The coverage floor: the cheapest diverged tests that, with the replayed ones, cover all they can."""
        return coverage_floor(self.ctx.change, h, catalog, props, self.tests, self.known, self.cost.get)

    def coverage(self, executed: list[str]) -> float:
        """The share of what the tests can cover of the change that the executed and the replayed ones cover."""
        coverable = set().union(*self.covers.values())
        if not coverable:
            return np.nan
        return len(set().union(*(self.covers[t] for t in [*executed, *self.known])) & coverable) / len(coverable)


def after_replay(source, replays, name: str) -> list[str]:
    """Adds the changes of a recording to ``changes`` and returns those the replay leaves open, after a line that
    says how many there are of each."""
    recorded = [v for v in source.variants if v in replays.rows]
    changes.update({v: Change(v, source, replays) for v in recorded})
    left = [v for v in recorded if not changes[v].settled]
    print(
        f"{name}: {len(recorded)} changes; the replay settles {len(recorded) - len(left)} "
        f"({sum(changes[v].found_by_replay for v in recorded)} as regressions); of the other {len(left)}, "
        f"{sum(bool(changes[v].revealing) for v in left)} are regressions"
    )
    return left


changes: dict[str, Change] = {}
open_changes = after_replay(h, its_replays, workdir)


# ---------------------------------------------------------------------------- the rules
# A rule is a function of the changes it may learn from, which returns the plan of any other change: its diverged
# tests in running order, each with its value.
def ordered(scores: dict[str, float]) -> list[tuple[str, float]]:
    """The plan of a rule that scores each test once: highest score first, the score as the value."""
    return sorted(scores.items(), key=lambda tv: -tv[1])


def at_random(trained):
    """No information: a score drawn at random, the same for a test every time (seeded by the two names)."""
    return lambda c: ordered({t: random.Random(f"{c.id}|{t}").random() for t in c.tests})


def by_text(trained):
    """The TF-IDF similarity of each test's text to the diff, which needs no other change."""
    return lambda c: ordered(c.text)


def learned(with_replay: bool):
    """A logistic model of "this diverged test reveals this change", fitted on the training changes; the two
    classes weigh the same in the fit, as in ``history_ml``. Without ``with_replay`` the three features the replay
    adds, the last three, are left out."""
    columns = slice(None) if with_replay else slice(0, -3)

    def learn(trained):
        pairs = [(changes[v], t) for v in trained for t in changes[v].tests]
        X = np.array([c.features[t][columns] for c, t in pairs])
        y = np.array([float(t in c.revealing) for c, t in pairs])
        if not 0 < y.sum() < len(y):  # one class only: nothing to learn from
            return at_random(trained)
        balance = np.where(y > 0, len(y) / (2 * y.sum()), len(y) / (2 * (len(y) - y.sum())))
        weights = fit_logistic(X, y, l2=1.0, iters=200, sample_weight=balance, free_intercept=True)

        def plan(c: Change):
            probabilities = sigmoid(np.array([c.features[t][columns] for t in c.tests]) @ weights)
            return ordered(dict(zip(c.tests, map(float, probabilities), strict=True)))

        return plan

    return learn


class TaughtOnReached(LearnsOnce):
    """The adaptive method, taught on the tests each past change reaches only. As shipped, it counts among the
    tests a past change "impacted" every test whose traces touch a changed component; with replay-first most of
    those replay to the end and cannot reveal anything, which lowers every reveal ratio it learns. Here a past
    change's impacted tests are those among its diverged ones (``TODO.md`` section 5, the replay as evidence)."""

    @staticmethod
    def impacted(ctx, change, comp):
        out = AdaptiveBayes.impacted(ctx, change, comp)
        past = changes.get(change.variant)
        return out if past is None else {link: tests & set(past.tests) for link, tests in out.items()}


def adaptive(method: LearnsOnce, constant: bool = False):
    """The order ``method`` runs the diverged tests in while each passes, and before each its probability that the
    change broke something (``AdaptiveBayes.trajectory``: the tests that can no longer move that probability come
    last, cheapest first). With ``constant``, the rule is also measured with the method's own constant as the
    threshold (``eps_clean``)."""

    def learn(trained):
        def plan(c: Change):
            steps = method.trajectory(replace(c.ctx, train_variants=trained))
            # a change that leaves the method no component to reason about: cheapest first, never stopped early
            return steps or [(t, 1.0) for t in sorted(c.tests, key=lambda t: (c.cost[t], t))]

        return plan

    learn.constant = method.eps_clean if constant else None
    return learn


RULES = {
    "random": at_random,
    "text (TF-IDF)": by_text,
    "learned": learned(with_replay=False),
    "learned + replay": learned(with_replay=True),
    "adaptive_bayes": adaptive(LearnsOnce(), constant=True),
    "adaptive_bayes, reached tests": adaptive(TaughtOnReached()),
}


# ---------------------------------------------------------------------------- the threshold, and a run under it
def at_first_reveal(c: Change, plan: list[tuple[str, float]]) -> float:
    """For a regression: the value its plan has reached when its first revealing test comes up. A threshold above
    it ends the run before that test, and the regression is missed."""
    low = math.inf
    for t, value in plan:
        low = min(low, value)
        if t in c.revealing:
            break
    return low


def run(c: Change, plan: list[tuple[str, float]], tau: float, floor: str | None = None) -> tuple[str, float, list]:
    """The rule on one change: its tests in the plan's order, until one fails or the value is under ``tau``.
    Each test ends as the majority of its recorded runs does. With ``floor`` "first", the change's coverage floor
    runs before the plan, and with "last", before a clean verdict. Returns the verdict, the tokens spent and the
    tests run."""
    executed: list[str] = []

    def reveals(tests) -> bool:
        """Run the tests not run yet, in order, until one reveals the change."""
        for t in tests:
            if t not in executed:
                executed.append(t)
                if t in c.revealing:
                    return True
        return False

    found = floor == "first" and reveals(c.floor)
    for t, value in [] if found else plan:
        if value < tau:
            break
        if reveals([t]):
            found = True
            break
    found = found or (floor == "last" and reveals(c.floor))
    return ("regression" if found else "clean"), sum(c.cost[t] for t in executed), executed


def measure(trained: list[str], calibrated: list[str], measured: list[str]) -> pd.DataFrame:
    """Every rule, with what it learns taken from ``trained`` and its thresholds set on ``calibrated``, run on
    ``measured`` under one threshold for all changes and under a threshold per group. One row per rule, way of
    setting the threshold, target and measured change: whether the change is a regression, the verdict, and the
    tokens spent as a share of the full suite."""
    rows = []
    for label, rule in RULES.items():
        plan_of = rule(trained)
        plans = {v: plan_of(changes[v]) for v in [*calibrated, *measured]}
        # the calibration regressions' values at their first revealing test: of all of them, and group by group
        firsts: dict[str, list[float]] = {"all": []}
        for v in calibrated:
            if changes[v].revealing:
                value = at_first_reveal(changes[v], plans[v])
                firsts["all"].append(value)
                firsts.setdefault(changes[v].group, []).append(value)
        firsts = {group: sorted(values) for group, values in firsts.items()}
        constant = getattr(rule, "constant", None)
        for v in measured:
            c = changes[v]
            # the thresholds this change is run under: how each was set, its target, its value (target 0: every
            # diverged test runs; a group without a past regression has no threshold either)
            under = [("one", alpha, threshold(firsts["all"], alpha), None) for alpha in (0.0, *ALPHAS)]
            per_group = [(alpha, threshold(firsts.get(c.group, []), alpha)) for alpha in ALPHAS]
            under += [("per group", alpha, tau, None) for alpha, tau in per_group]
            # the same thresholds with the change's coverage floor, run before a clean verdict or before the plan
            under += [("per group, floor last", alpha, tau, "last") for alpha, tau in per_group]
            under += [("per group, floor first", alpha, tau, "first") for alpha, tau in per_group]
            under += [("one, sure", alpha, threshold(firsts["all"], alpha, SURE), None) for alpha in ALPHAS]
            if constant is not None:  # the constant the method ships with, which promises no miss rate
                under.append(("one", f"none (eps_clean = {constant})", constant, None))
            for how, target, tau, floor in under:
                verdict, spent, executed = run(c, plans[v], tau, floor)
                rows.append(
                    {
                        "rule": label,
                        "thresholds": how,
                        "target": target,
                        "group": c.group,
                        "regression": bool(c.revealing),
                        "verdict": verdict,
                        "tokens": spent / full,
                        "coverage": c.coverage(executed),
                    }
                )
    return pd.DataFrame(rows)


def summary(rows: pd.DataFrame, by: tuple[str, ...] = ("thresholds", "rule", "target")) -> pd.DataFrame:
    """The rows of ``measure`` per way of setting the threshold, rule and target: the regressions missed (called
    clean), the clean verdicts given on a regression, and the mean tokens on the changes no test reveals, on the
    regressions and on all."""

    def one(g: pd.DataFrame) -> pd.Series:
        regressions, clean = g[g.regression], g[g.verdict == "clean"]
        missed = int((regressions.verdict == "clean").sum())
        return pd.Series(
            {
                "missed": f"{missed} of {len(regressions)}",
                "miss rate": missed / max(1, len(regressions)),
                "clean verdicts on a regression": missed / max(1, len(clean)),
                "tokens, no test reveals": g[~g.regression].tokens.mean() if not g.regression.all() else 0.0,
                "tokens, regressions": regressions.tokens.mean() if len(regressions) else 0.0,
                "tokens, all": g.tokens.mean(),
                # on a clean verdict, what the tests run and those the replay settled cover of what the change
                # touches, on average (a regression verdict needs no coverage)
                "coverage when clean": clean.coverage.mean(),
            }
        )

    return rows.groupby(list(by), sort=False)[["regression", "verdict", "tokens", "coverage"]].apply(one)


def fixed_minimal_set() -> list[str]:
    """Test-suite minimization, for comparison: the fewest tests that pass on the original app and cover all that
    the suite covers there (every component a run exercised, lines aside, and every mandatory property a test
    checks), chosen once and without any change. Greedy, the cheaper test first on a tie."""
    mandatory = {p for p, prop in props.items() if prop.mandatory}
    covers = {
        t: {d for d in h.deps(t) if not d.startswith("line:")}
        | {f"property:{p}" for p in mandatory & set(catalog[t].properties)}
        for t in h.baseline
        if passes.get(t) and t in catalog
    }
    left, chosen = set().union(*covers.values()), []
    pool = sorted(covers, key=lambda t: (h.cost(t), t))
    while left:
        best = max(pool, key=lambda t: len(covers[t] & left))
        chosen.append(best)
        left -= covers[best]
    return chosen


def show(title: str, table: pd.DataFrame):
    """Print a summary, the rows with one threshold first."""
    print(f"\n{title}")
    print(table.sort_index(level="thresholds", sort_remaining=False).reset_index().to_string(index=False))


pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 20)
pd.set_option("display.max_rows", 200)
pd.set_option("display.float_format", "{:.3f}".format)

# ---------------------------------------------------------------------------- within one set of changes
per_split, calibration_sizes = [], []
for s in range(SPLITS):
    # three parts, fixed by the ids and the split's number: a rule's, the threshold's, and the measured one
    learn, measured = split(open_changes, seed=s)
    trained, calibrated = split(learn, seed=SPLITS + s)
    calibration_sizes.append(sum(bool(changes[v].revealing) for v in calibrated))
    per_split.append(measure(trained, calibrated, measured).assign(split=s))
per_split = pd.concat(per_split)
smallest = 1 / (min(calibration_sizes) + 1)
print(
    f"\n{SPLITS} splits: a quarter of the changes is what a rule learns from, a quarter sets the threshold "
    f"({min(calibration_sizes)} to {max(calibration_sizes)} regressions), half measures the rule.\n"
    f"A target under {smallest:.3f} leaves no threshold in some split: every diverged test runs there."
)

# one row per way, rule and target: the means over the splits, the highest miss rate any split gave, and the
# share of the splits whose miss rate is over its target (a target on average leaves about half of them over)
splits = summary(per_split, by=("split", "thresholds", "rule", "target")).drop(columns="missed").astype(float)
rates = zip(splits["miss rate"], splits.index.get_level_values("target"), strict=True)
over = [rate > target if isinstance(target, float) else np.nan for rate, target in rates]
table = splits.assign(over=over).groupby(["thresholds", "rule", "target"], sort=False)
means = table.mean().drop(columns="over")
means.insert(1, "highest", table["miss rate"].max())
means.insert(2, "splits over target", table["over"].mean())
show("the rules on the measured changes: means over the splits, tokens as shares of the full suite", means)

# Where the misses fall and where the tokens go, group by group, at one target. The promise of one threshold is
# over all the changes together: a rule may keep it by missing most regressions of one group and none of another.
at_target = per_split[per_split["target"] == BY_GROUP_AT]
everything = per_split[(per_split["target"] == 0.0) & (per_split["rule"] == "random")]
sizes = pd.concat(
    [
        (everything.groupby("group").size() / SPLITS).rename("changes per split"),
        (everything[everything.regression].groupby("group").size() / SPLITS).rename("regressions"),
        everything.groupby("group")["tokens"].mean().rename("tokens, every test"),
    ],
    axis=1,
)
print(f"\nthe groups of changes, per split: {sizes.round(3).to_dict('index')}")
regressions = at_target[at_target.regression].assign(missed=lambda rows: rows.verdict == "clean")
for how in ("one", "per group"):
    misses = regressions[regressions.thresholds == how].pivot_table(index="group", columns="rule", values="missed")
    tokens = at_target[at_target.thresholds == how].pivot_table(index="group", columns="rule", values="tokens")
    print(f"\nmiss rate per group, target {BY_GROUP_AT}, thresholds: {how}")
    print(misses[list(RULES)].to_string())
    print(f"\ntokens per group, target {BY_GROUP_AT}, thresholds: {how}")
    print(tokens[list(RULES)].to_string())

# ---------------------------------------------------------------------------- one kind of change left out at a time
# The changes of one kind are measured with rules and thresholds that have seen the other kinds only: what the
# promise is worth for a kind of change the calibration never had. The rows of all the kinds are then pooled.
left_out = []
for kind in sorted({kind_of(v) for v in open_changes}):
    measured = [v for v in open_changes if kind_of(v) == kind]
    trained, calibrated = split([v for v in open_changes if kind_of(v) != kind])
    left_out.append(measure(trained, calibrated, measured))
show(
    "each kind of change measured with rules and thresholds from the other kinds (all kinds pooled)",
    summary(pd.concat(left_out)),
)

# ---------------------------------------------------------------------------- on the changes of a second recording
if len(sys.argv) > 2:
    theirs, _, their_replays = replayed(sys.argv[2])
    if abs(theirs.total_cost() - full) > 1e-6:
        raise SystemExit(f"{sys.argv[2]} is not a recording of the same original app as {workdir}")
    print()
    still_open = after_replay(theirs, their_replays, sys.argv[2])
    # every open change of the first recording is used: one half to learn from, the other to set the thresholds
    trained, calibrated = split(open_changes)
    show(
        f"the rules learnt on {len(trained)} changes of {workdir}, their thresholds set on the other "
        f"{len(calibrated)} ({sum(bool(changes[v].revealing) for v in calibrated)} regressions), run on those changes",
        summary(measure(trained, calibrated, still_open)),
    )

    # For comparison, selections that never stop on a value: a fixed minimal set of the whole suite, chosen once
    # without the change (test-suite minimization), run on the tests the change reaches or run whole; and the
    # change's own coverage floor alone.
    fixed = fixed_minimal_set()
    reference = []
    for v in still_open:
        c = changes[v]
        for label, tests, cost in (
            ("a fixed minimal set, the tests the change reaches", [t for t in fixed if t in c.cost], c.cost),
            ("a fixed minimal set, run whole", fixed, {t: h.cost(t) for t in fixed}),
            ("the coverage floor alone", c.floor, c.cost),
        ):
            executed = []
            for t in tests:  # in the set's order, until a test reveals the change
                executed.append(t)
                if t in c.revealing:
                    break
            reference.append(
                {
                    "selection": label,
                    "regression": bool(c.revealing),
                    "verdict": "regression" if c.revealing & set(executed) else "clean",
                    "tokens": sum(cost[t] for t in executed) / full,
                    "coverage": c.coverage([t for t in executed if t in c.covers]),
                }
            )
    print(f"\nthe fixed minimal set: {len(fixed)} tests, {sum(h.cost(t) for t in fixed) / full:.1%} of the suite")
    print(summary(pd.DataFrame(reference), by=("selection",)).reset_index().to_string(index=False))
