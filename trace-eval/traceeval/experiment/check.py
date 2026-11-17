"""Check one change live, as a developer would before merging it: the prototype.

The check has two phases.

1. Replay (``replay_first.py``): every test runs on the changed app with the model's calls answered from the
   answers recorded on the original app. A test that replays to the end has its outcome for no tokens; if one of
   those fails that passes on the original app, the change is a regression and the check ends there. The other
   tests diverge: they send the model something the original app never sent.
2. The adaptive method (``selection/adaptive_bayes.py``) picks among the diverged tests, one at a time. Each runs
   at once with the real model, behind the same recorded answers, so only the requests from its divergence on are
   paid for, and its outcome decides what runs next. The check stops at the first failure, when every diverged
   test has passed, when the method is confident nothing broke, or when the budget is spent. One failing run of
   a long test can be the minority of its runs, so a failure can first be confirmed (``confirm``): the test is
   run again, and a third time when the second run passes; two failures of three count.

"Confident" is a threshold on the method's probability that something broke. By default it is the method's
constant. With a target miss rate (``miss_rate``) it is set on the history's own changes, per group of changes, so
that a regression is called clean at most that often (``stopping.py``); the method then learns from the half of
the recorded changes the threshold was not set on, and goes on through every test the change reaches unless the
threshold stops it.

What is known beforehand comes from a recorded experiment (``--history``): the answers of the original app (its
cassette), each test's cost and the code it exercises there, and how earlier changes of each kind showed up in the
tests. Record it with the same model and the same version of the app (``traceeval experiment``), since code is
matched by line number and answers by the exact request: the check refuses a history whose copy of the app is not
``traceeval/sut`` as it is now (``manifest.py::drift``).

After the verdict it prints the change coverage (``coverage.change_coverage``) of the tests whose outcome is now
known, replayed or run: the share of the changed components they exercised, the share of the properties the change
may affect that they checked, and the affected properties left unchecked.
"""

import random
import tempfile
import time
from pathlib import Path

from traceeval.catalog import load_catalog, load_properties
from traceeval.llm.chat import new_client
from traceeval.mutation import compute_changeset, get_mutation, materialize_variant
from traceeval.selection import SelectionContext, get_strategy
from traceeval.selection.adaptive_bayes import AdaptiveBayes
from traceeval.selection.base import ExecutionLog
from traceeval.sut import SUT_ROOT

from .coverage import (
    _components,
    affected_error_paths,
    affected_features,
    affected_properties,
    affected_workflows,
    change_coverage,
    features,
    invoked,
    tools_called,
)
from .executor import run_case
from .history import History
from .manifest import drift
from .replay_first import cassette_client, cassette_path, in_front, recording_engine, replay_suite, write_cassette
from .stopping import clean_threshold
from .sutloader import load_sut


def check(
    change: str,
    history_dir: Path,
    budget: float,
    backend: str,
    confirm: bool = False,
    miss_rate: float | None = None,
):
    """Check ``change``, a mutation id or the folder of a changed copy of ``traceeval/sut``, spending at most
    ``budget`` (a fraction of the full suite's tokens) on the model. Prints the replay's result and each test as
    it runs, then the verdict and the change coverage; returns the execution log. With ``confirm`` a test that
    fails is run again before its failure ends the check. With ``miss_rate`` the clean verdict's threshold is set
    on the history's changes, for that miss rate at most."""
    # The change is compared with traceeval/sut as it is now, and what is known beforehand was recorded on the app
    # as it was. If the two differ, even by a comment, the recorded line numbers and answers no longer fit: refuse.
    if "app" in (differs := drift(history_dir)):
        raise SystemExit(f"{differs['app']}. Record the history again: traceeval experiment --workdir <new folder>")
    history = History.load(history_dir)
    catalog = {c.id: c for c in load_catalog()}
    cases = [catalog[t] for t in history.test_ids() if t in catalog]
    passes = {c.id: history.baseline_pass_rate(c.id) >= 0.5 for c in cases}
    # The answers of the original app. A Gemma recording made before cassettes were kept gets one now, from the
    # recorded answers at hand; without a cassette every test diverges, and the check runs as it would without replay.
    if not cassette_path(history_dir).exists() and recording_engine(history_dir) == "replay":
        write_cassette(history_dir, history.test_ids())
    client = cassette_client(history_dir, backend)
    # A mutation is applied to a fresh copy of the app in a temporary folder, removed at the end.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        members = []  # for a batch, the catalog changes it bundles: the method does not learn from them
        if Path(change).is_dir():
            sut_dir = Path(change)
            cs = compute_changeset(SUT_ROOT, sut_dir, name=sut_dir.name)
        else:
            mutation = get_mutation(change)
            members = mutation.members
            sut_dir, cs = materialize_variant(mutation, Path(tmp))
        sut = load_sut(sut_dir)
        print(f"{cs.variant}: changed {', '.join(sorted(cs.ids())) or 'nothing but comments or formatting'}")

        # ---- phase 1, the replay: no model, a few seconds
        started = time.perf_counter()
        with in_front(backend, client, judge_too=True):
            replay = {r["test_id"]: r for r in replay_suite(sut, cases, client, backend, cs.variant)}
        replayed = frozenset(t for t, r in replay.items() if r["replayed"])
        diverged = [t for t in replay if t not in replayed]
        print(
            f"replay: {len(replayed)} of {len(replay)} tests replay to the end, for no tokens, in "
            f"{time.perf_counter() - started:.0f} s; {len(diverged)} diverge and need the model"
        )
        # a replayed test that passes on the original app and fails here: a regression, before any model call
        # (in the order of the suite: a set's own order differs from one process to the next)
        found = [t for t in replay if t in replayed and passes[t] and not replay[t]["passed"]]
        for t in found:
            print(f"  {t:22s} FAIL {','.join(replay[t]['failed_checks']):40s} replayed, no tokens", flush=True)

        # ---- phase 2, the diverged tests, live: the recorded answers stay in front of the model
        seconds = [0.0]  # wall time of the tests run so far

        def run_once(test_id: str, again: bool = False) -> tuple[bool, float]:
            """Run the test now, on the changed app, with the real model behind the recorded answers. A run the
            environment broke (the model server did not answer) is tried once more; if it breaks again, the check
            stops rather than read the failure as the change's. The cost is the tokens the model was asked for."""
            for _ in range(2):
                client.begin()
                rec = run_case(sut, catalog[test_id], backend=backend, variant=cs.variant)
                seconds[0] += rec["latency_ms"] / 1000
                if rec["classification"] != "INFRA_INVALID":
                    break
            else:
                cause = (rec["error"] or "").strip().splitlines()[-1]
                raise SystemExit(f"stopped: the model did not answer while {test_id} ran ({cause}); no verdict")
            spent = max(0.0, float(rec["tokens"] - client.served_tokens))  # without what the cassette answered
            outcome = "pass" if rec["passed"] else f"FAIL {','.join(rec['failed_checks']) or rec['classification']}"
            whole = f" ({rec['tokens']:,} with its replayed part)" if client.served_tokens else ""
            label = f"{test_id} (again)" if again else test_id
            print(f"  {label:22s} {outcome:40s} {spent:>7,.0f} tokens{whole}", flush=True)
            return rec["passed"], spent

        def oracle(test_id: str) -> tuple[bool, float]:
            """What the method is told about a test: the outcome of one run. With ``confirm`` a failure is not
            taken at its word: the test is run again, and a third time when the second run passes. Two failures
            of three are a failure; one that does not repeat counts as a pass. Every run made is paid for."""
            passed, spent = run_once(test_id)
            if passed or not confirm:
                return passed, spent
            passed, more = run_once(test_id, again=True)
            spent += more
            if passed:  # one failure and one pass: a third run decides
                passed, more = run_once(test_id, again=True)
                spent += more
            return passed, spent

        if found:
            log = ExecutionLog("replay", steps=[(t, False, 0.0) for t in found], stop_reason="regression")
        elif not diverged:
            log = ExecutionLog("replay", stop_reason="exhausted")
        else:
            # never learn from the change itself, nor from the members of a batch
            learn = history.training_variants(cs.variant, members)
            # The method reasons about the components of the change set. A change that reaches the model without
            # leaving one (a re-wrapped prompt, say) gives it nothing to reason about: the diverged tests then run
            # cheapest first.
            method = get_strategy("adaptive_bayes" if cs.components else "cheapest")
            if not cs.components:
                print("the change set is empty, yet tests diverge: they run cheapest first")
            elif miss_rate is not None:
                # The clean threshold set on the recorded changes instead of the method's constant. The method
                # then learns from the half of them the threshold was not set on, and runs every reached test
                # unless the threshold stops it.
                tau, learn, basis = clean_threshold(history_dir, history, catalog, cs, miss_rate, learn)
                print(basis)
                method = AdaptiveBayes(eps_clean=tau, exhaustive=True)
            ctx = SelectionContext(
                change=cs,
                catalog=catalog,
                history=history,
                budget=budget * history.total_cost(),
                rng=random.Random(0),
                train_variants=learn,
                replayed=replayed,
                prefix={t: float(replay[t]["tokens"]) for t in diverged},
            )
            client.live = new_client(backend)
            with in_front(backend, client):
                log = method.run(ctx, oracle)
        sut.unload()

    failed = sorted({t for t, ok, _ in log.steps if not ok})
    # the diverged tests that could still tell something: they pass on the original app and were not run
    unrun = len([t for t in diverged if passes[t] and t not in log.executed])
    left = f" ({unrun} tests the change reaches were not run)" if unrun else ""
    if found:
        verdict = f"REGRESSION: {', '.join(failed)} failed in the replay, before any model call"
    elif not diverged:
        verdict = "no regression: no test sends the model anything new, and none that passes on the original app fails"
    elif log.stop_reason == "regression":
        verdict = f"REGRESSION: {', '.join(failed)} failed"
    elif log.stop_reason == "exhausted":
        verdict = "no regression: every test the change reaches ran and passed"
    elif log.stop_reason == "clean" and miss_rate is not None:
        verdict = f"no regression: stopped at a miss rate of at most {miss_rate:.0%}{left}"
    elif log.stop_reason == "clean":
        verdict = f"no regression: the method is confident nothing broke{left}"
    else:
        verdict = f"no failure within the budget{left}"
    live = len(log.steps) if not found else 0  # the failures the replay found were not run
    share = log.cost / history.total_cost()
    spent = (
        f"{live} tests run with the model, {log.cost:,.0f} tokens ({share:.0%} of the suite), "
        f"{seconds[0]:.0f} s (the whole suite takes about {history.total_seconds():.0f} s, one test at a time)"
    )
    p = f"; P(something broke) = {log.p_broken:.2f}" if log.p_broken is not None else ""
    print(f"{verdict}\n{spent}{p}")
    # The components the posterior holds responsible: for a batch of changes, which of them the failure points at.
    blamed = [f"{c} {pc:.2f}" for c, pc in (getattr(log, "blame", None) or []) if pc >= 0.2]
    if blamed:
        print("blamed: " + ", ".join(blamed[:6]))
    # the tests whose outcome on the changed app is now known: those run, and those that replayed and pass on the
    # original app (one that fails there checks nothing)
    known = log.executed + sorted(t for t in replayed if passes[t] and t not in log.executed)
    _print_coverage(cs, known, history, catalog)
    return log


def _print_coverage(cs, executed, history, catalog):
    """The change coverage of ``executed``, the tests whose outcome on the changed app is known, and what of the
    change they left out: the affected properties none of them checks, the affected workflows and features none of
    them ran, and the refusals in the changed code none of them reached."""
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
    feats, paths = affected_features(cs), affected_error_paths(cs)
    if cov["affected_feature_coverage"] is not None:
        parts.append(f"{cov['affected_feature_coverage']:.0%} of the {len(feats)} affected features reached")
    if cov["error_path_coverage"] is not None:
        parts.append(f"{cov['error_path_coverage']:.0%} of the {len(paths)} refusals in the changed code reached")
    if parts:
        print("coverage: " + ", ".join(parts))
    # what the executed tests invoked on the original app, out of what the application has
    deps = set().union(*(invoked(history, t) for t in executed)) if executed else set()
    counts = [
        f"{sum(f'{dim}:{n}' in deps for n in names)} of {len(names)} {dim}s"
        for dim, names in _components(SUT_ROOT).items()
        if dim != "config"
    ]
    reached_features = sum(bool(f.tool_ids() & deps) for f in features().values())
    print(f"invoked: {', '.join(counts)}, {reached_features} of {len(features())} features")
    checked = {p for t in executed for p in catalog[t].properties}
    missing = [p + (" (mandatory)" if props[p].mandatory else "") for p in sorted(affected - checked)]
    if missing:
        print("not checked: " + ", ".join(missing))
    ran = {catalog[t].workflow for t in executed if catalog[t].workflow}
    if workflows - ran:
        print("workflows not run: " + ", ".join(sorted(workflows - ran)))
    called = tools_called(history, executed)
    unreached = sorted(features()[f].name for f in feats if not features()[f].tool_ids() & called)
    if unreached:
        print("features not reached: " + "; ".join(unreached))
    deps = set().union(*(history.deps(t) for t in executed)) if executed else set()
    missed = [str(p) for p in paths if not p.reached(deps)]
    if missed:
        print("refusals in the changed code not reached: " + "; ".join(missed))
