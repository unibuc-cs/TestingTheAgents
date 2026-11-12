"""Eval catalog: scenario tests (``tests/*.yaml``) and dataset-style evals (``datasets/*.yaml``).

Every item becomes an ``EvalCase``. Dataset items inherit the dataset's agent, context, declared
dependencies, risk and properties, and carry ``dataset`` = the dataset id so that selectors can
reason about "subsets of eval datasets". The properties a case checks must be in the catalog of properties
(``properties.yaml``), loaded as ``Property``; the workflow a case runs end to end (``workflow: W1``) must be in
``workflows.yaml``, loaded as ``Workflow``. The features of the application, the unit of coverage the Adobe Team
suggested, are in ``features.yaml``, loaded as ``Feature``."""

import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml

CATALOG_ROOT = Path(__file__).resolve().parent

RISK_WEIGHT = {"critical": 4.0, "high": 3.0, "medium": 2.0, "low": 1.0}  # a case's severity, by its risk


@dataclass
class EvalCase:
    """One test: a scenario (an entry of ``tests/*.yaml``) or a dataset item (``datasets/*.yaml``). The executor
    runs it (``experiment/executor.py::run_case``) and the scorers check ``expect`` against the final state, the
    trace and the answer (``scoring/scorers.py``)."""

    id: str  # "PUB-01", or "DS-ROUTING/r01" for a dataset item
    name: str  # what the test is about, in one line
    agent: str  # the entry agent; "orchestrator" for nearly every test, which then routes to a specialist
    request: str  # what the user types, in plain language; the model reads it
    context: dict = field(default_factory=dict)  # the ids the request is about, the user, an approval token
    fixture: str = "base"  # the starting data: fixtures/<name>.json of the app (every test uses base)
    fixture_patch: dict = field(default_factory=dict)  # dotted paths set in the starting data before the run
    config: dict = field(default_factory=dict)  # settings this case runs with, by dotted key (the rest default)
    fault_profile: str = "healthy"  # or transient_once:<tool>, ack_timeout_once:<tool>, permanent_down:<tool>
    risk: str = "medium"  # critical | high | medium | low; a weight for the metrics and the strategies
    properties: list[str] = field(default_factory=list)  # ids from properties.yaml, the requirements it checks
    declared: dict = field(default_factory=dict)  # what the author says it depends on: agents, skills, tools, config
    expect: dict = field(default_factory=dict)  # the checks: route_to, state, tools_*, tool_errors, audit, ...
    judge: dict | None = None  # a rubric, for the two cases a model also judges after the checks pass
    dataset: str | None = None  # the dataset id of an item, None for a scenario test
    workflow: str | None = None  # the multi-agent workflow this case runs end to end (an id of workflows.yaml)

    @property
    def severity(self) -> float:
        """The case's weight in the metrics and the strategies, by its risk; an unknown risk counts as medium."""
        return RISK_WEIGHT.get(self.risk, 2.0)

    @property
    def is_safety(self) -> bool:
        """Whether the case checks a safety property (their ids start with ``safety``)."""
        return any(p.startswith("safety") for p in self.properties)

    def declared_components(self) -> set[str]:
        """The hand-written ``declared`` dependencies, as component ids (agent:, skill:, tool:, config:)."""
        out: set[str] = set()
        for a in self.declared.get("agents", []):
            out.add(f"agent:{a}")
        for s in self.declared.get("skills", []):
            out.add(f"skill:{s}")
        for t in self.declared.get("tools", []):
            out.add(f"tool:{t}")
        for c in [*self.declared.get("config", []), *self.config]:  # a setting the case sets is one it depends on
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
                self.workflow or "",
                json.dumps(self.declared),
            ]
        )


@dataclass
class Property:
    """A behavioural requirement the tests check (one entry of ``properties.yaml``): its category, how the tests
    check it (state, trace, judge, dataset), whether it is mandatory (a release blocker), the share of its tests
    that must pass on a run, and where it comes from: the components that state it, as the ids change sets use
    (``skill:<name>#procedure``, ``agent:<name>.<field>``, ``config:<key>``) or a spec (``spec:FS-0101``)."""

    id: str
    category: str
    description: str
    checked_by: list[str]
    mandatory: bool = False
    threshold: float = 1.0
    sources: list[str] = field(default_factory=list)


@dataclass
class Workflow:
    """One multi-agent workflow (an entry of ``workflows.yaml``): the chain of specialists a plan for it delegates
    to, in order. A test names the workflow it runs end to end; a run covers it when it delegates to exactly these
    agents, in this order (repeated delegations to a step's agent allowed)."""

    id: str
    name: str
    agents: list[str]


@dataclass
class Feature:
    """One feature of the application (an entry of ``features.yaml``): a capability the user sees. ``tools`` carry
    it out, so a test covers it when it declares or calls one of them; ``parts`` are the other components it is
    made of (skill:, agent:, config:, code: ids), so a change that touches a tool or a part affects it."""

    id: str
    name: str
    tools: list[str]
    parts: list[str] = field(default_factory=list)

    def tool_ids(self) -> set[str]:
        """Its tools as component ids (``tool:<name>``): a test that declares or calls one covers the feature."""
        return {f"tool:{t}" for t in self.tools}

    def components(self) -> set[str]:
        """Every component id the feature is made of: its tools and its parts."""
        return self.tool_ids() | set(self.parts)


def _load_yaml(path: Path):
    """The parsed YAML document at ``path``."""
    with open(path, encoding="utf-8") as fh:  # the same text on every platform, so the cache keys agree
        return yaml.safe_load(fh)


def load_properties(root: Path | str = CATALOG_ROOT) -> dict[str, Property]:
    """The catalog of properties, by id."""
    return {p["id"]: Property(**p) for p in _load_yaml(Path(root) / "properties.yaml")}


def load_workflows(root: Path | str = CATALOG_ROOT) -> dict[str, Workflow]:
    """The multi-agent workflows, by id."""
    return {w["id"]: Workflow(**w) for w in _load_yaml(Path(root) / "workflows.yaml")}


def load_features(root: Path | str = CATALOG_ROOT) -> dict[str, Feature]:
    """The features of the application, by id."""
    return {f["id"]: Feature(**f) for f in _load_yaml(Path(root) / "features.yaml")}


def load_catalog(root: Path | str = CATALOG_ROOT) -> list[EvalCase]:
    """Every eval case, scenario tests first and then dataset items, in file order. Fails on a repeated id, a
    property missing from ``properties.yaml`` or a workflow missing from ``workflows.yaml``."""
    root = Path(root)
    cases: list[EvalCase] = []
    # Scenario tests: one entry per item of each tests/*.yaml, the fields it leaves out at their defaults.
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
                    config=dict(raw.get("config", {})),
                    fault_profile=raw.get("fault_profile", "healthy"),
                    risk=raw.get("risk", "medium"),
                    properties=list(raw.get("properties", [])),
                    declared=dict(raw.get("declared", {})),
                    expect=dict(raw.get("expect", {})),
                    judge=raw.get("judge"),
                    workflow=raw.get("workflow"),
                )
            )
    # Dataset items: each inherits the dataset's agent, context, fixture, risk, properties and declared dependencies,
    # and its own values win where it has them.
    for path in sorted((root / "datasets").glob("*.yaml")):
        ds = _load_yaml(path)
        base_ctx = dict(ds.get("context", {}))
        for item in ds.get("items", []):
            ctx = dict(base_ctx)
            ctx.update(item.get("context", {}))
            if ds.get("route_only"):  # score the routing decision only: the chosen specialist does not run
                ctx["_route_only"] = True
            expect = dict(item.get("expect", {}))
            if "expect_route" in item:  # the dataset's shorthand for expect.route_to
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
                )
            )
    # The catalog must be consistent before anything runs: unique ids, and only known properties and workflows.
    ids = [c.id for c in cases]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise ValueError(f"duplicate eval ids: {sorted(dupes)}")
    unknown = sorted({p for c in cases for p in c.properties} - set(load_properties(root)))
    if unknown:
        raise ValueError(f"properties missing from properties.yaml: {unknown}")
    unknown = sorted({c.workflow for c in cases if c.workflow} - set(load_workflows(root)))
    if unknown:
        raise ValueError(f"workflows missing from workflows.yaml: {unknown}")
    return cases
