"""Tracing of eval runs: ``recorder`` collects the events the SUT emits during a run, and ``codecov`` records
which SUT functions and lines each test executed."""

from .recorder import TraceRecorder

__all__ = ["TraceRecorder"]
