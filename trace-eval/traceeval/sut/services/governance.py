"""Consent, data export, audit access and human approvals (privacy / governance).

The consent records and the personal data held about each data subject live in the state, under
``consents``, ``consent_purposes`` and ``data_subjects``; who approves the steps of a plan, and how they
decide, under ``approvals``."""

from . import permissions
from .errors import ApprovalRequired, NotFound, PermissionDenied


def check_consent(state, subject_id: str) -> dict:
    """Whether a data subject has consented to the processing of their data, and for which purposes.

    Returns ``subject_id``, ``consent`` (True or False) and ``purposes`` (possibly empty). A subject with no
    consent record at all is refused with NotFound rather than reported as not consenting."""
    consents = state.data.get("consents", {})
    if subject_id not in consents:
        raise NotFound(f"no consent record for subject '{subject_id}'")
    return {
        "subject_id": subject_id,
        "consent": bool(consents[subject_id]),
        "purposes": state.data.get("consent_purposes", {}).get(subject_id, []),
    }


def export_user_data(state, subject_id: str, actor: str, approval_token: str | None) -> dict:
    """Guarded mutation: requires the operator's approval token and the export_data role.

    The operator is the user making the request, and the token must be that user's own. Raises
    ApprovalRequired when the token is missing or belongs to someone else, PermissionDenied when the
    operator's roles do not allow ``export_data`` and NotFound for an unknown data subject. Consent is not
    checked here: the governance skill checks it with ``check_consent`` before it asks for the export.
    Returns ``subject_id``, ``records`` (how many records the export holds; the records themselves are not
    returned) and a new ``export_id``."""
    # The token has to be the operator's own: a token issued to another user, or none at all, is refused.
    # An operator the platform does not know has no token, so they are refused here as well.
    operator = state.users.get(actor, {})
    if not approval_token or approval_token != operator.get("approval_token"):
        raise ApprovalRequired(f"a valid approval token for '{actor}' is required")
    # Holding the token is not enough: the operator's roles must also allow exporting personal data.
    permissions.require(state, actor, "export_data")
    subject = state.data.get("data_subjects", {}).get(subject_id)
    if subject is None:
        raise NotFound(f"unknown data subject '{subject_id}'")
    # Every export of personal data is written to the audit log.
    state.audit("export_user_data", actor, subject_id=subject_id)
    return {
        "subject_id": subject_id,
        "records": len(subject.get("records", [])),
        "export_id": f"exp-{subject_id}-{state.tick()}",  # a new id for every export, from the logical clock
    }


def get_audit_log(state, page_id: str | None = None) -> dict:
    """Read the audit log, or only the entries about one page when ``page_id`` is given.

    Returns ``count``, the number of matching entries, and ``entries``, the most recent 20 of them, oldest
    first. When filtering by page, entries that concern no page (an asset upload, a data export) are left
    out."""
    entries = state.data["audit"]
    if page_id is not None:
        entries = [e for e in entries if e.get("page_id") == page_id]
    # count covers every matching entry, but only the last 20 are returned, to keep the answer short.
    return {"count": len(entries), "entries": entries[-20:]}


def check_permission(state, user_id: str, action: str) -> dict:
    """Answer whether ``user_id`` may perform ``action``: returns ``user_id``, ``action`` and ``allowed``.

    An action that no role grants, a misspelt one included, is simply not allowed. A user the platform does
    not know is refused with PermissionDenied (re-raised from the NotFound of the role lookup) rather than
    answered with ``allowed`` False."""
    try:
        allowed = permissions.can(state, user_id, action)
    except NotFound as exc:
        raise PermissionDenied(str(exc)) from exc
    return {"user_id": user_id, "action": action, "allowed": allowed}


def request_approval(state, summary: str, actor: str) -> dict:
    """Ask the platform's approver to sign off a step of a plan, and return the answer.

    The answer is part of the platform data, under ``approvals`` (who approves, and whether they approve), the
    way a person's answer is part of a test, so that a run can be repeated. An approval returns ``approved``
    True, the ``approver``, and under ``pass_on`` what the steps after it carry (the runtime adds it to the
    request context): the approver and their ``approval_token``, which guarded tools need. A refusal returns
    ``approved`` False and the approver. Every request is written to the audit log with the decision."""
    policy = state.data.get("approvals", {})
    approver = policy.get("approver", "carol")
    approved = policy.get("decision", "approve") == "approve"
    state.audit("request_approval", actor, summary=summary, approver=approver, approved=approved)
    if not approved:
        return {"approved": False, "approver": approver, "message": f"{approver} did not approve: {summary}"}
    token = state.users.get(approver, {}).get("approval_token")
    return {"approved": True, "approver": approver, "pass_on": {"approver": approver, "approval_token": token}}
