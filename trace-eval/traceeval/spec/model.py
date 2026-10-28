"""Spec and clause data model (loaded from ``traceeval/specs/*.yaml``) and the clause result type."""

from dataclasses import dataclass, field
from pathlib import Path

import yaml

SPECS_ROOT = Path(__file__).resolve().parent.parent / "specs"

KINDS = ("setting", "contract", "trace", "example", "placement")

# the assurance rung a clause kind reaches when its check passes (contracts: L5 only when proved)
RUNG = {"setting": "L4", "contract": "L2", "trace": "L3", "example": "L1", "placement": "L4"}
RUNG_LABEL = {
    "L0": "reviewed",
    "L1": "example-tested",
    "L2": "property-tested",
    "L3": "monitored",
    "L4": "statically checked",
    "L5": "proven",
}


@dataclass
class Clause:
    id: str
    kind: str
    text: str = ""  # one-line human reading of the clause
    data: dict = field(default_factory=dict)  # kind-specific fields, as written in the YAML

    def __getitem__(self, key):
        return self.data[key]

    def get(self, key, default=None):
        return self.data.get(key, default)


@dataclass
class Spec:
    id: str
    title: str
    intent: str
    clauses: list[Clause]
    owner: str = ""
    path: Path | None = None

    def clause(self, cid: str) -> Clause:
        for c in self.clauses:
            if c.id == cid:
                return c
        raise KeyError(cid)


@dataclass
class ClauseResult:
    clause_id: str
    kind: str
    rung: str  # rung reached (pass) or attempted (fail)
    status: str  # pass | fail | gap | skipped
    summary: str
    details: list[str] = field(default_factory=list)
    cost: dict = field(default_factory=dict)  # runs, examples, seconds

    def to_dict(self) -> dict:
        return self.__dict__.copy()


def load_spec(path: Path | str) -> Spec:
    path = Path(path)
    raw = yaml.safe_load(path.read_text())
    clauses = []
    for c in raw.get("clauses", []):
        kind = c["kind"]
        if kind not in KINDS:
            raise ValueError(f"{path.name}: unknown clause kind {kind!r} (clause {c.get('id')})")
        data = {k: v for k, v in c.items() if k not in ("id", "kind", "text")}
        clauses.append(Clause(id=str(c["id"]), kind=kind, text=c.get("text", ""), data=data))
    return Spec(
        id=raw["id"],
        title=raw["title"],
        intent=raw.get("intent", "").strip(),
        clauses=clauses,
        owner=raw.get("owner", ""),
        path=path,
    )


def load_specs(root: Path | str = SPECS_ROOT, ids: list[str] | None = None) -> list[Spec]:
    specs = [load_spec(p) for p in sorted(Path(root).glob("FS-*.yaml"))]
    if ids:
        specs = [s for s in specs if s.id in ids]
    return specs
