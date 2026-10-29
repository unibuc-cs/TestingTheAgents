"""Command-line interface.

traceeval catalog                         list eval cases
traceeval mutations                       list controlled changes
traceeval run --test PUB-01 [--backend llm]   run one case live and print the trace summary
traceeval baseline --workdir runs/exp1 --reps 3
traceeval mutants  --workdir runs/exp1 --reps 3 [--only id ...]
traceeval evaluate --workdir runs/exp1 --seeds 10
traceeval report   --workdir runs/exp1
traceeval experiment --workdir runs/exp1   (baseline + mutants + evaluate + report)
traceeval sdd --workdir runs/sdd [--specs FS-0101 ...] [--out docs/sdd]   spec-driven development demo
traceeval sdd draft --request request.md --id FS-0106 [--replay answer.json]   draft a spec with an LLM
"""

import argparse
import json
import sys
from pathlib import Path


def _parse_overrides(items):
    out = {}
    for item in items or []:
        key, _, value = item.partition("=")
        out[key] = json.loads(value) if value and value[0] in '[{0123456789tfn-"' else value
    return out


def cmd_catalog(args):
    from traceeval.catalog import load_catalog

    for c in load_catalog():
        print(f"{c.id:22s} {c.risk:8s} {c.agent:13s} {c.fault_profile:30s} {c.name}")


def cmd_mutations(args):
    from traceeval.mutation import MUTATIONS

    for m in MUTATIONS:
        print(f"{m.id:40s} {m.category:9s} {'regression' if m.expected_regression else 'benign    '} {m.description}")


def cmd_run(args):
    from traceeval.catalog import load_catalog
    from traceeval.experiment.executor import run_case
    from traceeval.experiment.sutloader import load_sut
    from traceeval.sut import SUT_ROOT

    cases = {c.id: c for c in load_catalog()}
    case = cases[args.test]
    sut = load_sut(Path(args.sut_dir) if args.sut_dir else SUT_ROOT)
    settings = None
    if args.backend == "llm":
        from traceeval.sut.harness.backends.llm_openai import LLMSettings

        settings = LLMSettings()
    rec = run_case(sut, case, backend=args.backend, config_overrides=_parse_overrides(args.set), llm_settings=settings)
    keep = {k: v for k, v in rec.items() if k not in ("deps", "code_functions")}
    print(json.dumps(keep, indent=1, default=str))


def cmd_baseline(args):
    from traceeval.experiment.runner import record_baseline

    record_baseline(
        Path(args.workdir),
        reps=args.reps,
        backend=args.backend,
        config_overrides=_parse_overrides(args.set),
        seed=args.seed,
    )


def cmd_mutants(args):
    from traceeval.experiment.runner import record_mutants

    record_mutants(
        Path(args.workdir),
        mutation_ids=args.only or None,
        reps=args.reps,
        backend=args.backend,
        config_overrides=_parse_overrides(args.set),
        seed=args.seed,
    )


def cmd_evaluate(args):
    from traceeval.experiment.evaluate import DEFAULT_BUDGETS, evaluate, evaluate_prioritization

    budgets = tuple(args.budgets) if args.budgets else DEFAULT_BUDGETS
    df = evaluate(Path(args.workdir), strategies=args.strategies or None, budgets=budgets, seeds=args.seeds)
    pr = evaluate_prioritization(Path(args.workdir), strategies=args.strategies or None, seeds=max(1, args.seeds // 3))
    print(f"replay rows: {len(df)}, prioritization rows: {len(pr)} -> {Path(args.workdir) / 'results'}")


def cmd_report(args):
    from traceeval.experiment.report import write_report

    out = write_report(Path(args.workdir))
    print(f"report written: {out}")


def cmd_experiment(args):
    cmd_baseline(args)
    cmd_mutants(args)
    cmd_evaluate(args)
    cmd_report(args)


def cmd_sdd(args):
    from traceeval.spec.runner import run_demo

    if args.action == "draft":
        return cmd_sdd_draft(args)
    run_demo(Path(args.workdir), spec_ids=args.specs or None, out=Path(args.out) if args.out else None)


def cmd_sdd_draft(args):
    from traceeval.catalog import load_catalog
    from traceeval.spec.draft import draft
    from traceeval.spec.product import ProductModel
    from traceeval.spec.runner import record_baseline

    if not args.request:
        raise SystemExit("sdd draft needs --request <file>")
    catalog = {c.id: c for c in load_catalog()}
    sut_dir, runs, deps = record_baseline(Path(args.workdir), catalog)
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
    p = argparse.ArgumentParser(
        prog="traceeval", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("catalog").set_defaults(fn=cmd_catalog)
    sub.add_parser("mutations").set_defaults(fn=cmd_mutations)

    r = sub.add_parser("run")
    r.add_argument("--test", required=True)
    r.add_argument("--backend", default="simulated", choices=["simulated", "llm"])
    r.add_argument("--sut-dir", default=None)
    r.add_argument("--set", action="append", help="config override key=value (JSON value)")
    r.set_defaults(fn=cmd_run)

    def common(sp):
        sp.add_argument("--workdir", default="runs/exp1")
        sp.add_argument("--reps", type=int, default=3)
        sp.add_argument("--backend", default="simulated", choices=["simulated", "llm"])
        sp.add_argument(
            "--set", action="append", help="config override key=value (JSON value), e.g. simulated.flakiness=0.05"
        )
        sp.add_argument("--seed", type=int, default=0)
        sp.add_argument("--only", nargs="*", help="mutation ids (mutants only)")
        sp.add_argument("--seeds", type=int, default=5, help="replay seeds (evaluate only)")
        sp.add_argument("--budgets", nargs="*", type=float)
        sp.add_argument("--strategies", nargs="*", help="strategy names, or 'all' (default: the core set)")

    for name, fn in (
        ("baseline", cmd_baseline),
        ("mutants", cmd_mutants),
        ("evaluate", cmd_evaluate),
        ("report", cmd_report),
        ("experiment", cmd_experiment),
    ):
        sp = sub.add_parser(name)
        common(sp)
        sp.set_defaults(fn=fn)

    sd = sub.add_parser("sdd")
    sd.add_argument("action", nargs="?", default="run", choices=["run", "draft"])
    sd.add_argument("--workdir", default="runs/sdd")
    sd.add_argument("--specs", nargs="*", help="run: spec ids (default: all)")
    sd.add_argument("--out", default=None, help="run: report directory (default: the workdir); draft: the draft file")
    sd.add_argument("--request", help="draft: the change request (markdown or text)")
    sd.add_argument("--id", default="FS-0106", help="draft: id of the new spec")
    sd.add_argument("--replay", help="draft: a saved model answer to use instead of calling the endpoint")
    sd.add_argument("--save-response", help="draft: save the model's answer here for later --replay")
    sd.set_defaults(fn=cmd_sdd)

    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
