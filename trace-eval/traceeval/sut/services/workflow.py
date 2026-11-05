"""Review / publish / schedule / unpublish workflow.

A page is a ``draft`` (not on the live site), ``scheduled`` (a publication time is planned) or ``published``
(live). Its review is tracked separately, as ``none``, ``requested`` or ``approved``. Publishing, scheduling
and taking a page down do not check the review, the links or the user's permissions: the publishing skill
makes the checks it needs before it calls these tools. Approving a review is different, because the service
itself checks the reviewer's approval token and role.

``request_review`` and ``publish_page`` accept an idempotency key. The other calls do not, so when such a
call has run but its acknowledgement was lost, the retry applies it, and audits it, a second time."""

from . import permissions
from .errors import ApprovalRequired, ValidationError
from .repository import get_page


def request_review(state, page_id: str, actor: str, idempotency_key: str | None = None) -> dict:
    """Ask for an editorial review of a page and return ``page_id``, ``review_status`` "requested" and
    ``open_requests``.

    The page's review becomes "requested", with no reviewer yet; an approval the page had is replaced.
    Each request is also added to the page's list of review requests in the state, and ``open_requests`` is
    the length of that list, so it counts every request made for the page so far, including those already
    approved or withdrawn by an edit. Raises NotFound for an unknown page. A retry with the same
    idempotency key returns the first answer and records nothing new."""
    # A retry of a request that already went through gets the first answer back.
    cached = state.idempotent(idempotency_key)
    if cached:
        return cached
    page = get_page(state, page_id)
    # Put the page into review, with no reviewer assigned yet.
    page["review"] = {"status": "requested", "reviewer": None}
    # Keep a record of every request: who asked, and when (as a tick of the logical clock).
    reviews = state.data["reviews"].setdefault(page_id, [])
    reviews.append({"requested_by": actor, "status": "requested", "seq": state.tick()})
    state.audit("request_review", actor, page_id=page_id, idempotency_key=idempotency_key)
    return state.remember(
        idempotency_key, {"page_id": page_id, "review_status": "requested", "open_requests": len(reviews)}
    )


def approve_review(state, page_id: str, reviewer_id: str, approval_token: str | None) -> dict:
    """Approving is a guarded mutation: this service enforces both the approval token *and* the role.

    The dispatcher in front of the tool only checks that some token was sent; the real checks are made
    here. ``approval_token`` must be the reviewer's own token, otherwise
    ApprovalRequired, and the reviewer's roles must allow ``approve_review``, otherwise PermissionDenied.
    Raises NotFound for an unknown page. The page does not need an open review request to be approved.
    Returns ``page_id`` and ``review_status`` "approved"."""
    page = get_page(state, page_id)
    # The token must be the one issued to the named reviewer: somebody else's token, or none, approves
    # nothing. A reviewer the platform does not know has no token, so they are refused here as well.
    reviewer = state.users.get(reviewer_id, {})
    if not approval_token or approval_token != reviewer.get("approval_token"):
        raise ApprovalRequired(f"a valid approval token for '{reviewer_id}' is required")
    # Holding the token is not enough: the reviewer's roles must also allow approving.
    permissions.require(state, reviewer_id, "approve_review")
    # Record the approval and who gave it. The audit entry names the reviewer as the one who acted.
    page["review"] = {"status": "approved", "reviewer": reviewer_id}
    state.audit("approve_review", reviewer_id, page_id=page_id)
    return {"page_id": page_id, "review_status": "approved"}


# Put a page on the live site now. Returns page_id, status "published", published_at and the page's path;
# published_at is a tick of the logical clock, not a date, and a planned publication (scheduled_at) is
# dropped. The page may be in any status. Apart from the page existing, nothing is checked here: the
# publishing skill checks the permission, the links and, when the platform requires one, the approved
# review before it calls the tool. Raises NotFound for an unknown page. A retry with the same idempotency
# key returns the first answer.
def publish_page(state, page_id: str, actor: str, idempotency_key: str | None = None) -> dict:
    cached = state.idempotent(idempotency_key)
    if cached:
        return cached
    page = get_page(state, page_id)
    page["status"] = "published"
    # The publication time is the next clock tick; publishing now also cancels any planned publication.
    page["published_at"] = state.tick()
    page["scheduled_at"] = None
    # Record the publication, and remember the answer so that a retry with the same key gets it unchanged.
    state.audit("publish_page", actor, page_id=page_id, idempotency_key=idempotency_key)
    return state.remember(
        idempotency_key,
        {"page_id": page_id, "status": "published", "published_at": page["published_at"], "path": page["path"]},
    )


# Plan the publication of a page at the time ``at``; returns page_id, status "scheduled" and scheduled_at.
# Only the length of ``at`` is checked: anything shorter than a date such as 2026-11-04 raises
# ValidationError, but neither the format nor whether the time lies in the future is verified. A page that
# is already live can be scheduled too, and its status then changes from published to scheduled. Nothing
# publishes the page when the time comes; the status only records the plan. Whether scheduling is allowed
# at all is decided by the tool (publishing.allow_scheduling). Raises NotFound for an unknown page.
def schedule_publish(state, page_id: str, at: str, actor: str) -> dict:
    page = get_page(state, page_id)
    if not at or len(at) < 10:
        raise ValidationError("'at' must be an ISO-8601 timestamp")
    page["status"] = "scheduled"
    # Keep the planned time. published_at is left as it is, so a live page that is scheduled again keeps its
    # old publication time.
    page["scheduled_at"] = at
    state.audit("schedule_publish", actor, page_id=page_id, at=at)
    return {"page_id": page_id, "status": "scheduled", "scheduled_at": at}


# Take a page off the live site: it goes back to draft and loses its publication time. Returns page_id and
# status "draft"; raises NotFound for an unknown page. The tool is guarded (the configuration requires an
# approval token for it), but the only token check is the dispatcher's, which makes sure that some token
# was sent: this service does not compare the token with anyone's. A planned publication time
# (scheduled_at) is left as it is.
def unpublish_page(state, page_id: str, actor: str) -> dict:
    page = get_page(state, page_id)
    # Back to draft, with no publication time: the page is no longer live.
    page["status"] = "draft"
    page["published_at"] = None
    state.audit("unpublish_page", actor, page_id=page_id)
    return {"page_id": page_id, "status": "draft"}
