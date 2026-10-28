"""Runtime configuration with instrumented reads (every ``get`` is reported to the tracer)."""

from pathlib import Path

import yaml


class Config:
    def __init__(self, data: dict, tracer=None):
        self.data = data
        self.tracer = tracer
        self.reads: list[str] = []

    @classmethod
    def load(cls, path: str | Path, tracer=None, overrides: dict | None = None) -> "Config":
        with open(path) as fh:
            data = yaml.safe_load(fh) or {}
        cfg = cls(data, tracer)
        for key, value in (overrides or {}).items():
            cfg.set(key, value)
        return cfg

    def get(self, key: str, default=None):
        """Dotted-path lookup, e.g. ``publishing.require_review``. Reads are recorded."""
        node = self.data
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                node = default
                break
            node = node[part]
        self.reads.append(key)
        if self.tracer is not None:
            self.tracer.event("config.read", key=key, value=_short(node))
        return node

    def set(self, key: str, value):
        node = self.data
        parts = key.split(".")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value


def _short(value):
    s = str(value)
    return s if len(s) <= 60 else s[:57] + "..."
