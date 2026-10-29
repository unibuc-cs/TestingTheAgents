"""Spec and clause data model, the clause catalog, and the clause result type.

A spec file (``traceeval/specs/FS-*.yaml``) is prose intent plus clauses. A clause is normally written
against the catalog (``catalog.yaml``)::

    - use: setting_in_range
      with: {key: publishing.review_max_age_days, min: 1, max: 365, value: 30}
      require: L4            # optional; the template has a default

``load_spec`` expands it into the fields the checker of that kind understands, generates its id
(``<template>:<first slot value>``) and its one-line text (the template's gloss). A clause may also be
written in expanded form (``kind: ...`` plus the checker fields), which is what the catalog produces.
``validate_spec`` checks slot values against the product model before anything runs.
"""

import ast
import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml

SPECS_ROOT = Path(__file__).resolve().parent.parent / "specs"
CATALOG_PATH = Path(__file__).resolve().parent / "catalog.yaml"

KINDS = ("setting", "contract", "trace", "example", "placement")

RUNG_LABEL = {
    "L0": "reviewed",
    "L1": "example-tested",
    "L2": "property-tested",
    "L3": "monitored",
    "L4": "statically checked",
    "L5": "proven",
}
RUNG_ORDER = {r: i for i, r in enumerate(RUNG_LABEL)}


def load_catalog(path: Path | str = CATALOG_PATH) -> dict:
    return yaml.safe_load(Path(path).read_text())


@dataclass
class Clause:
    id: str
    kind: str
    text: str = ""  # one-line human reading of the clause
    data: dict = field(default_factory=dict)  # kind-specific fields, as the checker expects them
    require: str = "L1"  # rung the clause must reach for the PR to be accepted without a gap
    template: str | None = None  # catalog template it was expanded from
    slots: dict = field(default_factory=dict)  # the slot values as written (for validation and rendering)

    def __getitem__(self, key):
        return self.data[key]

    def get(self, key, default=None):
        return self.data.get(key, default)


@dataclass
class Spec:
    id: str
    title: str
    intent: str
    clauses: list[Clause]
    owner: str = ""
    path: Path | None = None

    def clause(self, cid: str) -> Clause:
        for c in self.clauses:
            if c.id == cid:
                return c
        raise KeyError(cid)


@dataclass
class ClauseResult:
    clause_id: str
    kind: str
    rung: str  # rung reached (pass) or attempted (fail)
    status: str  # pass | fail | gap | skipped
    summary: str
    details: list[str] = field(default_factory=list)
    cost: dict = field(default_factory=dict)  # runs, examples, seconds
    required: str = "L1"

    @property
    def meets_required(self) -> bool:
        return RUNG_ORDER[self.rung] >= RUNG_ORDER[self.required]

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        d["meets_required"] = self.meets_required
        return d


# ---------------------------------------------------------------------------- expanding catalog clauses
def expand_clause(raw: dict, catalog: dict) -> Clause:
    """Turn ``{use, with, require?, id?, text?}`` into a Clause; an expanded clause (``kind: ...``) passes through."""
    if "use" not in raw:
        kind = raw["kind"]
        if kind not in KINDS:
            raise ValueError(f"unknown clause kind {kind!r} (clause {raw.get('id')})")
        data = {k: v for k, v in raw.items() if k not in ("id", "kind", "text", "require")}
        return Clause(str(raw["id"]), kind, raw.get("text", ""), data, raw.get("require", "L1"))
    name = raw["use"]
    if name not in catalog:
        raise ValueError(f"unknown catalog template {name!r}")
    t = catalog[name]
    given = dict(raw.get("with") or {})
    optional = set(t.get("optional", []))
    missing = [s for s in t["slots"] if s not in given and s not in optional]
    unknown = [s for s in given if s not in t["slots"]]
    if missing or unknown:
        raise ValueError(f"template {name}: missing slots {missing}, unknown slots {unknown}")
    data = _prune(_substitute(t["clause"], given))
    first = given.get(next(iter(t["slots"])))
    cid = raw.get("id") or f"{name}:{_short(first)}"
    text = raw.get("text") or _gloss(t["gloss"], given)
    return Clause(cid, t["kind"], text, data, raw.get("require", t.get("require", "L1")), name, given)


def _substitute(node, slots: dict):
    """Replace "{slot}" placeholders: a bare "{slot}" keeps the value's type, embedded ones are formatted."""
    if isinstance(node, dict):
        return {_substitute(k, slots): _substitute(v, slots) for k, v in node.items()}
    if isinstance(node, list):
        return [_substitute(v, slots) for v in node]
    if isinstance(node, str) and node.startswith("{") and node.endswith("}") and node.count("{") == 1:
        return slots.get(node[1:-1])
    if isinstance(node, str) and "{" in node:
        return node.format(**{k: _render(v) for k, v in slots.items()})
    return node


def _prune(node):
    """Drop keys whose slot was not given (None) and dicts left empty by that."""
    if isinstance(node, dict):
        out = {k: _prune(v) for k, v in node.items() if v is not None}
        return {k: v for k, v in out.items() if not (isinstance(v, dict) and not v)}
    if isinstance(node, list):
        return [_prune(v) for v in node]
    return node


def _render(value) -> str:
    if isinstance(value, list):
        return ", ".join(_render(v) for v in value)
    if isinstance(value, dict):
        if "request" in value:
            return repr(value["request"])
        if len(value) == 1:
            ((k, v),) = value.items()
            return f"{k} {_render(v)}"
        return json.dumps(value)
    return str(value)


def _short(value) -> str:
    if isinstance(value, dict):
        words = str(value.get("request", "inline")).lower().split()[:4]
        return "-".join("".join(ch for ch in w if ch.isalnum()) for w in words)
    if isinstance(value, list):
        return "+".join(str(v) for v in value)
    s = str(value)
    return s.split("::")[-1] if "::" in s else s


def _gloss(gloss: str, slots: dict) -> str:
    class Default(dict):
        def __missing__(self, key):
            return "-"

    return gloss.format_map(Default({k: _render(v) for k, v in slots.items()}))


# ---------------------------------------------------------------------------- loading
def load_spec(path: Path | str, catalog: dict | None = None) -> Spec:
    path = Path(path)
    catalog = catalog or load_catalog()
    raw = yaml.safe_load(path.read_text())
    clauses, seen = [], {}
    for c in raw.get("clauses", []):
        try:
            clause = expand_clause(c, catalog)
        except ValueError as exc:
            raise ValueError(f"{path.name}: {exc}") from None
        seen[clause.id] = seen.get(clause.id, 0) + 1
        if seen[clause.id] > 1:
            clause.id = f"{clause.id}#{seen[clause.id]}"
        clauses.append(clause)
    return Spec(raw["id"], raw["title"], raw.get("intent", "").strip(), clauses, raw.get("owner", ""), path)


def load_specs(root: Path | str = SPECS_ROOT, ids: list[str] | None = None) -> list[Spec]:
    catalog = load_catalog()
    specs = [load_spec(p, catalog) for p in sorted(Path(root).glob("FS-*.yaml"))]
    if ids:
        specs = [s for s in specs if s.id in ids]
    return specs


# ---------------------------------------------------------------------------- validation against the product model
def validate_spec(spec: Spec, model, catalog: dict | None = None) -> list[tuple[str, str]]:
    """Check slot values against the product model. Returns (level, message) pairs: 'error' for names that
    cannot be right (an unknown tool, case, skill or directory, an expression that does not parse) and
    'note' for names the current system does not have yet (a function or config key the request introduces)."""
    catalog = catalog or load_catalog()
    out: list[tuple[str, str]] = []
    tools = model.tools_static()
    skills = {rel.split("/")[1] for rel in model.files if rel.startswith("skills/") and rel.endswith("SKILL.md")}
    for c in spec.clauses:
        if not c.template:
            continue
        for slot, stype in catalog[c.template]["slots"].items():
            if slot not in c.slots:
                continue
            v = c.slots[slot]
            where = f"{c.id} ({slot})"
            if stype == "config_key" and model.config_value(v) is None:
                out.append(
                    ("note", f"{where}: config key {v} is not in the current configuration - the request introduces it")
                )
            elif stype == "function":
                rel, _, fn = str(v).partition("::")
                if rel not in model.functions:
                    out.append(("error", f"{where}: file {rel} does not exist"))
                elif fn not in {q for q, _, _ in model.functions[rel]}:
                    out.append(("note", f"{where}: {v} is not in the current code - the request introduces it"))
            elif stype == "file" and v not in model.files:
                out.append(("error", f"{where}: file {v} does not exist"))
            elif stype in ("tool", "tools"):
                for tname in v if isinstance(v, list) else [v]:
                    if tname not in tools and tname not in _AUDIT_ONLY_ACTIONS:
                        out.append(("error", f"{where}: unknown tool {tname}"))
            elif stype == "skill" and v not in skills:
                out.append(("error", f"{where}: unknown skill {v}"))
            elif stype == "case":
                if isinstance(v, str) and v not in model.catalog_ids:
                    out.append(("error", f"{where}: unknown catalog case {v}"))
                if isinstance(v, dict) and not ({"agent", "request"} <= set(v)):
                    out.append(("error", f"{where}: an inline case needs agent and request"))
            elif stype == "dirs":
                for d in v if isinstance(v, list) else [v]:
                    if not any(rel == d or rel.startswith(d.rstrip("/") + "/") for rel in model.files):
                        out.append(("error", f"{where}: {d} matches no file"))
            elif stype == "expr":
                try:
                    ast.parse(str(v), mode="eval")
                except SyntaxError as exc:
                    out.append(("error", f"{where}: expression does not parse ({exc.msg})"))
            elif stype == "inputs" and not all(t in ("int", "bool", "str") for t in dict(v).values()):
                out.append(("error", f"{where}: input types must be int, bool or str"))
    return out


_AUDIT_ONLY_ACTIONS = {"validate_links", "publish_refused", "approval_used"}
