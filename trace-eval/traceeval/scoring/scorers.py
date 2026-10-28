"""Deterministic scorers over (final state, trace, final message) plus an optional judge step.

Result classification follows the TRACE-Eval handoff: PASS, AGENT_FAILURE, HARNESS_ERROR.
(INFRA_INVALID is reserved for runs where the environment, not the agent, was broken.)"""

from dataclasses import dataclass, field

_MISSING = object()


@dataclass
class Verdict:
    passed: bool
    classification: str  # PASS | AGENT_FAILURE | HARNESS_ERROR | INFRA_INVALID
    checks: list[dict] = field(default_factory=list)
    judge: dict | None = None

    def failed_checks(self) -> list[str]:
        return [c["name"] for c in self.checks if not c["ok"]]


def _resolve(data, path: str):
    node = data
    for part in path.split("."):
        if isinstance(node, dict):
            if part not in node:
                return _MISSING
            node = node[part]
        elif isinstance(node, list):
            try:
                node = node[int(part)]
            except (ValueError, IndexError):
                return _MISSING
        else:
            return _MISSING
    return node


def _state_check(state: dict, assertion) -> tuple[bool, str]:
    path, op, value = assertion
    actual = _resolve(state, path)
    if op == "absent":
        return actual is _MISSING, f"{path} absent? actual={'MISSING' if actual is _MISSING else actual!r}"
    if op == "exists":
        return actual is not _MISSING, f"{path} exists? {actual is not _MISSING}"
    if actual is _MISSING:
        return False, f"{path} missing"
    if op == "==":
        return actual == value, f"{path} == {value!r} (actual {actual!r})"
    if op == "!=":
        return actual != value, f"{path} != {value!r} (actual {actual!r})"
    if op == "len":
        return len(actual) == value, f"len({path}) == {value} (actual {len(actual)})"
    if op == "contains":
        return value in actual, f"{path} contains {value!r} (actual {actual!r})"
    if op == "in":
        return actual in value, f"{path} in {value!r} (actual {actual!r})"
    if op == ">=":
        return actual >= value, f"{path} >= {value} (actual {actual})"
    if op == "<=":
        return actual <= value, f"{path} <= {value} (actual {actual})"
    return False, f"unknown op {op}"


def score_case(case, trace: dict, state: dict, run: dict, error: str | None = None) -> Verdict:
    """Evaluate every expectation of ``case``. ``trace`` is the recorder's ``to_dict()``."""
    if error is not None:
        return Verdict(False, "HARNESS_ERROR", [{"name": "harness", "ok": False, "detail": error}])
    exp = case.expect
    checks: list[dict] = []

    def add(name, ok, detail=""):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    calls = trace.get("tool_calls", [])
    ok_tools = {c["tool"] for c in calls if c.get("status") == "ok"}
    attempted = {c["tool"] for c in calls}
    message = trace.get("final_message") or run.get("message") or ""

    if "route_to" in exp:
        routes = trace.get("routes", [])
        first = routes[0][1] if routes else None
        add("route_to", first == exp["route_to"], f"expected {exp['route_to']}, got {first}")
    for assertion in exp.get("state", []):
        ok, detail = _state_check(state, assertion)
        add(f"state:{assertion[0]}", ok, detail)
    for tool in exp.get("tools_required", []):
        add(f"required:{tool}", tool in ok_tools, f"ok tools: {sorted(ok_tools)}")
    for tool in exp.get("tools_forbidden", []):
        add(f"forbidden:{tool}", tool not in ok_tools, f"ok tools: {sorted(ok_tools)}")
    for tool in exp.get("tools_not_attempted", []):
        add(f"not_attempted:{tool}", tool not in attempted, f"attempted: {sorted(attempted)}")
    for spec in exp.get("tool_attempts", []):
        mx = max([c.get("attempts", 0) for c in calls if c["tool"] == spec["tool"]] or [0])
        add(f"attempts:{spec['tool']}", mx >= spec.get("min", 1), f"max attempts {mx}")
    for spec in exp.get("audit", []):
        spec = dict(spec)
        action, count = spec.pop("action"), spec.pop("count")
        n = sum(
            1
            for e in state.get("audit", [])
            if e.get("action") == action and all(e.get(k) == v for k, v in spec.items())
        )
        add(f"audit:{action}", n == count, f"expected {count}, found {n}")
    for needle in exp.get("response_contains", []):
        add(f"response~{needle[:24]}", needle.lower() in message.lower(), f"message: {message[:120]!r}")
    for needle in exp.get("response_excludes", []):
        add(f"response!~{needle[:24]}", needle.lower() not in message.lower(), f"message: {message[:120]!r}")
    if "max_steps" in exp:
        add("max_steps", (run.get("steps") or 0) <= exp["max_steps"], f"steps {run.get('steps')}")
    if "termination" in exp:
        add("termination", run.get("termination") == exp["termination"], f"got {run.get('termination')}")

    passed = all(c["ok"] for c in checks)
    return Verdict(passed, "PASS" if passed else "AGENT_FAILURE", checks)


def simulated_judge(case, message: str) -> dict:
    """Stand-in for an LLM judge in simulated mode: deterministic rubric check with a token charge
    proportional to the evidence handed to the judge."""
    judge = case.judge or {}
    must = judge.get("must_mention", [])
    ok = all(m.lower() in message.lower() for m in must)
    tokens = 450 + len(judge.get("rubric", "")) // 4 + len(message) // 4
    return {"ok": ok, "tokens": tokens, "rubric": judge.get("rubric", ""), "mode": "simulated"}
