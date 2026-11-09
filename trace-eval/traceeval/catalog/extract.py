"""Draft the catalog of properties with a model, from the application's requirements (docs/AEM_ALIGNMENT.md).

``traceeval properties draft`` asks a model (the llm backend: Qwen by default) twice:

1. **The catalog.** The model reads only the requirements: the skills' rules (prose and procedure), the agents'
   definitions, the configuration (guards such as ``requires_approval``) and the specs. It proposes at most
   ``max_properties`` properties, each in one of the fixed ``CATEGORIES``, checked in one of the fixed
   ``CHECKED_BY`` ways, with the components it comes from as sources. Tests play no part here.
2. **The tags.** For each test (and each dataset), from its request and expectations, at most ``per_test`` ids of
   that catalog: the properties the test actually checks.

The code enforces the limits and the fixed lists, whatever the model answers. Thresholds and the mandatory flag
are policy, not extracted: a new property gets the defaults of its category, and an entry already in
``properties.yaml`` keeps its wording, thresholds and flag. The result is a draft (``properties.draft.yaml`` and a
report, ``properties.draft.md``) that a person edits; ``traceeval properties apply`` then writes
``properties.yaml`` and the tags in the test files. The model's answers can be saved and replayed, so a draft is
reproducible without a model.
"""

import json
import re
from pathlib import Path

import yaml

from traceeval.mutation.changeset import _flatten, _skill_parts
from traceeval.spec.draft import parse_answer
from traceeval.sut import SUT_ROOT

from .loader import CATALOG_ROOT, load_catalog, load_properties

# The fixed lists the model must choose from (documented in docs/USER_GUIDE.md and properties.yaml).
CATEGORIES = ("correctness", "safety", "resilience", "orchestration", "efficiency", "quality")
CHECKED_BY = ("state", "trace", "judge", "dataset")
# Policy defaults for a new property, by category: (mandatory, threshold).
DEFAULTS = {
    "safety": (True, 1.0),
    "correctness": (False, 0.95),
    "resilience": (False, 0.95),
    "orchestration": (False, 0.95),
    "efficiency": (False, 0.9),
    "quality": (False, 0.9),
}
MAX_PROPERTIES = 20  # the hard cap on --max: a larger catalog makes coverage meaningless
BATCH = 10  # tests tagged per model call


# ---------------------------------------------------------------------------- what the model reads
def requirements(sut: Path = SUT_ROOT, specs: Path | None = None) -> tuple[str, list[str]]:
    """The requirements as text, and the source ids a property may cite (the ids change sets use)."""
    specs = specs or Path(__file__).resolve().parents[1] / "specs"
    parts, ids = [], []
    for skill in sorted((sut / "skills").iterdir()):
        _, proc, prose = _skill_parts((skill / "SKILL.md").read_text(encoding="utf-8"))
        parts.append(f"## Skill {skill.name}\n{prose.strip()}\nProcedure:\n{proc.strip()}")
        ids += [f"skill:{skill.name}#prose", f"skill:{skill.name}#procedure"]
    for path in sorted((sut / "agents").glob("*.yaml")):
        agent = yaml.safe_load(path.read_text(encoding="utf-8"))
        parts.append(f"## Agent {agent['name']}\n{yaml.safe_dump(agent, sort_keys=False, width=110).strip()}")
        ids += [f"agent:{agent['name']}.{k}" for k in agent if k != "name"]
    config = (sut / "config" / "runtime.yaml").read_text(encoding="utf-8")
    parts.append(f"## Configuration (config/runtime.yaml)\n{config.strip()}")
    ids += [f"config:{k}" for k in _flatten(yaml.safe_load(config))]
    for path in sorted(specs.glob("FS-*.yaml")):
        spec = yaml.safe_load(path.read_text(encoding="utf-8"))
        uses = ", ".join(sorted({c.get("use", "?") for c in spec.get("clauses", [])}))
        parts.append(f"## Spec {spec['id']}: {spec['title']}\n{spec['intent'].strip()}\nClause kinds: {uses}")
        ids.append(f"spec:{spec['id']}")
    return "\n\n".join(parts), ids


def catalog_messages(text: str, source_ids: list[str], existing: dict, max_properties: int) -> list[dict]:
    """The request for the catalog: the requirements, the allowed source ids, and the existing ids to reuse."""
    system = (
        "You derive a catalog of behavioural properties for an agent platform from its requirements. A property is "
        "a requirement that tests can check, such as 'a page with broken links is never published'. Rules:\n"
        f"- At most {max_properties} properties: group related rules into one property instead of listing each rule.\n"
        f"- category: exactly one of {', '.join(CATEGORIES)}.\n"
        f"- checked_by: a non-empty subset of {', '.join(CHECKED_BY)} (state = the final application state, trace = "
        "the tool calls and agents, judge = a model reads the answer, dataset = prompt -> expected item).\n"
        "- id: snake_case. Reuse an existing id when an existing property already covers the requirement.\n"
        "- description: one plain sentence. sources: ids from the list of sources, where the requirement is stated.\n"
        'Answer with JSON only: {"properties": [{"id": ..., "category": ..., "description": ..., '
        '"checked_by": [...], "sources": [...]}]}'
    )
    user = (
        f"{text}\n\n## Sources you may cite\n{', '.join(source_ids)}\n\n"
        f"## Existing property ids\n{', '.join(existing) or '(none)'}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def tag_messages(entries: dict[str, str], props: dict, per_test: int) -> list[dict]:
    """The request for the tags of a batch of tests (id -> what the test asks and expects)."""
    catalog = "\n".join(f"- {p['id']}: {p['description']}" for p in props.values())
    system = (
        f"For each test, list the ids of the properties it checks: at most {per_test}, only from the catalog, and only "
        "properties its expectations actually check. "
        'Answer with JSON only: {"tags": {"<test id>": ["<property id>", ...]}}'
    )
    tests = "\n\n".join(f"### {tid}\n{desc}" for tid, desc in entries.items())
    return [{"role": "system", "content": system}, {"role": "user", "content": f"## Catalog\n{catalog}\n\n{tests}"}]


def test_entries(root: Path = CATALOG_ROOT) -> dict[str, str]:
    """What each test (or dataset: its items share their properties) asks and expects, briefly."""
    out = {}
    for case in load_catalog(root):
        key = case.dataset or case.id
        if key in out:  # a dataset is described once, by its first item
            continue
        exp = json.dumps(case.expect, default=str)[:600]
        judge = f"\nJudge rubric: {case.judge['rubric']}" if case.judge else ""
        out[key] = f"Request: {case.request}\nFault profile: {case.fault_profile}\nExpectations: {exp}{judge}"
    return out


# ---------------------------------------------------------------------------- checking the answers
def check_catalog(answer: dict, source_ids: list[str], existing: dict, max_properties: int):
    """The proposed properties after the code's checks, merged with the existing catalog, and the notes."""
    notes, out = [], {}
    for raw in answer.get("properties", []):
        pid = str(raw.get("id", "")).strip()
        if not re.fullmatch(r"[a-z][a-z0-9_]*", pid) or pid in out:
            notes.append(f"dropped: bad or repeated id {pid!r}")
            continue
        if raw.get("category") not in CATEGORIES:
            notes.append(f"dropped {pid}: category {raw.get('category')!r} is not in the fixed list")
            continue
        checked = [c for c in raw.get("checked_by", []) if c in CHECKED_BY]
        if not checked:
            notes.append(f"dropped {pid}: no valid checked_by")
            continue
        sources = [s for s in raw.get("sources", []) if s in source_ids]
        if len(sources) < len(raw.get("sources", [])):
            notes.append(f"{pid}: unknown sources left out")
        if pid in existing:  # a person's entry keeps its wording, thresholds and flag; it may gain sources
            entry = dict(existing[pid])
            entry["sources"] = entry.get("sources") or sources
        else:
            mandatory, threshold = DEFAULTS[raw["category"]]
            entry = {
                "id": pid,
                "category": raw["category"],
                "description": str(raw.get("description", "")).strip(),
                "checked_by": checked,
                "mandatory": mandatory,
                "threshold": threshold,
                "sources": sources,
            }
        out[pid] = entry
    # The limit caps the final catalog: a person's entries always stay, new ones fill the room that is left.
    room = max(0, max_properties - len(existing))
    for pid in [p for p in out if p not in existing][room:]:
        notes.append(f"dropped {pid}: over the limit of {max_properties} properties")
        del out[pid]
    for pid, entry in existing.items():
        if pid not in out:
            out[pid] = dict(entry)
            notes.append(f"kept {pid}: in properties.yaml but not proposed by the model")
    return out, notes


def check_tags(answer: dict, entries: dict, props: dict, per_test: int) -> tuple[dict, list[str]]:
    """The tags after the code's checks: known tests only, known properties only, at most per_test each."""
    notes, out = [], {}
    for tid, tags in (answer.get("tags") or {}).items():
        if tid not in entries:
            notes.append(f"tags for unknown test {tid} left out")
            continue
        known = [t for t in dict.fromkeys(tags) if t in props]
        if len(known) < len(tags):
            notes.append(f"{tid}: unknown or repeated properties left out")
        out[tid] = known[:per_test]
        if len(known) > per_test:
            notes.append(f"{tid}: kept the first {per_test} of {len(known)} properties")
    return out, notes


# ---------------------------------------------------------------------------- the whole flow
def call(client, model: str, messages: list[dict]) -> str:
    """One greedy chat completion."""
    resp = client.chat.completions.create(model=model, messages=messages, temperature=0.0, max_tokens=4000)
    return resp.choices[0].message.content or ""


def draft(
    root: Path = CATALOG_ROOT,
    max_properties: int = 15,
    per_test: int = 5,
    fresh: bool = False,
    replay: Path | None = None,
    save_response: Path | None = None,
    client=None,
) -> dict:
    """Draft the catalog and the tags; write properties.draft.yaml and properties.draft.md next to the catalog.
    ``fresh`` starts from an empty catalog instead of keeping the entries of properties.yaml."""
    if not 1 <= max_properties <= MAX_PROPERTIES:
        raise ValueError(f"--max must be between 1 and {MAX_PROPERTIES}")
    root = Path(root)
    existing = {} if fresh else {p.id: dict(vars(p)) for p in load_properties(root).values()}
    text, source_ids = requirements()
    entries = test_entries(root)
    batches = [dict(list(entries.items())[i : i + BATCH]) for i in range(0, len(entries), BATCH)]
    saved = json.loads(Path(replay).read_text()) if replay else None
    if client is None and saved is None:
        from traceeval.llm.chat import shared_client

        client = shared_client("llm")
    model = getattr(client, "model_id", "")
    answers = {"catalog": None, "tags": []}
    answers["catalog"] = (
        saved["catalog"] if saved else call(client, model, catalog_messages(text, source_ids, existing, max_properties))
    )
    props, notes = check_catalog(parse_answer(answers["catalog"]), source_ids, existing, max_properties)
    tags = {}
    for i, batch in enumerate(batches):
        reply = saved["tags"][i] if saved else call(client, model, tag_messages(batch, props, per_test))
        answers["tags"].append(reply)
        got, more = check_tags(parse_answer(reply), batch, props, per_test)
        tags.update(got)
        notes += more
    if save_response:
        Path(save_response).write_text(json.dumps(answers, indent=1), encoding="utf-8")
    out = root / "properties.draft.yaml"
    out.write_text(
        yaml.safe_dump({"properties": list(props.values()), "tags": tags}, sort_keys=False, width=110), encoding="utf-8"
    )
    report = write_report(root, props, tags, existing, entries, notes)
    return {"draft": out, "report": report, "properties": props, "tags": tags, "notes": notes}


def write_report(root: Path, props: dict, tags: dict, existing: dict, entries: dict, notes: list[str]) -> Path:
    """properties.draft.md: the proposed catalog, the properties no test checks, the tags that would change."""
    current = {c.dataset or c.id: c.properties for c in load_catalog(root)}
    tested = {p for ts in tags.values() for p in ts}
    lines = [
        "# Draft catalog of properties",
        "",
        "Review and edit `properties.draft.yaml`, then run `traceeval properties apply`.",
        "",
        "| property | category | new? | mandatory | threshold | sources |",
        "|---|---|---|---|---|---|",
    ]
    for p in props.values():
        lines.append(
            f"| `{p['id']}` | {p['category']} | {'' if p['id'] in existing else 'new'} | "
            f"{'yes' if p['mandatory'] else ''} | {p['threshold']} | {', '.join(p.get('sources', []))} |"
        )
    untested = [p for p in props if p not in tested]
    lines += ["", f"**Required but checked by no test** ({len(untested)}): {', '.join(untested) or 'none'}", ""]
    changed = [t for t in entries if sorted(tags.get(t, [])) != sorted(current.get(t, []))]
    lines += [f"**Tests whose properties would change** ({len(changed)} of {len(entries)}):", ""]
    lines += [f"- `{t}`: {current.get(t, [])} -> {tags.get(t, [])}" for t in changed]
    if notes:
        lines += ["", "## Notes from the checks", ""] + [f"- {n}" for n in notes]
    out = root / "properties.draft.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def apply(root: Path = CATALOG_ROOT) -> dict:
    """Write properties.yaml from the draft, and each test's (and dataset's) properties line in the test files."""
    root = Path(root)
    doc = yaml.safe_load((root / "properties.draft.yaml").read_text(encoding="utf-8"))
    target = root / "properties.yaml"
    # keep the explanatory comments at the top of properties.yaml
    old = target.read_text(encoding="utf-8").split("\n") if target.exists() else []
    header = "\n".join(line for line in old[: next((i for i, s in enumerate(old) if s.startswith("-")), 0)])
    body = yaml.safe_dump(doc["properties"], sort_keys=False, width=110)
    target.write_text((header.rstrip() + "\n\n" if header.strip() else "") + body, encoding="utf-8")
    # The test files are rewritten line by line rather than through a YAML dump, so that their comments and
    # layout survive. Two conventions make that safe: every test starts with "- id: X" at column 0 (a dataset
    # file has one top-level "id: X"), and a properties line is always written on one line as "properties: [...]".
    # The current id is remembered until the next one, and its properties line is replaced when the draft tags it.
    tags, written = doc.get("tags", {}), 0
    for path in sorted((root / "tests").glob("*.yaml")) + sorted((root / "datasets").glob("*.yaml")):
        lines, current = path.read_text(encoding="utf-8").split("\n"), None
        for i, line in enumerate(lines):
            m = re.match(r"^(?:- )?id: (\S+)", line)
            # Only a test's own id counts: an indented "- id:" inside an expectation block is not a test.
            if m and (line.startswith("- ") or path.parent.name == "datasets"):
                current = m.group(1)
            hit = re.match(r"^(\s*)properties: \[.*\]$", line)
            if hit and current in tags:
                lines[i] = f"{hit.group(1)}properties: [{', '.join(tags[current])}]"
                written += 1
        path.write_text("\n".join(lines), encoding="utf-8")
    load_catalog(root)  # fails at once if a tag names a property the catalog lacks
    return {"properties": len(doc["properties"]), "tags_written": written}
