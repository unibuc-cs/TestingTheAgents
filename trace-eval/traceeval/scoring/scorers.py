"""Deterministic scorers over (final state, trace, final message) plus an optional judge step.

Result classification follows the TRACE-Eval handoff, extended with the tool boundary:
    PASS           every expectation holds
    TOOL_ERROR     a tool call crashed, or failed with an error the case does not allow and was not recovered
    AGENT_FAILURE  tool calls behaved as allowed, but an expectation failed
    HARNESS_ERROR  the run itself raised (fixture, config, agent loop)
    INFRA_INVALID  the environment broke the run, not the agent or the app: the model server or the network did not
                   answer, or a replay met a request it has no recorded answer for. Such a run says nothing about the
                   agent, so it is left out of pass rates and replays (``experiment/history.py``).

Tool errors: a case lists the errors it expects in ``expect.tool_errors`` ({tool: code or [codes]}, or
``"*"`` for any). Any other error fails the case (check ``tool_error:<tool>``) unless a later call of the same tool
succeeded - e.g. an agent that fixes its own arguments. A crash (check ``crash:<tool>``) always fails.

The answer is checked for facts, not wording: ``response_contains`` lists what it must report (an item may be a
list of alternatives), and a run that ends with an answer must not end with an empty one (check ``answered``).
``tool_results`` checks what a tool returned (its last successful call), like the state.

Order, for runs that cross several agents: ``agents_in_order`` lists agents that the run's delegations must reach
in that order, and ``tools_in_order`` tools whose successful calls must come in that order (other agents and
calls may come in between).

A case with a ``judge`` block also has its answer read by a model against the block's rubric (``judge_answer``),
for what a fixed check cannot see, such as whether the answer confirms what was done."""

import re
from dataclasses import dataclass, field

_MISSING = object()


@dataclass
class Verdict:
    passed: bool
    classification: str  # PASS | TOOL_ERROR | AGENT_FAILURE | HARNESS_ERROR | INFRA_INVALID
    checks: list[dict] = field(default_factory=list)

    def failed_checks(self) -> list[str]:
        return [c["name"] for c in self.checks if not c["ok"]]


def _resolve(data, path: str):
    """The value at a dotted path ("pages.p1.status", list items by index), or _MISSING."""
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
    """Check one [path, op, value] assertion; returns (ok, detail for the record)."""
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


def score_case(case, trace: dict, state: dict, run: dict, error: str | None = None, infra: bool = False) -> Verdict:
    """Evaluate every expectation of ``case``. ``trace`` is the recorder's ``to_dict()``. ``error`` is the traceback of
    a run that raised; ``infra`` says that the environment, not the run, caused it."""
    if error is not None:
        kind, label = ("infra", "INFRA_INVALID") if infra else ("harness", "HARNESS_ERROR")
        return Verdict(False, label, [{"name": kind, "ok": False, "detail": error}])
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
    if "agents_in_order" in exp:
        targets = [target for _, target in trace.get("routes", [])]
        add("agents_in_order", _in_order(targets, exp["agents_in_order"]), f"delegated to: {targets}")
    if "tools_in_order" in exp:
        ok_calls = [c["tool"] for c in calls if c.get("status") == "ok"]
        add("tools_in_order", _in_order(ok_calls, exp["tools_in_order"]), f"ok calls: {ok_calls}")
    for spec in exp.get("tool_attempts", []):
        mx = max([c.get("attempts", 0) for c in calls if c["tool"] == spec["tool"]] or [0])
        add(f"attempts:{spec['tool']}", mx >= spec.get("min", 1), f"max attempts {mx}")
    # The last successful result of a tool, checked like the state: [tool, path, op, value].
    for tool, *assertion in exp.get("tool_results", []):
        last = next((c.get("result") for c in reversed(calls) if c["tool"] == tool and c.get("status") == "ok"), None)
        ok, detail = _state_check(last, assertion) if last is not None else (False, f"no successful {tool} call")
        add(f"result:{tool}.{assertion[0]}", ok, detail)
    for spec in exp.get("audit", []):
        spec = dict(spec)
        action, count = spec.pop("action"), spec.pop("count")
        n = sum(
            1
            for e in state.get("audit", [])
            if e.get("action") == action and all(e.get(k) == v for k, v in spec.items())
        )
        add(f"audit:{action}", n == count, f"expected {count}, found {n}")
    # A run that ended with the agent's own answer must say something to the user; a run that only routes
    # (dataset items marked route_only) or was cut off by the step budget has no answer to judge.
    if run.get("termination") == "final" and not getattr(case, "context", {}).get("_route_only"):
        add("answered", bool(message.strip()), f"message: {message[:120]!r}")
    # Facts the answer must report. An item that is a list is a set of alternatives; any one of them will do.
    for needle in exp.get("response_contains", []):
        options = [needle] if isinstance(needle, str) else list(needle)
        found = any(o.lower() in message.lower() for o in options)
        add(f"response~{options[0][:24]}", found, f"message: {message[:120]!r}")
    for needle in exp.get("response_excludes", []):
        add(f"response!~{needle[:24]}", needle.lower() not in message.lower(), f"message: {message[:120]!r}")
    if "max_steps" in exp:
        add("max_steps", (run.get("steps") or 0) <= exp["max_steps"], f"steps {run.get('steps')}")
    if "termination" in exp:
        add("termination", run.get("termination") == exp["termination"], f"got {run.get('termination')}")
    for name, detail in _tool_failures(calls, exp.get("tool_errors") or {}):
        add(name, False, detail)

    passed = all(c["ok"] for c in checks)
    if passed:
        return Verdict(True, "PASS", checks)
    at_tool = any(c["name"].startswith(("crash:", "tool_error:")) for c in checks if not c["ok"])
    return Verdict(False, "TOOL_ERROR" if at_tool else "AGENT_FAILURE", checks)


def _tool_failures(calls: list[dict], allowed) -> list[tuple[str, str]]:
    """(check name, detail) for every crash, and for every disallowed error that no later call of the
    same tool recovered from (``allowed == "*"`` allows every error). One entry per (tool, error code)."""
    out, seen = [], set()
    for i, call in enumerate(calls):
        tool, status, code = call["tool"], call.get("status"), call.get("error")
        if status == "crash":
            name = f"crash:{tool}"
        elif status == "error" and allowed != "*" and code not in _codes(allowed.get(tool)):
            if any(c["tool"] == tool and c.get("status") == "ok" for c in calls[i + 1 :]):
                continue
            name = f"tool_error:{tool}"
        else:
            continue
        if (name, code) not in seen:
            seen.add((name, code))
            out.append((name, f"{code}: {call.get('message') or ''}"))
    return out


def _in_order(seen: list[str], wanted: list[str]) -> bool:
    """Whether ``wanted`` occurs in ``seen`` in the same order, with anything allowed in between."""
    rest = iter(seen)
    return all(w in rest for w in wanted)  # each ``in`` consumes the iterator up to the match


def _codes(value) -> set[str]:
    if value is None:
        return set()
    return {value} if isinstance(value, str) else set(value)


JUDGE_PROMPT = (
    "You check an assistant's final answer against a rubric. Reply PASS if the answer meets the rubric and FAIL "
    "if it does not, then one short sentence saying why."
)


def judge_answer(case, message: str, client, model: str) -> dict:
    """The judge step of a case with a ``judge`` block: the model behind ``client`` reads the request, the rubric
    and the answer, and says PASS or FAIL. It decodes greedily, so the same answer always gets the same verdict;
    its tokens count in the test's cost."""
    rubric = case.judge["rubric"]
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": JUDGE_PROMPT},
            {"role": "user", "content": f"Request: {case.request}\n\nRubric: {rubric}\n\nAnswer: {message}"},
        ],
        temperature=0.0,
        max_tokens=80,
    )
    verdict = (resp.choices[0].message.content or "").strip()
    found = re.search(r"\b(PASS|FAIL)\b", verdict.upper())  # whichever word comes first decides
    return {
        "ok": bool(found) and found.group(1) == "PASS",
        "tokens": resp.usage.prompt_tokens + resp.usage.completion_tokens,
        "rubric": rubric,
        "verdict": verdict,
    }
