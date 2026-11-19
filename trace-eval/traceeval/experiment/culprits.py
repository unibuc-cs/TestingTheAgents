"""Which member of a batch a failure points to, found from the members' own replays.

A batch bundles several changes (a day's changelists, say) and is tested as one change. When a test fails on the
batch, the member to blame is one whose own replay reaches that test, or fails it. A member whose own replay runs
the test to the end and passes sends the model nothing new on that test and leaves its outcome as it was, so on its
own it cannot make the test fail (under conditions R and D, ``replay_first.py``). The members' replays need no
model, so the suspects of a failure are known before any further call:

- one suspect: it is the culprit, with no further run;
- several: only they need to be told apart, by running the failing test on halves of them;
- none: the failure comes from the members together (an interaction), which only the batch shows.
"""

import math
from pathlib import Path


def suspects(member_rows: dict[str, dict], test: str) -> list[str]:
    """The members whose own replay reaches ``test`` (it diverges there) or fails it. ``member_rows`` maps each
    member to its replay's rows, test id -> row, as ``Replays.rows`` holds them."""
    return [
        member
        for member, rows in member_rows.items()
        if test in rows and (not rows[test]["replayed"] or not rows[test]["passed"])
    ]


def halving_runs(n: int) -> int:
    """How many runs of the failing test find one culprit among ``n`` suspects by halving them: none for one."""
    return 0 if n <= 1 else math.ceil(math.log2(n))


def member_suspects(members, tests, catalog, history_dir: Path, backend: str, home: Path) -> dict[str, list[str]]:
    """For each of ``tests``, the members whose own replay against the recording's cassette reaches it or fails it.
    Each member is applied alone to a copy of the app under ``home`` and replayed on those tests only; the cassette
    answers alone, so no model is called."""
    from traceeval.mutation import get_mutation, materialize_variant

    from .replay_first import cassette_client, in_front, replay_suite
    from .sutloader import load_sut

    client = cassette_client(history_dir, backend)
    cases = [catalog[t] for t in tests]
    rows = {}
    for member in members:
        sut_dir, _ = materialize_variant(get_mutation(member), home)
        sut = load_sut(sut_dir)
        try:
            with in_front(backend, client, judge_too=True):
                rows[member] = {r["test_id"]: r for r in replay_suite(sut, cases, client, backend, member)}
        finally:
            sut.unload()
    return {t: suspects(rows, t) for t in tests}
