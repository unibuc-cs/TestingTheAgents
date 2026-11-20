"""Where the requests that are answered otherwise are: the empty change of one or more recordings, side by side.

The empty change is the original app run once more, the way the changed copies are; every request it sends is in
the recording's cassette, and the recorder counts those the model answers otherwise (``llm/cache.py::Compare``).
Per recording, this script says how many there are and how they fall over the tests and their runs:

- a test with another answer *in some of its runs* varies from run to run: the batch a request lands in does that;
- a test with another answer *in every run*, all its runs being one and the same, is repeatable and differs from
  the cassette: the server is not in the state it was in when the cassette was recorded (its prefix cache, or a
  setting that was changed).

It prints one markdown row per recording: the table of ``docs/RESEARCH_PLAN.md`` §5.2.

    python scripts/analysis/answered_otherwise.py runs/gemma8 runs/gemma8_pc1_w1 runs/gemma8_exact ...
"""

import sys

from replaylib import load

if len(sys.argv) < 2:
    raise SystemExit("usage: answered_otherwise.py <recording> [<recording> ...]")

rows = []
for workdir in sys.argv[1:]:
    h, _ = load(workdir)
    if not h.unchanged:
        raise SystemExit(f"{workdir} has no empty change: traceeval mutants --workdir {workdir} --only unchanged")
    runs = [r for stats in h.unchanged.values() for r in stats.runs]
    known = sum(r["cassette"]["known"] for r in runs)
    differ = sum(r["cassette"]["differ"] for r in runs)
    # the runs that end otherwise than the test's majority on the original app
    off = sum(r["passed"] != (h.baseline_pass_rate(r["test_id"]) >= 0.5) for r in runs)
    # per test: is a request answered otherwise in every run, in some, and are its runs one and the same (the
    # same count of other answers, the same tokens, the same final state)
    every = some = one_run = 0
    for stats in h.unchanged.values():
        hit = sum(r["cassette"]["differ"] > 0 for r in stats.runs)
        every += hit == len(stats.runs)
        some += 0 < hit < len(stats.runs)
        one_run += len({(r["cassette"]["differ"], r["tokens"], r["state_digest"]) for r in stats.runs}) == 1
    rows.append(
        f"| `{workdir}` | {differ:,} of {known:,} ({differ / known:.1%}) | {one_run} of {len(h.unchanged)} | "
        f"{every} | {some} | {off} of {len(runs)} | {len(h.unchanged_flips())} |"
    )

print()
print(
    "| recording | requests answered otherwise | tests whose runs are one and the same | tests with another answer "
    "in every run | in some runs | runs that end otherwise than the baseline | tests that flip |"
)
print("|---|---|---|---|---|---|---|")
print("\n".join(rows))
