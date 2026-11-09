"""Trace recording.

The SUT emits flat events (``tracer.event(kind, **attrs)``); the recorder turns them into a
normalised trace document with the dependency information the selectors consume:

    agents, skills (name and version), tools (every call with its arguments and status), config keys
    read, agent-definition fields consulted for routing, delegations, token usage, steps, final message,
    termination reason

The SUT code each test executed is not part of the trace: ``codecov`` measures it and the runner adds it
to the run's record. ``otel`` exports a trace as OpenTelemetry spans.
"""

import time
from dataclasses import dataclass, field


@dataclass
class TraceRecorder:
    """The events of one run, in the order they happened, and the views the scorers and selectors read.

    The SUT only ever calls ``event``; everything else here derives from the event list afterwards."""

    test_id: str = ""
    run_id: str = ""  # the executor writes "<variant>:<test id>:<repetition>"
    variant: str = "baseline"
    backend: str = ""
    events: list[dict] = field(default_factory=list)
    started: float = field(default_factory=time.perf_counter)
    # The same moment on the wall clock (epoch seconds): the origin of the events' times in an export
    # (tracing/otel.py). Nothing else reads it, so the runs stay comparable.
    started_at: float = field(default_factory=time.time)

    def event(self, kind: str, **attrs):
        """Append one event; ``t`` is the time since the recorder was created, in seconds."""
        self.events.append({"kind": kind, "t": round(time.perf_counter() - self.started, 6), **attrs})

    # ---------------------------------------------------------------- derived views
    def tool_calls(self) -> list[dict]:
        return [e for e in self.events if e["kind"] == "tool.call"]

    def tools_called(self) -> list[str]:
        return [e["tool"] for e in self.tool_calls()]

    def skills_loaded(self) -> list[str]:
        return sorted({e["skill"] for e in self.events if e["kind"] == "skill.load"})

    def agents_involved(self) -> list[str]:
        out = []
        for e in self.events:
            if e["kind"] == "agent.start" and e["agent"] not in out:
                out.append(e["agent"])
        return out

    def routes(self) -> list[tuple[str, str]]:
        """Successful delegations only (a refused delegation is not a route)."""
        return [
            (e["source"], e["target"]) for e in self.events if e["kind"] == "agent.route" and e.get("status") == "ok"
        ]

    def consulted(self) -> list[str]:
        """Agent-definition fields read by an orchestrator for routing: 'agent:<name>.<field>'."""
        out = []
        for e in self.events:
            if e["kind"] == "agent.consult":
                out.extend(f"agent:{e['agent']}.{f}" for f in e.get("fields", []))
        return sorted(set(out))

    def config_keys(self) -> list[str]:
        return sorted({e["key"] for e in self.events if e["kind"] == "config.read"})

    def usage(self) -> tuple[int, int]:
        """Prompt and completion tokens of the whole run, summed over its ``llm.call`` events."""
        p = sum(e.get("prompt_tokens", 0) for e in self.events if e["kind"] == "llm.call")
        c = sum(e.get("completion_tokens", 0) for e in self.events if e["kind"] == "llm.call")
        return p, c

    def to_dict(self) -> dict:
        """The trace document. Steps, termination and the final message come from the ``run.end`` event;
        a run that crashed before it has none, and those fields are then empty."""
        p, c = self.usage()
        end = next((e for e in reversed(self.events) if e["kind"] == "run.end"), {})
        return {
            "test_id": self.test_id,
            "run_id": self.run_id,
            "variant": self.variant,
            "backend": self.backend,
            "agents": self.agents_involved(),
            "routes": self.routes(),
            "skills": self.skills_loaded(),
            "skill_versions": {e["skill"]: e["version"] for e in self.events if e["kind"] == "skill.load"},
            "tools": self.tools_called(),
            "tool_calls": [{k: v for k, v in e.items() if k != "t"} for e in self.tool_calls()],
            "config_keys": self.config_keys(),
            "consulted": self.consulted(),
            "prompt_tokens": p,
            "completion_tokens": c,
            "tokens": p + c,
            "steps": end.get("steps"),
            "termination": end.get("termination"),
            "final_message": end.get("message", ""),
            "started_at": self.started_at,
            "events": self.events,
        }
