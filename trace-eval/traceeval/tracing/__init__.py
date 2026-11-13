"""Tracing of eval runs: ``recorder`` collects the events the SUT emits during a run, ``codecov`` records which
SUT functions and lines each test executed, and ``otel`` exports a run's trace as OpenTelemetry spans (OTLP JSON)."""

from .recorder import TraceRecorder

__all__ = ["TraceRecorder"]
