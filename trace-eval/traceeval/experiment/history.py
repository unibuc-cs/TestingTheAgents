"""A recording as the strategies and the evaluator read it: the runs on the original app (with the code each
exercised, its cost and its outcome) and the runs on each changed copy (the ground truth). Everything a strategy
may use about the change under evaluation comes from the runs on the original app; the runs on the changed copies
are read by the evaluator's oracle, by the metrics, and by the strategies that learn from the *other* changes
(``ctx.train_variants``).

A recording also holds the empty change (``history/unchanged.jsonl``): the original app run the way the changed
copies are, several cases at a time and without coverage. It is no change to evaluate; it says what the way of
running alone does to the outcomes, and a test that fails there reveals nothing.

On a changed copy a recording has either runs of every test, or runs of the tests the change reaches only
(``runner.record_mutants(reached_only=True)``). A test the change does not reach replays to the end on the copy,
and its one record there is that replayed run, marked ``stand_in``: no model was asked."""

import json
import statistics
from collections import Counter
from functools import cached_property
from pathlib import Path

from traceeval.mutation.changeset import ChangeSet

from .executor import read_jsonl

UNCHANGED = "unchanged"  # the name of the empty change, in its records and in ``traceeval mutants --only``


class TestStats:
    """The recorded runs of one test, on the baseline or on one variant. What is worked out from the runs (the
    valid ones, the pass rate, the mean cost, the dependencies) is kept after its first use, since a strategy asks
    for it thousands of times, and forgotten when a run is added."""

    def __init__(self, test_id: str):
        self.test_id = test_id
        # one record per repetition, as executor.run_case writes it (outcome, classification, tokens, deps, ...)
        self.runs: list[dict] = []

    def add(self, rec: dict):
        """One more recorded run: a line of the history file."""
        self.runs.append(rec)
        for kept in ("valid_runs", "pass_rate", "mean_tokens", "dep_frequency", "deps"):
            self.__dict__.pop(kept, None)  # worked out from the earlier runs: out of date now

    @property
    def n(self) -> int:
        """How many runs were recorded, those the environment broke included."""
        return len(self.runs)

    @cached_property
    def valid_runs(self) -> list[dict]:
        """The runs that say something about the agent: a run the environment broke (INFRA_INVALID) does not."""
        return [r for r in self.runs if r.get("classification") != "INFRA_INVALID"]

    @cached_property
    def pass_rate(self) -> float:
        """The share of the valid runs that passed (0 when no run is valid)."""
        runs = self.valid_runs
        return sum(1 for r in runs if r["passed"]) / len(runs) if runs else 0.0

    @cached_property
    def mean_tokens(self) -> float:
        """The mean cost of a run in tokens, over the valid runs (over all of them when none is valid)."""
        return statistics.fmean(r["tokens"] for r in (self.valid_runs or self.runs))

    @cached_property
    def dep_frequency(self) -> dict[str, float]:
        """For each component, the share of the valid runs that exercised it: how often the test depends on it."""
        runs = self.valid_runs or self.runs
        counts = Counter(d for r in runs for d in set(r.get("deps", [])))
        return {d: c / len(runs) for d, c in counts.items()}

    @cached_property
    def deps(self) -> set[str]:
        """Every component exercised in at least one run."""
        return set(self.dep_frequency)


class History:
    """A recording (``runs/<name>``) as the strategies and the evaluator read it: the runs of every test on the
    original app and on each changed copy, the change set of each copy, and the mutation's label."""

    def __init__(self):
        self.baseline: dict[str, TestStats] = {}  # test id -> its runs on the original app
        self.unchanged: dict[str, TestStats] = {}  # test id -> its runs under the empty change; empty if not recorded
        self.variants: dict[str, dict[str, TestStats]] = {}  # variant -> test id -> its runs on that changed copy
        self.changesets: dict[str, ChangeSet] = {}  # variant -> what its diff touched
        self.mutation_meta: dict[str, dict] = {}  # variant -> mutation.json (category, expected_regression, ...)

    # ---------------------------------------------------------------- loading
    @classmethod
    def load(cls, workdir: Path) -> "History":
        """Read ``history/baseline.jsonl``, ``history/unchanged.jsonl``, ``history/variants/*.jsonl`` and each
        variant's change set and mutation metadata (``variants/<id>/changeset.json``, ``mutation.json``)."""
        h, workdir = cls(), Path(workdir)
        # the original app, as the baseline ran it and as the empty change did: one record per test and repetition
        for name, stats in (("baseline", h.baseline), (UNCHANGED, h.unchanged)):
            path = workdir / "history" / f"{name}.jsonl"
            if path.exists():
                for rec in read_jsonl(path):
                    stats.setdefault(rec["test_id"], TestStats(rec["test_id"])).add(rec)
        # each changed copy: its runs, then what its diff touched and how its mutation is labelled
        vdir = workdir / "history" / "variants"
        if vdir.exists():
            for path in sorted(vdir.glob("*.jsonl")):
                name = path.stem
                stats = h.variants.setdefault(name, {})
                for rec in read_jsonl(path):
                    stats.setdefault(rec["test_id"], TestStats(rec["test_id"])).add(rec)
                # the change set and the label sit next to the copy itself, under variants/<id>/
                vroot = workdir / "variants" / name
                if (vroot / "changeset.json").exists():
                    h.changesets[name] = ChangeSet.from_dict(json.loads((vroot / "changeset.json").read_text()))
                if (vroot / "mutation.json").exists():
                    h.mutation_meta[name] = json.loads((vroot / "mutation.json").read_text())
        return h

    # ---------------------------------------------------------------- derived facts
    def test_ids(self) -> list[str]:
        """The tests the baseline ran, in the order the file lists them."""
        return list(self.baseline.keys())

    def cost(self, test_id: str) -> float:
        """Expected cost of a test: its mean tokens over the baseline runs."""
        return self.baseline[test_id].mean_tokens

    def total_cost(self) -> float:
        """The cost of the whole suite: what a budget fraction is a share of."""
        return sum(self.cost(t) for t in self.baseline)

    def seconds(self, test_id: str) -> float:
        """Expected run time of a test: its mean wall time over the baseline runs, which run one case at a time, so
        that no other run's load is in it."""
        st = self.baseline[test_id]
        return statistics.fmean(r["latency_ms"] for r in (st.valid_runs or st.runs)) / 1000

    def total_seconds(self) -> float:
        """The run time of the whole suite, one case after another."""
        return sum(self.seconds(t) for t in self.baseline)

    def deps(self, test_id: str) -> set[str]:
        """The observed dependencies of a test: every component its baseline runs exercised."""
        return self.baseline[test_id].deps

    def baseline_pass_rate(self, test_id: str) -> float:
        """The share of a test's valid runs on the original app that passed."""
        return self.baseline[test_id].pass_rate

    def variant_pass_rate(self, variant: str, test_id: str) -> float:
        """The share of a test's valid runs on the changed copy that passed."""
        # a missing pair (below) has no outcome of its own: it is given the baseline's, so that it reveals nothing
        st = self.variants.get(variant, {}).get(test_id)
        return st.pass_rate if st and st.valid_runs else self.baseline_pass_rate(test_id)

    def missing(self, variant: str) -> frozenset:
        """The tests with no valid run on a changed copy: it did not run them, or the environment broke every run.
        Such a pair is missing, not unchanged: the test reveals nothing there, no strategy is given it to run
        (``SelectionContext.missing``), and the report counts the pairs."""
        stats = self.variants.get(variant, {})
        return frozenset(t for t in self.baseline if not (t in stats and stats[t].valid_runs))

    def passes_unchanged(self, test_id: str, threshold: float = 0.5) -> bool:
        """Whether a test still passes under the empty change: the original app, run as the changed copies are.
        True when the empty change was not recorded, or has no valid run of the test."""
        st = self.unchanged.get(test_id)
        return not (st and st.valid_runs) or st.pass_rate >= threshold

    def training_variants(self, variant: str, members: list[str] | None = None) -> list[str]:
        """The recorded changes a strategy may learn from when ``variant`` is under test: every other one, except
        those that share a change with it. A batch is not checked by a model that has seen what each of its members
        breaks: its members are left out, and so are the batches that hold one of them; for a single change, the
        batches it is a member of. ``members`` names the changes a batch bundles when it is not in the recording."""

        def changes(v: str) -> set[str]:
            """The catalog changes a recorded variant applies: its members for a batch, itself otherwise."""
            return set(self.mutation_meta.get(v, {}).get("members") or [v])

        # the changes under test, then every other variant that applies none of them
        mine = set(members or []) | changes(variant)
        return [v for v in self.variants if v != variant and not changes(v) & mine]

    def revealing_tests(self, variant: str, threshold: float = 0.5) -> set[str]:
        """The tests that reveal the change, its ground truth: their majority outcome is a pass on the original app
        and a failure on the changed copy. A test that already fails under the empty change is left out: the way
        the changed copies are run, not the change, is what fails it."""
        noisy = {t for t in self.unchanged if not self.passes_unchanged(t, threshold)}
        out = set()
        for t in self.baseline:
            if (
                t not in noisy
                and self.baseline_pass_rate(t) >= threshold
                and self.variant_pass_rate(variant, t) < threshold
            ):
                out.add(t)
        return out

    def unchanged_flips(self, threshold: float = 0.5) -> list[str]:
        """The tests whose majority outcome under the empty change is not the baseline's: what running the original
        app as the changed copies are run does on its own (the noise floor of the recording)."""
        return [
            t
            for t, st in self.unchanged.items()
            if t in self.baseline
            and st.valid_runs
            and (st.pass_rate >= threshold) != (self.baseline_pass_rate(t) >= threshold)
        ]

    def summary(self) -> dict:
        """The facts in the report's header line."""
        return {
            "tests": len(self.baseline),
            "variants": len(self.variants),
            # the number of repetitions: the most runs any test has
            "baseline_reps": max((s.n for s in self.baseline.values()), default=0),
            "failing_tests": sorted(t for t, s in self.baseline.items() if s.pass_rate < 0.5),  # model mistakes
            "total_tokens_full_suite": round(self.total_cost()),
            # runs the environment broke, on the original app and the changed copies together; they count nowhere else
            "infra_invalid_runs": sum(
                s.n - len(s.valid_runs) for stats in (self.baseline, *self.variants.values()) for s in stats.values()
            ),
            # (change, test) pairs with no valid run at all
            "missing_pairs": sum(len(self.missing(v)) for v in self.variants),
        }
