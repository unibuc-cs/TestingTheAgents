"""A model update as a change without a diff: which tests pass under one model and fail under another, from the
baselines of recordings of the same app and suite. Each ordered pair of models is a ready-made change with a ground
truth, the setting the methods that do not read the diff were built for. Only the baseline files are read.

    python scripts/analysis/model_updates.py [recording ...]       # default runs/gemma7 runs/qwen7 runs/gptoss7
"""

import json
import sys
from collections import Counter
from itertools import permutations
from pathlib import Path


def baseline(workdir):
    """test id -> [(passed, tokens)] over its valid baseline runs."""
    runs = {}
    with open(Path(workdir) / "history" / "baseline.jsonl", encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            if r.get("classification") != "INFRA_INVALID":
                runs.setdefault(r["test_id"], []).append((bool(r["passed"]), r["tokens"]))
    return runs


recordings = sys.argv[1:] or ["runs/gemma7", "runs/qwen7", "runs/gptoss7"]
rates = {}
for workdir in recordings:
    runs = baseline(workdir)
    rates[workdir] = {t: sum(p for p, _ in v) / len(v) for t, v in runs.items()}
    unstable = sum(1 for r in rates[workdir].values() if 0 < r < 1)
    tokens = sum(sum(c for _, c in v) / len(v) for v in runs.values())
    print(
        f"{workdir:16s} {len(runs)} tests, {sum(r >= 0.5 for r in rates[workdir].values())} pass by majority, "
        f"{unstable} whose runs disagree, {tokens:,.0f} tokens for the suite"
    )

print("\nmodel update, old to new: tests that pass under the old model and fail under the new one")
for old, new in permutations(recordings, 2):
    common = sorted(set(rates[old]) & set(rates[new]))
    broke = [t for t in common if rates[old][t] >= 0.5 and rates[new][t] < 0.5]
    fixed = [t for t in common if rates[old][t] < 0.5 and rates[new][t] >= 0.5]
    families = Counter(t.split("-")[0].split("/")[0] for t in broke)
    by_family = dict(sorted(families.items()))
    print(f"  {old:16s} to {new:16s} regress {len(broke):3d}, fixed {len(fixed):2d}; by family {by_family}")
