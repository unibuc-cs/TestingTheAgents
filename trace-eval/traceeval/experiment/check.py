"""Check one change live, as a developer would before merging it: the prototype of the proposed method.

The adaptive method (``selection/adaptive_bayes.py``) picks the tests one at a time. Each runs at once on the
changed app with the real model, and its outcome decides what runs next. The check stops when the method is sure
either way or the budget is spent, and prints a verdict with the method's probability that something broke.

What the method knows beforehand comes from a recorded experiment (``--history``): each test's cost and the code
it exercises on the original app, and how earlier changes of each kind showed up in the tests. Record it with the
same model and the same version of the app (``traceeval experiment``), since code is matched by line number.
"""

import random
import tempfile
from pathlib import Path

from traceeval.catalog import load_catalog
from traceeval.mutation import compute_changeset, get_mutation, materialize_variant
from traceeval.selection import SelectionContext, get_strategy
from traceeval.sut import SUT_ROOT

from .executor import run_case
from .history import History
from .sutloader import load_sut


def check(change: str, history_dir: Path, budget: float, backend: str):
    """Check ``change``, a mutation id or the folder of a changed copy of ``traceeval/sut``, spending at most
    ``budget`` (a fraction of the full suite's tokens). Prints each test as it runs, then the verdict; returns
    the execution log."""
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

        def oracle(test_id: str) -> tuple[bool, float]:
            """Run the test now, on the changed app, with the real model."""
            rec = run_case(sut, catalog[test_id], backend=backend, variant=cs.variant)
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
    spent = f"{len(log.steps)} runs, {log.cost:,.0f} tokens ({log.cost / history.total_cost():.0%} of the suite)"
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
    return log
