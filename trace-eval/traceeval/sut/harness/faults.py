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
    """Fires the failures of one fault profile at the tool boundary.

    The dispatcher calls ``before`` just before a tool runs and ``after`` just after it returned. Both
    raise TransientError when the profile says that this call fails, so the retry policy treats an
    injected fault exactly like a real outage.
    """

    def __init__(self, profile: str = "healthy"):
        self.profile = profile or "healthy"  # e.g. "transient_once:publish_page"; empty or None means healthy
        # Split the profile into the fault kind and the tool it hits. "healthy", and any kind this class
        # does not know, never fires.
        self.kind, _, self.target = self.profile.partition(":")
        self._fired: dict[str, int] = {}  # tool name -> how many faults have fired for it so far

    def before(self, tool: str):
        """Called just before ``tool`` runs. Fails the first call of the target tool under
        ``transient_once`` and every call under ``permanent_down``; either way the tool has not run, so
        repeating the call is safe."""
        n = self._fired.get(tool, 0)
        # A one-off timeout: only the first call fails, so a single retry gets through.
        if self.kind == "transient_once" and tool == self.target and n == 0:
            self._fired[tool] = n + 1
            raise TransientError(f"[fault:{self.profile}] {tool} timed out before execution")
        # The tool is down for good: every call fails, and retrying cannot help.
        if self.kind == "permanent_down" and tool == self.target:
            self._fired[tool] = n + 1
            raise TransientError(f"[fault:{self.profile}] {tool} unavailable")

    def after(self, tool: str):
        """Called right after ``tool`` returned. Under ``ack_timeout_once`` the first call of the target
        tool that completes reports a timeout although its change has already been made, so a retry without
        an idempotency key makes the change a second time."""
        n = self._fired.get(tool, 0)
        # This point is reached only when the tool returned normally, so its work is already done; only
        # the acknowledgement is lost.
        if self.kind == "ack_timeout_once" and tool == self.target and n == 0:
            self._fired[tool] = n + 1
            raise TransientError(f"[fault:{self.profile}] acknowledgement of {tool} timed out")
