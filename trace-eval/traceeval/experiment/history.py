"""History store: baseline runs (with observed dependencies, costs, pass rates) and per-variant runs
(the ground-truth fault matrix). Everything the selectors may use about the change under evaluation is
derived from the *baseline* history; variant runs are used by the replay oracle, by the metrics, and by
the strategies that learn from the *other* changes (``ctx.train_variants``)."""

import json
import statistics
from collections import Counter
from functools import cached_property
from pathlib import Path

from traceeval.mutation.changeset import ChangeSet

from .executor import read_jsonl


class TestStats:
    """The recorded runs of one test, on the baseline or on one variant."""

    def __init__(self, test_id: str):
        self.test_id = test_id
        # one record per repetition, as executor.run_case writes it (outcome, classification, tokens, deps, ...)
        self.runs: list[dict] = []

    def add(self, rec: dict):
        """One more recorded run: a line of the history file."""
        self.runs.append(rec)

    @property
    def n(self) -> int:
        """How many runs were recorded, those the environment broke included."""
        return len(self.runs)

    @property
    def valid_runs(self) -> list[dict]:
        """The runs that say something about the agent: a run the environment broke (INFRA_INVALID) does not."""
        return [r for r in self.runs if r.get("classification") != "INFRA_INVALID"]

    @property
    def pass_rate(self) -> float:
        """The share of the valid runs that passed (0 when no run is valid)."""
        runs = self.valid_runs
        return sum(1 for r in runs if r["passed"]) / len(runs) if runs else 0.0

    @property
    def mean_tokens(self) -> float:
        """The mean cost of a run in tokens, over the valid runs (over all of them when none is valid)."""
        return statistics.fmean(r["tokens"] for r in (self.valid_runs or self.runs))

    # The two below are cached on first use: runs are only added while History.load reads the files.
    @cached_property
    def dep_frequency(self) -> dict[str, float]:
        """Fraction of the valid runs in which each component was exercised (depth/frequency of dependency)."""
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
        self.variants: dict[str, dict[str, TestStats]] = {}  # variant -> test id -> its runs on that changed copy
        self.changesets: dict[str, ChangeSet] = {}  # variant -> what its diff touched
        self.mutation_meta: dict[str, dict] = {}  # variant -> mutation.json (category, expected_regression, ...)

    # ---------------------------------------------------------------- loading
    @classmethod
    def load(cls, workdir: Path) -> "History":
        """Read ``history/baseline.jsonl``, ``history/variants/*.jsonl`` and each variant's change set and
        mutation metadata (``variants/<id>/changeset.json``, ``mutation.json``)."""
        h, workdir = cls(), Path(workdir)
        # the original app: one record per test and repetition
        base = workdir / "history" / "baseline.jsonl"
        if base.exists():
            for rec in read_jsonl(base):
                h.baseline.setdefault(rec["test_id"], TestStats(rec["test_id"])).add(rec)
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
        # a test the variant did not run, or ran only in runs the environment broke, counts as behaving like the
        # baseline
        st = self.variants.get(variant, {}).get(test_id)
        return st.pass_rate if st and st.valid_runs else self.baseline_pass_rate(test_id)

    def revealing_tests(self, variant: str, threshold: float = 0.5) -> set[str]:
        """Tests whose majority outcome flips from pass (baseline) to fail (variant) = ground truth."""
        out = set()
        for t in self.baseline:
            if self.baseline_pass_rate(t) >= threshold and self.variant_pass_rate(variant, t) < threshold:
                out.add(t)
        return out

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
        }
