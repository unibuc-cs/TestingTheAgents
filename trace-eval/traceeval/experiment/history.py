"""History store: baseline runs (with observed dependencies, costs, flakiness) and per-variant runs
(the ground-truth fault matrix). Everything the selectors may use at selection time is derived from
the *baseline* history; variant runs are only used by the replay oracle and by the metrics."""

import json
import statistics
from collections import defaultdict
from pathlib import Path

from traceeval.mutation.changeset import ChangeSet

from .executor import read_jsonl


class TestStats:
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
    def flaky(self) -> bool:
        return 0.0 < self.pass_rate < 1.0

    @property
    def mean_tokens(self) -> float:
        return statistics.fmean(r["tokens"] for r in self.runs) if self.runs else 0.0

    @property
    def mean_latency_ms(self) -> float:
        return statistics.fmean(r["latency_ms"] for r in self.runs) if self.runs else 0.0

    @property
    def deps(self) -> set[str]:
        cached = getattr(self, "_deps", None)
        if cached is not None and cached[0] == self.n:
            return cached[1]
        out: set[str] = set()
        for r in self.runs:
            out |= set(r.get("deps", []))
        self._deps = (self.n, out)
        return out

    def dep_frequency(self) -> dict[str, float]:
        """fraction of runs in which each component was exercised (depth/frequency of dependency)."""
        cached = getattr(self, "_dep_freq", None)
        if cached is not None and cached[0] == self.n:
            return cached[1]
        counts: dict[str, int] = defaultdict(int)
        for r in self.runs:
            for d in set(r.get("deps", [])):
                counts[d] += 1
        freq = {d: c / max(1, self.n) for d, c in counts.items()}
        self._dep_freq = (self.n, freq)
        return freq


class History:
    def __init__(self, workdir: Path):
        self.workdir = Path(workdir)
        self.baseline: dict[str, TestStats] = {}
        self.variants: dict[str, dict[str, TestStats]] = {}
        self.changesets: dict[str, ChangeSet] = {}
        self.mutation_meta: dict[str, dict] = {}

    # ---------------------------------------------------------------- loading
    @classmethod
    def load(cls, workdir: Path) -> "History":
        h = cls(workdir)
        base = h.workdir / "history" / "baseline.jsonl"
        if base.exists():
            for rec in read_jsonl(base):
                h.baseline.setdefault(rec["test_id"], TestStats(rec["test_id"])).add(rec)
        vdir = h.workdir / "history" / "variants"
        if vdir.exists():
            for path in sorted(vdir.glob("*.jsonl")):
                name = path.stem
                stats = h.variants.setdefault(name, {})
                for rec in read_jsonl(path):
                    stats.setdefault(rec["test_id"], TestStats(rec["test_id"])).add(rec)
                vroot = h.workdir / "variants" / name
                if (vroot / "changeset.json").exists():
                    h.changesets[name] = ChangeSet.from_dict(json.loads((vroot / "changeset.json").read_text()))
                if (vroot / "mutation.json").exists():
                    h.mutation_meta[name] = json.loads((vroot / "mutation.json").read_text())
        return h

    # ---------------------------------------------------------------- derived facts
    def test_ids(self) -> list[str]:
        return list(self.baseline.keys())

    def cost(self, test_id: str) -> float:
        return self.baseline[test_id].mean_tokens

    def total_cost(self) -> float:
        return sum(self.cost(t) for t in self.baseline)

    def deps(self, test_id: str) -> set[str]:
        return self.baseline[test_id].deps

    def baseline_pass_rate(self, test_id: str) -> float:
        return self.baseline[test_id].pass_rate

    def variant_pass_rate(self, variant: str, test_id: str) -> float:
        st = self.variants.get(variant, {}).get(test_id)
        return st.pass_rate if st else self.baseline_pass_rate(test_id)

    def revealing_tests(self, variant: str, threshold: float = 0.5) -> set[str]:
        """Tests whose majority outcome flips from pass (baseline) to fail (variant) = ground truth."""
        out = set()
        for t in self.baseline:
            if self.baseline_pass_rate(t) >= threshold and self.variant_pass_rate(variant, t) < threshold:
                out.add(t)
        return out

    def is_regression(self, variant: str) -> bool:
        return len(self.revealing_tests(variant)) > 0

    def fault_matrix(self) -> dict[str, dict[str, float]]:
        """variant -> test -> pass rate under the variant."""
        return {v: {t: self.variant_pass_rate(v, t) for t in self.baseline} for v in self.variants}

    def summary(self) -> dict:
        return {
            "tests": len(self.baseline),
            "variants": len(self.variants),
            "baseline_reps": max((s.n for s in self.baseline.values()), default=0),
            "flaky_tests": sorted(t for t, s in self.baseline.items() if s.flaky),
            "total_tokens_full_suite": round(self.total_cost()),
            "revealing": {v: sorted(self.revealing_tests(v)) for v in self.variants},
        }
