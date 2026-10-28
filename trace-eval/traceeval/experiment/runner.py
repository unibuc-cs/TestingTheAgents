"""Record phase of the record-then-replay protocol.

baseline : run the full suite K times on the unmodified SUT with code-coverage contexts
           -> history/baseline.jsonl (observed deps, cost, flakiness)
mutants  : for each mutation, materialise the variant, extract its change set, run the full
           suite K times -> history/variants/<id>.jsonl (ground-truth fault matrix)
"""

import sys
import time
from pathlib import Path

from traceeval.catalog import load_catalog
from traceeval.mutation import MUTATIONS, get_mutation, materialize_variant
from traceeval.tracing.codecov import CoverageSession

from .executor import attach_code_functions, run_case, write_jsonl
from .sutloader import load_sut


def _log(msg: str):
    print(msg, file=sys.stderr, flush=True)


def run_suite(
    sut,
    cases,
    *,
    reps: int,
    variant: str,
    backend: str,
    config_overrides: dict | None,
    with_coverage: bool,
    seed: int,
    llm_settings=None,
    only: set[str] | None = None,
) -> list[dict]:
    records: list[dict] = []
    cov = CoverageSession(sut.path) if with_coverage else None
    for rep in range(reps):
        for case in cases:
            if only is not None and case.id not in only:
                continue
            if cov:
                cov.begin(f"{case.id}|{rep}")
            rec = run_case(
                sut,
                case,
                backend=backend,
                rep=rep,
                variant=variant,
                config_overrides=config_overrides,
                seed=seed,
                llm_settings=llm_settings,
            )
            records.append(rec)
    if cov:
        functions = cov.finish()
        for rec in records:
            attach_code_functions(rec, functions.get(f"{rec['test_id']}|{rec['rep']}", set()))
    return records


def record_baseline(
    workdir: Path,
    *,
    reps: int = 3,
    backend: str = "simulated",
    config_overrides: dict | None = None,
    seed: int = 0,
    llm_settings=None,
) -> list[dict]:
    workdir = Path(workdir)
    cases = load_catalog()
    sut_dir, cs = materialize_variant(None, workdir / "variants")
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
        seed=seed,
        llm_settings=llm_settings,
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
    backend: str = "simulated",
    config_overrides: dict | None = None,
    seed: int = 0,
    llm_settings=None,
) -> dict[str, list[dict]]:
    workdir = Path(workdir)
    cases = load_catalog()
    mutations = [get_mutation(m) for m in mutation_ids] if mutation_ids else list(MUTATIONS)
    out: dict[str, list[dict]] = {}
    for m in mutations:
        t0 = time.time()
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
            seed=seed,
            llm_settings=llm_settings,
        )
        write_jsonl(workdir / "history" / "variants" / f"{m.id}.jsonl", records)
        failing = sorted({r["test_id"] for r in records if not r["passed"]})
        _log(
            f"[{m.id}] {len(records)} runs, failing tests: {len(failing)} "
            f"({'regression' if m.expected_regression else 'benign'}) in {time.time() - t0:.1f}s "
            f"components={sorted(cs.ids())}"
        )
        sut.unload()
        out[m.id] = records
    return out
