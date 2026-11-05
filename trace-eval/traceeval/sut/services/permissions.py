"""Role-based permissions. Roles -> allowed actions.

Each user has a list of ``roles`` in the user table and may perform every action that any of those roles
allows; a role this module does not know grants nothing. Most services do not check permissions themselves:
the skills ask ``check_permission`` before they act. Only approving a review and exporting personal data are
checked inside the service, with ``require``."""

from .errors import NotFound, PermissionDenied

# Role -> the actions it allows. A user who holds several roles (an author who is also a publisher) may do
# everything any of them allows. A publisher may publish but not edit content, and approving a review,
# rolling a page back and exporting personal data are reserved for admins.
ROLE_ACTIONS = {
    "viewer": {"read"},
    "author": {"read", "create", "edit", "attach", "set_metadata", "request_review", "translate"},
    "publisher": {"read", "publish", "unpublish", "schedule", "request_review"},
    "admin": {
        "read",
        "create",
        "edit",
        "attach",
        "set_metadata",
        "request_review",
        "translate",
        "publish",
        "unpublish",
        "schedule",
        "approve_review",
        "rollback",
        "export_data",
    },
}


def actions_for(state, user_id: str) -> set[str]:
    """Every action ``user_id`` may perform: the union of the actions of the user's roles. Raises NotFound
    for a user who is not in the user table."""
    user = state.users.get(user_id)
    if user is None:
        raise NotFound(f"unknown user '{user_id}'")
    allowed: set[str] = set()
    for role in user.get("roles", []):
        allowed |= ROLE_ACTIONS.get(role, set())
    return allowed


def can(state, user_id: str, action: str) -> bool:
    """True when ``user_id`` may perform ``action``. Raises NotFound for an unknown user."""
    return action in actions_for(state, user_id)


def require(state, user_id: str, action: str):
    """Raise PermissionDenied unless ``user_id`` may perform ``action``; return nothing when it may. Raises
    NotFound for an unknown user."""
    if not can(state, user_id, action):
        raise PermissionDenied(f"user '{user_id}' may not '{action}'")
