"""Counts for the paper draft (``docs/paper``): its floats, a rough word count, and its citation keys against the
bibliography.

    python scripts/analysis/paper_counts.py
"""

import re
from pathlib import Path

paper = Path("docs/paper")
tex = (paper / "main.tex").read_text(encoding="utf-8")
print(
    "tables:",
    tex.count(r"\begin{table}"),
    "| figures:",
    tex.count(r"\begin{figure}"),
    "| algorithms:",
    tex.count(r"\begin{algorithm}"),
    "| equations:",
    tex.count(r"\begin{equation}"),
)
cited = {key.strip() for group in re.findall(r"\\cite\{([^}]*)\}", tex) for key in group.split(",")}
entries = set(re.findall(r"@\w+\{([^,\s]+),", (paper / "refs.bib").read_text(encoding="utf-8")))
print("cited keys:", len(cited), "| bibliography entries:", len(entries))
print("cited but not in refs.bib:", sorted(cited - entries))
print("in refs.bib, never cited:", sorted(entries - cited))
words = re.findall(r"[A-Za-z]{2,}", re.sub(r"\\[a-zA-Z]+|\{|\}|\$[^$]*\$", " ", tex))
print("rough word count of main.tex:", len(words))
