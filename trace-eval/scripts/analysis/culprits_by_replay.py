"""Culprits by replay (TODO.md section 9, step 4): on a recording of batches whose members are recorded alone too,
how well the members' own replays name the member a batch's failure comes from.

For every pair of a batch and a test that reveals it:

- the culprits: the members the test reveals on their own (none: the members fail it only together);
- the suspects: the members whose own replay reaches the test or fails it (``experiment/culprits.py``), found with
  no model call;
- whether every culprit is a suspect, whether the one suspect is the culprit, and how many runs of the failing test
  find a culprit by halving: among the suspects, against among all the members.

With the logs of the live checks, the same for the test each check failed on, beside the member that owns the
component the check blamed most.

    python scripts/analysis/culprits_by_replay.py runs/gemma8_batches [runs/live_check8_batches] [--md out.md]
"""

import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, "scripts")
from batch_sweep import SWEEP  # noqa: E402  (the twenty batches drawn at random)

from traceeval.experiment.culprits import halving_runs, suspects  # noqa: E402
from traceeval.experiment.history import History  # noqa: E402
from traceeval.experiment.replay_first import Replays  # noqa: E402
from traceeval.mutation.catalog import BATCHES, get_mutation  # noqa: E402

BATCHES.extend(SWEEP)
argv = sys.argv[1:]
md = argv[argv.index("--md") + 1] if "--md" in argv else None
positional = [a for i, a in enumerate(argv) if not a.startswith("--") and (i == 0 or argv[i - 1] != "--md")]
workdir = Path(positional[0] if positional else "runs/gemma8_batches")
logs = Path(positional[1]) if len(positional) > 1 else None
h, rp = History.load(workdir), Replays.load(workdir)


def live(batch: str) -> tuple[str, str]:
    """The test the live check of ``batch`` failed on first, and the component it blamed most; empty if none."""
    path = logs / f"{batch}.log" if logs else None
    if path is None or not path.exists():
        return "", ""
    failed, blamed = "", ""
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not failed and (m := re.match(r"^  (\S+)\s+FAIL ", line)):
            failed = m[1]
        if line.startswith("blamed: "):
            blamed = line[len("blamed: ") :].split(",")[0].rsplit(" ", 1)[0]
    return failed, blamed


pairs, batches = [], []
for b in sorted(v for v in h.variants if v.startswith("batch_")):
    members = get_mutation(b).members
    member_rows = {m: rp.rows[m] for m in members if m in rp.rows}
    alone = {m: h.revealing_tests(m) for m in members}
    for t in sorted(h.revealing_tests(b)):
        culprits = [m for m in members if t in alone[m]]
        named = suspects(member_rows, t)
        pairs.append(
            {
                "batch": b,
                "members": len(members),
                "test": t,
                "culprits": culprits,
                "suspects": named,
                "interaction": not culprits,
                "covered": set(culprits) <= set(named),
                "unique": len(named) == 1 and named[0] in culprits,
                "runs, suspects": halving_runs(len(named)),
                "runs, all members": halving_runs(len(members)),
            }
        )
    failed, blamed = live(b)
    if failed:
        owner = next((m for m in members if blamed and blamed in h.changesets[m].ids()), "")
        named = suspects(member_rows, failed)
        culprits = [m for m in members if failed in alone[m]]
        batches.append(
            {
                "batch": b,
                "members": len(members),
                "failed live": failed,
                "culprits": ", ".join(culprits) or "none (an interaction)",
                "suspects": ", ".join(named) or "none",
                "blamed most, its member": owner,
                # for the counts below: a culprit alone, and how the suspects and the blame relate to the culprits
                "alone": bool(culprits),
                "blame right": owner in culprits,
                "covered": set(culprits) <= set(named),
                "unique": len(named) == 1 and named[0] in culprits,
                "only culprits": bool(named) and set(named) <= set(culprits),
            }
        )

df = pd.DataFrame(pairs)
single = df[~df.interaction]
print(
    f"{workdir}: {df.batch.nunique()} batches with a revealing test, {len(df)} (batch, revealing test) pairs; "
    f"{len(single)} with a culprit alone, {int(df.interaction.sum())} that only the members together fail"
)
print(f"every culprit among the suspects: {int(single.covered.sum())} of {len(single)}")
print(f"one suspect, and it is the culprit: {int(single.unique.sum())} of {len(single)}")
print(
    f"suspects per pair: {single.suspects.map(len).mean():.2f} on average, of {single.members.mean():.2f} members; "
    f"runs of the failing test to find a culprit by halving: {single['runs, suspects'].mean():.2f} among the "
    f"suspects, {single['runs, all members'].mean():.2f} among all the members"
)
inter = df[df.interaction]
if len(inter):
    print(
        f"the pairs only the members together fail: no suspect in "
        f"{int((inter.suspects.map(len) == 0).sum())} of {len(inter)}"
    )
if batches:
    live_df = pd.DataFrame(batches)
    print("\nthe test each live check failed on first:")
    print(live_df[["batch", "members", "failed live", "culprits", "suspects", "blamed most, its member"]].to_string())
    a = live_df[live_df.alone]
    print(
        f"\nof the {len(a)} live failures with a culprit alone: the member blamed most is a culprit in "
        f"{int(a['blame right'].sum())}; every culprit is a suspect in {int(a.covered.sum())}; one suspect, the "
        f"culprit, in {int(a.unique.sum())}; every suspect a culprit in {int(a['only culprits'].sum())}"
    )
if md:
    out = [
        "| batch | members | revealing tests | with a culprit alone | culprit among the suspects | one suspect, the "
        "culprit | runs to find it: suspects, all members |",
        "|---|---|---|---|---|---|---|",
    ]
    for b, g in df.groupby("batch", sort=False):
        s = g[~g.interaction]
        runs = f"{s['runs, suspects'].mean():.1f}, {s['runs, all members'].mean():.1f}" if len(s) else ""
        out.append(
            f"| `{b}` | {g.members.iloc[0]} | {len(g)} | {len(s)} | {int(s.covered.sum())} | "
            f"{int(s.unique.sum())} | {runs} |"
        )
    Path(md).write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
