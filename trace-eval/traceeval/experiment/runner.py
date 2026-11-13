"""Record phase of the record-then-replay protocol.

baseline : run the full suite K times on the unmodified SUT with code-coverage contexts
           -> history/baseline.jsonl (observed deps, cost, pass rate)
mutants  : for each mutation, materialise the variant, extract its change set, run the full
           suite K times -> history/variants/<id>.jsonl (ground-truth fault matrix)

With a served model (``workers`` > 1) the cases of a run go to the server in parallel threads; the baseline
stays sequential, because its coverage contexts are process-wide.
"""

import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from traceeval.catalog import load_catalog
from traceeval.mutation import MUTATIONS, get_mutation, materialize_variant
from traceeval.tracing.codecov import CoverageSession

from .executor import attach_code_functions, default_backend, run_case, write_jsonl
from .sutloader import load_sut


def _log(msg: str):
    """One line of progress on stderr, flushed at once so that it shows during a long run."""
    print(msg, file=sys.stderr, flush=True)


def run_suite(
    sut,
    cases,
    *,
    reps: int,
    variant: str,
    backend: str | None,
    config_overrides: dict | None,
    with_coverage: bool,
    workers: int = 1,
) -> list[dict]:
    """Run every case ``reps`` times on ``sut``; with coverage, attach the code each run executed."""
    backend = backend or default_backend()
    cov = CoverageSession(sut.path) if with_coverage else None
    # every case once per repetition: all of rep 0, then all of rep 1, ...
    jobs = [(rep, case) for rep in range(reps) for case in cases]

    def one(job):  # one case once; with coverage, inside its own coverage context
        rep, case = job
        if cov:
            cov.begin(f"{case.id}|{rep}")
        rec = run_case(sut, case, backend=backend, rep=rep, variant=variant, config_overrides=config_overrides)
        if backend != "replay":  # model runs are slow: report each case as it finishes
            failed = ",".join(rec["failed_checks"])
            _log(
                f"[{variant}] rep {rep} {case.id}: {rec['classification']} "
                f"{rec['latency_ms'] / 1000:.1f}s {rec['tokens']} tok {failed}"
            )
        return rec

    # threads only without coverage: its contexts are process-wide, so concurrent runs would mix up their lines
    if workers > 1 and cov is None:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            records = list(pool.map(one, jobs))  # in job order, whatever order they finish in
    else:
        records = [one(job) for job in jobs]
    # the code and lines each run executed, by its context, join the run's observed dependencies
    if cov:
        functions = cov.finish()
        for rec in records:
            attach_code_functions(rec, functions.get(f"{rec['test_id']}|{rec['rep']}", set()))
    return records


def record_baseline(
    workdir: Path,
    *,
    reps: int = 3,
    backend: str | None = None,
    config_overrides: dict | None = None,
) -> list[dict]:
    """Run the whole suite ``reps`` times on the original app with code coverage: history/baseline.jsonl, the
    recording every strategy reads (observed dependencies, costs, pass rates)."""
    workdir = Path(workdir)
    cases = load_catalog()
    # an unchanged copy under variants/baseline, loaded the same way as every changed copy; its change set is empty
    sut_dir, _ = materialize_variant(None, workdir / "variants")
    sut = load_sut(sut_dir)
    t0 = time.time()
    records = run_suite(
        sut,
        cases,
        reps=reps,
        variant="baseline",
        backend=backend,
        config_overrides=config_overrides,
        with_coverage=True,
    )
    write_jsonl(workdir / "history" / "baseline.jsonl", records)
    passed = sum(r["passed"] for r in records)
    _log(f"[baseline] {len(cases)} cases x {reps} reps: {passed}/{len(records)} passed in {time.time() - t0:.1f}s")
    sut.unload()
    return records


def record_mutants(
    workdir: Path,
    *,
    mutation_ids: list[str] | None = None,
    reps: int = 3,
    backend: str | None = None,
    config_overrides: dict | None = None,
    workers: int = 1,
) -> dict[str, list[dict]]:
    """For each mutation (the whole catalog by default): a changed copy, its change set, and the whole suite ``reps``
    times on it, into history/variants/<id>.jsonl, the ground truth of that change."""
    workdir = Path(workdir)
    cases = load_catalog()
    mutations = [get_mutation(m) for m in mutation_ids] if mutation_ids else list(MUTATIONS)
    out: dict[str, list[dict]] = {}
    for m in mutations:
        t0 = time.time()
        # the changed copy under variants/<id>, what its diff touched (changeset.json) and its label (mutation.json)
        sut_dir, cs = materialize_variant(m, workdir / "variants")
        sut = load_sut(sut_dir)
        records = run_suite(
            sut,
            cases,
            reps=reps,
            variant=m.id,
            backend=backend,
            config_overrides=config_overrides,
            with_coverage=False,
            workers=workers,
        )
        write_jsonl(workdir / "history" / "variants" / f"{m.id}.jsonl", records)
        # for the log only: the revealing tests are derived later, by History, against the baseline's pass rates
        failing = sorted({r["test_id"] for r in records if not r["passed"]})
        _log(
            f"[{m.id}] {len(records)} runs, failing tests: {len(failing)} "
            f"({'regression' if m.expected_regression else 'benign'}) in {time.time() - t0:.1f}s "
            f"components={sorted(cs.ids())}"
        )
        sut.unload()
        out[m.id] = records
    return out
