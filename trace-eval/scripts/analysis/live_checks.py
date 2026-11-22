"""The live checks of a recording's changes, against the evaluator's runs of the same method on the recorded runs.

``traceeval check <change> --history <recording> --budget B --backend vllm``, run on every change one at a time,
leaves one log per change in a folder (``<change>.log``). The evaluator ran the same method replay-first on the
recorded runs, offline (``results/replay_first.csv``, five seeds). This script puts the two side by side, per
change: the verdict, the tests run with the model, and the tokens. It prints markdown.

"Offline" below is the evaluator; "the replay" is the first phase of a check, which both of them start from.

    python scripts/analysis/live_checks.py runs/gemma8 runs/live_check8 [budget]     # budget 0.2 by default
"""

import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from replaylib import load

from traceeval.experiment.report import CLEAN_STOPS

if len(sys.argv) < 3:
    raise SystemExit("usage: live_checks.py <recording> <folder of check logs> [budget]")
workdir, logs = sys.argv[1], Path(sys.argv[2])
budget = float(sys.argv[3]) if len(sys.argv) > 3 else 0.2
h, _ = load(workdir)
full = h.total_cost()

# the lines of a check's log that are read (``experiment/check.py`` prints them)
REPLAY = re.compile(r"^replay: (\d+) of (\d+) tests replay to the end.*; (\d+) diverge")
SPENT = re.compile(r"^(\d+) tests run with the model, ([\d,]+) tokens")
FAILED = re.compile(r"^  (\S+)\s+FAIL ")


def kind(reason: str) -> str:
    """A stop reason of the evaluator as one of three verdicts."""
    return "regression" if reason == "regression" else "clean" if reason in CLEAN_STOPS else "budget"


def read(path: Path) -> dict | None:
    """One check's log: its verdict, the tests it ran with the model, its tokens and the tests that failed. None
    for a check that gave no verdict (the server went away)."""
    out = {"failed": [], "diverged": None}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if m := REPLAY.match(line):
            out["diverged"] = int(m[3])
        elif m := FAILED.match(line):
            out["failed"].append(m[1])
        elif line.startswith("REGRESSION"):
            out["verdict"] = "regression"
        elif line.startswith("no regression"):
            out["verdict"] = "clean"
        elif line.startswith("no failure within the budget"):
            out["verdict"] = "budget"
        elif m := SPENT.match(line):
            out["tests"], out["tokens"] = int(m[1]), float(m[2].replace(",", ""))
    return out if "verdict" in out and "tokens" in out else None


# the method as the evaluator ran it, replay-first, at the same budget: five seeds per change
rf = pd.read_csv(Path(workdir) / "results" / "replay_first.csv")
rf = rf[(rf.strategy == "adaptive_bayes") & np.isclose(rf.budget_fraction, budget)]

rows, same, majority_same, no_verdict = [], 0, 0, []
found = {"live": 0, "offline": 0}
false_alarms = {"live": 0, "offline": 0}
spent = {"live": [], "offline": []}  # per check, the tokens as a share of the suite
for variant in h.variants:
    live = read(logs / f"{variant}.log") if (logs / f"{variant}.log").exists() else None
    if live is None:
        no_verdict.append(variant)
        continue
    seeds = rf[rf.variant == variant]
    offline = Counter(kind(reason) for reason in seeds.stop_reason)
    majority = offline.most_common(1)[0][0]
    revealing = h.revealing_tests(variant)
    same += live["verdict"] in offline
    majority_same += live["verdict"] == majority
    if revealing:
        found["live"] += live["verdict"] == "regression"
        found["offline"] += majority == "regression"
    else:
        false_alarms["live"] += live["verdict"] == "regression"
        false_alarms["offline"] += majority == "regression"
    # the evaluator's tests and tokens: one value when the five seeds agree, a range otherwise
    few, many = seeds.tests_run.min(), seeds.tests_run.max()
    low, high = seeds.cost_fraction.min(), seeds.cost_fraction.max()
    tests = f"{few} to {many}" if many > few else f"{few}"
    tokens = f"{low:.1%} to {high:.1%}" if high - low > 0.0005 else f"{low:.1%}"
    spent["live"].append(live["tokens"] / full)
    spent["offline"].append(seeds.cost_fraction.mean())
    rows.append(
        f"| `{variant}` | {'yes' if revealing else 'no'} | {len(revealing)} | {live['diverged']} | {live['verdict']} | "
        f"{live['tests']} | {live['tokens'] / full:.1%} | {', '.join(live['failed'])} | "
        f"{', '.join(f'{v} ({n} of {len(seeds)})' for v, n in offline.most_common())} | {tests} | {tokens} |"
    )

regressions = sum(bool(h.revealing_tests(v)) for v in h.variants if v not in no_verdict)
print(f"- checks: {len(rows)} of {len(h.variants)}" + (f" (no verdict: {', '.join(no_verdict)})" if no_verdict else ""))
print(
    f"- the live verdict is one the evaluator gave in some seed on {same}, and its majority verdict on {majority_same};"
)
print(
    f"- regressions ({regressions}): the live check found {found['live']}, the evaluator's majority {found['offline']};"
)
print(
    f"- changes no test reveals ({len(rows) - regressions}): regression verdicts live {false_alarms['live']}, "
    f"offline {false_alarms['offline']};"
)
# The live check pays for the requests the cassette lacks, wherever they come in a run; the evaluator charges a
# diverged test everything after its divergence point, so its tokens are an upper bound of the live ones.
print(
    f"- tokens per check: live {np.mean(spent['live']):.1%} of the suite; offline, charged from the divergence "
    f"point on, {np.mean(spent['offline']):.1%}."
)
print()
print(
    "| change | regression | revealing tests | tests that diverge | live verdict | live tests | live tokens | "
    "failed live | offline verdicts | offline tests | offline tokens |"
)
print("|---|---|---|---|---|---|---|---|---|---|---|")
print("\n".join(rows))
