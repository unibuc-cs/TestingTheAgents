"""trace clause -> temporal rule checked over recorded runs (L3, "monitored").

scope: {tool: publish_page} | {tools: [...]} | {tool_kind: [write, guarded]} | {cases: [...]} | all
    which catalog runs the rule ranges over (resolved from the baseline traces: the product model)
stream: events | audit            events = trace events of the run; audit = the application's audit log
event: {kind: tool.call, tool: publish_page, status: ok}     items the rule is about (field equality;
                                                              a list value means "one of")
rule: always | never | precedes
  always   every matching item satisfies `where`
  never    no matching item exists (or none satisfying `where`)
  precedes every matching item is preceded, in the same run, by an item matching `before`
           that agrees on the `same` fields
where / before_where: expressions over `event`, `run`, `config(...)` and the helpers in context.py
must_cover: {model: status_setters, except: [unpublish_page]}
    completeness check against the product model: every tool the model says can do what the rule is
    about must be listed in `event.<field>` (reported as a gap, not a failure)
"""

import time

from ..context import evaluate, wrap
from ..model import ClauseResult


def check(clause, ctx) -> ClauseResult:
    t0 = time.perf_counter()
    runs = ctx.run_many(cases_in_scope(clause.get("scope", "all"), ctx.model, ctx.catalog))
    rule = clause.get("rule", "always")
    violations, checked = [], 0
    for tid, rec in runs.items():
        items = _items(rec, clause.get("stream", "events"))
        for i, item in enumerate(items):
            if not _match(item, clause["event"]):
                continue
            checked += 1
            try:
                if rule == "always":
                    ok = bool(evaluate(clause["where"], ctx.env(run=rec, event=wrap(item))))
                elif rule == "never":  # without `where`, any matching item is a violation
                    ok = not (
                        clause.get("where") is None or evaluate(clause["where"], ctx.env(run=rec, event=wrap(item)))
                    )
                elif rule == "precedes":
                    ok = _preceded(items[:i], item, clause, ctx, rec)
                else:
                    raise ValueError(f"unknown rule {rule}")
            except Exception as exc:  # noqa: BLE001 - an unevaluable rule is a violation, not a crash
                ok, item = False, dict(item, _error=f"{type(exc).__name__}: {exc}")
            if not ok:
                violations.append(f"{tid}: {_short(item)}")
    details = [f"{len(runs)} runs in scope, {checked} matching {clause.get('stream', 'events')} checked"]
    details += violations[:5]
    status = "fail" if violations else "pass"
    gaps = _coverage_gap(clause, ctx)
    if gaps and status == "pass":
        status = "gap"
    details += gaps
    summary = f"{len(violations)} violation(s) in {len(runs)} runs" if violations else f"holds over {len(runs)} runs"
    if gaps:
        summary += "; GAP: rule does not cover every path the product model finds"
    cost = {"runs": len(runs), "seconds": round(time.perf_counter() - t0, 2)}
    return ClauseResult(clause.id, "trace", "L3", status, summary, details, cost)


def cases_in_scope(scope, model, catalog: dict) -> list[str]:
    """The catalog cases a trace clause ranges over; a tool scope picks the cases whose baseline run called it."""
    if scope in (None, "all"):
        return list(catalog)
    if "cases" in scope:
        return [c for c in scope["cases"] if c in catalog]
    tools = scope.get("tools") or ([scope["tool"]] if "tool" in scope else None)
    kinds = scope.get("tool_kind")
    kinds = [kinds] if isinstance(kinds, str) else kinds
    return model.cases_calling(tools=tools, kinds=kinds)


def _items(rec: dict, stream: str) -> list[dict]:
    if stream == "audit":
        return list(rec["final_state"].get("audit", []))
    return list(rec["events"])


def _match(item: dict, pattern: dict) -> bool:
    """Field equality with every key of ``pattern``; a list value means "one of"."""
    for k, v in pattern.items():
        actual = item.get(k)
        if isinstance(v, list):
            if actual not in v:
                return False
        elif actual != v:
            return False
    return True


def _preceded(earlier: list[dict], item: dict, clause, ctx, rec) -> bool:
    """Is some earlier item a matching ``before`` that agrees on the ``same`` fields and passes ``before_where``?"""
    for prev in earlier:
        if not _match(prev, clause["before"]):
            continue
        if any(prev.get(f) != item.get(f) for f in clause.get("same", [])):
            continue
        if clause.get("before_where") and not evaluate(
            clause["before_where"], ctx.env(run=rec, event=wrap(item), before=wrap(prev))
        ):
            continue
        return True
    return False


def _coverage_gap(clause, ctx) -> list[str]:
    mc = clause.get("must_cover")
    if not mc:
        return []
    # the event field naming what the rule covers: an audit action or a tool
    field = mc.get("field", "action" if clause.get("stream") == "audit" else "tool")
    covered = clause["event"].get(field)
    covered = set(covered if isinstance(covered, list) else [covered])
    if mc["model"] == "status_setters":
        found = set(ctx.model.status_setters()) - set(mc.get("except", []))
    else:
        raise ValueError(f"unknown model query {mc['model']}")
    missing = sorted(found - covered)
    return (
        [
            f"product model: {sorted(found)} can change a page status; "
            f"the rule covers {sorted(covered)} -> missing {missing}"
        ]
        if missing
        else []
    )


def _short(item: dict) -> str:
    """The fields of an event or audit entry worth quoting in a violation."""
    keep = {
        k: v
        for k, v in item.items()
        if k in ("kind", "tool", "action", "status", "args", "page_id", "seq", "idempotency_key", "_error", "broken")
    }
    return str(keep)
