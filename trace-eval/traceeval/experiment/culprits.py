"""A batch's members, each replayed alone: which tests each reaches (the day's map), and which member a failure
points to.

A batch bundles several changes (a day's changelists, say) and is tested as one change. Each member can also be
replayed alone against the recording's cassette, in a few seconds and with no model. Before any model call, those
replays give the day's map (``day_map``):

- the tests each member reaches: those that need the model because of it;
- the members that reach no test and fail none: the suite cannot tell them from the original app, so they need
  no model at all (under conditions R and D, ``replay_first.py``);
- a member whose own replay fails a test that passes on the original app: a regression, found with its culprit;
- for each test the batch reaches, the members that reach it.

When a test fails on the batch, the member to blame is one whose own replay reaches that test, or fails it. A member
whose own replay runs the test to the end and passes sends the model nothing new on that test and leaves its outcome
as it was, so on its own it cannot make the test fail. The suspects of a failure are therefore known before any
further call:

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


def day_map(member_rows: dict[str, dict], passes: dict[str, bool]) -> dict:
    """What the members' own replays say before any model call. ``member_rows`` maps each member to its replay's
    rows (test id -> row); ``passes`` says which tests pass on the original app. Returns:

    - ``reached``: member -> the tests its replay reaches (they diverge, so they need the model);
    - ``broken``: member -> the tests its replay fails that pass on the original app;
    - ``settled``: the members that reach no test and break none;
    - ``owners``: test -> the members that reach it or break it, for every test some member does. For a test that
      passes on the original app these are its suspects (``suspects``); one that fails there fails in every replay
      that runs it to the end, says nothing of any member, and is never run."""
    reached = {m: [t for t, r in rows.items() if not r["replayed"]] for m, rows in member_rows.items()}
    broken = {
        m: [t for t, r in rows.items() if r["replayed"] and not r["passed"] and passes.get(t)]
        for m, rows in member_rows.items()
    }
    owners = {}
    for m in member_rows:
        for t in reached[m] + broken[m]:
            owners.setdefault(t, []).append(m)
    settled = [m for m in member_rows if not reached[m] and not broken[m]]
    return {"reached": reached, "broken": broken, "settled": settled, "owners": owners}


def member_replays(members, cases, history_dir: Path, backend: str, home: Path) -> dict[str, dict[str, dict]]:
    """Each member applied alone to a copy of the app under ``home`` and replayed on ``cases`` against the
    recording's cassette: member -> test id -> its replay's row. The cassette answers alone: no model is called."""
    from traceeval.mutation import get_mutation, materialize_variant

    from .replay_first import cassette_client, in_front, replay_suite
    from .sutloader import load_sut

    client = cassette_client(history_dir, backend)  # a client of its own, with no model behind it
    rows = {}
    for member in members:
        sut_dir, _ = materialize_variant(get_mutation(member), home)
        sut = load_sut(sut_dir)
        try:
            with in_front(backend, client, judge_too=True):
                rows[member] = {r["test_id"]: r for r in replay_suite(sut, cases, client, backend, member)}
        finally:
            sut.unload()
    return rows
