"""Retry policy for tool calls. Transient failures are retried; write tools are retried *with* an
idempotency key so that a retry after a lost acknowledgement does not duplicate the side effect."""

import uuid

from ..services.errors import TransientError


def new_idempotency_key() -> str:
    """A fresh, random idempotency key such as ``idem-3f9c0a1b2d``. Services remember the result of a write
    under its key, so a write repeated with the same key returns that result instead of acting twice."""
    return f"idem-{uuid.uuid4().hex[:10]}"


def with_retry(call, *, retries: int, is_write: bool, idempotency_enabled: bool, on_attempt=None):
    """``call(idempotency_key)`` is invoked up to ``retries + 1`` times on TransientError.

    Returns ``(result, attempts, key)``. Any other exception is passed on at once, without a retry, and
    when the last attempt fails too, its TransientError is raised. There is no pause between attempts.
    ``on_attempt(attempt, error)``, when given, hears about every attempt (``error`` is None for the
    one that succeeded).
    """
    # A write gets one key, made before the first attempt and reused by every retry: that is how the
    # service recognises a retry of a write it has already made. Reads, and writes with keys switched
    # off, get None.
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
            # Out of retries: the last transient failure goes to the caller.
            if attempt > retries:
                raise
