"""Execute eval cases against a loaded SUT variant and produce history records.

A history record is the unit the selectors learn from and the replay evaluator samples from:
    test_id, dataset, variant, rep, backend, passed, classification, checks, tokens (agent + judge),
    latency_ms, steps, deps (observed components), trace summary.
"""

import copy
import json
import time
import traceback
from pathlib import Path

from traceeval.catalog import EvalCase
from traceeval.scoring.scorers import score_case, simulated_judge
from traceeval.tracing import TraceRecorder


def observed_components(trace: dict) -> set[str]:
    deps: set[str] = set()
    for a in trace.get("agents", []):
        deps.add(f"agent:{a}")
    for s in trace.get("skills", []):
        deps.add(f"skill:{s}")
    for t in trace.get("tools", []):
        deps.add(f"tool:{t}")
    for k in trace.get("config_keys", []):
        deps.add(f"config:{k}")
    for c in trace.get("consulted", []):
        deps.add(c)
    for f in trace.get("code_functions", []):
        deps.add(f)
    return deps


def _apply_patch(data: dict, patch: dict):
    for dotted, value in patch.items():
        node = data
        parts = dotted.split(".")
        for p in parts[:-1]:
            node = node.setdefault(p, {})
        node[parts[-1]] = copy.deepcopy(value)


def run_case(
    sut,
    case: EvalCase,
    *,
    backend: str = "simulated",
    rep: int = 0,
    variant: str = "baseline",
    config_overrides: dict | None = None,
    llm_settings=None,
    llm_client=None,
    seed: int = 0,
    judge_mode: str = "simulated",
    fault_profile: str | None = None,
    keep_state: bool = False,
) -> dict:
    """Run one eval case once. Never raises: harness errors are recorded as HARNESS_ERROR.

    ``fault_profile`` overrides the case's own profile; ``keep_state`` adds the initial fixture and the
    final state to the record (used by the spec layer's trace monitors, too large for histories)."""
    tracer = TraceRecorder(test_id=case.id, run_id=f"{variant}:{case.id}:{rep}", variant=variant, backend=backend)
    State = sut.sub("services.state").State
    Config = sut.sub("harness.config").Config
    Runtime = sut.sub("harness.runtime").Runtime
    FaultInjector = sut.sub("harness.faults").FaultInjector

    t0 = time.perf_counter()
    error = None
    run = {}
    state = None
    initial = None
    try:
        state = State.from_fixture(sut.path / "fixtures" / f"{case.fixture}.json")
        if case.fixture_patch:
            _apply_patch(state.data, case.fixture_patch)
        if keep_state:
            initial = state.snapshot()
        config = Config.load(sut.path / "config" / "runtime.yaml", tracer=tracer, overrides=config_overrides)
        if backend == "simulated":
            sim = sut.sub("harness.backends.simulated")
            flakiness = float(config.data.get("simulated", {}).get("flakiness", 0.0))
            factory = sim.make_backend_factory(
                flakiness=flakiness, seed=seed * 7919 + rep * 104729 + hash(case.id) % 10007
            )
        elif backend == "llm":
            llm = sut.sub("harness.backends.llm_openai")
            factory = llm.make_backend_factory(settings=llm_settings, client=llm_client)
        else:
            raise ValueError(f"unknown backend {backend}")
        faults = FaultInjector(fault_profile if fault_profile is not None else case.fault_profile)
        runtime = Runtime(sut.path, config, state, tracer, factory, faults, sut.tools)
        run = runtime.run(case.agent, case.request, dict(case.context))
    except Exception:  # noqa: BLE001 - every failure must become a record
        error = traceback.format_exc(limit=6)
    wall_ms = (time.perf_counter() - t0) * 1000

    trace = tracer.to_dict()
    final_state = state.data if state is not None else {}
    verdict = score_case(case, trace, final_state, run, error=error)

    judge_tokens = 0
    judge_result = None
    if case.judge and verdict.passed:  # deterministic checks first; judge only if they passed
        if judge_mode == "simulated" or backend == "simulated":
            judge_result = simulated_judge(case, trace.get("final_message", ""))
        else:
            judge_result = simulated_judge(case, trace.get("final_message", ""))
            judge_result["mode"] = "deterministic-fallback"
        judge_tokens = judge_result["tokens"]
        if not judge_result["ok"]:
            verdict.passed = False
            verdict.classification = "AGENT_FAILURE"
            verdict.checks.append({"name": "judge", "ok": False, "detail": judge_result["rubric"]})
        verdict.judge = judge_result

    agent_tokens = trace["tokens"]
    if backend == "simulated":
        latency_ms = 120.0 * (run.get("steps") or 0) + 0.35 * agent_tokens + (0.4 * judge_tokens)
    else:
        latency_ms = wall_ms
    record = {
        "test_id": case.id,
        "dataset": case.dataset,
        "variant": variant,
        "rep": rep,
        "backend": backend,
        "passed": verdict.passed,
        "classification": verdict.classification,
        "checks": verdict.checks,
        "failed_checks": verdict.failed_checks(),
        "judge": judge_result,
        "agent_tokens": agent_tokens,
        "judge_tokens": judge_tokens,
        "tokens": agent_tokens + judge_tokens,
        "prompt_tokens": trace["prompt_tokens"],
        "completion_tokens": trace["completion_tokens"],
        "latency_ms": round(latency_ms, 1),
        "steps": run.get("steps"),
        "termination": run.get("termination"),
        "deps": sorted(observed_components(trace)),
        "agents": trace["agents"],
        "routes": trace["routes"],
        "skills": trace["skills"],
        "tools": trace["tools"],
        "config_keys": trace["config_keys"],
        "final_message": trace.get("final_message", ""),
        "state_digest": state.digest() if state else None,
        "error": error,
    }
    if keep_state:
        record["initial_state"] = initial
        record["final_state"] = final_state
        record["events"] = trace["events"]
    return record


def attach_code_functions(record: dict, functions: set[str]):
    record["code_functions"] = sorted(functions)
    record["deps"] = sorted(set(record["deps"]) | set(functions))
    return record


def write_jsonl(path: Path, records: list[dict]):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as fh:
        fh.writelines(json.dumps(r, default=str) + "\n" for r in records)


def read_jsonl(path: Path) -> list[dict]:
    with open(path) as fh:
        return [json.loads(line) for line in fh if line.strip()]
