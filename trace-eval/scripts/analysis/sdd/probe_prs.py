"""Probe 3: pull requests written to test what the spec layer's verdict rests on. Everything is written under
the scratch workdir given as argv[1]; the repository is only read. Agents replay Gemma's recorded answers."""

import json
import sys
from collections import Counter
from pathlib import Path

from traceeval.catalog import load_catalog
from traceeval.experiment.sutloader import load_sut
from traceeval.mutation.catalog import Mutation
from traceeval.mutation.engine import materialize_variant
from traceeval.spec import load_specs
from traceeval.spec import prs as P
from traceeval.spec.checks import CHECKERS, traces
from traceeval.spec.context import CheckContext
from traceeval.spec.model import load_spec
from traceeval.spec.product import ProductModel
from traceeval.spec.prs import PR
from traceeval.spec.runner import evaluate_pr, record_baseline

workdir = Path(sys.argv[1])
catalog = {c.id: c for c in load_catalog()}
sut_dir, runs, deps = record_baseline(workdir, catalog)
specs = {s.id: s for s in load_specs()}


def show(title, ev, only_bad=False):
    print(f"\n=== {title}\n    verdict: {ev['verdict']}   files: {ev['change']['files']}   runs: {ev['cost']['runs']}")
    for c in ev["clauses"]:
        if only_bad and c["status"] == "pass":
            continue
        print(f"    {c['status']:4s} {c['rung']}/{c['required']} {c['clause_id']}: {c['summary'][:150]}")


def judge(spec_id, pid, edits, **kw):
    pr = PR(f"{spec_id}/{pid}", spec_id, pid, "?", Mutation(f"probe_{spec_id}_{pid}", "pr", pid, True, edits))
    return evaluate_pr(specs[spec_id], pr, workdir, catalog, runs, deps, **kw)


def infra_runs(spec_id, pid, edits):
    """Classifications of the catalog runs in scope of the spec's trace clauses on this variant."""
    mut = Mutation(f"probe_{spec_id}_{pid}_ctx", "pr", pid, True, edits)
    vdir, _ = materialize_variant(mut, workdir / "variants")
    sut = load_sut(vdir)
    ctx = CheckContext(sut=sut, model=ProductModel(vdir, runs, deps), catalog=catalog, variant=pid)
    out = []
    for clause in specs[spec_id].clauses:
        if clause.kind != "trace":
            continue
        res = CHECKERS["trace"](clause, ctx)
        out.append((clause.id, res.status, res.summary, res.details[0]))
    classes = Counter(rec["classification"] for rec in ctx.runs.values())
    sut.unload()
    return out, classes


# ---------------------------------------------------------------- A. the proven function is not the one the gate uses
# FS-0101's correct PR, except that the gate compares for itself and forgets the lower bound; review_age_ok stays,
# correct and unused.
a_edits = P._with(
    P.FS0101_CORRECT,
    (
        "replace",
        "services/workflow.py",
        "    if age is None or not review_age_ok(age, max_age_days):\n",
        "    if age is None or age > max_age_days:\n",
    ),
)
ev = judge("FS-0101", "gate_bypasses_proven_fn", a_edits)
show("A. FS-0101: gate does its own comparison without the lower bound; review_age_ok proven but unused", ev)

# what the accepted variant does with a future-dated approval, against the correct PR
for label, edits in (("correct PR", P.FS0101_CORRECT), ("variant A", a_edits)):
    vdir, _ = materialize_variant(Mutation(f"probe_a_{label[:3]}", "pr", label, True, edits), workdir / "variants")
    sut = load_sut(vdir)
    state = sut.sub("services.state").State.from_fixture(vdir / "fixtures" / "base.json")
    state.pages["p4"]["review"]["approved_on"] = "2026-11-15"  # today is 2026-10-28: the approval lies 18 days ahead
    try:
        out = sut.sub("services.workflow").publish_page(state, "p4", "bob", None, 30)
        print(f"    {label}: future-dated approval -> published: {out['status']}")
    except Exception as exc:  # noqa: BLE001
        print(f"    {label}: future-dated approval -> refused: {type(exc).__name__}: {exc}")
    sut.unload()

# ---------------------------------------------------------------- B. the rule in the adapter, behind decoy functions
b_tool_fn = (
    "append",
    "tools/publish_tools.py",
    """

def _refuse_stale_approval(ctx, page_id: str):
    max_age = ctx.config.get("publishing.review_max_age_days")
    if max_age is None:
        return
    page = workflow.get_page(ctx.state, page_id)
    age = workflow.approval_age_days(ctx.state, page)
    if age is None or age > max_age:
        ctx.state.audit("publish_refused", ctx.user_id, page_id=page_id, rule_id="FS-0101", age_days=age)
        raise ValidationError(
            f"the approval of {page_id} is {age} days old; approvals are valid for {max_age} days - request a new review"
        )
""",  # noqa: E501 - the appended code is kept as it was probed
)
b_tool_import = (
    "replace",
    "tools/publish_tools.py",
    "from ..services import links, workflow\n",
    "from ..services import links, workflow\nfrom ..services.errors import ValidationError\n",
)
b_edits = [
    P._CFG_MAX_AGE,
    P._WF_IMPORT,
    P._WF_APPROVE,
    P._WF_FUNCTIONS,  # review_age_ok, approval_age_days, _check_review_age: defined in the service, gate never called
    P._SKILL_PROSE,
    b_tool_import,
    b_tool_fn,
    P._TOOL_INLINE_PUBLISH,
    P._TOOL_INLINE_SCHEDULE,
]
ev = judge("FS-0101", "rule_in_adapter_with_decoys", b_edits)
show("B. FS-0101: the decision made in tools/publish_tools.py (no lower bound); service functions are decoys", ev)

# ---------------------------------------------------------------- C. the harness reads the user table, by subscript
c_inline = (
    "replace",
    "harness/dispatcher.py",
    '        approver = permissions.approver_for(self.state, ctx.get("approval_token"))\n',
    '        token = ctx.get("approval_token")\n'
    "        approver = next(\n"
    '            (uid for uid, user in self.state.data["users"].items() '
    'if token and user.get("approval_token") == token),\n'
    "            None,\n"
    "        )\n",
)
c_edits = [P._PERM_APPROVER, P._DISP_IMPORT, P._DISP_RESOLVE, P._DISP_GATE, P._DISP_AUDIT, P._DISP_EVENT, c_inline]
ev = judge("FS-0102", "lookup_in_harness_by_subscript", c_edits)
show("C. FS-0102: dispatcher looks the token up in state.data['users'] itself; approver_for defined, unused", ev)

# ---------------------------------------------------------------- D. the PR decides what the quantifier ranges over
d_edits = P._with(
    P._IDEM_SCHEDULE,  # the partial fix: unpublish_page and approve_review still duplicate
    (
        "replace",
        "tools/publish_tools.py",
        "from .registry import ToolContext, tool\n",
        'from .registry import ToolContext, tool\n\nGUARDED = "guarded"\n',
    ),
    (
        "replace",
        "tools/publish_tools.py",
        '    "approve_review",\n    "guarded",\n',
        '    "approve_review",\n    GUARDED,\n',
    ),
    (
        "replace",
        "tools/publish_tools.py",
        '    "unpublish_page",\n    "guarded",\n',
        '    "unpublish_page",\n    GUARDED,\n',
    ),
)
ev_partial = evaluate_pr(
    specs["FS-0105"], next(p for p in P.PRS if p.id == "FS-0105/pr_partial_fix"), workdir, catalog, runs, deps
)
show("D0. FS-0105/pr_partial_fix as shipped (reference)", ev_partial, only_bad=True)
ev = judge("FS-0105", "partial_fix_kind_as_constant", d_edits)
show("D. FS-0105: the same partial fix, with the tool kind of the two unfixed tools written as a constant", ev)
for c in ev["clauses"]:
    if c["clause_id"] == "property_over_set:tool":
        print("    quantifier details:", c["details"])

# ---------------------------------------------------------------- E. runs that never happened pass the monitors
e_edits = [
    (
        "replace",
        "skills/publishing-workflow/SKILL.md",
        "Use this skill when the user wants a page published, scheduled for publication, or taken down.",
        "Use this skill (probe wording) when the user wants a page published, scheduled or taken down.",
    )
]
for sid in ("FS-0105", "FS-0103"):
    out, classes = infra_runs(sid, "prose_probe", e_edits)
    print(f"\n=== E. {sid} trace clauses on a variant whose publishing prompts have no recorded answer")
    print(f"    run classifications in scope: {dict(classes)}")
    for cid, status, summary, first in out:
        print(f"    {status:4s} {cid}: {summary} | {first}")

# ---------------------------------------------------------------- F. the model-drafted example spec, as it stands
draft = load_spec(Path("docs/sdd/draft_example/FS-0101.draft.yaml"))
pr = next(p for p in P.PRS if p.id == "FS-0101/pr_correct")
ev = evaluate_pr(draft, pr, workdir, catalog, runs, deps)
show("F. the drafted FS-0101 (docs/sdd/draft_example) against FS-0101/pr_correct", ev)

# ---------------------------------------------------------------- G. must_cover and the status-setter pattern
g_tool = """

@tool("go_live", "write", "Put a page on the live site at once.", {"page_id": "page identifier"})
def go_live(ctx: ToolContext, page_id: str):
    return workflow.go_live(ctx.state, page_id, actor=ctx.user_id)
"""
g_service = {
    "subscript on state.pages": """

def go_live(state, page_id: str, actor: str) -> dict:
    state.pages[page_id]["status"] = "published"
    state.audit("go_live", actor, page_id=page_id)
    return {"page_id": page_id, "status": "published"}
""",
    "page.update(...)": """

def go_live(state, page_id: str, actor: str) -> dict:
    page = get_page(state, page_id)
    page.update(status="published")
    state.audit("go_live", actor, page_id=page_id)
    return {"page_id": page_id, "status": "published"}
""",
    "page['status'] = ... on a variable named page (the idiom the query looks for)": """

def go_live(state, page_id: str, actor: str) -> dict:
    page = get_page(state, page_id)
    page["status"] = "published"
    state.audit("go_live", actor, page_id=page_id)
    return {"page_id": page_id, "status": "published"}
""",
}
precedes = next(c for c in specs["FS-0103"].clauses if c.id.startswith("precedes_in_audit"))
print("\n=== G. FS-0103 must_cover: a new tool that sets a page live without any link check")
for i, (idiom, body) in enumerate(g_service.items()):
    edits = P._with(
        P.FS0103_CORRECT, ("append", "services/workflow.py", body), ("append", "tools/publish_tools.py", g_tool)
    )
    vdir, _ = materialize_variant(Mutation(f"probe_g_{i}", "pr", idiom, True, edits), workdir / "variants")
    model = ProductModel(vdir, runs, deps)
    ctx = CheckContext(sut=None, model=model, catalog=catalog)
    gap = traces._coverage_gap(precedes, ctx) or "none"
    print(f"    {idiom}: status_setters={sorted(model.status_setters())} gap={gap}")

# ---------------------------------------------------------------- H. what each kind of clause contributes
print("\n=== H. shipped demo: which kinds of clause reject each PR (from the evidence of this run)")
shipped = {}
for spec in specs.values():
    for pr in P.prs_for(spec.id):
        shipped[pr.id] = evaluate_pr(spec, pr, workdir, catalog, runs, deps)
for pid, ev in shipped.items():
    fails = [(c["clause_id"], c["kind"]) for c in ev["clauses"] if c["status"] == "fail"]
    kinds = Counter("regression" if cid == "regression-tests" else k for cid, k in fails)
    print(f"    {pid:40s} {ev['verdict']:19s} {dict(kinds)}")
json.dump(
    {
        pid: [(c["clause_id"], c["kind"], c["status"], c["rung"], c["summary"]) for c in ev["clauses"]]
        for pid, ev in shipped.items()
    },
    open(workdir / "shipped_clauses.json", "w"),
    indent=1,
)
