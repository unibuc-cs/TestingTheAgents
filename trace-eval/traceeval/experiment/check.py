"""Check one change live, as a developer would before merging it: the prototype of the proposed method.

The adaptive method (``selection/adaptive_bayes.py``) picks the tests one at a time. Each runs at once on the
changed app with the real model, and its outcome decides what runs next. The check stops when the method is sure
either way or the budget is spent, and prints a verdict with the method's probability that something broke.

What the method knows beforehand comes from a recorded experiment (``--history``): each test's cost and the code
it exercises on the original app, and how earlier changes of each kind showed up in the tests. Record it with the
same model and the same version of the app (``traceeval experiment``), since code is matched by line number.

After the verdict it prints the change coverage (``coverage.change_coverage``): the share of the changed components
the tests exercised, the share of the properties the change may affect that they checked, and the affected
properties left unchecked. A check that found no regression has tested every affected mandatory property the
budget allowed (the method's step 5).
"""

import random
import tempfile
from pathlib import Path

from traceeval.catalog import load_catalog, load_properties
from traceeval.mutation import compute_changeset, get_mutation, materialize_variant
from traceeval.selection import SelectionContext, get_strategy
from traceeval.sut import SUT_ROOT

from .coverage import affected_properties, affected_workflows, change_coverage
from .executor import run_case
from .history import History
from .sutloader import load_sut


def check(change: str, history_dir: Path, budget: float, backend: str):
    """Check ``change``, a mutation id or the folder of a changed copy of ``traceeval/sut``, spending at most
    ``budget`` (a fraction of the full suite's tokens). Prints each test as it runs, then the verdict and the
    change coverage; returns the execution log."""
    history = History.load(history_dir)
    catalog = {c.id: c for c in load_catalog()}
    # A mutation is applied to a fresh copy of the app in a temporary folder, removed at the end.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        if Path(change).is_dir():
            sut_dir = Path(change)
            cs = compute_changeset(SUT_ROOT, sut_dir, name=sut_dir.name)
        else:
            sut_dir, cs = materialize_variant(get_mutation(change), Path(tmp))
        sut = load_sut(sut_dir)
        seconds = [0.0]  # wall time of the tests run so far

        def oracle(test_id: str) -> tuple[bool, float]:
            """Run the test now, on the changed app, with the real model. A run the environment broke (the model
            server did not answer) is tried once more; if it breaks again, the check stops rather than read the
            failure as the change's."""
            for _ in range(2):
                rec = run_case(sut, catalog[test_id], backend=backend, variant=cs.variant)
                seconds[0] += rec["latency_ms"] / 1000
                if rec["classification"] != "INFRA_INVALID":
                    break
            else:
                cause = (rec["error"] or "").strip().splitlines()[-1]
                raise SystemExit(f"stopped: the model did not answer while {test_id} ran ({cause}); no verdict")
            outcome = "pass" if rec["passed"] else f"FAIL {','.join(rec['failed_checks']) or rec['classification']}"
            print(f"  {test_id:22s} {outcome:40s} {rec['tokens']:>7,} tokens", flush=True)
            return rec["passed"], float(rec["tokens"])

        print(f"{cs.variant}: changed {', '.join(sorted(cs.ids())) or 'nothing but comments or formatting'}")
        ctx = SelectionContext(
            change=cs,
            catalog=catalog,
            history=history,
            budget=budget * history.total_cost(),
            rng=random.Random(0),
            train_variants=[v for v in history.variants if v != cs.variant],  # never learn from the change itself
        )
        log = get_strategy("adaptive_bayes").run(ctx, oracle)
        sut.unload()

    failed = sorted({t for t, ok, _ in log.steps if not ok})
    spent = (
        f"{len(log.steps)} runs, {log.cost:,.0f} tokens ({log.cost / history.total_cost():.0%} of the suite), "
        f"{seconds[0]:.0f} s (the whole suite takes about {history.total_seconds():.0f} s, one test at a time)"
    )
    if log.stop_reason == "no_components":
        verdict = "nothing to test: the change touches no code"
    elif log.stop_reason == "regression":
        verdict = f"REGRESSION: {', '.join(failed)} failed"
    elif log.stop_reason == "clean":
        verdict = "no regression: the method is confident nothing broke"
    elif failed:  # only tests the model fails on the original app too, which says nothing about the change
        verdict = f"no regression found within the budget ({', '.join(failed)} fail on the original app too)"
    else:
        verdict = "no failure within the budget"
    p = f"; P(something broke) = {log.p_broken:.2f}" if log.p_broken is not None else ""
    print(f"{verdict}\n{spent}{p}")
    _print_coverage(cs, log.executed, history, catalog)
    return log


def _print_coverage(cs, executed, history, catalog):
    """The change coverage of the executed tests, the affected properties no executed test checks, and the
    affected workflows no executed test ran."""
    props = load_properties()
    affected = affected_properties(cs, history, catalog, props)
    workflows = affected_workflows(cs, history, catalog)
    cov = change_coverage(cs, executed, history, catalog, props, affected, workflows)
    parts = []
    if cov["component_coverage"] is not None:
        parts.append(f"{cov['component_coverage']:.0%} of the changed components exercised")
    if cov["affected_property_coverage"] is not None:
        parts.append(f"{cov['affected_property_coverage']:.0%} of the {len(affected)} affected properties checked")
    if cov["affected_workflow_coverage"] is not None:
        parts.append(f"{cov['affected_workflow_coverage']:.0%} of the {len(workflows)} affected workflows run")
    if parts:
        print("coverage: " + ", ".join(parts))
    checked = {p for t in executed for p in catalog[t].properties}
    missing = [p + (" (mandatory)" if props[p].mandatory else "") for p in sorted(affected - checked)]
    if missing:
        print("not checked: " + ", ".join(missing))
    ran = {catalog[t].workflow for t in executed if catalog[t].workflow}
    if workflows - ran:
        print("workflows not run: " + ", ".join(sorted(workflows - ran)))
