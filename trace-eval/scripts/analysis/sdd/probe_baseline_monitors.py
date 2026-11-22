"""Probe 5: trace rules applied to the unchanged application's own runs. Which catalog cases break a rule, and do
those cases pass their own checks? Also: a trace clause whose scope names something no baseline run called."""

import locale
import sys
import tempfile
from collections import Counter
from pathlib import Path

from traceeval.catalog import load_catalog
from traceeval.experiment.sutloader import load_sut
from traceeval.spec.checks import traces
from traceeval.spec.context import CheckContext, evaluate, wrap
from traceeval.spec.model import Clause
from traceeval.spec.product import ProductModel
from traceeval.spec.runner import record_baseline

workdir = Path(sys.argv[1])
catalog = {c.id: c for c in load_catalog()}
sut_dir, runs, deps = record_baseline(workdir, catalog)
sut = load_sut(sut_dir)
ctx = CheckContext(sut=sut, model=ProductModel(sut_dir, runs, deps), catalog=catalog)
ctx.runs.update({(tid, None): rec for tid, rec in runs.items()})  # the baseline runs themselves: nothing is run again

print(
    f"baseline: {len(runs)} runs, {sum(r['passed'] for r in runs.values())} pass, "
    f"failing: {sorted(t for t, r in runs.items() if not r['passed'])}"
)

RULES = {
    "going live is preceded by a clean link check of the same page": Clause(
        "r1",
        "trace",
        data={
            "scope": {"tools": ["publish_page", "schedule_publish"]},
            "stream": "audit",
            "rule": "precedes",
            "event": {"action": ["publish_page", "schedule_publish"]},
            "before": {"action": "validate_links", "broken": 0},
            "same": ["page_id"],
        },
    ),
    "no page goes live with broken links (independent oracle)": Clause(
        "r2",
        "trace",
        data={
            "scope": {"tools": ["publish_page", "schedule_publish"]},
            "stream": "audit",
            "rule": "always",
            "event": {"action": ["publish_page", "schedule_publish"]},
            "where": "expected_broken(run, event.page_id) == 0",
        },
    ),
    "an applied SEO title respects the configured limit": Clause(
        "r3",
        "trace",
        data={
            "scope": {"tools": ["set_page_metadata"]},
            "rule": "always",
            "event": {"kind": "tool.call", "tool": "set_page_metadata", "status": "ok"},
            "where": "event.args.get('title') is None or len(event.args['title']) <= config('seo.max_title_length')",
        },
    ),
    "a page that goes live has an approved review (when required)": Clause(
        "r4",
        "trace",
        data={
            "scope": {"tools": ["publish_page", "schedule_publish"]},
            "rule": "always",
            "event": {"kind": "tool.call", "tool": ["publish_page", "schedule_publish"], "status": "ok"},
            "where": "not config('publishing.require_review') or applied(run, 'approve_review') or "
            "(run.initial_state.pages.get(event.args.page_id) or {}).get('review', {}).get('status') == 'approved'",
        },
    ),
}

for title, clause in RULES.items():
    scope = traces.cases_in_scope(clause.get("scope"), ctx.model, catalog)
    bad = Counter()
    for tid in scope:
        rec = runs[tid]
        items = traces._items(rec, clause.get("stream", "events"))
        for i, item in enumerate(items):
            if not traces._match(item, clause["event"]):
                continue
            try:
                if clause["rule"] == "precedes":
                    ok = traces._preceded(items[:i], item, clause, ctx, rec)
                else:
                    ok = bool(evaluate(clause["where"], ctx.env(run=rec, event=wrap(item))))
            except Exception:  # noqa: BLE001
                ok = False
            if not ok:
                bad[tid] += 1
    passing = sorted(t for t in bad if runs[t]["passed"])
    failing = sorted(t for t in bad if not runs[t]["passed"])
    print(f"\n{title}\n  {len(scope)} runs in scope; rule broken in {len(bad)} runs")
    print(f"  ... of which the case PASSES its own checks: {len(passing)} {passing}")
    print(f"  ... of which the case fails already: {len(failing)} {failing}")

# a trace clause about an audit action that no baseline run produced: its scope is empty
empty = Clause(
    "r5",
    "trace",
    data={
        "scope": {"tools": ["publish_refused"]},
        "stream": "audit",
        "rule": "always",
        "event": {"action": ["publish_refused"]},
        "where": "event.rule_id == 'NO-SUCH-RULE'",
    },
)
res = traces.check(empty, ctx)
print(
    f"\nclause over an action no baseline run has: status={res.status} rung={res.rung} summary={res.summary!r} "
    f"| {res.details[0]}"
)

# default text encoding of the files the layer writes without naming one
print(f"\npreferred encoding for Path.write_text here: {locale.getpreferredencoding(False)}")
try:
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "x.yaml").write_text("intent: age ≤ 30 days\n")
    print("  a draft with a non-Latin-1 character writes fine")
except UnicodeEncodeError as exc:
    print(f"  a draft with a non-Latin-1 character fails to write: {exc}")
sut.unload()
