"""Trace recording.

The SUT emits flat events (``tracer.event(kind, **attrs)``); the recorder turns them into a
normalised trace document with the dependency information the selectors consume:

    agents, skills (name+version+digest), tools (with call counts, args, status), config keys read,
    agent transitions, token usage, latency, final message, termination reason

plus, when coverage measurement is enabled by the executor, the set of SUT code functions executed.
"""

import time
from dataclasses import dataclass, field


class NullTracer:
    def event(self, kind: str, **attrs):
        pass


@dataclass
class TraceRecorder:
    test_id: str = ""
    run_id: str = ""
    variant: str = "baseline"
    backend: str = "simulated"
    events: list[dict] = field(default_factory=list)
    started: float = field(default_factory=time.perf_counter)

    def event(self, kind: str, **attrs):
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
        p = sum(e.get("prompt_tokens", 0) for e in self.events if e["kind"] == "llm.call")
        c = sum(e.get("completion_tokens", 0) for e in self.events if e["kind"] == "llm.call")
        return p, c

    def to_dict(self, code_functions: list[str] | None = None) -> dict:
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
            "code_functions": sorted(code_functions or []),
            "prompt_tokens": p,
            "completion_tokens": c,
            "tokens": p + c,
            "steps": end.get("steps"),
            "termination": end.get("termination"),
            "final_message": end.get("message", ""),
            "events": self.events,
        }
