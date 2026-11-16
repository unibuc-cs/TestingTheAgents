"""Probe (read-only on the repo): do the line ids of change sets computed today still fit a recorded history?"""

import json
import sys
from pathlib import Path

from traceeval.mutation import MUTATIONS, materialize_variant

scratch = Path(sys.argv[1])
work = Path(sys.argv[2])

deps: dict[str, set[str]] = {}
with open(work / "history" / "baseline.jsonl", encoding="utf-8") as fh:
    for line in fh:
        if line.strip():
            r = json.loads(line)
            deps.setdefault(r["test_id"], set()).update(r["deps"])


def tests_on(line_ids):
    return {t for t, d in deps.items() if any(i in d for i in line_ids)}


drifted = 0
for m in MUTATIONS:
    stored_path = work / "variants" / m.id / "changeset.json"
    if not stored_path.exists():
        continue
    stored = json.loads(stored_path.read_text())
    old = sorted(c["id"] for c in stored["components"] if c["kind"] == "line")
    _, cs = materialize_variant(m, scratch / "drift")
    new = sorted(c.id for c in cs.components if c.kind == "line")
    old_other = sorted(c["id"] for c in stored["components"] if c["kind"] != "line")
    new_other = sorted(c.id for c in cs.components if c.kind != "line")
    if old != new or old_other != new_other:
        drifted += 1
        a, b = tests_on(old), tests_on(new)
        print(m.id)
        print("   recorded line ids:", old)
        print("   today's line ids :", new)
        print(
            "   tests that executed a changed line: recorded ids",
            len(a),
            "| today's ids against the same history",
            len(b),
            "| lost",
            len(a - b),
            "| gained",
            len(b - a),
        )
        if old_other != new_other:
            print("   other components differ:", old_other, new_other)
print("mutations whose change set differs from the recorded one:", drifted, "of", len(MUTATIONS))

# batches recorded later into copies of this history
for other in sys.argv[3:]:
    o = Path(other)
    for vdir in sorted((o / "variants").iterdir()):
        cs_path = vdir / "changeset.json"
        meta_path = vdir / "mutation.json"
        if not cs_path.exists() or not meta_path.exists():
            continue
        meta = json.loads(meta_path.read_text())
        if not meta.get("members"):
            continue
        comps = json.loads(cs_path.read_text())["components"]
        lines = {c["id"] for c in comps if c["kind"] == "line"}
        member_lines = set()
        for mid in meta["members"]:
            p = work / "variants" / mid / "changeset.json"
            if p.exists():
                member_lines |= {c["id"] for c in json.loads(p.read_text())["components"] if c["kind"] == "line"}
        if lines != member_lines:
            print(
                o.name,
                vdir.name,
                "line ids not those of its members as recorded:",
                sorted(lines - member_lines)[:6],
                "vs",
                sorted(member_lines - lines)[:6],
            )
