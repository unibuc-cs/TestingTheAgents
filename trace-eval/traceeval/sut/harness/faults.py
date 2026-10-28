"""Fault profiles injected at the tool boundary (deterministic, versioned, visible in the trace).

Profiles:
  healthy                      no faults
  transient_once:<tool>        the first invocation of <tool> fails *before* execution (safe retry)
  ack_timeout_once:<tool>      the first invocation of <tool> executes but its acknowledgement is lost
                               (a retry without an idempotency key duplicates the side effect)
  permanent_down:<tool>        every invocation of <tool> fails with a transient error
"""

from ..services.errors import TransientError


class FaultInjector:
    def __init__(self, profile: str = "healthy"):
        self.profile = profile or "healthy"
        self.kind, _, self.target = self.profile.partition(":")
        self._fired: dict[str, int] = {}

    def before(self, tool: str):
        n = self._fired.get(tool, 0)
        if self.kind == "transient_once" and tool == self.target and n == 0:
            self._fired[tool] = n + 1
            raise TransientError(f"[fault:{self.profile}] {tool} timed out before execution")
        if self.kind == "permanent_down" and tool == self.target:
            self._fired[tool] = n + 1
            raise TransientError(f"[fault:{self.profile}] {tool} unavailable")

    def after(self, tool: str):
        n = self._fired.get(tool, 0)
        if self.kind == "ack_timeout_once" and tool == self.target and n == 0:
            self._fired[tool] = n + 1
            raise TransientError(f"[fault:{self.profile}] acknowledgement of {tool} timed out")
