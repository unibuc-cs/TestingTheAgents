"""Probe (read-only): which deps differ between repetitions, and whether a judged case flips on its answer or
on its verdict."""

import json
import sys
from pathlib import Path


def read(path):
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


g = Path(sys.argv[1])
rows = [r for r in read(g / "history" / "baseline.jsonl") if r["test_id"] in ("AUT-10", "WF3-01", "AST-01")]
for t in ("AUT-10", "WF3-01"):
    rs = sorted((r for r in rows if r["test_id"] == t), key=lambda r: r["rep"])
    a, b = set(rs[0]["deps"]), set(rs[1]["deps"])
    print(t, "only in rep 0:", sorted(a - b)[:12], "| only in rep 1:", sorted(b - a)[:40])
    print(
        "   tools per rep:",
        [r["tools"] for r in rs][:2],
        "steps",
        [r["steps"] for r in rs],
        "tokens",
        [r["tokens"] for r in rs],
    )
    print("   same final message in all reps:", len({r["final_message"] for r in rs}) == 1)
# how often the trajectory (tools, tokens) differs between reps on the baseline
by = {}
for r in read(g / "history" / "baseline.jsonl"):
    by.setdefault(r["test_id"], []).append(r)
diff_tools = [t for t, rs in by.items() if len({tuple(r["tools"]) for r in rs}) > 1]
diff_tokens = [t for t, rs in by.items() if len({r["tokens"] for r in rs}) > 1]
diff_msg = [t for t, rs in by.items() if len({r["final_message"] for r in rs}) > 1]
print("baseline tests whose tool sequence differs between reps:", diff_tools)
print("baseline tests whose token count differs between reps:", len(diff_tokens), diff_tokens[:12])
print("baseline tests whose final message differs between reps:", len(diff_msg), diff_msg[:12])
for t in diff_tokens[:6]:
    print("   ", t, [(r["rep"], r["tokens"], r["steps"]) for r in sorted(by[t], key=lambda r: r["rep"])])

q = Path(sys.argv[2])
base = [r for r in read(q / "history" / "baseline.jsonl") if r["test_id"] == "PUB-20"]
var = [r for r in read(q / "history" / "variants" / "benign_code_comment_docstring.jsonl") if r["test_id"] == "PUB-20"]
print("qwen PUB-20 baseline:")
for r in base:
    print(
        "   rep",
        r["rep"],
        r["classification"],
        repr(r["final_message"][:150]),
        "| judge:",
        (r.get("judge") or {}).get("verdict", "")[:90],
    )
print("qwen PUB-20 on the comment-only change:")
for r in var:
    print(
        "   rep",
        r["rep"],
        r["classification"],
        repr(r["final_message"][:150]),
        "| judge:",
        (r.get("judge") or {}).get("verdict", "")[:90],
    )
cs = json.loads((q / "variants" / "benign_code_comment_docstring" / "changeset.json").read_text())
print("change set of benign_code_comment_docstring:", cs["components"], cs["files"])
