"""Probe a recorded experiment (read-only): classifications, flakiness, deps attribution, failing checks."""

import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

work = Path(sys.argv[1])


def read(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


base = read(work / "history" / "baseline.jsonl")
print(
    "baseline records", len(base), "tests", len({r["test_id"] for r in base}), "reps", sorted({r["rep"] for r in base})
)
print("baseline classes", Counter(r["classification"] for r in base))
print("backend", Counter(r["backend"] for r in base))
by_test = defaultdict(list)
for r in base:
    by_test[r["test_id"]].append(r)
order = list(by_test)
print("first test in file:", order[0])
# pass-rate distribution
rates = {t: sum(r["passed"] for r in rs) / len(rs) for t, rs in by_test.items()}
print("baseline pass-rate histogram", Counter(round(v, 2) for v in rates.values()))
print("baseline tests failing always:", sorted(t for t, v in rates.items() if v == 0))
print("baseline tests flaky:", sorted((t, v) for t, v in rates.items() if 0 < v < 1))
# the shape of the baseline runs: steps, agents, tokens, how they ended, the judge's verdicts
steps = [r["steps"] for r in base if r["steps"] is not None]
print(
    "steps: median",
    statistics.median(steps),
    "mean",
    round(statistics.fmean(steps), 2),
    "max",
    max(steps),
    "min",
    min(steps),
)
print("agents per run", Counter(len(r["agents"]) for r in base))
print("tokens per run: median", statistics.median(r["tokens"] for r in base), "max", max(r["tokens"] for r in base))
print("termination", Counter(r["termination"] for r in base))
print("judge runs", Counter((r["test_id"], (r["judge"] or {}).get("ok")) for r in base if r.get("judge")))
# module-level deps attribution
for t in order[:2]:
    for r in by_test[t]:
        mod = sorted(d for d in r["deps"] if d.startswith("code:") and "::" not in d)
        print("  ", t, "rep", r["rep"], "deps", len(r["deps"]), "module-level", mod)
any_mod = Counter()
for r in base:
    for d in r["deps"]:
        if d.startswith("code:") and "::" not in d:
            any_mod[(r["test_id"], r["rep"], d)] += 1
print("all module-level deps in the baseline:", sorted(any_mod))
# dep stability across reps
unstable = 0
for rs in by_test.values():
    sets = [frozenset(d for d in r["deps"]) for r in rs]
    if len(set(sets)) > 1:
        unstable += 1
print("tests whose deps differ between reps:", unstable, "of", len(by_test))
# kinds of deps
kinds = Counter(d.split(":", 1)[0] for r in base if r["rep"] == 0 for d in r["deps"])
print("dep kinds (rep 0)", kinds)
print("tests with fixture dep:", sum(any(d.startswith("fixture:") for d in r["deps"]) for r in base))

# the changed copies: outcomes, runs that disagree with their majority, and what fails
vdir = work / "history" / "variants"
tot = Counter()
flaky_pairs = 0
pairs = 0
reveal_checks = Counter()
reveal_only_answer = []
harness = []
infra = Counter()
revealing_per_variant = {}
for path in sorted(vdir.glob("*.jsonl")):
    recs = read(path)
    tot.update(r["classification"] for r in recs)
    vt = defaultdict(list)
    for r in recs:
        vt[r["test_id"]].append(r)
        if r["classification"] == "HARNESS_ERROR":
            harness.append((path.stem, r["test_id"], r["rep"], (r["error"] or "").strip().splitlines()[-1][:160]))
        if r["classification"] == "INFRA_INVALID":
            infra[path.stem] += 1
    revealing = []
    for t, rs in vt.items():
        valid = [r for r in rs if r["classification"] != "INFRA_INVALID"]
        if not valid:
            continue
        rate = sum(r["passed"] for r in valid) / len(valid)
        pairs += 1
        if 0 < rate < 1:
            flaky_pairs += 1
        if rates.get(t, 0) >= 0.5 and rate < 0.5:
            revealing.append(t)
            # which checks fail in the failing runs
            names = Counter()
            for r in valid:
                if not r["passed"]:
                    for c in r["failed_checks"]:
                        names[c.split(":")[0].split("~")[0].split("!")[0]] += 1
                    if not r["failed_checks"]:
                        names["(none listed: " + r["classification"] + ")"] += 1
            kinds_failed = set(names)
            for k in kinds_failed:
                reveal_checks[k] += 1
            if kinds_failed <= {"response", "answered", "judge"}:
                reveal_only_answer.append((path.stem, t, dict(names)))
    revealing_per_variant[path.stem] = revealing
print("variants", len(revealing_per_variant), "classes", tot)
print("(variant,test) pairs", pairs, "with mixed outcomes across reps", flaky_pairs)
print("INFRA_INVALID per variant", dict(infra))
print("HARNESS_ERROR runs", len(harness))
for h in harness[:25]:
    print("   ", h)
print("revealing tests per variant:")
for v, ts in revealing_per_variant.items():
    print(f"   {v:45s} {len(ts):3d} {ts[:8]}")
print("check kinds among revealing (variant,test) pairs", reveal_checks.most_common())
print("revealing pairs whose only failed checks are about the answer text:", len(reveal_only_answer))
for x in reveal_only_answer[:40]:
    print("   ", x)
