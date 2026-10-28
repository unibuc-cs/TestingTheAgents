"""example clause -> one concrete scenario executed against the variant (L1).

case: PUB-01                       a catalog case, or an inline case (agent, request, context, ...)
context / fixture_patch            overrides merged into the case (values may be "=expr")
expect                             replaces the case's expectations (catalog format: state,
                                   tools_required, tools_forbidden, audit, response_contains, ...)
fault_profile                      e.g. ack_timeout_once:publish_page
"""

import time
from dataclasses import replace

from ..context import resolve
from ..model import ClauseResult
from .contracts import _make_case


def check(clause, ctx) -> ClauseResult:
    t0 = time.perf_counter()
    sc = resolve(clause.data, ctx.env())
    case = _make_case(sc, ctx)
    if sc.get("expect"):
        case = replace(case, expect=sc["expect"])
    rec = ctx.run(case, fault_profile=sc.get("fault_profile"), cache=False)
    failed = rec["failed_checks"]
    details = [f"case {case.id}: {case.request!r} -> {rec['final_message'][:120]!r}"]
    if failed:
        details += [f"failed check {c['name']}: {c.get('detail', '')}" for c in rec["checks"] if not c["ok"]]
    summary = "expected outcome observed" if rec["passed"] else f"failed checks: {', '.join(failed)}"
    cost = {"runs": 1, "seconds": round(time.perf_counter() - t0, 2)}
    return ClauseResult(clause.id, "example", "L1", "pass" if rec["passed"] else "fail", summary, details, cost)
