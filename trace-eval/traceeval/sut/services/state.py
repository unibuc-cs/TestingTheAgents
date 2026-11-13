"""In-memory application state loaded from a JSON fixture, with audit log and idempotency support."""

import copy
import hashlib
import json
from pathlib import Path


class State:
    """All the data of the platform, held in memory, together with a logical clock and the idempotency cache.

    ``data`` is the fixture's JSON document (``fixtures/base.json``), and the services change it in place.
    Its top-level keys:

        users              user id -> {"name", "roles", and "approval_token" for a user who may approve
                           guarded operations}
        pages              page id -> page record (``repository.create_page`` lists its fields)
        assets             asset id -> {"name", "folder", "mime", "uploaded_by"}
        external_links     external URL -> its last known reachability, "ok" or "broken"
        consents           data subject id -> True when the subject has consented to processing
        consent_purposes   data subject id -> the purposes the subject has consented to
        data_subjects      data subject id -> {"email", "records"}, the personal data held about the subject
        translation_jobs   job id -> {"page_id", "locales", "status", "requested_by"}
        reviews            page id -> every review request made for the page, oldest first; an entry is
                           never updated or removed afterwards
        audit              the audit log, oldest entry first (see ``audit``)
        today              the platform's current date, as an ISO date string
    """

    def __init__(self, data: dict):
        self.data = data  # used as it is, not copied: the services change this very dict
        # A fixture may leave out the collections that only fill up while requests run; make sure they exist.
        self.data.setdefault("audit", [])
        self.data.setdefault("translation_jobs", {})
        self.data.setdefault("reviews", {})
        self._idem: dict[str, dict] = {}  # idempotency key -> the result of the first call made with that key
        self._clock = 0  # the logical clock behind tick(); every state starts at 0
        self._requests = 0  # requests started against this state so far, behind next_request_id()

    # ---------------------------------------------------------------- loading / snapshots
    @classmethod
    def from_fixture(cls, path: str | Path) -> "State":
        """Load a state from a JSON fixture file such as ``fixtures/base.json``."""
        with open(path) as fh:
            return cls(json.load(fh))

    def snapshot(self) -> dict:
        """A deep copy of the data as it is now, unaffected by later changes (for example the data as it was
        before a request ran). The idempotency cache, the clock and the request counter are not part of it."""
        return copy.deepcopy(self.data)

    def digest(self) -> str:
        """A short fingerprint of the data: the first 16 hex digits of a SHA-256 over its JSON form with sorted
        keys, so equal data gives an equal digest whatever the order of the keys. Values that JSON cannot
        represent are written with ``str()``."""
        canon = json.dumps(self.data, sort_keys=True, default=str).encode()
        return hashlib.sha256(canon).hexdigest()[:16]

    def tick(self) -> int:
        """Advance the logical clock by one and return the new value (1, 2, 3, ...).

        The platform has no wall clock. Whatever needs an order or a time (audit sequence numbers, review
        requests, the ``published_at`` of a page, export ids) takes the next tick instead, so that a run
        can be reproduced exactly."""
        self._clock += 1
        return self._clock

    def next_request_id(self) -> str:
        """The id of a new request: ``req-1``, ``req-2``, ... The idempotency keys of a request's writes are
        derived from it. Numbering requests here, where the idempotency cache lives, keeps keys unique among
        all the requests that share the cache, and gives the same ids each time the same requests run."""
        self._requests += 1
        return f"req-{self._requests}"

    # ---------------------------------------------------------------- audit / idempotency
    def audit(self, action: str, actor: str | None, **fields):
        """Append an entry to the audit log and return it.

        An entry holds ``seq`` (the next clock tick), ``action``, ``actor`` and the details passed as keyword
        arguments, such as ``page_id``. ``actor`` is the user who acted, or None when the caller has no user
        to name."""
        entry = {"seq": self.tick(), "action": action, "actor": actor}
        entry.update(fields)
        self.data["audit"].append(entry)
        return entry

    def audit_count(self, action: str, **match) -> int:
        """The number of audit entries for ``action`` whose fields equal every value given in ``match``; for
        example, ``audit_count("publish_page", page_id="p1")`` counts how many times p1 was published."""
        n = 0
        for e in self.data["audit"]:
            if e["action"] != action:
                continue
            if all(e.get(k) == v for k, v in match.items()):
                n += 1
        return n

    def idempotent(self, key: str | None):
        """Return a cached result for an idempotency key (or None when unknown / no key given).

        A write service asks this first. A hit means that the same call already went through once and is
        now being retried, typically because its acknowledgement was lost on the way back; the service then
        returns the remembered result instead of applying the change again."""
        if key is None:
            return None
        return self._idem.get(key)

    def remember(self, key: str | None, result: dict):
        """Remember ``result`` as the answer for idempotency key ``key`` (when a key was given) and return it
        unchanged, so that a write service can store and return its answer in one step."""
        if key is not None:
            self._idem[key] = result
        return result

    # ---------------------------------------------------------------- accessors
    @property
    def users(self) -> dict:
        """User id -> user record (``name``, ``roles``, and ``approval_token`` for a user who may approve)."""
        return self.data["users"]

    @property
    def pages(self) -> dict:
        """Page id -> page record."""
        return self.data["pages"]

    @property
    def assets(self) -> dict:
        """Asset id -> asset record (``name``, ``folder``, ``mime``, ``uploaded_by``)."""
        return self.data["assets"]
