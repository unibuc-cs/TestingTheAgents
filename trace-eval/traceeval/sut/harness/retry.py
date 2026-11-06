"""Retry policy for tool calls. Transient failures are retried; write tools are retried *with* an
idempotency key so that a retry after a lost acknowledgement does not duplicate the side effect."""

import hashlib

from ..services.errors import TransientError


def idempotency_key(operation: str) -> str:
    """The idempotency key of a write operation, such as ``idem-3f9c0a1b2d``: a digest of the operation's
    identity (the dispatcher builds it from the request, the tool, the arguments and how often that call has
    already succeeded), so the same operation always gets the same key and every run gets the same keys.
    Services remember the result of a write under its key, so a write repeated with the same key returns
    that result instead of acting twice."""
    return "idem-" + hashlib.sha256(operation.encode()).hexdigest()[:10]


def with_retry(call, *, retries: int, is_write: bool, idempotency_enabled: bool, operation: str, on_attempt=None):
    """``call(idempotency_key)`` is invoked up to ``retries + 1`` times on TransientError.

    Returns ``(result, attempts, key)``. Any other exception is passed on at once, without a retry, and
    when the last attempt fails too, its TransientError is raised. There is no pause between attempts.
    ``operation`` identifies the write for its idempotency key. ``on_attempt(attempt, error)``, when
    given, hears about every attempt (``error`` is None for the one that succeeded).
    """
    # A write gets one key, made before the first attempt and reused by every retry: that is how the
    # service recognises a retry of a write it has already made. Reads, and writes with keys switched
    # off, get None.
    key = idempotency_key(operation) if (is_write and idempotency_enabled) else None
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
