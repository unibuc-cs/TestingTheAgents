"""Two recordings of the same changes on the same original app, side by side: does a recording made again, under
another start of the model server, say the same?

It compares the empty change of each, the label of every (change, test) pair, the revealing tests of every change,
and the requests the model answered otherwise than the cassette. A pair is compared where both recordings ran it:
a recording made with ``--reached-only`` ran the tests each change reaches, and the others have the replay's
outcome, which no server can move.

    python scripts/analysis/two_recordings.py runs/gemma8 runs/gemma8_restart
"""

import sys

from replaylib import load

if len(sys.argv) != 3:
    raise SystemExit("usage: two_recordings.py <recording> <the same changes recorded again>")
names = sys.argv[1:3]
first, second = (load(name)[0] for name in names)


def made(stats) -> list[dict]:
    """The runs of a test that were really made: valid ones, without the replay's stand-in."""
    return [r for r in stats.valid_runs if not r.get("stand_in")]


def passes(runs: list[dict]) -> bool:
    """The majority outcome of some runs."""
    return sum(r["passed"] for r in runs) / len(runs) >= 0.5


def asked(runs: list[dict]) -> tuple[int, int]:
    """Over some runs: the requests the original app had sent too, and those answered otherwise than the cassette."""
    counts = [r.get("cassette") or {} for r in runs]
    return sum(c.get("known", 0) for c in counts), sum(c.get("differ", 0) for c in counts)


# ---------------------------------------------------------------------------- the empty change of each recording
print("\nthe empty change: the original app, run as the changed copies are")
for name, h in zip(names, (first, second), strict=True):
    runs = [r for stats in h.unchanged.values() for r in made(stats)]
    off = sum(r["passed"] != (h.baseline_pass_rate(r["test_id"]) >= 0.5) for r in runs)
    known, differ = asked(runs)
    print(
        f"  {name}: {len(runs)} runs, {off} end otherwise than the baseline's majority; tests whose majority flips: "
        f"{len(h.unchanged_flips())} {sorted(h.unchanged_flips())}; of {known} requests sent before, {differ} "
        f"({differ / max(1, known):.2%}) answered otherwise"
    )

# ---------------------------------------------------------------------------- the pairs both recordings ran
changes = [v for v in first.variants if v in second.variants]
pairs = [
    (v, t)
    for v in changes
    for t in first.variants[v]
    if t in second.variants[v] and made(first.variants[v][t]) and made(second.variants[v][t])
]
moved = [(v, t) for v, t in pairs if passes(made(first.variants[v][t])) != passes(made(second.variants[v][t]))]
print(
    f"\n{len(changes)} changes in both; {len(pairs)} (change, test) pairs run in both, {len(moved)} with another label"
)
for v, t in moved:
    a, b = made(first.variants[v][t]), made(second.variants[v][t])
    print(
        f"  {v:45s} {t:16s} passing runs: {sum(r['passed'] for r in a)} of {len(a)}, then "
        f"{sum(r['passed'] for r in b)} of {len(b)}"
    )
for name, h in zip(names, (first, second), strict=True):
    runs = [r for v, t in pairs for r in made(h.variants[v][t])]
    known, differ = asked(runs)
    share = differ / max(1, known)
    print(f"  {name}: on those pairs, of {known} requests sent before, {differ} ({share:.2%}) answered otherwise")

# ---------------------------------------------------------------------------- what the labels add up to
revealing = {name: {v: h.revealing_tests(v) for v in changes} for name, h in zip(names, (first, second), strict=True)}
a, b = (revealing[name] for name in names)
print(
    f"\nchanges with at least one revealing test: {sum(bool(a[v]) for v in changes)}, then "
    f"{sum(bool(b[v]) for v in changes)}; the same in both: {sum(bool(a[v]) and bool(b[v]) for v in changes)}"
)
for v in changes:
    if a[v] != b[v]:
        print(f"  {v}: only in the first {sorted(a[v] - b[v])}, only in the second {sorted(b[v] - a[v])}")
if all(a[v] == b[v] for v in changes):
    print("  every change has the same revealing tests in both")
