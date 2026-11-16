"""Probe 6: FS-0101's reference PR against the existing feature 'reviews not required' (case CFG-01), and the
cases the regression line leaves out because they fail on the unchanged application."""

import sys
from pathlib import Path

from traceeval.catalog import load_catalog
from traceeval.experiment.executor import run_case
from traceeval.experiment.sutloader import load_sut
from traceeval.mutation.engine import materialize_variant
from traceeval.selection.base import affinity
from traceeval.spec import prs as P
from traceeval.spec.runner import record_baseline

workdir = Path(sys.argv[1])
catalog = {c.id: c for c in load_catalog()}
sut_dir, runs, deps = record_baseline(workdir, catalog)

base = runs["CFG-01"]
print("CFG-01 on the unchanged app:", base["classification"], base["failed_checks"], "|", base["final_message"][:160])
print("  tool calls:", [(e["tool"], e["status"]) for e in base["events"] if e.get("kind") == "tool.call"])

for pid in ("FS-0101/pr_correct", "FS-0103/pr_correct", "FS-0102/pr_correct", "FS-0105/pr_fix"):
    pr = next(p for p in P.PRS if p.id == pid)
    vdir, change = materialize_variant(pr.mutation, workdir / "variants")
    selected = sorted(t for t in catalog if affinity(change, deps[t]) > 0)
    red = [t for t in selected if not runs[t]["passed"]]
    print(f"\n{pid}: {len(selected)} cases selected, left out as failing on the unchanged app: {red}")
    if pid != "FS-0101/pr_correct":
        continue
    sut = load_sut(vdir)
    # the service itself, with reviews not required: the publishing skill would go straight to publish_page
    for page in ("p5", "p4"):
        state = sut.sub("services.state").State.from_fixture(vdir / "fixtures" / "base.json")
        try:
            out = sut.sub("services.workflow").publish_page(state, page, "bob", None, 30)
            print(f"  service publish_page({page}) with the 30-day limit: {out['status']}")
        except Exception as exc:  # noqa: BLE001
            print(f"  service publish_page({page}) with the 30-day limit: refused - {type(exc).__name__}: {exc}")
    rec = run_case(sut, catalog["CFG-01"], backend="replay", variant=pid, keep_state=True)
    print("  CFG-01 on the PR:", rec["classification"], rec["failed_checks"], "|", rec["final_message"][:160])
    print(
        "  tool calls:",
        [
            (e["tool"], e["status"], (e.get("message") or "")[:70])
            for e in rec["events"]
            if e.get("kind") == "tool.call"
        ],
    )
    sut.unload()
