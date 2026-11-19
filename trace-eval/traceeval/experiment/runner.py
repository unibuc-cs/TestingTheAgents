"""Record phase of the record-then-replay protocol.

baseline : run the full suite K times on the unmodified SUT with code-coverage contexts
           -> history/baseline.jsonl (observed deps, cost, pass rate), history/cassette.jsonl (its answers)
mutants  : the empty change first: the same app, run the way the changed copies are
           -> history/unchanged.jsonl (what the way of running alone does to the outcomes)
           then, for each mutation, materialise the variant, extract its change set, run the full suite K times
           -> history/variants/<id>.jsonl (ground-truth fault matrix)

With a served model (``workers`` > 1) the cases of a run go to the server in parallel threads; the baseline
stays sequential, because its coverage contexts are process-wide. The two ways of running are therefore not the
same, which is why the empty change is recorded: it is the original app under the changed copies' conditions.

Every recording says what it was made from and with in ``history/manifest.json`` (``manifest.py``), and its
changed copies are made from its own copy of the original app (``variants/baseline/sut``), not from
``traceeval/sut`` as it is when they are recorded.

A changed copy can also be recorded for the tests the change reaches only (``reached_only``): the copy is replayed
first, and the tests that replay to the end are not run.
"""

import shutil
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from pathlib import Path

from traceeval.catalog import load_catalog
from traceeval.llm.cache import Compare, Tee
from traceeval.llm.chat import shared_client
from traceeval.mutation import MUTATIONS, get_mutation, materialize_variant
from traceeval.tracing.codecov import CoverageSession

from .executor import attach_code_functions, default_backend, run_case, write_jsonl
from .history import UNCHANGED
from .manifest import baseline_copy, load_manifest, selection_digest, write_manifest
from .replay_first import Replays, add_replay, cassette_path, cassette_replay, in_front, recording_engine
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
    compare: Compare | None = None,
) -> list[dict]:
    """Run every case ``reps`` times on ``sut``; with coverage, attach the code each run executed. ``compare`` is
    the client that stands in front of the model for these runs, if one does (``record_mutants``): each record
    then says how the run's requests compare with the answers of the original app (``cassette``)."""
    backend = backend or default_backend()
    cov = CoverageSession(sut.path) if with_coverage else None
    # every case once per repetition: all of rep 0, then all of rep 1, ...
    jobs = [(rep, case) for rep in range(reps) for case in cases]

    def one(job):  # one case once; with coverage, inside its own coverage context
        rep, case = job
        if cov:
            cov.begin(f"{case.id}|{rep}")
        if compare:
            compare.begin()  # this thread's counts start over: a run is made by one thread from end to end
        rec = run_case(sut, case, backend=backend, rep=rep, variant=variant, config_overrides=config_overrides)
        if compare:
            rec["cassette"] = compare.counts()
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
    recording every strategy reads (observed dependencies, costs, pass rates). Every answer the model gives on the
    way is kept as the recording's cassette, history/cassette.jsonl, which replay-first testing answers from
    (``replay_first.py``). The manifest of the recording is started here (``manifest.py``)."""
    workdir = Path(workdir)
    backend = backend or default_backend()
    cases = load_catalog()
    # an unchanged copy under variants/baseline, loaded the same way as every changed copy; its change set is empty
    sut_dir, _ = materialize_variant(None, workdir / "variants")
    sut = load_sut(sut_dir)
    # ``answers``: how the cassette tells two answers to one request apart (``Tee``), for the report's count of them
    how = dict(backend=backend, reps=reps, workers=1, config=config_overrides or {}, answers="by what they say")
    write_manifest(workdir, "baseline", **how)
    t0 = time.time()
    # the tee stands in front of the model for the agents and the judge, and keeps what each request was answered
    with in_front(backend, Tee(shared_client(backend), canonical_ids=(backend == "llm"))) as tee:
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
    tee.write(cassette_path(workdir))
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
    reached_only: bool = False,
    resume: bool = False,
) -> dict[str, list[dict]]:
    """The empty change, then each mutation of the catalog; or only those ``mutation_ids`` name ("unchanged" is the
    empty change). ``resume`` leaves out the changes that already have recorded runs, after a recording that was
    stopped. For a mutation: a changed copy, its change set, and the whole suite ``reps`` times on it, into
    history/variants/<id>.jsonl, the ground truth of that change. For the empty change: the suite on the
    recording's copy of the original app, into history/unchanged.jsonl.

    With ``reached_only`` a changed copy is replayed against the recording's cassette first, without a model, and
    only the tests that diverge there are run. The others send the model nothing the original app did not send,
    so the replay gives their outcome on the copy: each gets one record, its replayed run, marked ``stand_in``.
    A change is then recorded for the tokens of the tests it reaches, which is what makes several hundred
    generated changes affordable; the copy itself is not kept."""
    workdir = Path(workdir)
    backend = backend or default_backend()
    if reached_only and config_overrides:
        raise SystemExit("--reached-only replays with the app's own settings: it cannot be combined with --set")
    cases = load_catalog()
    # The recording's own copy of the original app. Every changed copy is made from it and compared with it, so
    # that its change set (the line numbers above all) fits the baseline's runs whatever traceeval/sut is today;
    # an anchor the copy no longer has stops the recording.
    original = baseline_copy(workdir)
    if not original.exists():
        raise SystemExit(f"{workdir} has no baseline to change: run traceeval baseline --workdir {workdir} first")
    # In front of the model for all of these runs: each answer is compared with the one the original app got for
    # the same request, and each record gets the counts (``Compare``). A recording without a cassette has nothing
    # to compare with.
    cassette = cassette_path(workdir)
    compare = Compare(shared_client(backend), cassette, canonical_ids=(backend == "llm")) if cassette.exists() else None
    how = dict(backend=backend, reps=reps, workers=workers, config=config_overrides or {}, reached_only=reached_only)
    # With a digest of the strategies' code: evidence, later, that no constant was set on these runs. A recording
    # taken up again (``resume``) keeps the digest of its first call: the code as it was before any of its changes
    # had been recorded.
    first = load_manifest(workdir).get("changes", {}).get("selection") if resume else None
    write_manifest(workdir, "changes", **how, selection=first or selection_digest())
    engine = recording_engine(workdir)  # whose requests the cassette is keyed by: what a replay runs as

    if reached_only and "baseline" not in (Replays.load(workdir) or Replays([])).rows:
        # the replay of the original app: what "a test that passes there and fails here" is read against
        baseline = load_sut(original)
        add_replay(workdir, cassette_replay(baseline, cases, workdir, engine, "baseline"))
        baseline.unload()
    out: dict[str, list[dict]] = {}
    with in_front(backend, compare) if compare else nullcontext():
        for mid in mutation_ids or [UNCHANGED, *(m.id for m in MUTATIONS)]:
            if resume and (workdir / "history" / "variants" / f"{mid}.jsonl").exists():
                continue  # recorded by an earlier call that was stopped
            t0 = time.time()
            lean = reached_only and mid != UNCHANGED  # the empty change is always run whole
            # A copy recorded whole is kept under variants/<id>. One recorded for the tests it reaches only is made
            # in a temporary folder and thrown away after its runs: several hundred copies are not kept.
            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
                if mid == UNCHANGED:
                    # the empty change: nothing to copy or to diff, the original app as the recording has it
                    sut_dir, path, label = original, workdir / "history" / f"{UNCHANGED}.jsonl", "no change"
                else:
                    # the changed copy, what its diff touched (changeset.json) and its label (mutation.json; a
                    # generated change has none)
                    m = get_mutation(mid)
                    home = Path(tmp) if lean else workdir / "variants"
                    sut_dir, cs = materialize_variant(m, home, baseline=original)
                    if lean:  # what History reads of a copy stays in the recording, without the copy itself
                        (workdir / "variants" / mid).mkdir(parents=True, exist_ok=True)
                        for name in ("changeset.json", "mutation.json", "diff.patch"):
                            shutil.copy(home / mid / name, workdir / "variants" / mid / name)
                    path = workdir / "history" / "variants" / f"{mid}.jsonl"
                    expected = {True: "regression", False: "benign", None: "no label"}[m.expected_regression]
                    label = f"{expected}, components={sorted(cs.ids())}"
                sut = load_sut(sut_dir)
                suite, stand_ins = cases, []
                if lean:
                    # Replay first. A test that replays to the end is not run: its replayed run is its record on
                    # this copy, marked as a stand-in. Only the tests that diverge go to the model.
                    replay = cassette_replay(sut, cases, workdir, engine, mid)
                    add_replay(workdir, replay)
                    stand_ins = [
                        {**row, "stand_in": True, "rep": 0, "backend": engine} for row in replay if row["replayed"]
                    ]
                    suite = [case for case in cases if case.id not in {row["test_id"] for row in stand_ins}]
                    label += f"; {len(suite)} of {len(cases)} tests diverge and are run"
                records = run_suite(
                    sut,
                    suite,
                    reps=reps,
                    variant=mid,
                    backend=backend,
                    config_overrides=config_overrides,
                    with_coverage=False,
                    workers=workers,
                    compare=compare,
                )
                # A server that went away breaks every run after it. Stop here, before this copy is written: the
                # copies recorded so far stand, and ``resume`` records the rest once the server is back.
                broken = sum(r["classification"] == "INFRA_INVALID" for r in records)
                if broken > len(records) / 2:
                    raise SystemExit(f"stopped at {mid}: the environment broke {broken} of its {len(records)} runs")
                write_jsonl(path, [*records, *stand_ins])
                # for the log only: the revealing tests are derived later, by History, against the baseline's pass
                # rates
                failing = sorted({r["test_id"] for r in [*records, *stand_ins] if not r["passed"]})
                known = sum(r.get("cassette", {}).get("known", 0) for r in records)
                differ = sum(r.get("cassette", {}).get("differ", 0) for r in records)
                _log(
                    f"[{mid}] {len(records)} runs, failing tests: {len(failing)} ({label}) in {time.time() - t0:.1f}s; "
                    f"of {known} requests the original app made too, {differ} answered otherwise"
                )
                sut.unload()
                out[mid] = records
    return out
