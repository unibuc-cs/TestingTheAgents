"""Draft a spec from a prose change request with an LLM, constrained by the catalog and the product model.

    traceeval sdd draft --request request.md --id FS-0106 [--out traceeval/specs/FS-0106.draft.yaml]
                        [--replay response.json] [--save-response response.json]

The model receives three things: the clause catalog (templates, slots, glosses), a slice of the product
model (tools and the services behind them, configuration keys, skills and the tools they call, the
code paths that change a page status, the catalog cases), and the request. It must answer with JSON
``{title, intent, clauses: [{use, with, require?}]}`` - template names and slot values only, so it
cannot write free text into the spec. The answer is expanded through the catalog, validated against the
product model, and written as a draft spec plus a plain-language rendering for the owner to review,
edit and confirm (rename ``.draft.yaml`` to ``.yaml``).

``--replay`` uses a saved model answer instead of calling the endpoint (for demos without a model);
``--save-response`` saves the live answer for that purpose. The endpoint is configured like the LLM
backend: TRACEEVAL_LLM_BASE_URL, TRACEEVAL_LLM_API_KEY, TRACEEVAL_LLM_MODEL.
"""

import json
import re
from pathlib import Path

import yaml

from .model import CATALOG_PATH, Spec, expand_clause, load_catalog, validate_spec

HELPERS = (
    "config('dotted.key') -> the configured value; "
    "approval_age(run, page_id) -> days since the page's approval; "
    "expected_broken(run, page_id) -> broken links computed independently; "
    "audit_count(run, action, **fields) -> number of matching audit entries; "
    "applied(run, tool) -> True when the run called the tool successfully; "
    "token_owner(run, token) -> user id owning an approval token, or None; "
    "title_of_length(n) -> a title of n characters; "
    "first_case_calling(tool) -> id of a recorded case that calls the tool; "
    "baseline_run(test_id) -> the baseline record of a case. "
    "In `where` expressions: event.tool, event.args.<name>, event.status ('ok'/'error'), event.idempotency_key, "
    "event.approved_by; audit entries: event.action, event.page_id, event.version, event.broken; "
    "run.context.<key>, run.passed, run.test_id."
)


# ---------------------------------------------------------------------------- what the model sees
def product_slice(model, catalog_cases: dict) -> str:
    """A compact, factual description of the current system: the only names a draft may use."""
    tools = model.tools_static()
    lines = ["## Tools (name: kind, adapter -> service functions)"]
    for name, (kind, rel, _) in sorted(tools.items()):
        services = [f"{f}::{','.join(fns)}" for f, fns in model.locate([name]).items() if f.startswith("services/")]
        lines.append(f"- {name}: {kind}, {rel} -> {' '.join(services) or '-'}")
    lines.append("\n## Configuration keys (current values)")
    for key, value in _flatten(model.config).items():
        lines.append(f"- {key} = {value!r}")
    lines.append("\n## Skills (tools their procedure calls)")
    for rel in sorted(model.files):
        if rel.startswith("skills/") and rel.endswith("SKILL.md"):
            skill = rel.split("/")[1]
            calls = sorted(
                {s.get("call") for s in model.skill_procedure(skill) if isinstance(s, dict) and s.get("call")}
            )
            lines.append(f"- {skill}: {', '.join(calls) or '-'}")
    lines.append("\n## Code paths that change a page status (service function -> tool)")
    for tool, fns in model.status_setters().items():
        lines.append(f"- {', '.join(fns)} -> {tool}")
    lines.append("\n## Recorded cases (id: name; tools called)")
    for tid, case in catalog_cases.items():
        rec = model.baseline_runs.get(tid, {})
        lines.append(f"- {tid}: {case.name}; {', '.join(sorted(set(rec.get('tools', []))))}")
    return "\n".join(lines)


def _flatten(node: dict, prefix: str = "") -> dict:
    out = {}
    for k, v in node.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(_flatten(v, key + "."))
        else:
            out[key] = v
    return out


def build_messages(request_text: str, catalog: dict, slice_text: str) -> list[dict]:
    templates = "\n".join(
        f"- {name}: kind {t['kind']}, slots {json.dumps(t['slots'])}"
        + (f", optional {t['optional']}" if t.get("optional") else "")
        + f', default required rung {t.get("require", "L1")}\n  reads: "{t["gloss"]}"'
        for name, t in catalog.items()
    )
    system = f"""You turn a change request for an agent-based content platform into a machine-checkable spec.

Answer with JSON only:
{{"title": str, "intent": str, "clauses": [{{"use": template, "with": {{slot: value}}, "require": "L<n>"}}]}}

Rules:
- "use" must be one of the catalog templates below; "with" must give exactly its slots (optional ones may be left out).
- Slot values must be names from the product model below (tool names, config keys, skills, case ids, file
  paths). A function or config key the request introduces may be new, but it must live in the right layer:
  business rules in services/<module>.py, numbers in config/runtime.yaml, never in tools/ or skills/.
- Expressions use Python syntax and only these helpers: {HELPERS}
- Cover the request from several angles: a setting for every number, a contract for every rule that is a
  pure function of its inputs (require L5 when it is plain arithmetic or comparisons), a trace rule for what
  must always or never happen at run time, two or three scenarios (a normal case, a refusal, a boundary),
  and placement rules saying where the code must live and what must not be hard-coded.
- The intent is two to four sentences restating the request; do not invent requirements.

## Catalog of clause templates
{templates}

## Product model (the current system)
{slice_text}
"""
    return [{"role": "system", "content": system}, {"role": "user", "content": f"Change request:\n\n{request_text}"}]


# ---------------------------------------------------------------------------- calling the model
def call_model(messages: list[dict], client=None, settings=None) -> str:
    """One chat completion; ``client`` may be any object with the OpenAI ``chat.completions.create`` shape."""
    if settings is None:
        from traceeval.sut.harness.backends.llm_openai import LLMSettings

        settings = LLMSettings()
    if client is None:
        from openai import OpenAI

        client = OpenAI(base_url=settings.base_url, api_key=settings.api_key)
    resp = client.chat.completions.create(model=settings.model, messages=messages, temperature=0.0, max_tokens=2500)
    return resp.choices[0].message.content or ""


def parse_answer(text: str) -> dict:
    """The JSON object in the model's answer (tolerates a ```json fence or prose around it)."""
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON object in the model's answer")
    return json.loads(m.group(0))


# ---------------------------------------------------------------------------- from answer to draft
def draft_from_answer(answer: dict, spec_id: str, catalog: dict | None = None) -> tuple[Spec, list[str]]:
    """Expand the answer's clauses; clauses that do not fit the catalog are dropped and reported."""
    catalog = catalog or load_catalog()
    clauses, problems = [], []
    for i, raw in enumerate(answer.get("clauses", []), 1):
        try:
            clauses.append(expand_clause(raw, catalog))
        except (ValueError, KeyError, TypeError) as exc:
            problems.append(f"clause {i} dropped: {exc} ({json.dumps(raw)[:120]})")
    seen: dict[str, int] = {}
    for c in clauses:
        seen[c.id] = seen.get(c.id, 0) + 1
        if seen[c.id] > 1:
            c.id = f"{c.id}#{seen[c.id]}"
    spec = Spec(spec_id, answer.get("title", spec_id), str(answer.get("intent", "")).strip(), clauses)
    return spec, problems


def write_draft(spec: Spec, answer: dict, notes: list[str], out: Path) -> tuple[Path, Path]:
    """Write <out> (the draft spec, in catalog form) and <out>.md (its plain-language rendering)."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "id": spec.id,
        "title": spec.title,
        "intent": spec.intent + "\n",
        "clauses": [
            {k: v for k, v in raw.items() if k in ("use", "with", "require")}
            for raw in answer.get("clauses", [])
            if "use" in raw
        ],
    }
    header = "# DRAFT - generated from a change request; review, edit, then rename to .yaml to confirm.\n"
    if notes:
        header += "".join(f"# {n}\n" for n in notes)
    out.write_text(header + yaml.dump(doc, Dumper=_Dumper, sort_keys=False, allow_unicode=True, width=110))
    md = [f"# {spec.id} (draft): {spec.title}", "", spec.intent, "", "## Clauses to confirm", ""]
    for i, c in enumerate(spec.clauses, 1):
        md.append(f"{i}. **{c.text}**  \n   `{c.id}` - {c.kind}, must reach {c.require}")
    if notes:
        md += ["", "## Notes from the checks before any run", ""] + [f"- {n}" for n in notes]
    md_path = out.with_suffix(".md")
    md_path.write_text("\n".join(md) + "\n")
    return out, md_path


class _Dumper(yaml.SafeDumper):
    """Multi-line strings (the intent) as readable ``|`` blocks."""


_Dumper.add_representer(
    str,
    lambda d, v: d.represent_scalar("tag:yaml.org,2002:str", v, style="|" if "\n" in v else None),
)


def draft(
    request_path: Path,
    spec_id: str,
    out: Path,
    model,
    catalog_cases: dict,
    *,
    replay: Path | None = None,
    save_response: Path | None = None,
    client=None,
    settings=None,
) -> dict:
    """The whole flow; returns {spec, problems, validation, draft, rendering, answer_text}."""
    catalog = load_catalog(CATALOG_PATH)
    request_text = Path(request_path).read_text()
    if replay:
        saved = json.loads(Path(replay).read_text())
        text = saved["content"] if isinstance(saved, dict) and "content" in saved else json.dumps(saved)
    else:
        text = call_model(build_messages(request_text, catalog, product_slice(model, catalog_cases)), client, settings)
        if save_response:
            Path(save_response).write_text(json.dumps({"content": text}, indent=1))
    spec, problems = draft_from_answer(parse_answer(text), spec_id, catalog)
    validation = [f"{level}: {msg}" for level, msg in validate_spec(spec, model, catalog)]
    draft_path, md_path = write_draft(spec, parse_answer(text), problems + validation, out)
    return {
        "spec": spec,
        "problems": problems,
        "validation": validation,
        "draft": draft_path,
        "rendering": md_path,
        "answer_text": text,
    }
