"""Apply specs to pull requests.

record_baseline  run the catalog once on the unmodified SUT with coverage -> product model (dynamic part)
agent_brief      the "locate" step: what to read and which checks will run, with resource numbers
evaluate_pr      materialise the PR, run every clause checker, run the change-selected regression
                 tests, write the evidence record
run_demo         all of the above for every spec and PR -> <workdir>/evidence/*.json + report
"""

import json
import re
import sys
import time
from pathlib import Path

from traceeval.catalog import load_catalog
from traceeval.experiment.executor import run_case
from traceeval.experiment.sutloader import load_sut
from traceeval.mutation.engine import materialize_variant
from traceeval.selection.base import affinity
from traceeval.tracing.codecov import CoverageSession

from .checks import CHECKERS
from .context import CheckContext
from .model import RUNG_LABEL, ClauseResult, Spec, load_specs, validate_spec
from .product import ProductModel
from .prs import PR, prs_for


def _log(msg: str):
    print(msg, file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------- baseline / product model
def record_baseline(workdir: Path, catalog: dict) -> tuple[Path, dict, dict]:
    """Run every catalog case on the baseline with coverage: records (events + states) and observed deps."""
    sut_dir, _ = materialize_variant(None, workdir / "variants")
    sut = load_sut(sut_dir)
    cov = CoverageSession(sut.path)
    runs = {}
    for tid, case in catalog.items():
        cov.begin(tid)
        runs[tid] = run_case(sut, case, keep_state=True)
    functions = cov.finish()
    deps = {tid: set(rec["deps"]) | functions.get(tid, set()) for tid, rec in runs.items()}
    sut.unload()
    return sut_dir, runs, deps


# ---------------------------------------------------------------------------- the locate step
def agent_brief(spec: Spec, model: ProductModel, catalog: dict) -> dict:
    """What a coding agent needs for this request, derived from the spec and the product model."""
    scoped: set[str] = set()
    checks = []
    for c in spec.clauses:
        if c.kind == "trace":
            ids = _cases_in_scope(model, catalog, c.get("scope", "all"))
            scoped |= set(ids)
            checks.append({"clause": c.id, "kind": c.kind, "runs": len(ids)})
        elif c.kind == "example":
            base = c.get("case")
            if isinstance(base, str):
                scoped.add(base)
            checks.append({"clause": c.id, "kind": c.kind, "runs": 1})
        elif c.kind == "contract":
            if "function" in c.data:
                checks.append(
                    {"clause": c.id, "kind": c.kind, "runs": 0, "examples": c.get("examples", 200), "proof": True}
                )
            else:
                values = model.model_set(next(iter(c["forall"].values())), catalog)
                n = len(values) if values is not None else c.get("examples", 40)
                checks.append({"clause": c.id, "kind": c.kind, "runs": n})
        else:
            checks.append({"clause": c.id, "kind": c.kind, "runs": 0})
    # locate: the tools the spec talks about -> their adapters, the services behind them, the skills calling them;
    # plus files named by placement rules and the configuration keys of setting clauses
    text = spec.path.read_text() if spec.path else ""
    tools = {t for t in model.tools_static() if re.search(rf"\b{re.escape(t)}\b", text)}
    for c in spec.clauses:  # a clause quantifying over a set of tools makes all of their sites relevant
        if c.kind == "contract" and "forall" in c.data:
            values = model.model_set(next(iter(c["forall"].values())), catalog) or []
            tools |= {v for v in values if v in model.tools_static()}
    tools = sorted(tools)
    read: dict[str, set[str]] = {k: set(v) for k, v in model.locate(tools).items()}
    for c in spec.clauses:
        if c.kind == "placement":
            for rule in c["rules"]:
                ((_, body),) = rule.items()
                if "function" in body and isinstance(body.get("in"), str):
                    read.setdefault(body["in"], set())
                if "skill" in body:
                    read.setdefault(f"skills/{body['skill']}/SKILL.md", set())
        if c.kind == "setting":
            read.setdefault("config/runtime.yaml", set()).add(c["key"])
    read = {k: sorted(v) for k, v in sorted(read.items()) if k in model.files}
    return {
        "request": spec.id,
        "tools": tools,
        "spec_check": [f"{level}: {msg}" for level, msg in validate_spec(spec, model)],
        "read": read,
        "context_tokens": model.tokens_of(read),
        "repo_tokens": model.repo_tokens(),
        "repo_files": len(model.files),
        "checks": checks,
        "runs_planned": len(scoped),
        "full_suite": len(catalog),
    }


def _cases_in_scope(model, catalog, scope):
    ctx = CheckContext(sut=None, model=model, catalog=catalog)
    return ctx.cases_in_scope(scope)


# ---------------------------------------------------------------------------- evaluating one PR
def evaluate_pr(spec: Spec, pr: PR, workdir: Path, catalog: dict, baseline_runs: dict, baseline_deps: dict) -> dict:
    t0 = time.perf_counter()
    sut_dir, change = materialize_variant(pr.mutation, workdir / "variants")
    sut = load_sut(sut_dir)
    model = ProductModel(sut_dir, baseline_runs, baseline_deps)
    ctx = CheckContext(sut=sut, model=model, catalog=catalog, variant=pr.id)
    results: list[ClauseResult] = []
    for clause in spec.clauses:
        try:
            res = CHECKERS[clause.kind](clause, ctx)
        except Exception as exc:  # noqa: BLE001 - a crashing checker is itself evidence
            res = ClauseResult(clause.id, clause.kind, "L0", "fail", f"checker error: {type(exc).__name__}: {exc}")
        res.required = clause.require
        if res.status == "pass" and not res.meets_required:
            res.status = "gap"
            res.summary += f"; reached {res.rung}, {res.required} required"
        results.append(res)
    clause_runs = ctx.cost["runs"]
    # regression: the catalog cases whose recorded traces touch the changed components (trace-eval selection)
    selected = sorted(t for t in catalog if affinity(change, baseline_deps[t]) > 0)
    failed = [t for t in selected if not ctx.run(catalog[t])["passed"]]
    results.append(
        ClauseResult(
            "regression-tests",
            "example",
            "L1",
            "fail" if failed else "pass",
            f"{len(selected)} of {len(catalog)} catalog cases selected by observed dependencies; "
            + (f"failed: {failed}" if failed else "all pass"),
            failed,
            {"runs": len(selected)},
        )
    )
    sut.unload()
    # verdict: any failing clause rejects; a clause with a gap (unexercised value, uncovered path, or a rung
    # below the required one) is reported but does not reject
    statuses = {r.status for r in results}
    verdict = "rejected" if "fail" in statuses else ("accepted with gaps" if "gap" in statuses else "accepted")
    profile: dict[str, int] = {}
    for r in results:
        if r.status in ("pass", "gap"):
            profile[r.rung] = profile.get(r.rung, 0) + 1
    full_tokens = sum(r["tokens"] for r in baseline_runs.values())
    return {
        "request": spec.id,
        "title": spec.title,
        "pr": pr.id,
        "pr_title": pr.title,
        "expected": pr.expected,
        "note": pr.note,
        "change": {
            "files": change.files,
            "components": sorted(change.ids(semantic_only=True)),
            "diff_lines": sum(
                1
                for line in change.diff.splitlines()
                if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
            ),
        },
        "clauses": [r.to_dict() for r in results],
        "verdict": verdict,
        "assurance": dict(sorted(profile.items(), reverse=True)),
        "cost": {
            "runs": ctx.cost["runs"],
            "clause_runs": clause_runs,
            "regression_selected": len(selected),
            "tokens": ctx.cost["tokens"],
            "seconds": round(time.perf_counter() - t0, 1),
            "full_suite_runs": len(catalog),
            "full_suite_tokens": full_tokens,
        },
    }


# ---------------------------------------------------------------------------- everything
def run_demo(workdir: Path, spec_ids: list[str] | None = None, out: Path | None = None) -> dict:
    workdir = Path(workdir)
    catalog = {c.id: c for c in load_catalog()}
    t0 = time.time()
    sut_dir, baseline_runs, baseline_deps = record_baseline(workdir, catalog)
    _log(f"[sdd] baseline: {len(catalog)} runs with coverage in {time.time() - t0:.1f}s")
    base_model = ProductModel(sut_dir, baseline_runs, baseline_deps)
    specs = load_specs(ids=spec_ids)
    briefs, evidence = {}, []
    (workdir / "evidence").mkdir(parents=True, exist_ok=True)
    for stale in (workdir / "evidence").glob("*.json"):
        stale.unlink()
    for spec in specs:
        briefs[spec.id] = agent_brief(spec, base_model, catalog)
        for pr in prs_for(spec.id):
            ev = evaluate_pr(spec, pr, workdir, catalog, baseline_runs, baseline_deps)
            evidence.append(ev)
            (workdir / "evidence" / (pr.id.replace("/", "__") + ".json")).write_text(
                json.dumps(ev, indent=1, default=str)
            )
            flag = "" if ev["verdict"].startswith(pr.expected) else "   <-- UNEXPECTED"
            _log(
                f"[sdd] {pr.id:45s} {ev['verdict']:19s} (expected {pr.expected}) "
                f"runs={ev['cost']['runs']:3d} {ev['cost']['seconds']}s{flag}"
            )
    from .report import write_report

    path = write_report(workdir, specs, briefs, evidence, base_model, out=out)
    _log(f"[sdd] report: {path}")
    return {"briefs": briefs, "evidence": evidence, "report": str(path)}


RUNGS_IN_ORDER = list(RUNG_LABEL)
