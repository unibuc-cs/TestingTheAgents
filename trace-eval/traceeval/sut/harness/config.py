"""Runtime configuration with instrumented reads (every ``get`` is reported to the tracer)."""

from pathlib import Path

import yaml


class Config:
    """The runtime settings of the platform, read by dotted key such as ``runtime.max_tool_calls``.

    Every read through ``get`` is reported to the tracer as a ``config.read`` event, so the trace of a run
    lists the settings it depended on, and a change to a setting can be matched to the runs that read it.
    Reading ``data`` directly bypasses that recording.
    """

    def __init__(self, data: dict, tracer=None):
        self.data = data  # the nested settings, as parsed from the YAML file
        self.tracer = tracer  # receives a "config.read" event per read; None turns the recording off

    @classmethod
    def load(cls, path: str | Path, tracer=None, overrides: dict | None = None) -> "Config":
        """Read the settings from a YAML file and apply ``overrides`` on top. Overrides are keyed by dotted
        path as well, replace single values, and are not reported as reads."""
        # An empty file is an empty configuration.
        with open(path) as fh:
            data = yaml.safe_load(fh) or {}
        cfg = cls(data, tracer)
        for key, value in (overrides or {}).items():
            cfg.set(key, value)
        return cfg

    def get(self, key: str, default=None):
        """Dotted-path lookup, e.g. ``publishing.require_review``. Reads are recorded.

        ``default`` is returned when the path does not exist. The read is recorded either way, with the
        value returned: a run that looked for a missing setting still depends on it.
        """
        # Walk down the nested sections one part of the key at a time. A missing part, or a value along
        # the way that is not a section, ends the walk with the default.
        node = self.data
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                node = default
                break
            node = node[part]
        # Record the read, also when the default was returned.
        if self.tracer is not None:
            self.tracer.event("config.read", key=key, value=_short(node))
        return node

    def set(self, key: str, value):
        """Set the value at a dotted key, creating the sections on the way when they are missing. Unlike
        ``get``, this is not traced."""
        node = self.data
        parts = key.split(".")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value


def _short(value):
    """The value as text, cut to 60 characters, so that config events stay small in the trace."""
    s = str(value)
    return s if len(s) <= 60 else s[:57] + "..."
