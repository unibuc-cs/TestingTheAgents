"""Probe (read-only): are the repetitions of a recording alike? Patterns of token counts across reps."""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


def read(path):
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


def pattern(values):
    names, out = {}, []
    for v in values:
        out.append(names.setdefault(v, "ABCDE"[len(names)]))
    return "".join(out)


for name in sys.argv[1:]:
    work = Path(name)
    print("=====", work.name)
    for label, paths in (
        ("baseline", [work / "history" / "baseline.jsonl"]),
        ("variants", sorted((work / "history" / "variants").glob("*.jsonl"))),
    ):
        tok, msg, traj, outcome = Counter(), Counter(), Counter(), Counter()
        n = 0
        for path in paths:
            per = defaultdict(dict)
            for r in read(path):
                if r["classification"] != "INFRA_INVALID":
                    per[r["test_id"]][r["rep"]] = r
            for by_rep in per.values():
                reps = [by_rep[k] for k in sorted(by_rep)]
                if len(reps) < 2:
                    continue
                n += 1
                tok[pattern([r["tokens"] for r in reps])] += 1
                msg[pattern([r["final_message"] for r in reps])] += 1
                traj[pattern([tuple(r["tools"]) for r in reps])] += 1
                outcome[pattern([r["passed"] for r in reps])] += 1
        print(label, "pairs", n)
        print("   tokens  :", tok.most_common(6))
        print("   message :", msg.most_common(6))
        print("   tools   :", traj.most_common(6))
        print("   outcome :", outcome.most_common(6))
