"""Coverage from several angles (docs/AEM_ALIGNMENT.md §3.5, a feature the AEM team asked for).

Two levels:

- **Suite coverage** (``suite_coverage``): how well the tests cover the application before any change. For each
  dimension of Adobe's requirements (agent, skill, tool, configuration, property, execution path, risk), the share
  of its components that at least one test covers, declared (the tests' metadata) and observed (the recorded
  traces), and what no test covers. Workflows join when the multi-agent workflows exist.
- **Change coverage** (``change_coverage``): for one change and the tests a strategy ran, how much of what the change
  touches they cover. It needs no ground truth, so it can be reported live: the changed components the tests
  exercised, the affected properties they checked, and whether every affected mandatory property got a test.

The properties a change may affect (``affected_properties``) are known before running anything: those whose
sources (in the catalog of properties) the change touches, and those of the tests that exercised a changed
component on the original app.
"""

import re
from pathlib import Path

import yaml

from traceeval.mutation.changeset import _flatten
from traceeval.selection.base import matches


def changed_components(change) -> list:
    """The changed components a change is reasoned about by: line and tool ids are other views of a code change."""
    return [c for c in change.components if c.kind not in ("line", "tool")]


def linked_tests(change, history) -> set[str]:
    """The tests that exercised a changed component (or ran a changed line) on the original app."""
    comps, lines = changed_components(change), {c.id for c in change.components if c.kind == "line"}
    return {t for t in history.baseline if lines & history.deps(t) or any(matches(c, history.deps(t)) for c in comps)}


def affected_properties(change, history, catalog, props) -> set[str]:
    """The properties a change may affect: those whose sources it touches, and those of its linked tests."""
    ids = {c.id for c in change.components} | {c.base for c in change.components}
    by_source = {p.id for p in props.values() if ids & set(p.sources)}
    by_tests = {p for t in linked_tests(change, history) if t in catalog for p in catalog[t].properties}
    return by_source | by_tests


def change_coverage(change, executed, history, catalog, props, affected: set | None = None) -> dict:
    """What the executed tests cover of the change: shares of the changed components and of the affected
    properties, and whether every affected mandatory property has at least one executed test. ``affected`` may be
    passed when it is already known (it depends on the change only)."""
    comps = changed_components(change)
    deps = set().union(*(history.deps(t) for t in executed)) if executed else set()
    checked = {p for t in executed if t in catalog for p in catalog[t].properties}
    affected = affected if affected is not None else affected_properties(change, history, catalog, props)
    mandatory = {p for p in affected if p in props and props[p].mandatory}
    return {
        "component_coverage": (sum(matches(c, deps) for c in comps) / len(comps)) if comps else None,
        "affected_property_coverage": (len(affected & checked) / len(affected)) if affected else None,
        "mandatory_covered": mandatory <= checked,
    }


def suite_coverage(history, catalog, props, sut_dir: Path) -> list[dict]:
    """One row per dimension: how many components it has, how many the tests declare and the traces show, and the
    components no test covers (declared or observed)."""
    observed = set().union(*(history.deps(t) for t in history.baseline))
    if any(r.get("routes") for s in history.baseline.values() for r in s.runs):
        observed.add("tool:route_to_agent")  # a delegation is recorded as a route, not as a tool call
    declared = set().union(*(c.declared_components() for c in catalog.values()))
    agents = sorted(yaml.safe_load(p.read_text(encoding="utf-8"))["name"] for p in (sut_dir / "agents").glob("*.yaml"))
    skills = sorted(p.name for p in (sut_dir / "skills").iterdir() if p.is_dir())
    config = sorted(_flatten(yaml.safe_load((sut_dir / "config" / "runtime.yaml").read_text(encoding="utf-8"))))
    tools = sorted({d.split(":", 1)[1] for d in observed if d.startswith("tool:")} | _registered_tools(sut_dir))
    rows = []
    for name, prefix, universe in (
        ("agent", "agent", agents),
        ("skill", "skill", skills),
        ("tool", "tool", tools),
        ("configuration", "config", config),
    ):
        ids = {u: f"{prefix}:{u}" for u in universe}
        dec = {u for u, i in ids.items() if i in declared}
        obs = {u for u, i in ids.items() if i in observed}
        rows.append(
            {
                "dimension": name,
                "components": len(universe),
                "declared": len(dec),
                "observed": len(obs),
                "not covered": sorted(set(universe) - dec - obs),
            }
        )
    tested = {p for c in catalog.values() for p in c.properties}
    rows.append(
        {
            "dimension": "property",
            "components": len(props),
            "declared": len(tested & set(props)),
            "observed": len(tested & set(props)),
            "not covered": sorted(set(props) - tested),
        }
    )
    paths = {
        tuple(r.get("agents", [])) + ("|",) + tuple(r.get("tools", []))
        for s in history.baseline.values()
        for r in s.runs
    }
    rows.append(
        {
            "dimension": "execution path",
            "components": len(paths),
            "declared": None,
            "observed": len(paths),
            "not covered": [],
        }
    )
    risks = {}
    for c in catalog.values():
        risks[c.risk] = risks.get(c.risk, 0) + 1
    rows.append(
        {
            "dimension": "risk",
            "components": len(risks),
            "declared": len(risks),
            "observed": len(risks),
            "not covered": [],
            "detail": ", ".join(f"{k} {v}" for k, v in sorted(risks.items())),
        }
    )
    return rows


def _registered_tools(sut_dir: Path) -> set[str]:
    """The tools the application registers (``@tool("name", ...)`` in its tool modules), so that a tool no test
    calls shows up as uncovered."""
    names = set()
    for path in (sut_dir / "tools").glob("*.py"):
        names |= set(re.findall(r'@tool\(\s*"([a-z_]+)"', path.read_text(encoding="utf-8")))
    return names
