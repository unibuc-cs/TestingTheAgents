"""Eval catalog: scenario tests (``tests/*.yaml``) and dataset-style evals (``datasets/*.yaml``).

Every item becomes an ``EvalCase``. Dataset items inherit the dataset's agent, context, declared
dependencies, risk and properties, and carry ``dataset`` = the dataset id so that selectors can
reason about "subsets of eval datasets"."""

import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml

CATALOG_ROOT = Path(__file__).resolve().parent

RISK_WEIGHT = {"critical": 4.0, "high": 3.0, "medium": 2.0, "low": 1.0}


@dataclass
class EvalCase:
    id: str
    name: str
    agent: str
    request: str
    context: dict = field(default_factory=dict)
    fixture: str = "base"
    fixture_patch: dict = field(default_factory=dict)
    fault_profile: str = "healthy"
    risk: str = "medium"
    properties: list[str] = field(default_factory=list)
    declared: dict = field(default_factory=dict)
    expect: dict = field(default_factory=dict)
    judge: dict | None = None
    dataset: str | None = None
    tags: list[str] = field(default_factory=list)
    mandatory: bool = False

    @property
    def severity(self) -> float:
        return RISK_WEIGHT.get(self.risk, 2.0)

    @property
    def is_safety(self) -> bool:
        return any(p.startswith("safety") for p in self.properties)

    def declared_components(self) -> set[str]:
        out: set[str] = set()
        for a in self.declared.get("agents", []):
            out.add(f"agent:{a}")
        for s in self.declared.get("skills", []):
            out.add(f"skill:{s}")
        for t in self.declared.get("tools", []):
            out.add(f"tool:{t}")
        for c in self.declared.get("config", []):
            out.add(f"config:{c}")
        return out

    def text(self) -> str:
        """Textual representation for IR-based strategies."""
        return " ".join(
            [
                self.id,
                self.name,
                self.request,
                json.dumps(self.context, default=str),
                " ".join(self.properties),
                json.dumps(self.declared),
            ]
        )


def _load_yaml(path: Path):
    with open(path) as fh:
        return yaml.safe_load(fh)


def load_catalog(root: Path | str = CATALOG_ROOT) -> list[EvalCase]:
    root = Path(root)
    cases: list[EvalCase] = []
    for path in sorted((root / "tests").glob("*.yaml")):
        for raw in _load_yaml(path) or []:
            cases.append(
                EvalCase(
                    id=raw["id"],
                    name=raw.get("name", raw["id"]),
                    agent=raw["agent"],
                    request=raw["request"],
                    context=dict(raw.get("context", {})),
                    fixture=raw.get("fixture", "base"),
                    fixture_patch=dict(raw.get("fixture_patch", {})),
                    fault_profile=raw.get("fault_profile", "healthy"),
                    risk=raw.get("risk", "medium"),
                    properties=list(raw.get("properties", [])),
                    declared=dict(raw.get("declared", {})),
                    expect=dict(raw.get("expect", {})),
                    judge=raw.get("judge"),
                    tags=list(raw.get("tags", [])),
                    mandatory=bool(raw.get("mandatory", False)),
                )
            )
    for path in sorted((root / "datasets").glob("*.yaml")):
        ds = _load_yaml(path)
        base_ctx = dict(ds.get("context", {}))
        for item in ds.get("items", []):
            ctx = dict(base_ctx)
            ctx.update(item.get("context", {}))
            if ds.get("route_only"):
                ctx["_route_only"] = True
            expect = dict(item.get("expect", {}))
            if "expect_route" in item:
                expect["route_to"] = item["expect_route"]
            cases.append(
                EvalCase(
                    id=f"{ds['id']}/{item['id']}",
                    name=item.get("name", item["request"]),
                    agent=item.get("agent", ds.get("agent", "orchestrator")),
                    request=item["request"],
                    context=ctx,
                    fixture=item.get("fixture", ds.get("fixture", "base")),
                    fixture_patch=dict(item.get("fixture_patch", ds.get("fixture_patch", {}))),
                    fault_profile=item.get("fault_profile", "healthy"),
                    risk=item.get("risk", ds.get("risk", "medium")),
                    properties=list(item.get("properties", ds.get("properties", []))),
                    declared=dict(item.get("declared", ds.get("declared", {}))),
                    expect=expect,
                    judge=item.get("judge"),
                    dataset=ds["id"],
                    tags=list(ds.get("tags", [])),
                )
            )
    ids = [c.id for c in cases]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise ValueError(f"duplicate eval ids: {sorted(dupes)}")
    return cases
