"""Coverage from several angles (docs/AEM_ALIGNMENT.md §3.5, a feature the AEM team asked for).

Two levels:

- **Suite coverage** (``suite_coverage``): how well the tests cover the application before any change. For each
  dimension of Adobe's requirements (agent, feature, skill, tool, tool error path, configuration, setting value,
  property, workflow, execution path, risk), the share of its components that at least one test covers, declared
  (the tests' metadata) and observed (the recorded traces), and what no test covers.
- **Change coverage** (``change_coverage``): for one change and the tests a strategy ran, how much of what the change
  touches they cover. It needs no ground truth, so it can be reported live: the changed components the tests
  exercised, the affected properties they checked, whether every affected mandatory property got a test, the
  affected workflows they ran, the affected features they reached, and the refusals in the changed code they
  reached.

The properties a change may affect (``affected_properties``) are known before running anything: those whose
sources (in the catalog of properties) the change touches, and those of the tests that exercised a changed
component on the original app. The workflows it may affect (``affected_workflows``) are those of the same tests.
The features it affects (``affected_features``) are those with a tool or a part it touches (``features.yaml``).

A tool error path (``ErrorPath``) is one place where the application refuses a tool call, found by reading the code
(``error_paths``); a test reaches it when its run executes that statement, which the baseline's line coverage
records.
"""

import ast
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from traceeval.catalog import load_features, load_workflows
from traceeval.mutation.changeset import _flatten
from traceeval.selection.base import matches
from traceeval.sut import SUT_ROOT


def changed_components(change) -> list:
    """The changed components a change is reasoned about by: line and tool ids are other views of a code change."""
    return [c for c in change.components if c.kind not in ("line", "tool")]


def linked_tests(change, history) -> set[str]:
    """The tests that exercised a changed component (or ran a changed line) on the original app."""
    comps, lines = changed_components(change), {c.id for c in change.components if c.kind == "line"}
    # a changed line matches a run that executed it; the other components match through ``matches``, so a change to
    # skill:x#procedure links every test that used skill x
    return {t for t in history.baseline if lines & history.deps(t) or any(matches(c, history.deps(t)) for c in comps)}


def affected_properties(change, history, catalog, props) -> set[str]:
    """The properties a change may affect: those whose sources it touches, and those of its linked tests."""
    # a property's sources name whole components (skill:x), so a change to a part (skill:x#procedure) counts by its base
    ids = {c.id for c in change.components} | {c.base for c in change.components}
    by_source = {p.id for p in props.values() if ids & set(p.sources)}
    by_tests = {p for t in linked_tests(change, history) if t in catalog for p in catalog[t].properties}
    return by_source | by_tests


def affected_workflows(change, history, catalog) -> set[str]:
    """The workflows a change may affect: those of the tests that exercised a changed component on the original
    app (a workflow test names its workflow, ``workflow: W1``)."""
    return {catalog[t].workflow for t in linked_tests(change, history) if t in catalog and catalog[t].workflow}


@lru_cache(maxsize=1)
def features():
    """The features of ``catalog/features.yaml``, read once."""
    return load_features()


def touches(change, components: set[str]) -> bool:
    """Does the change touch one of ``components``? A sub-component counts for its component (``skill:x#prose`` for
    ``skill:x``, ``agent:x.tools`` for ``agent:x``), and a function for its file (``code:<file>::f`` for
    ``code:<file>``)."""
    return any(
        c.id in components or c.base in components or c.id.split("::", 1)[0] in components for c in change.components
    )


def affected_features(change) -> set[str]:
    """The features a change affects: those with a tool or a part it touches. Known from the change alone."""
    return {f.id for f in features().values() if touches(change, f.components())}


def tools_called(history, tests) -> set[str]:
    """The tools (``tool:<name>``) the tests' baseline runs called. A delegation is recorded as a route, not as a
    tool call, so a run with a route counts as calling ``route_to_agent``."""
    deps = set().union(*(history.deps(t) for t in tests)) if tests else set()
    out = {d for d in deps if d.startswith("tool:")}
    if any(r.get("routes") for t in tests for r in history.baseline[t].runs):
        out.add("tool:route_to_agent")
    return out


def change_coverage(
    change, executed, history, catalog, props, affected: set | None = None, affected_wf: set | None = None
) -> dict:
    """What the executed tests cover of the change: shares of the changed components, of the affected properties,
    of the affected workflows, of the affected features and of the refusals in the changed code, and whether every
    affected mandatory property has at least one executed test. ``affected`` and ``affected_wf`` may be passed when
    they are already known (they depend on the change only)."""
    comps = changed_components(change)
    # every component the executed tests exercised on the original app, and the properties they check
    deps = set().union(*(history.deps(t) for t in executed)) if executed else set()
    checked = {p for t in executed if t in catalog for p in catalog[t].properties}
    affected = affected if affected is not None else affected_properties(change, history, catalog, props)
    # the affected properties that are release blockers: each needs at least one executed test
    mandatory = {p for p in affected if p in props and props[p].mandatory}
    workflows = affected_wf if affected_wf is not None else affected_workflows(change, history, catalog)
    # the workflows the executed tests run end to end
    ran = {catalog[t].workflow for t in executed if t in catalog and catalog[t].workflow}
    # a feature is reached when an executed test called one of its tools
    feats, called = affected_features(change), tools_called(history, executed)
    reached = {f for f in feats if features()[f].tool_ids() & called}
    paths = affected_error_paths(change)
    return {
        # the share of the changed components some executed test exercised
        "component_coverage": (sum(matches(c, deps) for c in comps) / len(comps)) if comps else None,
        "affected_property_coverage": (len(affected & checked) / len(affected)) if affected else None,
        "mandatory_covered": mandatory <= checked,
        "affected_workflow_coverage": (len(workflows & ran) / len(workflows)) if workflows else None,
        "affected_feature_coverage": (len(reached) / len(feats)) if feats else None,
        # the share of the refusals in the changed code some executed test reached
        "error_path_coverage": (sum(p.reached(deps) for p in paths) / len(paths)) if paths else None,
    }


def _crosses(run: dict, agents: list[str]) -> bool:
    """Did the run delegate to exactly ``agents``, in that order? A run of a plan delegates once per step, so the
    targets of its routes are the specialists in the order they ran; a step repeated for several pages delegates to
    the same specialist again, which is why only the first delegation to each counts. An in-order subsequence would
    not do: a workflow whose chain is part of a longer one (W4 inside W1) would then count as run by the longer
    one's tests."""
    first_seen = list(dict.fromkeys(target for _, target in run.get("routes", [])))
    return first_seen == list(agents)


@dataclass(frozen=True)
class ErrorPath:
    """One place where the application refuses a tool call: a statement of ``file`` (lines ``first`` to ``last``)
    in ``function`` that raises one of the errors of ``services/errors.py`` or writes out an error result. ``code``
    is the error the agent receives (``not_found``, ``permission_denied``, ``approval_required``, ...)."""

    file: str
    first: int
    last: int
    function: str
    code: str

    def reached(self, deps: set[str]) -> bool:
        """Did a run with these dependencies execute the statement (any of its lines, as the line coverage has them)?"""
        return any(f"line:{self.file}:{n}" in deps for n in range(self.first, self.last + 1))

    def __str__(self) -> str:
        return f"{self.file}:{self.first} {self.function} {self.code}"


# A crash is not a refusal, and control_tool is the stub route_to_agent returns if a model ever called it as a plain
# tool (the runtime handles it); neither is a way a tool turns a request down.
_NOT_REFUSALS = {"tool_crash", "control_tool"}


@lru_cache(maxsize=4)
def error_paths(sut_dir: Path = SUT_ROOT) -> tuple[ErrorPath, ...]:
    """Every place in the application's code where a tool call is refused, found by reading the code: a ``raise`` of
    one of the errors of ``services/errors.py`` (its ``code``), or an error result written out as a literal
    (``{"error": "<code>", ...}``, the dispatcher's gates)."""
    codes = {}  # error class -> the code the agent receives
    # the error classes of services/errors.py and the code each carries (class NotFound(ToolError): code = "not_found")
    for node in ast.parse((sut_dir / "services" / "errors.py").read_text(encoding="utf-8")).body:
        if isinstance(node, ast.ClassDef):
            for stmt in node.body:
                if isinstance(stmt, ast.Assign) and getattr(stmt.targets[0], "id", "") == "code":
                    codes[node.name] = stmt.value.value
    # every simple statement inside a function, in every module of the application
    out = []
    for path in sorted(sut_dir.rglob("*.py")):
        rel = path.relative_to(sut_dir).as_posix()
        for function, stmt in _statements(ast.parse(path.read_text(encoding="utf-8"))):
            code = _refusal(stmt, codes)
            if code and code not in _NOT_REFUSALS:
                out.append(ErrorPath(rel, stmt.lineno, stmt.end_lineno, function, code))
    return tuple(out)


def _statements(node, prefix=""):
    """(qualified function name, statement) for every simple statement inside a function, named the way the change
    sets name functions (``Class.method``, ``outer.inner``)."""
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            yield from _statements(child, f"{prefix}{child.name}.")
        elif isinstance(child, (ast.Raise, ast.Assign, ast.Return, ast.Expr)):
            if prefix:
                yield prefix[:-1], child
        elif isinstance(child, ast.stmt):  # if, for, with, try: the statements in their bodies
            yield from _statements(child, prefix)


def _refusal(stmt, codes: dict[str, str]) -> str | None:
    """The error code a statement refuses with, or None."""
    # raise NotFound(...): the code of the error class, when it is one of the application's
    if isinstance(stmt, ast.Raise) and isinstance(stmt.exc, ast.Call) and isinstance(stmt.exc.func, ast.Name):
        return codes.get(stmt.exc.func.id)
    # a literal error result, {"error": "<code>", ...}, anywhere in the statement
    for node in ast.walk(stmt):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values, strict=True):
                if getattr(key, "value", None) == "error" and isinstance(getattr(value, "value", None), str):
                    return value.value
    return None


def affected_error_paths(change, sut_dir: Path = SUT_ROOT) -> list[ErrorPath]:
    """The refusals in the code a change touches: in a changed function, or anywhere in a file changed outside its
    functions."""
    ids = {c.id for c in change.components}
    return [p for p in error_paths(sut_dir) if f"code:{p.file}::{p.function}" in ids or f"code:{p.file}" in ids]


def invoked(history, test_id: str) -> set[str]:
    """What a test's recorded baseline runs invoked: the agents, skills, tools, settings and code in their
    dependencies, plus ``tool:route_to_agent`` when a run delegated (a delegation is recorded as a route, not as a
    tool call)."""
    deps = history.deps(test_id)
    if any(r.get("routes") for r in history.baseline[test_id].runs):
        deps = deps | {"tool:route_to_agent"}
    return deps


def _components(sut_dir: Path) -> dict[str, list[str]]:
    """The application's agents, skills, tools (every tool it registers) and settings, by dimension."""
    return {
        "agent": sorted(
            yaml.safe_load(p.read_text(encoding="utf-8"))["name"] for p in (sut_dir / "agents").glob("*.yaml")
        ),
        "skill": sorted(p.name for p in (sut_dir / "skills").iterdir() if p.is_dir()),
        "tool": sorted(_registered_tools(sut_dir) | {"route_to_agent"}),
        "config": sorted(_flatten(yaml.safe_load((sut_dir / "config" / "runtime.yaml").read_text(encoding="utf-8")))),
    }


def tests_per_component(history, catalog, sut_dir: Path) -> dict[str, list[tuple[str, int, int]]]:
    """For each agent, skill, tool and feature: (name, the tests that declare it, the tests that invoke it in their
    recorded runs). A component few tests invoke is thinly covered even when the suite-level row counts it as
    covered; a gap between the two counts is metadata that does not match what the tests do."""
    tests = list(history.baseline)
    # per test: what its recorded runs invoked, and what its metadata declares
    inv = {t: invoked(history, t) for t in tests}
    dec = {t: catalog[t].declared_components() if t in catalog else set() for t in tests}
    out = {}
    for dim, names in _components(sut_dir).items():
        if dim != "config":
            out[dim] = [
                (n, sum(f"{dim}:{n}" in dec[t] for t in tests), sum(f"{dim}:{n}" in inv[t] for t in tests))
                for n in names
            ]
    # a feature is declared or invoked through its tools
    out["feature"] = [
        (f.name, sum(bool(f.tool_ids() & dec[t]) for t in tests), sum(bool(f.tool_ids() & inv[t]) for t in tests))
        for f in features().values()
    ]
    return out


def setting_value(key: str, value) -> str:
    """The component id of a setting at a value: ``config:publishing.require_review=false``."""
    return f"config:{key}={json.dumps(value)}"


def setting_values(sut_dir: Path, catalog) -> list[str]:
    """The settings at a value other than their default that the suite should cover: the other value of every
    on/off setting, and every value a case sets (``config:`` in the case)."""
    defaults = _flatten(yaml.safe_load((sut_dir / "config" / "runtime.yaml").read_text(encoding="utf-8")))
    # the other value of every on/off setting (the flattened values are JSON text, so "true" flips to false)
    flipped = {f"config:{k}={json.dumps(v != 'true')}" for k, v in defaults.items() if v in ("true", "false")}
    return sorted(flipped | {setting_value(k, v) for c in catalog.values() for k, v in c.config.items()})


def suite_coverage(history, catalog, props, sut_dir: Path) -> list[dict]:
    """One row per dimension: how many components it has, how many the tests declare and the traces show, and the
    components no test covers (declared or observed)."""
    # everything any recorded run invoked, and everything any test declares
    observed = set().union(*(invoked(history, t) for t in history.baseline))
    declared = set().union(*(c.declared_components() for c in catalog.values()))
    comps = _components(sut_dir)
    rows = []
    # the dimensions whose universe is the application's own list of agents, skills, tools and settings
    for name, prefix in (("agent", "agent"), ("skill", "skill"), ("tool", "tool"), ("configuration", "config")):
        universe = comps[prefix]
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
    # A feature is covered when a test declares or calls one of its tools (features.yaml).
    feats = features()
    dec = {f.id for f in feats.values() if f.tool_ids() & declared}
    obs = {f.id for f in feats.values() if f.tool_ids() & observed}
    rows.insert(
        1,
        {
            "dimension": "feature",
            "components": len(feats),
            "declared": len(dec),
            "observed": len(obs),
            "not covered": sorted(feats[f].name for f in set(feats) - dec - obs),
        },
    )
    # A setting at a non-default value is declared by the cases that set it, and observed when such a case's
    # recorded run read the setting.
    values = setting_values(sut_dir, catalog)
    dec = {setting_value(k, v) for c in catalog.values() for k, v in c.config.items()}
    obs = {
        setting_value(k, v)
        for t in history.baseline
        if t in catalog
        for k, v in catalog[t].config.items()
        if f"config:{k}" in invoked(history, t)
    }
    rows.insert(
        len(rows),
        {
            "dimension": "setting value",
            "components": len(values),
            "declared": len(dec & set(values)),
            "observed": len(obs & set(values)),
            "not covered": [v[len("config:") :] for v in values if v not in dec | obs],
        },
    )
    # A tool error path is observed when a baseline run executed it. A test's expect.tool_errors names a tool and an
    # error code, not the statement that refuses, so there is no declared form.
    paths = error_paths(sut_dir)
    rows.insert(
        4,
        {
            "dimension": "tool error path",
            "components": len(paths),
            "declared": None,
            "observed": sum(p.reached(observed) for p in paths),
            "not covered": [str(p) for p in paths if not p.reached(observed)],
        },
    )
    # A property is covered when a test lists it. There is no observed form: a trace cannot show which
    # requirement a test checked, so the declared and observed counts are the same number on purpose.
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
    # A workflow is declared by the tests that name it and observed when a baseline run delegates to exactly its
    # agents in order; the universe is workflows.yaml, so a workflow no test runs yet shows up as not covered.
    workflows = load_workflows()
    named = {c.workflow for c in catalog.values() if c.workflow}
    runs = [r for s in history.baseline.values() for r in s.runs]
    crossed = {w.id for w in workflows.values() if any(_crosses(r, w.agents) for r in runs)}
    rows.append(
        {
            "dimension": "workflow",
            "components": len(workflows),
            "declared": len(named & set(workflows)),
            "observed": len(crossed),
            "not covered": sorted(set(workflows) - named - crossed),
        }
    )
    # An execution path is one distinct sequence of agents and tool calls seen in a baseline run. Paths are
    # counted, not covered: there is no universe of "all paths" to compare against.
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
    risks = {}  # the recorded tests per risk level (a case added after the recording is not in it)
    for c in catalog.values():
        if c.id in history.baseline:
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
