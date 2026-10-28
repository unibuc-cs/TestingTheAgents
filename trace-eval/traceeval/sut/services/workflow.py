"""Review / publish / schedule / unpublish workflow."""

from . import permissions
from .errors import ApprovalRequired, ValidationError
from .repository import get_page


def request_review(state, page_id: str, actor: str, idempotency_key: str | None = None) -> dict:
    cached = state.idempotent(idempotency_key)
    if cached:
        return cached
    page = get_page(state, page_id)
    page["review"] = {"status": "requested", "reviewer": None}
    reviews = state.data["reviews"].setdefault(page_id, [])
    reviews.append({"requested_by": actor, "status": "requested", "seq": state.tick()})
    state.audit("request_review", actor, page_id=page_id, idempotency_key=idempotency_key)
    return state.remember(
        idempotency_key, {"page_id": page_id, "review_status": "requested", "open_requests": len(reviews)}
    )


def approve_review(state, page_id: str, reviewer_id: str, approval_token: str | None) -> dict:
    """Approving is a guarded mutation: the tool layer enforces the approval token *and* the role."""
    page = get_page(state, page_id)
    reviewer = state.users.get(reviewer_id, {})
    if not approval_token or approval_token != reviewer.get("approval_token"):
        raise ApprovalRequired(f"a valid approval token for '{reviewer_id}' is required")
    permissions.require(state, reviewer_id, "approve_review")
    page["review"] = {"status": "approved", "reviewer": reviewer_id}
    state.audit("approve_review", reviewer_id, page_id=page_id)
    return {"page_id": page_id, "review_status": "approved"}


def publish_page(state, page_id: str, actor: str, idempotency_key: str | None = None) -> dict:
    cached = state.idempotent(idempotency_key)
    if cached:
        return cached
    page = get_page(state, page_id)
    page["status"] = "published"
    page["published_at"] = state.tick()
    page["scheduled_at"] = None
    state.audit("publish_page", actor, page_id=page_id, idempotency_key=idempotency_key)
    return state.remember(
        idempotency_key,
        {"page_id": page_id, "status": "published", "published_at": page["published_at"], "path": page["path"]},
    )


def schedule_publish(state, page_id: str, at: str, actor: str) -> dict:
    page = get_page(state, page_id)
    if not at or len(at) < 10:
        raise ValidationError("'at' must be an ISO-8601 timestamp")
    page["status"] = "scheduled"
    page["scheduled_at"] = at
    state.audit("schedule_publish", actor, page_id=page_id, at=at)
    return {"page_id": page_id, "status": "scheduled", "scheduled_at": at}


def unpublish_page(state, page_id: str, actor: str) -> dict:
    page = get_page(state, page_id)
    page["status"] = "draft"
    page["published_at"] = None
    state.audit("unpublish_page", actor, page_id=page_id)
    return {"page_id": page_id, "status": "draft"}
