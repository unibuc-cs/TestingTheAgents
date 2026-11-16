"""Probe 4: from the evidence of the shipped demo, which clauses tell each wrong PR from the correct PR of
its spec, and what each kind of check contributes."""

import json
import sys
from collections import Counter
from pathlib import Path

data = json.load(open(Path(sys.argv[1]) / "shipped_clauses.json"))
CORRECT = {
    "FS-0101": "FS-0101/pr_correct",
    "FS-0102": "FS-0102/pr_correct",
    "FS-0103": "FS-0103/pr_correct",
    "FS-0104": "FS-0104/pr_config_70",
    "FS-0105": "FS-0105/pr_fix",
}
ALSO_CORRECT = {"FS-0101/pr_branchy"}


def fails(pid):
    return {cid: (kind, summary) for cid, kind, status, rung, summary in data[pid] if status == "fail"}


def group(cid, kind, summary):
    if cid == "regression-tests":
        return "regression"
    if kind == "contract" and cid.startswith("function_contract"):
        if "does not exist" in summary:
            return "contract:function-missing"
        if "property test" in summary:
            return "contract:pbt(+solver)" if "solver" in summary else "contract:pbt"
        return "contract:solver-only"
    if kind == "contract":
        return "behaviour-property"
    return kind


rows, only = [], Counter()
for pid in data:
    spec = pid.split("/")[0]
    if pid in CORRECT.values() or pid in ALSO_CORRECT:
        continue
    base = fails(CORRECT[spec])
    mine = fails(pid)
    extra = {cid: group(cid, *v) for cid, v in mine.items() if cid not in base}
    groups = sorted(set(extra.values()))
    rows.append((pid, groups, sorted(extra)))
    plain = {"example", "regression"}
    if not groups:
        only["nothing distinguishes it from the correct PR"] += 1
    elif set(groups) & plain:
        only["a scenario or a regression test distinguishes it (plain tests)"] += 1
    else:
        only["only: " + ", ".join(groups)] += 1

print("wrong PR -> checks that fail on it and not on the correct PR of the same spec")
for pid, groups, _cids in rows:
    print(f"  {pid:38s} {groups}")
print()
for k, v in only.most_common():
    print(f"  {v:2d}  {k}")
print(f"  {len(rows)} wrong PRs in all")

print("\ncorrect PRs and what rejects them")
for pid in list(CORRECT.values()) + sorted(ALSO_CORRECT):
    f = fails(pid)
    print(f"  {pid:38s} {sorted(f) or 'accepted'}")
