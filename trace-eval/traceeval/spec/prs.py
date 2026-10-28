"""The pull requests of the demo: for every spec, one or more variants of the SUT with a known verdict.

A PR is a ``Mutation`` (real file edits applied to a copy of the baseline) plus the verdict we expect
the spec to give. "Wrong" PRs are either hand-written mistakes a coding agent could plausibly make or
existing entries of the mutation catalogue. The spec layer never sees ``expected``; the report compares.
"""

from dataclasses import dataclass

from traceeval.mutation.catalog import Mutation, get_mutation

ACCEPTED, REJECTED = "accepted", "rejected"


@dataclass
class PR:
    id: str
    spec_id: str
    title: str
    expected: str  # accepted | rejected
    mutation: Mutation | None  # None = the unmodified baseline
    note: str = ""  # why it is right or wrong (shown next to the verdict)


# ---------------------------------------------------------------------------- FS-0101 approval validity window
_WF_IMPORT = (
    "replace",
    "services/workflow.py",
    "from . import permissions\n",
    "from datetime import date\n\nfrom . import permissions\n",
)
_WF_APPROVE = (
    "replace",
    "services/workflow.py",
    '    page["review"] = {"status": "approved", "reviewer": reviewer_id}\n',
    '    page["review"] = {"status": "approved", "reviewer": reviewer_id, "approved_on": state.data.get("today")}\n',
)
_WF_PUBLISH = (
    "replace",
    "services/workflow.py",
    "def publish_page(state, page_id: str, actor: str, idempotency_key: str | None = None) -> dict:\n"
    "    cached = state.idempotent(idempotency_key)\n"
    "    if cached:\n"
    "        return cached\n"
    "    page = get_page(state, page_id)\n",
    "def publish_page(\n"
    "    state, page_id: str, actor: str, idempotency_key: str | None = None, max_age_days: int | None = None\n"
    ") -> dict:\n"
    "    cached = state.idempotent(idempotency_key)\n"
    "    if cached:\n"
    "        return cached\n"
    "    page = get_page(state, page_id)\n"
    "    _check_review_age(state, page_id, page, actor, max_age_days)\n",
)
_WF_SCHEDULE = (
    "replace",
    "services/workflow.py",
    "def schedule_publish(state, page_id: str, at: str, actor: str) -> dict:\n"
    "    page = get_page(state, page_id)\n"
    "    if not at or len(at) < 10:\n"
    "        raise ValidationError(\"'at' must be an ISO-8601 timestamp\")\n",
    "def schedule_publish(state, page_id: str, at: str, actor: str, max_age_days: int | None = None) -> dict:\n"
    "    page = get_page(state, page_id)\n"
    "    if not at or len(at) < 10:\n"
    "        raise ValidationError(\"'at' must be an ISO-8601 timestamp\")\n"
    "    _check_review_age(state, page_id, page, actor, max_age_days)\n",
)
_WF_FUNCTIONS = (
    "append",
    "services/workflow.py",
    '''

# ---------------------------------------------------------------- FS-0101: approvals expire
def review_age_ok(age_days: int, max_age_days: int) -> bool:
    """An approval is usable while it is between 0 and ``max_age_days`` days old."""
    return 0 <= age_days <= max_age_days


def approval_age_days(state, page: dict) -> int | None:
    """Days since the page's recorded approval, or None when no approval date is recorded."""
    approved_on = (page.get("review") or {}).get("approved_on")
    today = state.data.get("today")
    if not approved_on or not today:
        return None
    return (date.fromisoformat(today) - date.fromisoformat(approved_on)).days


def _check_review_age(state, page_id: str, page: dict, actor: str, max_age_days: int | None):
    if max_age_days is None:
        return
    age = approval_age_days(state, page)
    if age is None or not review_age_ok(age, max_age_days):
        state.audit("publish_refused", actor, page_id=page_id, rule_id="FS-0101", age_days=age)
        raise ValidationError(
            f"the approval of {page_id} is {age} days old; approvals are valid for {max_age_days} days"
            " - request a new review"
        )
''',
)
_CFG_MAX_AGE = (
    "replace",
    "config/runtime.yaml",
    "  allow_scheduling: true\n",
    "  allow_scheduling: true\n  review_max_age_days: 30     # FS-0101: an approval expires after this many days\n",
)
_TOOL_PUBLISH = (
    "replace",
    "tools/publish_tools.py",
    "    return workflow.publish_page(ctx.state, page_id, actor=ctx.user_id, idempotency_key=ctx.idempotency_key)\n",
    "    return workflow.publish_page(\n"
    "        ctx.state,\n"
    "        page_id,\n"
    "        actor=ctx.user_id,\n"
    "        idempotency_key=ctx.idempotency_key,\n"
    '        max_age_days=ctx.config.get("publishing.review_max_age_days"),\n'
    "    )\n",
)
_TOOL_SCHEDULE = (
    "replace",
    "tools/publish_tools.py",
    "    return workflow.schedule_publish(ctx.state, page_id, at, actor=ctx.user_id)\n",
    "    return workflow.schedule_publish(\n"
    '        ctx.state, page_id, at, actor=ctx.user_id, max_age_days=ctx.config.get("publishing.review_max_age_days")\n'
    "    )\n",
)
_SKILL_PROSE = (
    "replace",
    "skills/publishing-workflow/SKILL.md",
    "platform requires one. Only then publish or schedule.",
    "platform requires one; an approval older than `publishing.review_max_age_days` days is stale and the\n"
    "platform refuses it - ask for a new review. Only then publish or schedule.",
)
FS0101_CORRECT = [
    _CFG_MAX_AGE,
    _WF_IMPORT,
    _WF_APPROVE,
    _WF_PUBLISH,
    _WF_SCHEDULE,
    _WF_FUNCTIONS,
    _TOOL_PUBLISH,
    _TOOL_SCHEDULE,
    _SKILL_PROSE,
]

# the same logic written inside the tool adapter instead of the service (architecturally wrong)
_TOOL_INLINE_IMPORT = (
    "replace",
    "tools/publish_tools.py",
    "from ..services import links, workflow\n",
    "from datetime import date\n\nfrom ..services import links, workflow\nfrom ..services.errors import ValidationError\n",
)
_TOOL_INLINE_FN = (
    "append",
    "tools/publish_tools.py",
    """

def _refuse_stale_approval(ctx, page_id: str):
    page = ctx.state.pages[page_id]
    max_age = ctx.config.get("publishing.review_max_age_days")
    approved_on = (page.get("review") or {}).get("approved_on")
    if max_age is None or not approved_on:
        return
    age = (date.fromisoformat(ctx.state.data["today"]) - date.fromisoformat(approved_on)).days
    if not (0 <= age <= max_age):
        ctx.state.audit("publish_refused", ctx.user_id, page_id=page_id, rule_id="FS-0101", age_days=age)
        raise ValidationError(
            f"the approval of {page_id} is {age} days old; approvals are valid for {max_age} days - request a new review"
        )
""",
)
_TOOL_INLINE_PUBLISH = (
    "replace",
    "tools/publish_tools.py",
    "def publish_page(ctx: ToolContext, page_id: str):\n    return workflow.publish_page(",
    "def publish_page(ctx: ToolContext, page_id: str):\n    _refuse_stale_approval(ctx, page_id)\n    return workflow.publish_page(",
)
_TOOL_INLINE_SCHEDULE = (
    "replace",
    "tools/publish_tools.py",
    "    return workflow.schedule_publish(ctx.state, page_id, at, actor=ctx.user_id)\n",
    "    _refuse_stale_approval(ctx, page_id)\n    return workflow.schedule_publish(ctx.state, page_id, at, actor=ctx.user_id)\n",
)

# ---------------------------------------------------------------------------- FS-0102 valid approval tokens
_PERM_APPROVER = (
    "append",
    "services/permissions.py",
    '''


def approver_for(state, token: str | None) -> str | None:
    """The user whose approval token this is, or None: an unknown or missing token approves nothing."""
    if not token:
        return None
    return next((uid for uid, user in state.users.items() if user.get("approval_token") == token), None)
''',
)
_DISP_IMPORT = (
    "replace",
    "harness/dispatcher.py",
    "from ..services.errors import ToolError\n",
    "from ..services import permissions\nfrom ..services.errors import ToolError\n",
)
_DISP_RESOLVE = (
    "replace",
    "harness/dispatcher.py",
    '        attempts, key, status = 0, None, "ok"\n',
    '        attempts, key, status = 0, None, "ok"\n'
    '        approver = permissions.approver_for(self.state, ctx.get("approval_token"))\n',
)
_DISP_GATE = (
    "replace",
    "harness/dispatcher.py",
    '        elif self._needs_approval(spec, name) and not ctx.get("approval_token"):\n'
    "            out = {\n"
    '                "error": "approval_required",\n'
    '                "message": f"\'{name}\' is a guarded operation and requires an approval token",\n',
    "        elif self._needs_approval(spec, name) and approver is None:\n"
    "            out = {\n"
    '                "error": "approval_required",\n'
    '                "message": f"\'{name}\' is a guarded operation and requires a valid approval token",\n',
)
_DISP_AUDIT = (
    "replace",
    "harness/dispatcher.py",
    '        if "error" in out:\n            status = "error"\n',
    '        if "error" in out:\n            status = "error"\n'
    '        elif spec.kind == "guarded":\n'
    '            self.state.audit("approval_used", approver, tool=name)\n',
)
_DISP_EVENT = (
    "replace",
    "harness/dispatcher.py",
    "            tool_kind=spec.kind if spec else None,\n",
    "            tool_kind=spec.kind if spec else None,\n"
    '            approved_by=approver if (spec and spec.kind == "guarded" and status == "ok") else None,\n',
)
FS0102_CORRECT = [_PERM_APPROVER, _DISP_IMPORT, _DISP_RESOLVE, _DISP_GATE, _DISP_AUDIT, _DISP_EVENT]
# any token accepted: an unknown token is "approved by the caller"
_DISP_SELF = (
    "replace",
    "harness/dispatcher.py",
    '        approver = permissions.approver_for(self.state, ctx.get("approval_token"))\n',
    '        approver = permissions.approver_for(self.state, ctx.get("approval_token")) or (\n'
    '            ctx.get("user_id") if ctx.get("approval_token") else None\n'
    "        )\n",
)
# the lookup written inside the dispatcher: the harness inspects the user table itself
_DISP_INLINE = (
    "replace",
    "harness/dispatcher.py",
    '        approver = permissions.approver_for(self.state, ctx.get("approval_token"))\n',
    '        token = ctx.get("approval_token")\n'
    "        approver = next(\n"
    '            (uid for uid, user in self.state.users.items() if token and user.get("approval_token") == token), None\n'
    "        )\n",
)

# ---------------------------------------------------------------------------- FS-0103 nothing goes live unvalidated
_LINKS_STAMP = (
    "replace",
    "services/links.py",
    '    state.audit("validate_links", None, page_id=page_id, broken=len(broken))\n'
    '    return {"page_id": page_id, "checked": checked, "broken_count": len(broken), "broken": broken}\n',
    '    version = len(page.get("versions", []))\n'
    '    page["link_check"] = {"version": version, "broken": len(broken)}\n'
    '    state.audit("validate_links", None, page_id=page_id, broken=len(broken), version=version)\n'
    '    return {"page_id": page_id, "checked": checked, "broken_count": len(broken), "broken": broken, "version": version}\n',
)
_WF_PUBLISH_GATE = (
    "replace",
    "services/workflow.py",
    '    page = get_page(state, page_id)\n    page["status"] = "published"\n',
    '    page = get_page(state, page_id)\n    _require_clean_links(state, page_id, page, actor)\n    page["status"] = "published"\n',
)
_WF_PUBLISH_AUDIT = (
    "replace",
    "services/workflow.py",
    '    state.audit("publish_page", actor, page_id=page_id, idempotency_key=idempotency_key)\n',
    '    state.audit("publish_page", actor, page_id=page_id, idempotency_key=idempotency_key, version=len(page["versions"]))\n',
)
_WF_SCHEDULE_GATE = (
    "replace",
    "services/workflow.py",
    '        raise ValidationError("\'at\' must be an ISO-8601 timestamp")\n    page["status"] = "scheduled"\n',
    '        raise ValidationError("\'at\' must be an ISO-8601 timestamp")\n'
    "    _require_clean_links(state, page_id, page, actor)\n"
    '    page["status"] = "scheduled"\n',
)
_WF_SCHEDULE_AUDIT = (
    "replace",
    "services/workflow.py",
    '    state.audit("schedule_publish", actor, page_id=page_id, at=at)\n',
    '    state.audit("schedule_publish", actor, page_id=page_id, at=at, version=len(page["versions"]))\n',
)
_WF_LINK_GATE = (
    "append",
    "services/workflow.py",
    '''

# ---------------------------------------------------------------- FS-0103: nothing goes live unvalidated
def links_clean(check_version: int, page_version: int, broken: int) -> bool:
    """A link check is usable when it was made for the page's current version and found nothing broken."""
    return check_version == page_version and broken == 0


def _require_clean_links(state, page_id: str, page: dict, actor: str):
    check = page.get("link_check") or {"version": -1, "broken": 0}
    version = len(page.get("versions", []))
    if not links_clean(int(check["version"]), version, int(check["broken"])):
        state.audit("publish_refused", actor, page_id=page_id, rule_id="FS-0103", version=version)
        raise ValidationError(
            f"{page_id} has no clean link check for its current version (v{version}); validate its links first"
        )
''',
)
FS0103_CORRECT = [_LINKS_STAMP, _WF_PUBLISH_GATE, _WF_PUBLISH_AUDIT, _WF_SCHEDULE_GATE, _WF_SCHEDULE_AUDIT, _WF_LINK_GATE]
# the gate written in the tool adapter: same behaviour, wrong layer
_TOOL_LINK_GATE = (
    "append",
    "tools/publish_tools.py",
    '''

def _require_clean_links(ctx, page_id: str):
    from ..services.errors import ValidationError

    page = ctx.state.pages[page_id]
    check = page.get("link_check") or {"version": -1, "broken": 0}
    version = len(page.get("versions", []))
    if check["version"] != version or check["broken"] != 0:
        ctx.state.audit("publish_refused", ctx.user_id, page_id=page_id, rule_id="FS-0103", version=version)
        raise ValidationError(
            f"{page_id} has no clean link check for its current version (v{version}); validate its links first"
        )
''',
)
_TOOL_LINK_PUBLISH = (
    "replace",
    "tools/publish_tools.py",
    "def publish_page(ctx: ToolContext, page_id: str):\n    return workflow.publish_page(",
    "def publish_page(ctx: ToolContext, page_id: str):\n    _require_clean_links(ctx, page_id)\n    return workflow.publish_page(",
)
_TOOL_LINK_SCHEDULE = (
    "replace",
    "tools/publish_tools.py",
    "    return workflow.schedule_publish(ctx.state, page_id, at, actor=ctx.user_id)\n",
    "    _require_clean_links(ctx, page_id)\n    return workflow.schedule_publish(ctx.state, page_id, at, actor=ctx.user_id)\n",
)
FS0103_IN_ADAPTER = [_LINKS_STAMP, _WF_PUBLISH_AUDIT, _WF_SCHEDULE_AUDIT, _TOOL_LINK_GATE, _TOOL_LINK_PUBLISH, _TOOL_LINK_SCHEDULE]
_SKILL_REORDER = [
    ("delete_line", "skills/publishing-workflow/SKILL.md", "- include: link-validation"),
    (
        "replace",
        "skills/publishing-workflow/SKILL.md",
        "- id: publish\n  call: publish_page\n",
        "- include: link-validation\n- id: publish\n  call: publish_page\n",
    ),
]

# ---------------------------------------------------------------------------- FS-0105 idempotent publishing writes
_IDEM_SCHEDULE = [
    (
        "replace",
        "services/workflow.py",
        "def schedule_publish(state, page_id: str, at: str, actor: str) -> dict:\n    page = get_page(state, page_id)\n",
        "def schedule_publish(state, page_id: str, at: str, actor: str, idempotency_key: str | None = None) -> dict:\n    cached = state.idempotent(idempotency_key)\n    if cached:\n        return cached\n    page = get_page(state, page_id)\n",
    ),
    (
        "replace",
        "services/workflow.py",
        '    state.audit("schedule_publish", actor, page_id=page_id, at=at)\n    return {"page_id": page_id, "status": "scheduled", "scheduled_at": at}\n',
        '    state.audit("schedule_publish", actor, page_id=page_id, at=at, idempotency_key=idempotency_key)\n    return state.remember(idempotency_key, {"page_id": page_id, "status": "scheduled", "scheduled_at": at})\n',
    ),
    (
        "replace",
        "tools/publish_tools.py",
        "    return workflow.schedule_publish(ctx.state, page_id, at, actor=ctx.user_id)\n",
        "    return workflow.schedule_publish(ctx.state, page_id, at, actor=ctx.user_id, idempotency_key=ctx.idempotency_key)\n",
    ),
]
_IDEM_UNPUBLISH = [
    (
        "replace",
        "services/workflow.py",
        "def unpublish_page(state, page_id: str, actor: str) -> dict:\n    page = get_page(state, page_id)\n",
        "def unpublish_page(state, page_id: str, actor: str, idempotency_key: str | None = None) -> dict:\n    cached = state.idempotent(idempotency_key)\n    if cached:\n        return cached\n    page = get_page(state, page_id)\n",
    ),
    (
        "replace",
        "services/workflow.py",
        '    state.audit("unpublish_page", actor, page_id=page_id)\n    return {"page_id": page_id, "status": "draft"}\n',
        '    state.audit("unpublish_page", actor, page_id=page_id, idempotency_key=idempotency_key)\n    return state.remember(idempotency_key, {"page_id": page_id, "status": "draft"})\n',
    ),
    (
        "replace",
        "tools/publish_tools.py",
        "    return workflow.unpublish_page(ctx.state, page_id, actor=ctx.user_id)\n",
        "    return workflow.unpublish_page(ctx.state, page_id, actor=ctx.user_id, idempotency_key=ctx.idempotency_key)\n",
    ),
]
FS0105_FIX = _IDEM_SCHEDULE + _IDEM_UNPUBLISH


def _m(mid, desc, edits, category="pr"):
    return Mutation(mid, category, desc, True, edits)


def _with(edits, *more):
    return list(edits) + list(more)


PRS: list[PR] = [
    # FS-0101 ------------------------------------------------------------------------------------
    PR(
        "FS-0101/pr_correct",
        "FS-0101",
        "Add the 30-day approval window (config + service + adapters + skill prose)",
        ACCEPTED,
        _m("FS-0101_pr_correct", "approval window, correct", FS0101_CORRECT),
        "rule in the service layer, limit in config, proven for all inputs",
    ),
    PR(
        "FS-0101/pr_no_lower_bound",
        "FS-0101",
        "Same, but `age_days <= max_age_days` (no lower bound)",
        REJECTED,
        _m(
            "FS-0101_pr_no_lower_bound",
            "approval window, accepts future-dated approvals",
            _with(
                FS0101_CORRECT,
                (
                    "replace",
                    "services/workflow.py",
                    "return 0 <= age_days <= max_age_days",
                    "return age_days <= max_age_days",
                ),
            ),
        ),
        "a future-dated approval (negative age) would be accepted; no fixture has one, only the proof sees it",
    ),
    PR(
        "FS-0101/pr_off_by_one",
        "FS-0101",
        "Same, but `<` instead of `<=` at the boundary",
        REJECTED,
        _m(
            "FS-0101_pr_off_by_one",
            "approval window, off by one",
            _with(
                FS0101_CORRECT,
                (
                    "replace",
                    "services/workflow.py",
                    "return 0 <= age_days <= max_age_days",
                    "return 0 <= age_days < max_age_days",
                ),
            ),
        ),
        "an approval exactly 30 days old is refused",
    ),
    PR(
        "FS-0101/pr_in_adapter",
        "FS-0101",
        "Same behaviour, but the date logic written inside tools/publish_tools.py",
        REJECTED,
        _m(
            "FS-0101_pr_in_adapter",
            "approval window implemented in the tool adapter",
            [
                _CFG_MAX_AGE,
                _WF_APPROVE,
                _SKILL_PROSE,
                _TOOL_INLINE_IMPORT,
                _TOOL_INLINE_FN,
                _TOOL_INLINE_PUBLISH,
                _TOOL_INLINE_SCHEDULE,
            ],
        ),
        "every run-time check passes; the contract cannot find the function where the spec says it lives, and the placement rules fail",
    ),
    PR(
        "FS-0101/pr_unwired",
        "FS-0101",
        "Service functions added and proven, but the adapters never pass the limit",
        REJECTED,
        _m(
            "FS-0101_pr_unwired",
            "approval window not wired into the adapters",
            [_CFG_MAX_AGE, _WF_IMPORT, _WF_APPROVE, _WF_PUBLISH, _WF_SCHEDULE, _WF_FUNCTIONS, _SKILL_PROSE],
        ),
        "the unit-level proof holds, the system-level monitor and the example fail",
    ),
    # FS-0102 ------------------------------------------------------------------------------------
    PR(
        "FS-0102/current",
        "FS-0102",
        "The current gate: any non-empty token passes and nobody is recorded",
        REJECTED,
        None,
        "the spec exposes a weakness of the current code: a made-up token takes a page down",
    ),
    PR(
        "FS-0102/pr_correct",
        "FS-0102",
        "Resolve the token against the user table (permissions service) and record the approver (dispatcher)",
        ACCEPTED,
        _m("FS-0102_pr_correct", "valid approval tokens, approver recorded", FS0102_CORRECT),
        "2 files: the lookup is a permissions-service function, the gate stays in the one place it lives",
    ),
    PR(
        "FS-0102/pr_self_approved",
        "FS-0102",
        "Same, but an unknown token falls back to 'approved by the caller'",
        REJECTED,
        _m("FS-0102_pr_self_approved", "unknown tokens approved by the caller", _with(FS0102_CORRECT, _DISP_SELF)),
        "property, monitor and example all catch the made-up token",
    ),
    PR(
        "FS-0102/pr_in_dispatcher",
        "FS-0102",
        "Same behaviour, but the user-table lookup written inside the dispatcher",
        REJECTED,
        _m(
            "FS-0102_pr_in_dispatcher",
            "token lookup inside the harness",
            [_DISP_IMPORT, _DISP_RESOLVE, _DISP_GATE, _DISP_AUDIT, _DISP_EVENT, _DISP_INLINE],
        ),
        "every run-time check passes; the harness must not inspect the user table (placement)",
    ),
    PR(
        "FS-0102/code_approval_gate_bypass",
        "FS-0102",
        "Correct PR plus a later change: the dispatcher stops enforcing the gate",
        REJECTED,
        _m(
            "FS-0102_code_approval_gate_bypass",
            "gate bypassed",
            _with(FS0102_CORRECT, *get_mutation("code_approval_gate_bypass").edits),
        ),
        "monitor: a guarded call succeeded without an approver",
    ),
    # FS-0103 ------------------------------------------------------------------------------------
    PR(
        "FS-0103/pr_correct",
        "FS-0103",
        "Stamp each validation on the page (links service); publish and schedule refuse without a clean stamp for the current version (workflow service)",
        ACCEPTED,
        _m("FS-0103_pr_correct", "link gate in the service layer", FS0103_CORRECT),
        "2 files: the rule moves from the skill procedure (a prompt) into the service, and is proven",
    ),
    PR(
        "FS-0103/pr_gate_ignores_version",
        "FS-0103",
        "Same, but the gate looks only at the broken count, not at the version the check was made for",
        REJECTED,
        _m(
            "FS-0103_pr_gate_ignores_version",
            "stale link checks accepted",
            _with(
                FS0103_CORRECT,
                ("replace", "services/workflow.py", "return check_version == page_version and broken == 0", "return broken == 0"),
            ),
        ),
        "no recorded scenario edits a page after validating it; only the proof sees the stale check",
    ),
    PR(
        "FS-0103/pr_gate_in_adapter",
        "FS-0103",
        "Same behaviour, but the gate written inside tools/publish_tools.py",
        REJECTED,
        _m("FS-0103_pr_gate_in_adapter", "link gate in the adapter", FS0103_IN_ADAPTER),
        "every run-time check passes; the contract cannot find links_clean in the service and the placement rules fail",
    ),
    PR(
        "FS-0103/pr_validate_after_schedule",
        "FS-0103",
        "Correct PR plus a skill reordering: link validation moved after the schedule step",
        REJECTED,
        _m("FS-0103_pr_validate_after_schedule", "link validation after scheduling", _with(FS0103_CORRECT, *_SKILL_REORDER)),
        "the service gate holds (nothing unvalidated is scheduled) but scheduling stops working: example and skill-order lint fail",
    ),
    PR(
        "FS-0103/code_links_external_lenient",
        "FS-0103",
        "Correct PR plus a later change: validate_links treats every external URL as reachable",
        REJECTED,
        _m(
            "FS-0103_code_links_external_lenient",
            "lenient external links",
            _with(FS0103_CORRECT, *get_mutation("code_links_external_lenient").edits),
        ),
        "ordering and the gate hold; the independent oracle on the validation result fails",
    ),
    # FS-0104 ------------------------------------------------------------------------------------
    PR(
        "FS-0104/pr_config_70",
        "FS-0104",
        "Raise the SEO title limit to 70 (configuration only, 0 code lines)",
        ACCEPTED,
        _m(
            "FS-0104_pr_config_70",
            "title limit 70",
            [("replace", "config/runtime.yaml", "max_title_length: 60", "max_title_length: 70")],
        ),
        "nothing to generate: a setting change verified by schema, property, boundary examples and monitor",
    ),
    PR(
        "FS-0104/pr_config_20",
        "FS-0104",
        "Limit set to 20 instead of 70",
        REJECTED,
        _m(
            "FS-0104_pr_config_20",
            "title limit 20",
            [("replace", "config/runtime.yaml", "max_title_length: 60", "max_title_length: 20")],
        ),
        "schema-valid but not what the request says",
    ),
    PR(
        "FS-0104/pr_hardcoded_70",
        "FS-0104",
        "Limit 70 written into the skill procedure instead of read from config",
        REJECTED,
        _m(
            "FS-0104_pr_hardcoded_70",
            "title limit hard-coded in the skill",
            [
                ("replace", "config/runtime.yaml", "max_title_length: 60", "max_title_length: 70"),
                (
                    "replace",
                    "skills/seo-metadata/SKILL.md",
                    "len(ctx['seo_title']) > config('seo.max_title_length')",
                    "len(ctx['seo_title']) > 70",
                ),
                (
                    "replace",
                    "skills/seo-metadata/SKILL.md",
                    "above the limit of {config('seo.max_title_length')}",
                    "above the limit of 70",
                ),
            ],
        ),
        "behaviourally identical today; only the placement lint sees the duplicated constant",
    ),
    PR(
        "FS-0104/pr_drop_guard",
        "FS-0104",
        "Limit raised to 70 but the skill's length guard deleted",
        REJECTED,
        _m(
            "FS-0104_pr_drop_guard",
            "title limit 70, guard removed",
            _with(
                get_mutation("skill_seo_drop_length_guard").edits,
                ("replace", "config/runtime.yaml", "max_title_length: 60", "max_title_length: 70"),
            ),
        ),
        "property over titles of every length finds the smallest over-long title that gets applied",
    ),
    # FS-0105 ------------------------------------------------------------------------------------
    PR(
        "FS-0105/current",
        "FS-0105",
        "Specify 'retried publishing writes never duplicate' against the current code",
        REJECTED,
        None,
        "the spec finds a latent defect: schedule_publish and unpublish_page duplicate their effect after a lost acknowledgement",
    ),
    PR(
        "FS-0105/pr_fix",
        "FS-0105",
        "Thread the idempotency key through schedule_publish and unpublish_page",
        ACCEPTED,
        _m("FS-0105_pr_fix", "idempotent publishing writes", FS0105_FIX),
        "2 files: the two services honour the key, the two adapters pass it through",
    ),
    PR(
        "FS-0105/pr_partial_fix",
        "FS-0105",
        "Same fix, but unpublish_page forgotten",
        REJECTED,
        _m("FS-0105_pr_partial_fix", "idempotent schedule only", _IDEM_SCHEDULE),
        "quantifying over the skill's write tools (from the product model) catches the one left out",
    ),
    PR(
        "FS-0105/code_retry_drop_idempotency",
        "FS-0105",
        "Correct PR plus a later change: retries no longer carry idempotency keys",
        REJECTED,
        _m(
            "FS-0105_code_retry_drop_idempotency",
            "keys dropped",
            _with(FS0105_FIX, *get_mutation("code_retry_drop_idempotency").edits),
        ),
        "monitor: successful writes without a key; property: the duplicates are back",
    ),
    PR(
        "FS-0105/config_retries_0",
        "FS-0105",
        "Correct PR plus a later change: transient failures no longer retried",
        REJECTED,
        _m("FS-0105_config_retries_0", "retries off", _with(FS0105_FIX, *get_mutation("config_retries_0").edits)),
        "setting clause (static) and the property both fail",
    ),
]


def prs_for(spec_id: str) -> list[PR]:
    return [p for p in PRS if p.spec_id == spec_id]
