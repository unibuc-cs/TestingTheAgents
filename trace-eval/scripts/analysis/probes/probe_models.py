"""Probe (read-only): judge verdicts, harness errors and infra-invalid runs in the recordings of each model."""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


def read(path):
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


for name in sys.argv[1:]:
    work = Path(name)
    print("=====", work.name)
    base = list(read(work / "history" / "baseline.jsonl"))
    print(
        "baseline:",
        len(base),
        Counter(r["classification"] for r in base),
        "backend",
        Counter(r["backend"] for r in base),
    )
    by = defaultdict(list)
    for r in base:
        by[r["test_id"]].append(r)
    valid = {t: [r for r in rs if r["classification"] != "INFRA_INVALID"] for t, rs in by.items()}
    rates = {t: (sum(r["passed"] for r in v) / len(v) if v else None) for t, v in valid.items()}
    print(
        "  baseline pass-rate histogram:",
        sorted(Counter(None if v is None else round(v, 2) for v in rates.values()).items(), key=str),
    )
    print("  tests with no valid baseline run:", [t for t, v in rates.items() if v is None])
    print("  valid runs per test:", sorted(Counter(len(v) for v in valid.values()).items()))
    for t in ("SEO-07", "PUB-20"):
        for r in by[t]:
            j = r.get("judge")
            print(
                "  ",
                t,
                "rep",
                r["rep"],
                r["classification"],
                r["failed_checks"],
                "judge:",
                None if not j else (j["ok"], j["tokens"], (j["verdict"] or "")[:110]),
            )
    errs = Counter()
    for r in base:
        if r["classification"] in ("HARNESS_ERROR", "INFRA_INVALID"):
            errs[(r["classification"], (r["error"] or "").strip().splitlines()[-1][:110])] += 1
    for k, v in errs.most_common(8):
        print("  base error:", v, k)
    # deps that differ between reps, and why
    for t, rs in by.items():
        sets = [frozenset(r["deps"]) for r in rs]
        if len(set(sets)) > 1 and work.name == "gemma7":
            common = frozenset.intersection(*sets)
            extra = sorted({d for s in sets for d in s} - common)
            print(
                "  deps differ:",
                t,
                [len(s) for s in sets],
                "non-common sample:",
                [e for e in extra if not e.startswith("line:")][:8],
                len(extra),
            )
    vt = Counter()
    verrs = Counter()
    judge_fail = Counter()
    mixed = []
    n_pairs = 0
    for path in sorted((work / "history" / "variants").glob("*.jsonl")):
        per = defaultdict(list)
        for r in read(path):
            vt[r["classification"]] += 1
            per[r["test_id"]].append(r)
            if r["classification"] in ("HARNESS_ERROR", "INFRA_INVALID"):
                verrs[(path.stem, r["classification"], (r["error"] or "").strip().splitlines()[-1][:100])] += 1
            if r.get("judge") and not r["judge"]["ok"]:
                judge_fail[(path.stem, r["test_id"])] += 1
        for t, rs in per.items():
            v = [r for r in rs if r["classification"] != "INFRA_INVALID"]
            if v:
                n_pairs += 1
                rate = sum(r["passed"] for r in v) / len(v)
                if 0 < rate < 1:
                    mixed.append((path.stem, t, rate))
    print("variants:", vt)
    print("  (variant,test) pairs:", n_pairs, "mixed:", len(mixed))
    if work.name.startswith("gemma7"):
        print("  mixed pairs:", mixed)
    for k, v in verrs.most_common(12):
        print("  variant error:", v, k)
    print("  judge failures (variant,test):", len(judge_fail), list(judge_fail.items())[:6])
