"""Are a recording's change sets those of its own tree? A change set names changed code by line number, and the
baseline names the lines each test executed. Both must count lines in the same files: a variant recorded after the
app's code moved (even by a comment-only edit) gets line ids no recorded test executed, and the strategies no
longer see which tests ran the changed line.

For each variant of a recording, the stored change set is compared with the one recomputed as the diff of the
recording's own baseline copy (``variants/baseline/sut``) and the variant's copy (comments do not count in a diff,
so only the line numbers can differ). ``--fix`` rewrites the stored change sets that differ and keeps the old file
beside the new one as ``changeset.stale.json``.

    python scripts/analysis/stale_line_ids.py [--fix] [recording ...]
    # default: runs/gemma7 runs/gemma7_batches runs/gemma7_sweep
"""

import json
import sys
from pathlib import Path

from traceeval.mutation import compute_changeset

fix = "--fix" in sys.argv
recordings = [a for a in sys.argv[1:] if a != "--fix"] or ["runs/gemma7", "runs/gemma7_batches", "runs/gemma7_sweep"]
for workdir in recordings:
    variants = Path(workdir) / "variants"
    baseline = variants / "baseline" / "sut"
    if not baseline.exists():
        print(f"{workdir}: no baseline copy, nothing to compare with")
        continue
    stale = 0
    for folder in sorted(p for p in variants.iterdir() if p.name != "baseline" and (p / "sut").exists()):
        stored_path = folder / "changeset.json"
        stored = json.loads(stored_path.read_text(encoding="utf-8"))
        recomputed = compute_changeset(baseline, folder / "sut", name=folder.name)
        old, new = {c["id"] for c in stored["components"]}, set(recomputed.ids())
        if old == new:
            continue
        stale += 1
        print(f"   {folder.name}: stored {sorted(old - new)}, on the recording's own tree {sorted(new - old)}")
        if fix:
            (folder / "changeset.stale.json").write_text(stored_path.read_text(encoding="utf-8"), encoding="utf-8")
            stored_path.write_text(json.dumps(recomputed.to_dict(), indent=1), encoding="utf-8")
            (folder / "diff.patch").write_text(recomputed.diff, encoding="utf-8")
    checked = sum(1 for p in variants.iterdir() if p.name != "baseline" and (p / "sut").exists())
    print(
        f"{workdir}: {checked} variants, {stale} with a change set that is not of the recording's tree"
        + (" (rewritten)" if fix and stale else "")
    )
