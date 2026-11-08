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
        self.runs: list[dict] = []

    def add(self, rec: dict):
        self.runs.append(rec)

    @property
    def n(self) -> int:
        return len(self.runs)

    @property
    def pass_rate(self) -> float:
        return sum(1 for r in self.runs if r["passed"]) / max(1, self.n)

    @property
    def mean_tokens(self) -> float:
        return statistics.fmean(r["tokens"] for r in self.runs)

    # The two below are cached on first use: runs are only added while History.load reads the files.
    @cached_property
    def dep_frequency(self) -> dict[str, float]:
        """Fraction of runs in which each component was exercised (depth/frequency of dependency)."""
        counts = Counter(d for r in self.runs for d in set(r.get("deps", [])))
        return {d: c / self.n for d, c in counts.items()}

    @cached_property
    def deps(self) -> set[str]:
        """Every component exercised in at least one run."""
        return set(self.dep_frequency)


class History:
    def __init__(self):
        self.baseline: dict[str, TestStats] = {}
        self.variants: dict[str, dict[str, TestStats]] = {}
        self.changesets: dict[str, ChangeSet] = {}
        self.mutation_meta: dict[str, dict] = {}

    # ---------------------------------------------------------------- loading
    @classmethod
    def load(cls, workdir: Path) -> "History":
        """Read ``history/baseline.jsonl``, ``history/variants/*.jsonl`` and each variant's change set and
        mutation metadata (``variants/<id>/changeset.json``, ``mutation.json``)."""
        h, workdir = cls(), Path(workdir)
        base = workdir / "history" / "baseline.jsonl"
        if base.exists():
            for rec in read_jsonl(base):
                h.baseline.setdefault(rec["test_id"], TestStats(rec["test_id"])).add(rec)
        vdir = workdir / "history" / "variants"
        if vdir.exists():
            for path in sorted(vdir.glob("*.jsonl")):
                name = path.stem
                stats = h.variants.setdefault(name, {})
                for rec in read_jsonl(path):
                    stats.setdefault(rec["test_id"], TestStats(rec["test_id"])).add(rec)
                vroot = workdir / "variants" / name
                if (vroot / "changeset.json").exists():
                    h.changesets[name] = ChangeSet.from_dict(json.loads((vroot / "changeset.json").read_text()))
                if (vroot / "mutation.json").exists():
                    h.mutation_meta[name] = json.loads((vroot / "mutation.json").read_text())
        return h

    # ---------------------------------------------------------------- derived facts
    def test_ids(self) -> list[str]:
        return list(self.baseline.keys())

    def cost(self, test_id: str) -> float:
        """Expected cost of a test: its mean tokens over the baseline runs."""
        return self.baseline[test_id].mean_tokens

    def total_cost(self) -> float:
        return sum(self.cost(t) for t in self.baseline)

    def deps(self, test_id: str) -> set[str]:
        return self.baseline[test_id].deps

    def baseline_pass_rate(self, test_id: str) -> float:
        return self.baseline[test_id].pass_rate

    def variant_pass_rate(self, variant: str, test_id: str) -> float:
        # a test the variant did not run counts as behaving like the baseline
        st = self.variants.get(variant, {}).get(test_id)
        return st.pass_rate if st else self.baseline_pass_rate(test_id)

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
            "baseline_reps": max((s.n for s in self.baseline.values()), default=0),
            "failing_tests": sorted(t for t, s in self.baseline.items() if s.pass_rate < 0.5),  # model mistakes
            "total_tokens_full_suite": round(self.total_cost()),
        }
