"""The generated changes of a recording, replayed for free.

``mutation/generator.py`` enumerates several hundred changes of the app. Recording each of them with the model
would cost what the 43 hand-written ones cost, many times over. Replaying them costs CPU only: each change is
applied to a copy of the recording's original app in a temporary folder, every test is run on it with the model's
calls answered from the recording's cassette (``replay_first.py``), and the copy is thrown away. What comes out,
per change, is which tests replay to the end, with their outcome, and which diverge and would need the model.

``replay_generated`` writes ``history/generated.jsonl``, one line per change (the first is the original app):

    id, kind, category, description     the change
    files, components                   what its diff touched (the change set)
    rows                                one per test, as in ``history/replay_first.jsonl``, without the run's shape

``Generated`` reads it back as the report and the recorder need it.
"""

import json
import os
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from traceeval.catalog import load_catalog
from traceeval.mutation import materialize_variant
from traceeval.mutation.changeset import ChangeSet
from traceeval.mutation.generator import generated, kind_of, sample

from .executor import read_jsonl
from .manifest import baseline_copy
from .replay_first import Replays, cassette_replay, recording_engine
from .sutloader import load_sut

# what a row keeps: enough to say whether the test replays, how it ends and where it diverges
ROW = ("test_id", "replayed", "passed", "failed_checks", "requests", "tokens", "diverged_in")


def generated_path(workdir: Path) -> Path:
    """Where a recording keeps the replay of its generated changes."""
    return Path(workdir) / "history" / "generated.jsonl"


def _replay_one(job: tuple[str, str | None, str, list[str]]) -> dict:
    """One line of the file (a worker process's task): the recording, the change (None: the original app), the
    engine whose requests the cassette is keyed by, and the recording's tests."""
    workdir, mid, engine, tests = job
    workdir, tests = Path(workdir), set(tests)
    cases = [c for c in load_catalog() if c.id in tests]
    original = baseline_copy(workdir)
    # the changes are those of the recording's own app, so that every edit finds the line it names
    change = generated(original)[mid] if mid else None
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        sut_dir, cs = materialize_variant(change, Path(tmp), baseline=original)
        try:
            sut = load_sut(sut_dir)
        except Exception as exc:  # noqa: BLE001 - whatever importing the changed app raises
            # The app does not even load with this change: every test fails before it sends the model anything,
            # which is a replayed failure of every test.
            failed = {"replayed": True, "passed": False, "failed_checks": [f"load: {type(exc).__name__}"]}
            rows = [{"test_id": c.id, **failed, "requests": 0, "tokens": 0, "diverged_in": None} for c in cases]
        else:
            try:
                rows = cassette_replay(sut, cases, workdir, engine, mid or "baseline")
            finally:
                sut.unload()
    return {
        "id": mid or "baseline",
        "kind": kind_of(mid) if mid else "baseline",
        "category": change.category if change else "baseline",
        "description": change.description if change else "the original app",
        "files": cs.files,
        "components": [c.__dict__ for c in cs.components],
        "rows": [{k: row[k] for k in ROW} for row in rows],
    }


def replay_generated(workdir: Path, workers: int = 4, per_kind: int | None = None, seed: int = 0) -> Path:
    """Replay every generated change, or ``per_kind`` of each kind (``generator.sample``), against the recording's
    cassette, and write ``history/generated.jsonl``. Calls no model; a change takes a few seconds, and ``workers``
    of them are replayed at a time, each in a process of its own."""
    workdir = Path(workdir)
    engine = recording_engine(workdir)
    tests = list(dict.fromkeys(r["test_id"] for r in read_jsonl(workdir / "history" / "baseline.jsonl")))
    changes = list(generated(baseline_copy(workdir)).values())
    if per_kind is not None:
        changes = sample(changes, per_kind, seed)
    jobs = [(str(workdir), mid, engine, tests) for mid in [None, *(m.id for m in changes)]]
    out = generated_path(workdir)
    with ProcessPoolExecutor(max_workers=min(workers, os.cpu_count() or 1)) as pool, open(out, "w") as fh:
        for line in pool.map(_replay_one, jobs):  # in the order of the jobs, written as each is done
            fh.write(json.dumps(line, default=str) + "\n")
    return out


class Generated:
    """``history/generated.jsonl`` as its readers want it: the changes in the order they were generated, what
    each one's diff touched, and the replay of all of them."""

    def __init__(self, lines: list[dict]):
        # every change but the original app, by id
        self.changes: dict[str, dict] = {line["id"]: line for line in lines if line["id"] != "baseline"}
        # the rows of all of them and of the original app, as the replay of a recording's own copies is read
        self.replays = Replays([{**row, "variant": line["id"]} for line in lines for row in line["rows"]])

    @classmethod
    def load(cls, workdir: Path) -> "Generated | None":
        """The replay of a recording's generated changes, or None when it has not been made."""
        path = generated_path(workdir)
        return cls(read_jsonl(path)) if path.exists() else None

    def changeset(self, mid: str) -> ChangeSet:
        """The change set of one generated change (without its diff, which the file does not keep)."""
        line = self.changes[mid]
        return ChangeSet.from_dict({"variant": mid, "files": line["files"], "components": line["components"]})
