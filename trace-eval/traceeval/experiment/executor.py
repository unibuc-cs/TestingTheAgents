"""Execute eval cases against a loaded SUT variant and produce history records.

A history record is the unit the selectors learn from and the replay evaluator samples from:
    test_id, dataset, variant, rep, backend, passed, classification, checks, tokens (agent + judge),
    latency_ms, steps, deps (observed components), trace summary.
"""

import copy
import json
import os
import time
import traceback
from pathlib import Path

from traceeval.catalog import EvalCase
from traceeval.scoring.scorers import judge_answer, score_case
from traceeval.tracing import TraceRecorder


def observed_components(trace: dict) -> set[str]:
    """The components a run exercised, as the ids change sets use (code functions are added later from
    coverage, see ``attach_code_functions``)."""
    deps: set[str] = set()
    for a in trace.get("agents", []):
        deps.add(f"agent:{a}")
    for s in trace.get("skills", []):
        deps.add(f"skill:{s}")
    for t in trace.get("tools", []):
        deps.add(f"tool:{t}")
    for k in trace.get("config_keys", []):
        deps.add(f"config:{k}")
    for c in trace.get("consulted", []):  # already ids: agent:<name>.<field>
        deps.add(c)
    return deps


def _apply_patch(data: dict, patch: dict):
    """Set each dotted key of ``patch`` in the fixture data (a case's ``fixture_patch``)."""
    for dotted, value in patch.items():
        node = data
        parts = dotted.split(".")
        for p in parts[:-1]:
            node = node.setdefault(p, {})
        node[parts[-1]] = copy.deepcopy(value)


# Errors of the OpenAI client that mean the server did not serve the request (it was down, overloaded or out of
# time), as opposed to a request the server rejected (a prompt too long for the model: the run's own fault).
_SERVER_ERRORS = {"APIConnectionError", "APITimeoutError", "InternalServerError", "RateLimitError"}


def is_infrastructure_error(exc: BaseException) -> bool:
    """Whether the environment, not the agent or the app, broke the run: the model server or the network did not
    answer, or a replay met a request it has no recorded answer for (``CacheMiss``). The run is then INFRA_INVALID."""
    from traceeval.llm.cache import CacheMiss

    for e in (exc, exc.__cause__):  # a client may wrap the network error it met
        if isinstance(e, (ConnectionError, TimeoutError, CacheMiss)) or type(e).__name__ in _SERVER_ERRORS:
            return True
        if e is not None and type(e).__module__.split(".")[0] in ("httpx", "httpcore"):
            return True
    return False


def default_backend() -> str:
    """The backend of a run that names none: ``TRACEEVAL_BACKEND``, or "replay" (recorded answers, no model).
    Running the test suite with ``TRACEEVAL_BACKEND=vllm`` records the answers its cassette lacks."""
    return os.environ.get("TRACEEVAL_BACKEND", "replay")


def run_case(
    sut,
    case: EvalCase,
    *,
    backend: str | None = None,
    rep: int = 0,
    variant: str = "baseline",
    config_overrides: dict | None = None,
    llm_settings=None,
    llm_client=None,
    fault_profile: str | None = None,
    keep_state: bool = False,
) -> dict:
    """Run one eval case once. Never raises: a run that raised is recorded as HARNESS_ERROR, or as INFRA_INVALID
    when the environment caused it (``is_infrastructure_error``).

    ``backend`` picks who plays the agents: "hf" (Gemma on the local GPU), "vllm" (Gemma on a vLLM server),
    "replay" (Gemma's recorded answers, no model; ``traceeval/llm/cache.py``) or "llm" (an OpenAI-compatible
    endpoint, by default Qwen on the GPU server, configured by ``llm_settings``); None means
    ``default_backend()``. ``llm_client`` replaces the model client, e.g. with a scripted one in tests.
    ``fault_profile`` overrides the case's own profile; ``keep_state`` adds the initial fixture, the final state
    and the trace's events to the record (used by the spec layer's trace monitors and by the OpenTelemetry
    export, ``tracing/otel.py``; too large for histories). A case with a
    ``judge`` block is judged by the model ``TRACEEVAL_JUDGE`` names (``llm/chat.py::judge_client``)."""
    backend = backend or default_backend()
    tracer = TraceRecorder(test_id=case.id, run_id=f"{variant}:{case.id}:{rep}", variant=variant, backend=backend)
    State = sut.sub("services.state").State
    Config = sut.sub("harness.config").Config
    Runtime = sut.sub("harness.runtime").Runtime
    FaultInjector = sut.sub("harness.faults").FaultInjector

    t0 = time.perf_counter()
    error, infra = None, False
    run = {}
    state = None
    initial = None
    try:
        state = State.from_fixture(sut.path / "fixtures" / f"{case.fixture}.json")
        if case.fixture_patch:
            _apply_patch(state.data, case.fixture_patch)
        if keep_state:
            initial = state.snapshot()
        # the case's own settings, then the caller's (traceeval run --set), which win
        overrides = {**case.config, **(config_overrides or {})}
        config = Config.load(sut.path / "config" / "runtime.yaml", tracer=tracer, overrides=overrides)
        if backend not in ("llm", "hf", "vllm", "replay"):
            raise ValueError(f"unknown backend {backend}")
        llm = sut.sub("harness.backends.llm_openai")
        if llm_client is None:
            # Gemma (local, on the GPU server, or its recorded answers) or the llm backend's servers (Qwen by
            # default). The client is created once per process and shared by every case and variant.
            from traceeval.llm.chat import shared_client

            llm_client = shared_client(backend)
        if backend != "llm":  # with "llm" the backend's own settings name the model (Qwen, or TRACEEVAL_LLM_MODEL)
            llm_settings = llm_settings or llm.LLMSettings(model=llm_client.model_id)
        factory = llm.make_backend_factory(settings=llm_settings, client=llm_client)
        faults = FaultInjector(fault_profile if fault_profile is not None else case.fault_profile)
        runtime = Runtime(sut.path, config, state, tracer, factory, faults, sut.tools)
        run = runtime.run(case.agent, case.request, dict(case.context))
    except Exception as exc:  # noqa: BLE001 - every failure must become a record
        error, infra = traceback.format_exc(limit=6), is_infrastructure_error(exc)
    wall_ms = (time.perf_counter() - t0) * 1000

    trace = tracer.to_dict()
    final_state = state.data if state is not None else {}
    verdict = score_case(case, trace, final_state, run, error=error, infra=infra)

    judge_tokens = 0
    judge_result = None
    if case.judge and verdict.passed:  # deterministic checks first; the judge only if they passed
        from traceeval.llm.chat import judge_client

        try:
            judge_result = judge_answer(case, trace.get("final_message", ""), *judge_client(backend))
            judge_tokens = judge_result["tokens"]
            if not judge_result["ok"]:
                verdict.passed = False
                verdict.classification = "AGENT_FAILURE"
                verdict.checks.append({"name": "judge", "ok": False, "detail": judge_result["verdict"]})
        except Exception as exc:  # noqa: BLE001 - a judge that cannot answer fails the run like any harness error
            error = traceback.format_exc(limit=6)
            verdict.passed = False
            verdict.classification = "INFRA_INVALID" if is_infrastructure_error(exc) else "HARNESS_ERROR"

    agent_tokens = trace["tokens"]
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
        "latency_ms": round(wall_ms, 1),
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
        # With the events, what an OpenTelemetry export of the run needs (tracing/otel.py::to_otlp).
        record["run_id"] = trace["run_id"]
        record["started_at"] = trace["started_at"]
    return record


def attach_code_functions(record: dict, functions: set[str]):
    """Add the code functions and lines that coverage saw in this run to the record's dependencies."""
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
