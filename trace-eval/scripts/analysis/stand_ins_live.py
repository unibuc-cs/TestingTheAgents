"""The replay's stand-ins checked live (TODO.md, "Next"): a sample of the (change, test) pairs a recording did not
run, because the test replays to the end on the changed copy, run with the model and compared with the replay.

A recording made with ``--reached-only`` runs only the tests a change reaches. Every other test of a change has one
record, its replayed run, marked ``stand_in``: under conditions R and D the live outcome is the replay's
(``experiment/replay_first.py``). This script measures that on the model as it is served now. Unlike the other
scripts of this folder it calls the model; it changes nothing in the recording.

1. It draws changes at random among those of the recording, and for each some of the tests that replay to the end.
   The draw is fixed by the seed and the ids.
2. It makes each changed copy again, as the recorder does, from the recording's own copy of the original app, and
   runs the drawn tests on it with the model. Every answer is compared with the cassette's (``llm/cache.py``).
3. It compares each live run with its stand-in: the outcome, and whether it is the same conversation (tool calls,
   final answer, final state and tokens).

    python scripts/analysis/stand_ins_live.py runs/gemma8_gen --backend vllm --workers 32 [--changes 100] [--tests 30]
    python scripts/analysis/stand_ins_live.py runs/gemma8_gen --summary      # the tables of what was run so far

It writes runs/analysis/stand_ins/<recording>.jsonl, one line per pair run; run again, it goes on where it stopped.
"""

import argparse
import json
import random
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

from traceeval.catalog import load_catalog
from traceeval.experiment.history import History
from traceeval.experiment.manifest import baseline_copy
from traceeval.experiment.replay_first import Replays, cassette_path, in_front
from traceeval.experiment.runner import run_suite
from traceeval.experiment.stopping import group_of
from traceeval.experiment.sutloader import load_sut
from traceeval.llm.cache import Compare
from traceeval.llm.chat import shared_client
from traceeval.mutation import get_mutation, materialize_variant

ap = argparse.ArgumentParser()
ap.add_argument("workdir")
ap.add_argument("--backend", default="vllm")
ap.add_argument("--workers", type=int, default=32)
ap.add_argument("--changes", type=int, default=100, help="how many changes to draw")
ap.add_argument("--tests", type=int, default=30, help="how many replayed tests to draw per change")
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--summary", action="store_true", help="only print the tables of what was run so far")
ap.add_argument("--out", help="where the pairs are written (default: runs/analysis/stand_ins/<recording>.jsonl)")
args = ap.parse_args()

workdir = Path(args.workdir)
out = Path(args.out) if args.out else Path("runs/analysis/stand_ins") / f"{workdir.name}.jsonl"
history, replays = History.load(workdir), Replays.load(workdir)
SHAPE = ("passed", "tokens", "tools", "final_message", "state_digest")  # a run, as the report compares two runs


def draw() -> dict[str, list[str]]:
    """The sample: change -> the replayed tests to run on it. A random.Random seeded with text is the same in every
    process (it does not use ``hash``)."""
    # the changes that have a test replaying to the end, in a fixed order
    changes = sorted(v for v in history.variants if replays.replayed(v))
    picked = random.Random(f"{args.seed}:changes").sample(changes, min(args.changes, len(changes)))
    sample = {}
    for change in sorted(picked):
        tests = sorted(replays.replayed(change))
        sample[change] = sorted(random.Random(f"{args.seed}:{change}").sample(tests, min(args.tests, len(tests))))
    return sample


def run(sample: dict[str, list[str]], done: set[str]):
    """Run the sample's pairs with the model, one changed copy at a time, and append one line per pair to ``out``."""
    catalog = {c.id: c for c in load_catalog()}
    original = baseline_copy(workdir)
    # in front of the model: each answer compared with the one the original app got for the same request
    compare = Compare(shared_client(args.backend), cassette_path(workdir), canonical_ids=(args.backend == "llm"))
    out.parent.mkdir(parents=True, exist_ok=True)
    with in_front(args.backend, compare), open(out, "a", encoding="utf-8") as fh:
        for n, (change, tests) in enumerate(sample.items(), 1):
            if change in done:
                continue
            stand_in = replays.rows[change]
            group = group_of(history.changesets[change])
            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
                sut_dir, _ = materialize_variant(get_mutation(change), Path(tmp), baseline=original)
                try:
                    sut = load_sut(sut_dir)
                except Exception as exc:  # noqa: BLE001 - whatever importing the changed app raises
                    # The app does not load with this change. The replay says so too: every test is a replayed
                    # failure there (``experiment/generated.py``), so each pair agrees and no run is made.
                    for t in tests:
                        row = {"change": change, "group": group, "test": t, "replayed_passed": stand_in[t]["passed"]}
                        row |= {
                            "live_passed": False,
                            "classification": f"load: {type(exc).__name__}",
                            "identical": True,
                        }
                        fh.write(json.dumps(row | {"requests": 0, "known": 0, "differ": 0}) + "\n")
                    continue
                try:
                    records = run_suite(
                        sut,
                        [catalog[t] for t in tests],
                        reps=1,
                        variant=change,
                        backend=args.backend,
                        config_overrides=None,
                        with_coverage=False,
                        workers=args.workers,
                        compare=compare,
                    )
                finally:
                    sut.unload()
            # a server that went away breaks every run after it: stop before this change is written
            broken = sum(r["classification"] == "INFRA_INVALID" for r in records)
            if broken > len(records) / 2:
                raise SystemExit(f"stopped at {change}: the environment broke {broken} of its {len(records)} runs")
            for rec in records:
                ref = stand_in[rec["test_id"]]
                fh.write(
                    json.dumps(
                        {
                            "change": change,
                            "group": group,
                            "test": rec["test_id"],
                            "replayed_passed": ref["passed"],
                            "live_passed": rec["passed"],
                            "classification": rec["classification"],
                            # the same conversation as the replay's, not only the same outcome
                            "identical": all(rec[k] == ref[k] for k in SHAPE),
                            **rec["cassette"],
                        }
                    )
                    + "\n"
                )
            fh.flush()
            print(f"{n} of {len(sample)} changes: {change}, {len(records)} tests", file=sys.stderr, flush=True)


def summary():
    """The pairs run so far: how many end like their stand-in, by group of changes, and those that do not."""
    rows = [json.loads(line) for line in open(out, encoding="utf-8")] if out.exists() else []
    valid = [r for r in rows if r["classification"] != "INFRA_INVALID"]
    if not valid:
        print("no pair run yet")
        return
    replayed = sum(len(replays.replayed(v)) for v in history.variants)
    print(
        f"{workdir}: {len(valid)} pairs run live, of {len({r['change'] for r in valid})} changes "
        f"(the recording has {replayed:,} pairs that replay to the end, over {len(history.variants)} changes); "
        f"{len(rows) - len(valid)} runs the environment broke are left out"
    )
    same = [r for r in valid if r["live_passed"] == r["replayed_passed"]]
    identical = sum(r["identical"] for r in valid)
    print(f"end like the stand-in: {len(same)} of {len(valid)}; the same conversation: {identical}")
    known, differ = sum(r["known"] for r in valid), sum(r["differ"] for r in valid)
    off = sum(r["requests"] > r["known"] for r in valid)
    print(
        f"requests: {sum(r['requests'] for r in valid):,}, of which the cassette knows {known:,} and {differ} are "
        f"answered otherwise; runs that sent a request the cassette lacks: {off}"
    )
    by_group = defaultdict(Counter)
    for r in valid:
        g = by_group[r["group"]]
        g["pairs"] += 1
        g["same outcome"] += r["live_passed"] == r["replayed_passed"]
        g["same conversation"] += r["identical"]
        g["replayed to a failure"] += not r["replayed_passed"]
    print("\n| group of the change | pairs | the replay fails | end like the stand-in | the same conversation |")
    print("|---|---|---|---|---|")
    for group, g in sorted(by_group.items()):
        counts = (g["pairs"], g["replayed to a failure"], g["same outcome"], g["same conversation"])
        print(f"| {group} | " + " | ".join(map(str, counts)) + " |")
    print(f"| all | {len(valid)} | {sum(not r['replayed_passed'] for r in valid)} | {len(same)} | {identical} |")
    for r in valid:
        if r["live_passed"] != r["replayed_passed"]:
            print(
                f"differs: {r['change']} {r['test']}: the replay {'passes' if r['replayed_passed'] else 'fails'}, the "
                f"live run {r['classification']}; {r['differ']} of its {r['known']} known requests answered otherwise"
            )


if not args.summary:
    done = {json.loads(line)["change"] for line in open(out, encoding="utf-8")} if out.exists() else set()
    run(draw(), done)
summary()
