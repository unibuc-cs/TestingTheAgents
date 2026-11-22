"""Probe (read-only): which cases a specialist that does nothing would pass, and which checks hold before the run."""

import copy
import json
from collections import Counter

from traceeval.catalog import load_catalog
from traceeval.experiment.executor import _apply_patch
from traceeval.scoring.scorers import _state_check, score_case
from traceeval.sut import SUT_ROOT

fixture = json.loads((SUT_ROOT / "fixtures" / "base.json").read_text(encoding="utf-8"))
cases = load_catalog()
inaction, vacuous_state, n_state = [], [], 0
for c in cases:
    if c.context.get("_route_only"):
        continue
    state = copy.deepcopy(fixture)
    state.setdefault("audit", [])
    state.setdefault("translation_jobs", {})
    state.setdefault("reviews", {})
    _apply_patch(state, c.fixture_patch)
    # the orchestrator routes as expected; the specialist calls nothing and answers with a neutral sentence
    routes = []
    if "route_to" in c.expect:
        routes = [("orchestrator", c.expect["route_to"])]
    trace = {"routes": routes, "tool_calls": [], "final_message": "I could not complete this request."}
    v = score_case(c, trace, state, {"termination": "final", "steps": len(routes), "message": trace["final_message"]})
    if v.passed:
        inaction.append(c.id)
    for a in c.expect.get("state", []):
        n_state += 1
        if _state_check(state, a)[0]:
            vacuous_state.append((c.id, a[0], a[1]))
print("scenario and intent cases:", sum(1 for c in cases if not c.context.get("_route_only")))
print("cases a do-nothing specialist passes (correct routing, no tool call, a neutral answer):", len(inaction))
print("  ", inaction)
by_prop = Counter(p for c in cases if c.id in inaction for p in c.properties)
print("   their properties:", by_prop.most_common())
print("   their risk:", Counter(c.risk for c in cases if c.id in inaction).most_common())
print("state assertions:", n_state, "| already true before the run:", len(vacuous_state))
only_vacuous = Counter(cid for cid, _, _ in vacuous_state)
print("   cases with such assertions:", len(only_vacuous))
# cases whose answer check cannot tell a negated answer from the expected one
polarity = []
for c in cases:
    for needle in c.expect.get("response_contains", []):
        opts = [needle] if isinstance(needle, str) else list(needle)
        if any(
            o.lower()
            in ("compliant", "meets", "passes", "complies", "consent", "disclaimer", "protected", "broken", "100")
            for o in opts
        ):
            polarity.append((c.id, opts))
print("answer checks on a word that a wrong answer would also contain:", polarity)
