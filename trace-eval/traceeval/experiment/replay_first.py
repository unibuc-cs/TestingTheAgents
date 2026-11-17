"""Replay-first: which tests can a change reach, found without a model.

The models decode greedily and the app has no clock and no randomness, so a model call is a function of its
request. The answers recorded on the original app (the recording's cassette, ``history/cassette.jsonl``) can then
stand in for the model on a changed copy for as long as the copy sends requests the original app sent. Every test
is run that way on every changed copy, and either

    replays to the end   every request it made is one the original app made: its outcome on the changed copy is
                         known, for no tokens;
    diverges             at the first request the original app never made: the change reaches the model there,
                         and only from there on does the test need the model.

``replay_first`` writes the result to ``history/replay_first.jsonl``, one line per (change, test), and ``Replays``
reads it back. Three places use it:
- the evaluator (``evaluate.py``) lets a strategy run the diverged tests only, and ends a run for no tokens when
  a replayed test fails;
- the report (``report.py``) says what the replay settles alone and checks it against the recorded ground truth;
- ``traceeval check`` (``check.py``) does the same live, with the cassette in front of the model.

The condition all of it rests on, a model call being a function of its request, is the serving setup's to keep.
The report measures it on a recording: the recorded runs of the pairs that replay to the end, against the replay.
"""

import json
import os
from concurrent.futures import ProcessPoolExecutor
from contextlib import contextmanager
from pathlib import Path

from traceeval.catalog import load_catalog
from traceeval.llm.cache import ReplayFirstClient, Tee
from traceeval.llm.chat import model_name, new_client, set_shared_client

from .executor import read_jsonl, run_case, write_jsonl
from .sutloader import load_sut


def cassette_path(workdir: Path) -> Path:
    """Where a recording keeps the answers its original app got: one line per request (``cache.py``)."""
    return Path(workdir) / "history" / "cassette.jsonl"


def recording_engine(workdir: Path) -> str:
    """The engine whose requests a recording's cassette is keyed by: "llm" for a recording made with the llm
    backend (Qwen, gpt-oss: the server builds the prompt), "replay" for Gemma's (the prompt is built here, and is
    the same whichever engine served the model)."""
    with open(Path(workdir) / "history" / "baseline.jsonl", encoding="utf-8") as fh:
        return "llm" if json.loads(fh.readline())["backend"] == "llm" else "replay"


@contextmanager
def in_front(engine: str, client, judge_too: bool = False):
    """``client`` as this process's client of ``engine`` for the length of the block; the client that was there
    comes back afterwards. A judge that is the agents' model goes through ``client`` as well. ``judge_too`` moves
    the judge to the agents' model whatever ``TRACEEVAL_JUDGE`` says: a replay must not reach a server."""
    judge = os.environ.get("TRACEEVAL_JUDGE")
    if judge_too:
        os.environ["TRACEEVAL_JUDGE"] = "qwen" if engine == "llm" else "gemma"
    previous = set_shared_client(engine, client)
    try:
        yield client
    finally:
        set_shared_client(engine, previous)
        if judge is None:
            os.environ.pop("TRACEEVAL_JUDGE", None)
        else:
            os.environ["TRACEEVAL_JUDGE"] = judge


def cassette_client(workdir: Path, engine: str) -> ReplayFirstClient:
    """A recording's cassette as a client: replay only, until its ``live`` is set to a model."""
    return ReplayFirstClient(cassette_path(workdir), model_name(engine), canonical_ids=(engine == "llm"))


def replay_suite(sut, cases, client: ReplayFirstClient, engine: str, variant: str) -> list[dict]:
    """Every case once on ``sut``, a changed copy of the app, answered from the cassette alone by ``client``,
    which must be the process's client of ``engine`` (``in_front``). One row per test: whether it replayed to the
    end, its outcome if it did, and how far the cassette carried it."""
    rows = []
    for case in cases:
        client.begin()
        rec = run_case(sut, case, backend=engine, variant=variant)
        replayed = client.missed == 0
        rows.append(
            {
                "variant": variant,
                "test_id": case.id,
                # every request was one the original app made: the outcome below is the test's on this copy
                "replayed": replayed,
                "passed": bool(rec["passed"]) if replayed else None,
                "failed_checks": rec["failed_checks"] if replayed else [],
                # how far the cassette carried the test: the requests it answered and their tokens (the whole
                # test when it replayed; the part that needs no model, before the divergence, when it did not)
                "requests": client.requests,
                "tokens": client.tokens,
                # how the change reached the model first: in what an agent is sent up front, or in a tool result
                "diverged_in": client.diverged_in,
                # the shape of a replayed run, to compare the recorded runs of the same test with
                "tools": rec["tools"] if replayed else None,
                "final_message": rec["final_message"] if replayed else None,
                "state_digest": rec["state_digest"] if replayed else None,
            }
        )
        if replayed:
            # A recording that runs only the tests a change reaches has no run of this one: the recorder writes
            # this row as the test's record on the copy (``runner.record_mutants``), so it carries what a strategy
            # may read of a run it has just made.
            keep = ("classification", "steps", "agents", "skills", "config_keys", "completion_tokens")
            rows[-1].update({k: rec[k] for k in keep})
    return rows


def replay_path(workdir: Path) -> Path:
    """Where a recording keeps the replay of its copies: one line per (copy, test)."""
    return Path(workdir) / "history" / "replay_first.jsonl"


def add_replay(workdir: Path, rows: list[dict]) -> None:
    """Append the rows of one replayed copy to the recording's replay file. The recorder does it for a copy it
    then throws away (``runner.record_mutants(reached_only=True)``). A copy replayed twice has its rows twice, and
    the later ones are the ones read (``Replays``)."""
    path = replay_path(workdir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as fh:
        fh.writelines(json.dumps(row, default=str) + "\n" for row in rows)


def _replay_copy(job: tuple[str, str, str, list[str]]) -> list[dict]:
    """One copy of the app replayed against the recording's cassette (a worker process's task): the recording,
    the variant, the engine, and the recording's tests."""
    workdir, variant, engine, tests = job
    workdir, tests = Path(workdir), set(tests)
    cases = [c for c in load_catalog() if c.id in tests]
    sut = load_sut(workdir / "variants" / variant / "sut")
    try:
        with in_front(engine, cassette_client(workdir, engine), judge_too=True) as client:
            return replay_suite(sut, cases, client, engine, variant)
    finally:
        sut.unload()


def write_cassette(workdir: Path, tests: list[str]) -> Path:
    """Give a Gemma recording made before cassettes were kept one of its own: its baseline copy is run once more,
    answered from recorded answers (those ``TRACEEVAL_CACHE`` names, or the test suite's), and every answer is
    kept. A test whose answers that source lacks cannot be run; it gets no answers in the cassette, and therefore
    diverges on every copy. A recording of the llm backend has no such source: only its model could answer."""
    workdir = Path(workdir)
    cases = [c for c in load_catalog() if c.id in set(tests)]
    sut = load_sut(workdir / "variants" / "baseline" / "sut")
    try:
        with in_front("replay", Tee(new_client("replay")), judge_too=True) as tee:
            for case in cases:
                run_case(sut, case, backend="replay", variant="baseline")
    finally:
        sut.unload()
    return tee.write(cassette_path(workdir))


def replay_first(workdir: Path, workers: int = 4) -> Path:
    """Replay the original app and every changed copy of a recording against its cassette, and write
    ``history/replay_first.jsonl``. Calls no model; a copy takes a few seconds, and ``workers`` copies are
    replayed at a time, each in a process of its own."""
    workdir = Path(workdir)
    engine = recording_engine(workdir)
    # the recording's tests, in the order of its baseline file
    tests = list(dict.fromkeys(r["test_id"] for r in read_jsonl(workdir / "history" / "baseline.jsonl")))
    if not cassette_path(workdir).exists():
        if engine == "llm":
            raise SystemExit(
                f"{workdir} has no cassette (history/cassette.jsonl): it was recorded before the baseline kept its "
                "answers. Record its baseline again (traceeval baseline) to replay it."
            )
        write_cassette(workdir, tests)
    # the copies that have recorded runs, the original app first
    recorded = sorted(p.stem for p in (workdir / "history" / "variants").glob("*.jsonl"))
    variants = ["baseline"] + [v for v in recorded if (workdir / "variants" / v / "sut").exists()]
    jobs = [(str(workdir), v, engine, tests) for v in variants]
    if workers > 1:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            copies = list(pool.map(_replay_copy, jobs))
    else:
        copies = [_replay_copy(job) for job in jobs]
    out = replay_path(workdir)
    # A copy that was recorded for the tests it reaches only is no longer there to replay: the rows it was given
    # when it was recorded (``add_replay``) are kept.
    earlier = read_jsonl(out) if out.exists() else []
    kept = [row for row in earlier if row["variant"] in recorded and row["variant"] not in variants]
    write_jsonl(out, kept + [row for rows in copies for row in rows])
    return out


class Replays:
    """``history/replay_first.jsonl`` as the evaluator, the report and the check read it: per changed copy and
    test, what the replay found."""

    def __init__(self, rows: list[dict]):
        # variant -> test id -> its row
        self.rows: dict[str, dict[str, dict]] = {}
        for r in rows:
            self.rows.setdefault(r["variant"], {})[r["test_id"]] = r

    @classmethod
    def load(cls, workdir: Path) -> "Replays | None":
        """The replays of a recording, or None when ``traceeval replay-first`` has not been run on it."""
        path = replay_path(workdir)
        return cls(read_jsonl(path)) if path.exists() else None

    def replayed(self, variant: str) -> frozenset:
        """The tests whose outcome on the changed copy the replay gives."""
        return frozenset(t for t, r in self.rows.get(variant, {}).items() if r["replayed"])

    def diverged(self, variant: str) -> list[str]:
        """The tests the change reaches: those that need the model on the changed copy."""
        return [t for t, r in self.rows.get(variant, {}).items() if not r["replayed"]]

    def prefix(self, variant: str) -> dict[str, float]:
        """For each diverged test, the tokens of the requests that replay before the divergence."""
        return {t: float(r["tokens"]) for t, r in self.rows.get(variant, {}).items() if not r["replayed"]}

    def new_failures(self, variant: str) -> list[str]:
        """The tests that replay to a failure on the changed copy and to a pass on the original app: the change
        broke them, and no model was needed to see it."""
        base = self.rows.get("baseline", {})
        return [
            t
            for t, r in self.rows.get(variant, {}).items()
            if r["replayed"] and not r["passed"] and base.get(t, {}).get("passed")
        ]
