"""In-memory application state loaded from a JSON fixture, with audit log and idempotency support."""

import copy
import hashlib
import json
from pathlib import Path


class State:
    def __init__(self, data: dict):
        self.data = data
        self.data.setdefault("audit", [])
        self.data.setdefault("translation_jobs", {})
        self.data.setdefault("reviews", {})
        self._idem: dict[str, dict] = {}
        self._clock = 0

    # ---------------------------------------------------------------- loading / snapshots
    @classmethod
    def from_fixture(cls, path: str | Path) -> "State":
        with open(path) as fh:
            return cls(json.load(fh))

    def snapshot(self) -> dict:
        return copy.deepcopy(self.data)

    def digest(self) -> str:
        canon = json.dumps(self.data, sort_keys=True, default=str).encode()
        return hashlib.sha256(canon).hexdigest()[:16]

    def tick(self) -> int:
        self._clock += 1
        return self._clock

    # ---------------------------------------------------------------- audit / idempotency
    def audit(self, action: str, actor: str | None, **fields):
        entry = {"seq": self.tick(), "action": action, "actor": actor}
        entry.update(fields)
        self.data["audit"].append(entry)
        return entry

    def audit_count(self, action: str, **match) -> int:
        n = 0
        for e in self.data["audit"]:
            if e["action"] != action:
                continue
            if all(e.get(k) == v for k, v in match.items()):
                n += 1
        return n

    def idempotent(self, key: str | None):
        """Return a cached result for an idempotency key (or None when unknown / no key given)."""
        if key is None:
            return None
        return self._idem.get(key)

    def remember(self, key: str | None, result: dict):
        if key is not None:
            self._idem[key] = result
        return result

    # ---------------------------------------------------------------- accessors
    @property
    def users(self) -> dict:
        return self.data["users"]

    @property
    def pages(self) -> dict:
        return self.data["pages"]

    @property
    def assets(self) -> dict:
        return self.data["assets"]
