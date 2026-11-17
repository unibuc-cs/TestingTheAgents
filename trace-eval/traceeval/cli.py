"""Command-line interface.

traceeval catalog                         list eval cases
traceeval mutations [--generated]         list controlled changes, or those generated from the app (no labels)
traceeval run --test PUB-01 [--backend hf|vllm|llm|replay] [--otel trace.json]   run one case, print the record
    hf: Gemma on the local GPU; vllm: Gemma on the GPU server (scripts/gpu_remote.sh up gemma); llm: Qwen on
    the GPU server (scripts/gpu_remote.sh up qwen), or any OpenAI-compatible endpoint (TRACEEVAL_LLM_*);
    replay: Gemma's recorded answers, no model
    (TRACEEVAL_CACHE names the file of recorded answers; with hf or vllm, new answers are added to it)
    TRACEEVAL_JUDGE=gemma|qwen picks the model that judges the cases with a rubric (default: the agents' model)
    --otel also writes the run's trace as OpenTelemetry spans, in OTLP JSON (agents, tools, model calls, skills;
    plan, routing, approvals and consulted agents as span events)
traceeval baseline --workdir runs/gemma7 --reps 5
    the original app with coverage, one case at a time; also its answers (the cassette) and the manifest
traceeval mutants  --workdir runs/gemma7 --reps 5 [--only id ...]
    the empty change ("unchanged": the original app run as the changed copies are), then every changed copy
traceeval mutants  --workdir runs/gemma8_gen --reps 5 --generated [N] --reached-only [--resume]
    the generated changes (all, or N of each kind), each for the tests it reaches only: the copy is replayed
    first, the tests that diverge are run, and the others get the replay's outcome; no copy is kept
traceeval replay-first --workdir runs/gemma7 [--generated [N]]
    every test on every changed copy, answered from the answers recorded on the original app: which tests
    replay to the end (their outcome is known) and which diverge (they need the model); no model is called.
    --generated replays the generated changes instead, none of which needs to be recorded for it
traceeval evaluate --workdir runs/gemma7 --seeds 10 [--held-out]
    the strategies on the recording, and again replay-first; --held-out, for generated changes: learn from one
    fixed half of them and evaluate on the other
traceeval report   --workdir runs/gemma7
traceeval experiment --workdir runs/gemma7   (baseline + mutants + replay-first + evaluate + report)
traceeval check <mutation id | changed copy of traceeval/sut> --history runs/gemma7 [--budget 0.2] [--backend vllm]
    check one change live: replay first, then the proposed method over the tests that diverge; --history is an
    experiment recorded with the same model; prints the verdict and the change coverage
traceeval properties draft [--max 15] [--per-test 5] [--fresh] [--replay a.json] [--save-response a.json]
    a model (Qwen, the llm backend) drafts the catalog of properties from the requirements and tags the tests
traceeval properties apply   write properties.yaml and the tests' tags from the reviewed draft
traceeval sdd --workdir runs/sdd [--specs FS-0101 ...] [--out docs/sdd] [--backend replay]   spec-driven demo
traceeval sdd draft --request request.md --id FS-0106 [--replay answer.json]   draft a spec with an LLM
"""

import argparse
import json
import os
import sys
from pathlib import Path

BACKENDS = ["hf", "vllm", "llm", "replay"]

# Each command imports what it needs when it runs, so that a quick one (catalog, mutations) does not load
# pandas, coverage or the model libraries.


def _parse_overrides(items):
    """The ``--set key=value`` options as a dict. A value that starts like JSON (a number, list, object, quoted
    string, true, false or null) is read as JSON; any other value is kept as text."""
    out = {}
    for item in items or []:
        key, _, value = item.partition("=")
        out[key] = json.loads(value) if value and value[0] in '[{0123456789tfn-"' else value
    return out


def cmd_catalog(args):
    """One line per eval case: id, risk, entry agent, workflow, fault profile and name."""
    from traceeval.catalog import load_catalog

    for c in load_catalog():
        print(f"{c.id:22s} {c.risk:8s} {c.agent:13s} {c.workflow or '':4s} {c.fault_profile:30s} {c.name}")


def cmd_mutations(args):
    """One line per controlled change (id, category, regression or benign, what it does), then the batches. With
    ``--generated``: the changes made mechanically from the app (``mutation/generator.py``), which have no label."""
    from traceeval.mutation.catalog import BATCHES, MUTATIONS

    if args.generated:
        from collections import Counter

        from traceeval.mutation.generator import generate, kind_of

        changes = generate()
        for m in changes:
            print(f"{m.id:40s} {m.category:8s} {m.description}")
        kinds = Counter(kind_of(m.id) for m in changes)
        print(f"\n{len(changes)} generated changes: " + ", ".join(f"{n} {kind}" for kind, n in kinds.most_common()))
        return
    for m in MUTATIONS:
        print(f"{m.id:40s} {m.category:9s} {'regression' if m.expected_regression else 'benign    '} {m.description}")
    print()
    for m in BATCHES:  # recorded on request only: traceeval mutants --only <batch>
        label = "regression" if m.expected_regression else "benign    "
        print(f"{m.id:40s} {m.category:9s} {label} {m.description} Members: {', '.join(m.members)}.")


def cmd_run(args):
    """Run one case, live or from the recorded answers, and print its record; ``--otel`` also exports its trace."""
    from traceeval.catalog import load_catalog
    from traceeval.experiment.executor import run_case
    from traceeval.experiment.sutloader import load_sut
    from traceeval.sut import SUT_ROOT

    case = {c.id: c for c in load_catalog()}[args.test]
    sut = load_sut(Path(args.sut_dir) if args.sut_dir else SUT_ROOT)
    # With --backend llm the endpoint and model are the backend's defaults (Qwen, or TRACEEVAL_LLM_*). An export
    # needs the trace's events, which keep_state adds to the record.
    overrides = _parse_overrides(args.set)
    rec = run_case(sut, case, backend=args.backend, config_overrides=overrides, keep_state=bool(args.otel))
    # The observed dependencies, covered functions, states and events are long, left out of the printout.
    hidden = ("deps", "code_functions", "initial_state", "final_state", "events")
    print(json.dumps({k: v for k, v in rec.items() if k not in hidden}, indent=1, default=str))
    if args.otel:
        from traceeval.tracing.otel import write_otlp

        print(f"OpenTelemetry trace (OTLP JSON): {write_otlp(args.otel, rec)}", file=sys.stderr)


def cmd_baseline(args):
    """Record the baseline: every case ``--reps`` times on the unchanged application, with its code coverage."""
    from traceeval.experiment.runner import record_baseline

    # No --workers here: the baseline records code coverage, which follows one case at a time.
    record_baseline(
        Path(args.workdir),
        reps=args.reps,
        backend=args.backend,
        config_overrides=_parse_overrides(args.set),
    )


def _workers(args) -> int:
    """Cases run in parallel: as many as asked, or by default 32 for a served model and 1 otherwise."""
    return args.workers or (32 if args.backend in ("vllm", "llm") else 1)


def _warn_drift(workdir: Path):
    """Say on stderr what differs between a recording and the files of today (``experiment/manifest.py``): the app
    it was recorded on, or the catalog its tests were read from. The commands that only read a recording go on."""
    from traceeval.experiment.manifest import drift

    for sentence in drift(workdir).values():
        print(f"warning: {sentence}", file=sys.stderr)


def cmd_mutants(args):
    """Record the empty change and the variants (or those of ``--only``): each controlled change applied to a copy
    of the recording's original app, every case run on it."""
    from traceeval.experiment.runner import record_mutants

    workdir = Path(args.workdir)
    _warn_drift(workdir)
    ids = args.only or None
    if args.generated is not None:
        # the generated changes of the recording's own app: all of them, or so many of each kind
        from traceeval.experiment.manifest import baseline_copy
        from traceeval.mutation.generator import generated, sample

        changes = list(generated(baseline_copy(workdir)).values())
        ids = [m.id for m in (sample(changes, args.generated) if args.generated else changes)]
    record_mutants(
        workdir,
        mutation_ids=ids,
        reps=args.reps,
        backend=args.backend,
        config_overrides=_parse_overrides(args.set),
        workers=_workers(args),
        reached_only=args.reached_only,
        resume=args.resume,
    )


def cmd_replay_first(args):
    """Replay the original app and every changed copy against the recording's cassette; no model is called."""
    from traceeval.experiment.replay_first import Replays, replay_first

    workdir = Path(args.workdir)
    _warn_drift(workdir)
    # replays are CPU work, one process per copy: four at a time unless --workers says otherwise, and never more
    # than the machine has cores (inside `experiment`, --workers is the model server's concurrency)
    workers = min(args.workers or 4, os.cpu_count() or 4)
    if args.generated is not None:
        # the generated changes instead of the recorded copies: each from a temporary copy, none recorded
        from traceeval.experiment.generated import replay_generated
        from traceeval.experiment.history import History
        from traceeval.experiment.report import _generated_section

        out = replay_generated(workdir, workers=workers, per_kind=args.generated or None)
        print("\n".join(_generated_section(workdir, History.load(workdir))))
        print(f"replays written: {out}")
        return
    out = replay_first(workdir, workers=workers)
    replays = Replays.load(workdir)
    for variant in replays.rows:
        tests = len(replays.rows[variant])
        diverged, failures = len(replays.diverged(variant)), len(replays.new_failures(variant))
        print(f"{variant:42s} replayed {tests - diverged:3d}  diverged {diverged:3d}  new failures replayed {failures}")
    print(f"replays written: {out}")


def cmd_evaluate(args):
    """Replay every strategy against the recording: a selection at each budget, and a ranking of the whole suite.
    When the recording has been replayed (``replay-first``), the selection is evaluated replay-first as well."""
    from traceeval.experiment.evaluate import DEFAULT_BUDGETS, evaluate, evaluate_prioritization
    from traceeval.experiment.replay_first import Replays

    workdir, strategies = Path(args.workdir), args.strategies or None
    _warn_drift(workdir)
    budgets = tuple(args.budgets) if args.budgets else DEFAULT_BUDGETS
    which = {}  # the changes to evaluate and those to learn from; empty: all, each learning from the others
    if args.held_out:
        # The generated changes in two fixed halves (the same whichever of them are recorded): the strategies that
        # learn do so from one, and every strategy is evaluated on the other.
        from traceeval.experiment.manifest import baseline_copy
        from traceeval.mutation.generator import generated, split

        recorded = {path.stem for path in (workdir / "history" / "variants").glob("*.jsonl")}
        learn, held_out = split(list(generated(baseline_copy(workdir))))
        which = {"train": [v for v in learn if v in recorded], "variants": [v for v in held_out if v in recorded]}
        print(f"held out: {len(which['variants'])} generated changes; learning from the other {len(which['train'])}")
    which["jobs"] = args.jobs
    df = evaluate(workdir, strategies=strategies, budgets=budgets, seeds=args.seeds, **which)
    # Prioritization: APFD over each strategy's complete order, with the same seeds for the orders drawn at random.
    pr = evaluate_prioritization(workdir, strategies, args.seeds, which.get("variants"), which.get("train"))
    print(f"replay rows: {len(df)}, prioritization rows: {len(pr)} -> {workdir / 'results'}")
    if Replays.load(workdir) is not None:
        rf = evaluate(workdir, strategies=strategies, budgets=budgets, seeds=args.seeds, replay_first=True, **which)
        print(f"replay-first rows: {len(rf)}")


def cmd_report(args):
    """Write the experiment's report and figures from the results in the workdir."""
    from traceeval.experiment.report import write_report

    out = write_report(Path(args.workdir))
    print(f"report written: {out}")


def cmd_experiment(args):
    """The whole experiment in a row: baseline, variants, their replay, evaluation, report."""
    cmd_baseline(args)
    cmd_mutants(args)
    cmd_replay_first(args)
    cmd_evaluate(args)
    cmd_report(args)


def cmd_check(args):
    """The prototype: one change checked live, replay first and then the proposed method, against a recorded
    experiment."""
    from traceeval.experiment.check import check

    check(args.change, Path(args.history), args.budget, args.backend)


def cmd_coverage(args):
    """Print what the suite covers, per dimension and component, from a recorded experiment."""
    from traceeval.experiment.history import History
    from traceeval.experiment.report import suite_coverage_lines
    from traceeval.sut import SUT_ROOT

    print("\n".join(suite_coverage_lines(History.load(Path(args.history)), SUT_ROOT)))


def cmd_properties(args):
    """Draft the catalog of properties with a model, or apply the draft once a person has reviewed it."""
    from traceeval.catalog import extract

    if args.action == "apply":
        print(extract.apply())
        return
    result = extract.draft(
        max_properties=args.max,
        per_test=args.per_test,
        fresh=args.fresh,
        replay=Path(args.replay) if args.replay else None,
        save_response=Path(args.save_response) if args.save_response else None,
    )
    print(f"draft: {result['draft']}\nreport: {result['report']}")
    print(f"{len(result['properties'])} properties, {len(result['tags'])} tests tagged, {len(result['notes'])} notes")


def cmd_sdd(args):
    """The spec-driven development demo over the demo PRs; ``draft`` instead drafts a new spec with a model."""
    from traceeval.spec.runner import run_demo

    if args.action == "draft":
        return cmd_sdd_draft(args)
    run_demo(
        Path(args.workdir),
        spec_ids=args.specs or None,
        out=Path(args.out) if args.out else None,
        backend=args.backend,
        workers=_workers(args),
    )


def cmd_sdd_draft(args):
    """Draft a spec from a change request with a model, and validate it against the application's names."""
    from traceeval.catalog import load_catalog
    from traceeval.spec.draft import draft
    from traceeval.spec.product import ProductModel
    from traceeval.spec.runner import record_baseline

    if not args.request:
        raise SystemExit("sdd draft needs --request <file>")
    catalog = {c.id: c for c in load_catalog()}
    # The product model (tools, settings, functions, cases the draft may name) comes from a baseline recording;
    # the default replay backend gives one without a model.
    sut_dir, runs, deps = record_baseline(Path(args.workdir), catalog, backend=args.backend)
    out = Path(args.out) if args.out else Path("traceeval/specs") / f"{args.id}.draft.yaml"
    result = draft(
        Path(args.request),
        args.id,
        out,
        ProductModel(sut_dir, runs, deps),
        catalog,
        replay=Path(args.replay) if args.replay else None,
        save_response=Path(args.save_response) if args.save_response else None,
    )
    print(f"draft: {result['draft']}\nrendering: {result['rendering']}")
    for n in result["problems"] + result["validation"]:
        print(f"  {n}")


def main(argv=None):
    """Parse the command line and run the command it names."""
    p = argparse.ArgumentParser(
        prog="traceeval", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("catalog").set_defaults(fn=cmd_catalog)
    mu = sub.add_parser("mutations")
    mu.add_argument("--generated", action="store_true", help="list the changes generated from the app instead")
    mu.set_defaults(fn=cmd_mutations)

    r = sub.add_parser("run")
    r.add_argument("--test", required=True)
    r.add_argument("--backend", default="hf", choices=BACKENDS)
    r.add_argument("--sut-dir", default=None)
    r.add_argument("--set", action="append", help="config override key=value (JSON value)")
    r.add_argument("--otel", metavar="PATH", help="write the run's trace as OpenTelemetry spans (OTLP JSON) to PATH")
    r.set_defaults(fn=cmd_run)

    # The experiment commands share one set of options, since `experiment` runs the other five in a row; each
    # command reads only the options it needs.
    def common(sp):
        """The options every experiment command takes."""
        sp.add_argument("--workdir", default="runs/experiment")
        sp.add_argument("--reps", type=int, default=3)
        sp.add_argument("--backend", default="hf", choices=BACKENDS)
        workers = "cases in parallel (default: 32 for vllm/llm, else 1); replay-first: copies in parallel (default: 4)"
        sp.add_argument("--workers", type=int, default=0, help=workers)
        sp.add_argument("--set", action="append", help="config override key=value (JSON value), e.g. runtime.retries=0")
        sp.add_argument("--only", nargs="*", help="mutation ids (mutants only)")
        generated = "the generated changes, all or N of each kind (mutants: record them; replay-first: replay them)"
        sp.add_argument("--generated", nargs="?", const=0, type=int, default=None, metavar="N", help=generated)
        reached = "mutants: replay each copy first and run only the tests that diverge; the copy is not kept"
        sp.add_argument("--reached-only", action="store_true", help=reached)
        sp.add_argument("--resume", action="store_true", help="mutants: leave out the changes already recorded")
        held = "evaluate: learn from one half of the generated changes and evaluate on the other, held out"
        sp.add_argument("--held-out", action="store_true", help=held)
        jobs = "evaluate: processes to share the changes among; each loads the recording (default 1)"
        sp.add_argument("--jobs", type=int, default=1, help=jobs)
        sp.add_argument("--seeds", type=int, default=5, help="replay seeds (evaluate only)")
        sp.add_argument("--budgets", nargs="*", type=float)
        sp.add_argument("--strategies", nargs="*", help="strategy names, or 'all' (default: the core set)")

    for name, fn in (
        ("baseline", cmd_baseline),
        ("mutants", cmd_mutants),
        ("replay-first", cmd_replay_first),
        ("evaluate", cmd_evaluate),
        ("report", cmd_report),
        ("experiment", cmd_experiment),
    ):
        sp = sub.add_parser(name)
        common(sp)
        sp.set_defaults(fn=fn)

    ck = sub.add_parser("check")
    ck.add_argument("change", help="a mutation id (see traceeval mutations) or a changed copy of traceeval/sut")
    ck.add_argument("--history", required=True, help="an experiment recorded with the same model, e.g. runs/gemma7")
    ck.add_argument("--budget", type=float, default=0.2, help="at most this fraction of the full suite's tokens")
    ck.add_argument("--backend", default="vllm", choices=BACKENDS, help="who plays the agents (default: vllm, Gemma)")
    ck.set_defaults(fn=cmd_check)

    cv = sub.add_parser("coverage")
    cv.add_argument("--history", required=True, help="a recorded experiment, e.g. runs/gemma7")
    cv.set_defaults(fn=cmd_coverage)

    pp = sub.add_parser("properties")
    pp.add_argument("action", choices=["draft", "apply"])
    pp.add_argument("--max", type=int, default=15, help="at most this many properties in the catalog (1-20)")
    pp.add_argument("--per-test", type=int, default=5, help="at most this many properties per test")
    pp.add_argument("--fresh", action="store_true", help="derive the catalog anew instead of keeping properties.yaml")
    pp.add_argument("--replay", help="saved model answers to use instead of calling the model")
    pp.add_argument("--save-response", help="save the model's answers here, for --replay")
    pp.set_defaults(fn=cmd_properties)

    sd = sub.add_parser("sdd")
    sd.add_argument("action", nargs="?", default="run", choices=["run", "draft"])
    sd.add_argument("--workdir", default="runs/sdd")
    sd.add_argument("--specs", nargs="*", help="run: spec ids (default: all)")
    sd.add_argument("--out", default=None, help="run: report directory (default: the workdir); draft: the draft file")
    sd.add_argument("--request", help="draft: the change request (markdown or text)")
    sd.add_argument("--id", default="FS-0106", help="draft: id of the new spec")
    sd.add_argument("--replay", help="draft: a saved model answer to use instead of calling the endpoint")
    sd.add_argument("--save-response", help="draft: save the model's answer here for later --replay")
    sd.add_argument("--backend", default="replay", choices=BACKENDS, help="who plays the agents (default: replay)")
    sd.add_argument("--workers", type=int, default=0, help="cases in parallel (default: 32 for vllm/llm, else 1)")
    sd.set_defaults(fn=cmd_sdd)

    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
