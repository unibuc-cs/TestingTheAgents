"""Probe (read-only): the fault matrix of a recording. Which tests ever reveal a change, how many are redundant,
how many model calls a test makes, and what share of the suite's cost the never-revealing tests are."""

import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

work = Path(sys.argv[1])


def read(path):
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


base = defaultdict(list)
for r in read(work / "history" / "baseline.jsonl"):
    base[r["test_id"]].append(r)
rate = {t: sum(r["passed"] for r in rs) / len(rs) for t, rs in base.items()}
cost = {t: statistics.fmean(r["tokens"] for r in rs) for t, rs in base.items()}
tests = list(base)
variants = {}
meta = {}
for path in sorted((work / "history" / "variants").glob("*.jsonl")):
    per = defaultdict(list)
    for r in read(path):
        if r["classification"] != "INFRA_INVALID":
            per[r["test_id"]].append(r)
    variants[path.stem] = {t: sum(r["passed"] for r in rs) / len(rs) for t, rs in per.items()}
    mp = work / "variants" / path.stem / "mutation.json"
    meta[path.stem] = json.loads(mp.read_text()) if mp.exists() else {}
reveal = {v: {t for t in tests if rate[t] >= 0.5 and vr.get(t, rate[t]) < 0.5} for v, vr in variants.items()}
ever = set().union(*reveal.values())
print("tests:", len(tests), "| ever revealing:", len(ever), "| never revealing:", len(tests) - len(ever))
never = [t for t in tests if t not in ever]
print("never revealing, by family:", Counter(t.split("-")[0].split("/")[0] for t in never).most_common())
print(
    "share of the suite's tokens spent on never-revealing tests:",
    round(sum(cost[t] for t in never) / sum(cost.values()), 3),
)
# signature of each test across variants
sig = defaultdict(list)
for t in tests:
    sig[tuple(sorted(v for v in reveal if t in reveal[v]))].append(t)
groups = [g for s, g in sig.items() if s and len(g) > 1]
print(
    "distinct non-empty reveal signatures:",
    sum(1 for s in sig if s),
    "| tests sharing a signature with another:",
    sum(len(g) for g in groups),
)
for s, g in sorted(sig.items(), key=lambda kv: -len(kv[1]))[:8]:
    print("   ", len(g), "tests reveal exactly", list(s)[:4], "..." if len(s) > 4 else "", g[:8])
reg = [v for v in variants if meta[v].get("expected_regression")]
print("regressions:", len(reg), "| revealed by 0 tests:", [v for v in reg if not reveal[v]])
print("regressions revealed by exactly one test:", [(v, list(reveal[v])[0]) for v in reg if len(reveal[v]) == 1])
sizes = sorted(len(reveal[v]) for v in reg)
print("revealing tests per regression (sorted):", sizes)
# what share of the regressions' revealing tests come from the three biggest
tot = sum(sizes)
print("total (regression, revealing test) pairs:", tot, "| top 3 changes hold", round(sum(sizes[-3:]) / tot, 2))
# model calls: steps + agent turns is a lower bound (a turn ends with one more call); tokens per call
steps = [r["steps"] + len(r["agents"]) for rs in base.values() for r in rs if r["rep"] == 0 and r["steps"] is not None]
print(
    "model calls per test (tool calls + delegations + one final answer per agent turn, rep 0): median",
    statistics.median(steps),
    "mean",
    round(statistics.fmean(steps), 1),
    "p90",
    sorted(steps)[int(0.9 * len(steps))],
    "max",
    max(steps),
)
print(
    "tests that are a single model call (route-only):",
    sum(1 for rs in base.values() if rs[0]["steps"] == 1 and len(rs[0]["agents"]) == 1),
)
fam = defaultdict(list)
for t, rs in base.items():
    fam[
        "route-only dataset"
        if t.startswith("DS-ROUTING")
        else "intents dataset"
        if t.startswith("DS-INTENTS")
        else "workflow"
        if t.startswith("WF")
        else "scenario"
    ].append(rs[0])
for k, rs in fam.items():
    print(
        "   ",
        k,
        len(rs),
        "tests | median tool calls+delegations",
        statistics.median(r["steps"] for r in rs),
        "| median agents",
        statistics.median(len(r["agents"]) for r in rs),
        "| median tokens",
        int(statistics.median(r["tokens"] for r in rs)),
        "| share of suite tokens",
        round(sum(r["tokens"] for r in rs) / sum(x[0]["tokens"] for x in base.values()), 2),
    )
print(
    "prompt vs completion tokens, whole baseline rep 0:",
    sum(rs[0]["prompt_tokens"] for rs in base.values()),
    sum(rs[0]["completion_tokens"] for rs in base.values()),
)
