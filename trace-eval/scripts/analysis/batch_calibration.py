"""Batches of changes: what the adaptive method's result owes to calibrating on the batch's own members, and which
member it blames when they are held out.

A batch must not be checked by a model that has seen what each of its members breaks, so the evaluator and
``traceeval check`` hold out a batch's members and the batches that share one (``History.training_variants``).
This script shows what that rule changes, by replaying the batches three ways:
    held out      the evaluator's rule
    singles       every single change, the batch's members included
    all others    every other variant, the other batches included
and then, under the evaluator's rule, whether the component the method blames most belongs to a member that is a
regression on its own.

    python scripts/analysis/batch_calibration.py [recording ...]   # default runs/gemma7_sweep runs/gemma7_batches
"""

import json
import sys
from pathlib import Path

import pandas as pd
from replaylib import CachedAB, load, replay

pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 200)

for workdir in sys.argv[1:] or ["runs/gemma7_sweep", "runs/gemma7_batches"]:
    h, cat = load(workdir)
    variants = sorted(h.variants)
    members = {}
    for v in variants:
        meta = json.loads((Path(workdir) / "variants" / v / "mutation.json").read_text(encoding="utf-8"))
        if meta.get("members"):
            members[v] = meta["members"]
    batches = sorted(members)
    singles = [v for v in variants if v not in members]
    print(f"{workdir}: {len(batches)} batches, {len(singles)} single changes")
    modes = {
        "held out": h.training_variants,
        "singles": lambda v, singles=singles: list(singles),
        "all others": lambda v, variants=variants: [x for x in variants if x != v],
    }
    runs = []
    for label, train_of in modes.items():
        d = replay(h, cat, CachedAB(), batches, train_of, budgets=(0.05, 0.2))
        d["mode"] = label
        runs.append(d)
    table = pd.concat(runs)
    revealed = table[table.is_regression]
    print("\nbatches a test reveals: detection, tests run, tokens (share of the suite)")
    print(
        revealed.groupby(["budget", "mode"])
        .agg(
            batches=("variant", "nunique"),
            detect=("detected", "mean"),
            tests=("tests_run", "mean"),
            cost=("cost_fraction", "mean"),
            max_cost=("cost_fraction", "max"),
        )
        .round(3)
        .to_string()
    )
    print("\nper batch at a 20% budget: share of the five seeds that detect it, and tests run")
    per_batch = table[table.budget == 0.2].pivot_table(
        index=["variant", "is_regression", "n_revealing"], columns="mode", values=["detected", "tests_run"]
    )
    print(per_batch.round(2).to_string())
    print("\nstop reasons at a 20% budget")
    stops = table[table.budget == 0.2].groupby(["mode", "is_regression"]).stop_reason.value_counts()
    print(stops.unstack(fill_value=0).to_string(), flush=True)

    # The blame, members held out, at a 20% budget: for every run that ended at a failure, the component the
    # method then holds most likely broken, the member whose change set has it, and whether that member is a
    # regression on its own (a test reveals it in its own recording) and is revealed by the test that failed.
    found = table[(table["mode"] == "held out") & (table.budget == 0.2) & (table.stop_reason == "regression")]
    rows = []
    for (batch, test, component), runs_of in found.groupby(["variant", "failed_test", "top_blamed"]):
        owners = [m for m in members[batch] if any(c.id == component for c in h.changesets[m].components)]
        rows.append(
            {
                "batch": batch,
                "seeds": len(runs_of),
                "failed test": test,
                "blamed most": component,
                "its member": ", ".join(owners),
                "a regression alone": any(h.revealing_tests(m) for m in owners),
                "revealed by that test": any(test in h.revealing_tests(m) for m in owners),
            }
        )
    blame = pd.DataFrame(rows)
    print("\nthe blame at a 20% budget, members held out (one line per batch, failed test and blamed component)")
    print(blame.to_string(index=False))
    if len(blame):
        runs_found = blame.seeds.sum()
        alone = blame[blame["a regression alone"]].seeds.sum()
        same = blame[blame["revealed by that test"]].seeds.sum()
        print(
            f"\n{runs_found} runs ended at a failure: in {alone} the component blamed most belongs to a member that "
            f"is a regression alone, in {same} the failed test reveals that member alone",
            flush=True,
        )
    print()
