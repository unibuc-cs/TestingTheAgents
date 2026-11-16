"""Edits that reach the model through its prompt but not through anything a trace records as used. For each, on a
temporary copy of the app: the change set, how many tests the traced dependencies link to it, and how many tests
make a request the original app never made when replayed against the recording's cassette
(``traceeval/experiment/replay_first.py``; run ``traceeval replay-first`` on the recording first).

    python scripts/analysis/prompt_only_edits.py [recording]       # default runs/gemma7
"""

import shutil
import tempfile
from pathlib import Path

from replaylib import load, recording

from traceeval.experiment.replay_first import cassette_client, in_front, replay_suite
from traceeval.experiment.sutloader import load_sut
from traceeval.mutation import compute_changeset
from traceeval.selection.base import weighted_affinity
from traceeval.sut import SUT_ROOT

SKILL = "skills/publishing-workflow/SKILL.md"
SENTENCE = "Use this skill when the user wants a page published, scheduled for publication, or taken down."
EDITS = [
    (
        "a tool's description reworded (schedule_publish)",
        "tools/publish_tools.py",
        '"Schedule a page to be published at a given time."',
        '"Schedule a page for publication at the given time."',
    ),
    (
        "the delegation tool's description reworded (route_to_agent)",
        "tools/control_tools.py",
        '"Delegate work to a specialist agent: the whole request, or one step of a plan."',
        '"Hand work to a specialist agent: the whole request, or one step of a plan."',
    ),
    (
        "a skill's prose re-wrapped, same words (publishing-workflow)",
        SKILL,
        SENTENCE,
        SENTENCE.replace("published, scheduled", "published,\nscheduled"),
    ),
    (
        "a second space in a skill's prose (publishing-workflow)",
        SKILL,
        SENTENCE,
        SENTENCE.replace("published, scheduled", "published,  scheduled"),
    ),
]

if __name__ == "__main__":
    workdir = recording()
    h, catalog = load(workdir)
    tests = h.test_ids()
    cases = [catalog[t] for t in tests if t in catalog]
    client = cassette_client(workdir, "replay")  # the answers of the original app, and nothing behind them
    for label, relative, old, new in EDITS:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            copy = Path(tmp) / "sut"
            shutil.copytree(SUT_ROOT, copy, ignore=shutil.ignore_patterns("__pycache__"))
            path = copy / relative
            text = path.read_text(encoding="utf-8")
            assert text.count(old) == 1, f"anchor not found once in {relative}"
            path.write_text(text.replace(old, new), encoding="utf-8")
            change = compute_changeset(SUT_ROOT, copy, name="probe")
            traced = {t for t in tests if weighted_affinity(change, h.baseline[t].dep_frequency) > 0}
            sut = load_sut(copy)
            with in_front("replay", client, judge_too=True):
                rows = replay_suite(sut, cases, client, "replay", "probe")
            sut.unload()
        diverged = {r["test_id"] for r in rows if not r["replayed"]}
        new_failures = [
            r["test_id"]
            for r in rows
            if r["replayed"] and not r["passed"] and h.baseline_pass_rate(r["test_id"]) >= 0.5
        ]
        components = [
            c.id for c in change.components
        ] or "none (traceeval check runs the diverged tests cheapest first)"
        print(
            f"{label}\n   change set: {components}"
            f"\n   tests the traced dependencies link: {len(traced)}"
            f"\n   tests whose requests diverge under replay: {len(diverged)}"
            f"\n   diverging tests the traced dependencies do not link: {len(diverged - traced)}"
            f"\n   new failures found by replay alone: {new_failures}"
        )
