"""Consent, data export and audit access (privacy / governance)."""

from . import permissions
from .errors import ApprovalRequired, NotFound, PermissionDenied


def check_consent(state, subject_id: str) -> dict:
    consents = state.data.get("consents", {})
    if subject_id not in consents:
        raise NotFound(f"no consent record for subject '{subject_id}'")
    return {
        "subject_id": subject_id,
        "consent": bool(consents[subject_id]),
        "purposes": state.data.get("consent_purposes", {}).get(subject_id, []),
    }


def export_user_data(state, subject_id: str, actor: str, approval_token: str | None) -> dict:
    """Guarded mutation: requires the operator's approval token and the export_data role."""
    operator = state.users.get(actor, {})
    if not approval_token or approval_token != operator.get("approval_token"):
        raise ApprovalRequired(f"a valid approval token for '{actor}' is required")
    permissions.require(state, actor, "export_data")
    subject = state.data.get("data_subjects", {}).get(subject_id)
    if subject is None:
        raise NotFound(f"unknown data subject '{subject_id}'")
    state.audit("export_user_data", actor, subject_id=subject_id)
    return {
        "subject_id": subject_id,
        "records": len(subject.get("records", [])),
        "export_id": f"exp-{subject_id}-{state.tick()}",
    }


def get_audit_log(state, page_id: str | None = None) -> dict:
    entries = state.data["audit"]
    if page_id is not None:
        entries = [e for e in entries if e.get("page_id") == page_id]
    return {"count": len(entries), "entries": entries[-20:]}


def check_permission(state, user_id: str, action: str) -> dict:
    try:
        allowed = permissions.can(state, user_id, action)
    except NotFound as exc:
        raise PermissionDenied(str(exc)) from exc
    return {"user_id": user_id, "action": action, "allowed": allowed}
