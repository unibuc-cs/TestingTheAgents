"""Retry policy for tool calls. Transient failures are retried; write tools are retried *with* an
idempotency key so that a retry after a lost acknowledgement does not duplicate the side effect."""

import uuid

from ..services.errors import TransientError


def new_idempotency_key() -> str:
    return f"idem-{uuid.uuid4().hex[:10]}"


def with_retry(call, *, retries: int, is_write: bool, idempotency_enabled: bool, on_attempt=None):
    """``call(idempotency_key)`` is invoked up to ``retries + 1`` times on TransientError."""
    key = new_idempotency_key() if (is_write and idempotency_enabled) else None
    attempt = 0
    while True:
        attempt += 1
        try:
            result = call(key)
            if on_attempt:
                on_attempt(attempt, None)
            return result, attempt, key
        except TransientError as exc:
            if on_attempt:
                on_attempt(attempt, exc)
            if attempt > retries:
                raise
