"""Role-based permissions. Roles -> allowed actions."""

from .errors import NotFound, PermissionDenied

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
    user = state.users.get(user_id)
    if user is None:
        raise NotFound(f"unknown user '{user_id}'")
    allowed: set[str] = set()
    for role in user.get("roles", []):
        allowed |= ROLE_ACTIONS.get(role, set())
    return allowed


def can(state, user_id: str, action: str) -> bool:
    return action in actions_for(state, user_id)


def require(state, user_id: str, action: str):
    if not can(state, user_id, action):
        raise PermissionDenied(f"user '{user_id}' may not '{action}'")
