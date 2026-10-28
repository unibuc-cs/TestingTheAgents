"""One checker per clause kind. ``check(clause, ctx)`` returns a ClauseResult."""

from . import contracts, examples, placement, settings, traces

CHECKERS = {
    "setting": settings.check,
    "contract": contracts.check,
    "trace": traces.check,
    "example": examples.check,
    "placement": placement.check,
}

__all__ = ["CHECKERS"]
