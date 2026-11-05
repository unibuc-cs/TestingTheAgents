"""The refusals a service can raise.

The dispatcher turns each of them into the tool result the agent receives, ``{"error": <code>, "message":
<text>}``, so the agent learns why its call was refused and can react, instead of seeing an exception."""


class ToolError(Exception):
    """Base class for errors surfaced to the agent as tool results."""

    code = "tool_error"  # what the agent receives in the "error" field; every subclass sets its own
    retryable = False  # True when the same call may succeed if it is simply repeated (only TransientError)

    def to_dict(self):
        """The tool result that replaces the normal answer: the error code and the human-readable message."""
        return {"error": self.code, "message": str(self)}


class NotFound(ToolError):
    """The request names something that does not exist: a page, a page version, an asset, a user, a data
    subject or a translation job."""

    code = "not_found"


class PermissionDenied(ToolError):
    """The user's roles do not allow the requested action, or the user is not known at all when a
    permission is checked."""

    code = "permission_denied"


class ValidationError(ToolError):
    """The request is malformed or breaks a business rule: for example an empty title, an unknown template,
    an unsupported MIME type or locale, a badly formed publication time, or scheduling switched off by the
    configuration."""

    code = "validation_error"


class ApprovalRequired(ToolError):
    """A guarded operation came without a valid approval token.

    The dispatcher already refuses a guarded call that carries no token at all, with the same error code. A
    service raises this when the token is missing or is not the token of the user who has to approve: the
    reviewer approving a page, or the operator exporting personal data."""

    code = "approval_required"


class TransientError(ToolError):
    """A transient infrastructure failure (timeout, 503). Safe to retry *with* an idempotency key.

    The fault injector raises it at the tool boundary, and the dispatcher's retry helper repeats a call that
    fails with it, up to ``runtime.retries`` more times. When ``runtime.idempotency_keys`` is on, a write
    call keeps the same idempotency key across those repeats, so a service that honours the key does not
    apply the change a second time."""

    code = "transient_error"
    retryable = True
