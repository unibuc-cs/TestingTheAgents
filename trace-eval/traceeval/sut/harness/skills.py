"""Skill loading. A skill is a SKILL.md with YAML front matter, prose instructions and a machine-readable
``## Procedure`` block. The simulated backend executes the procedure; a model reads it as numbered plain
steps (``render_procedure``), with included skills written out in place and settings shown with their
values. The procedure block is the canonical statement of the workflow, so a mutation of the procedure
changes the behaviour of *both* backends."""

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

# The YAML front matter: the block between the two "---" lines at the very top of the file.
_FRONT = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
# The YAML code block that follows the "## Procedure" heading.
_PROC = re.compile(r"## Procedure\s*```yaml\n(.*?)```", re.DOTALL)


@dataclass
class Skill:
    """One parsed skill: what its front matter declares, its full markdown text and its procedure."""

    name: str
    version: str  # from the front matter, always kept as a string ("0" when it is missing)
    description: str
    tools: list[str]  # tools the skill says it uses; what an agent may call is set by its own definition
    text: str  # full markdown (for the LLM backend)
    procedure: list[dict] = field(default_factory=list)  # one dict per step, include steps not yet expanded
    path: str = ""  # the SKILL.md it was read from; empty when no path was given

    @property
    def digest(self) -> str:
        """Short fingerprint of the full text (the first 12 hex digits of its SHA-256). Any edit, to the
        prose or to the procedure, changes it, so the trace shows exactly which version of a skill ran."""
        return hashlib.sha256(self.text.encode()).hexdigest()[:12]

    @property
    def token_estimate(self) -> int:
        """Rough size of the skill in tokens (about four characters per token, at least 1)."""
        return max(1, len(self.text) // 4)


class SkillLoader:
    """Reads skills from ``<skills_dir>/<name>/SKILL.md``, parses each file once and reports every load to
    the tracer, so that the trace lists the skills, with their versions, that a run depended on."""

    def __init__(self, skills_dir: str | Path, tracer=None):
        self.skills_dir = Path(skills_dir)
        self.tracer = tracer  # receives a "skill.load" event per load; None turns the recording off
        self._cache: dict[str, Skill] = {}  # skill name -> parsed Skill, so each file is read only once

    def available(self) -> list[str]:
        """Names of all skills on disk (the folders that contain a SKILL.md), sorted."""
        return sorted(p.parent.name for p in self.skills_dir.glob("*/SKILL.md"))

    def load(self, name: str, record: bool = True) -> Skill:
        """Return the skill called ``name``, parsing its file on first use. Each call with ``record`` set
        is reported as a ``skill.load`` event, also when the skill comes from the cache. Raises
        FileNotFoundError for a skill that does not exist."""
        # First use: read and parse the file, then keep the result.
        if name not in self._cache:
            path = self.skills_dir / name / "SKILL.md"
            if not path.exists():
                raise FileNotFoundError(f"skill '{name}' not found under {self.skills_dir}")
            self._cache[name] = parse_skill(path.read_text(), path=str(path))
        # Report the use; in the trace it makes this skill, at this version, a dependency of the run.
        skill = self._cache[name]
        if record and self.tracer is not None:
            self.tracer.event(
                "skill.load", skill=skill.name, version=skill.version, digest=skill.digest, tokens=skill.token_estimate
            )
        return skill

    def expand(self, name: str, _seen=None) -> list[dict]:
        """Procedure of ``name`` with ``include:`` steps inlined (records every included skill load).

        Each returned step is a copy, tagged with ``_skill``: the name of the skill it comes from.
        ``_seen`` holds the skills on the current include path; a skill that ends up including itself,
        directly or through others, raises ValueError.
        """
        # An include cycle would recurse forever, so it is refused.
        _seen = _seen or set()
        if name in _seen:
            raise ValueError(f"cyclic include of skill '{name}'")
        skill = self.load(name)
        steps: list[dict] = []
        # An include step is replaced by the included skill's own expanded steps; any other step is copied
        # and tagged. Each include gets its own copy of the include path, so a shared skill may be included
        # by several steps; only a real cycle is refused.
        for step in skill.procedure:
            if "include" in step:
                steps.extend(self.expand(step["include"], _seen | {name}))
            else:
                steps.append(dict(step, _skill=name))
        return steps


PROCEDURE_INTRO = (
    "Follow these steps in order, one tool call at a time. <name> is the value `name` from the request "
    "context, or the value an earlier step set. `fetch.path` is the field `path` in the result of the step "
    "whose result is called `fetch`. Text in {braces} is filled in from those values. If a call returns an "
    "error, stop and tell the user what failed."
)

_CONFIG = re.compile(r"config\('([^']+)'\)")


def _plain(expr, config, template: bool = False) -> str:
    """An expression of a procedure, written for a reader: settings with their current value, context slots
    as <name> (bare names inside a message template), ``result.x`` as ``x``, ``last.`` (the result of the
    step's own call) dropped, and ``intent == 'x'`` as "the intent is `x`" (the agent's intents are listed
    in its prompt)."""
    text = str(expr)

    def setting(m):  # config('key') -> "key (value)", or just the value inside a message
        value = json.dumps(config.get(m.group(1)))
        return value if template else f"{m.group(1)} ({value})"

    text = _CONFIG.sub(setting, text)
    text = re.sub(r"ctx\.get\('(\w+)'\) is not None", r"<\1> is given", text)
    text = re.sub(r"ctx\.get\('(\w+)'\) is None", r"<\1> is not given", text)
    slot = (lambda m: m.group(1) or m.group(2)) if template else (lambda m: f"<{m.group(1) or m.group(2)}>")
    text = re.sub(r"ctx(?:\.get\('(\w+)'\)|\['(\w+)'\])", slot, text)
    text = re.sub(r"intent == '(\w+)'", r"the intent is `\1`", text)
    # [b['link'] for b in last.broken] -> "the link of each entry in broken"
    text = re.sub(r"\[(\w+)\['(\w+)'\] for \1 in ([\w.]+)\]", r"the \2 of each entry in \3", text)
    text = re.sub(r"\bresult\.", "", text)
    return re.sub(r"\blast\.", "", text)


def _template(message: str, config) -> str:
    """A message template with every ``{expression}`` written for a reader; a placeholder that is only a
    setting becomes the setting's value."""

    def placeholder(m):
        if _CONFIG.fullmatch(m.group(1).strip()):
            return _plain(m.group(1).strip(), config, template=True)
        return "{" + _plain(m.group(1), config, template=True) + "}"

    return re.sub(r"\{([^{}]+)\}", placeholder, message)


def _value(value, config) -> str:
    """An argument or slot value: ``$slot`` as <slot>, ``=expr`` as the expression, anything else as JSON."""
    if isinstance(value, str) and value.startswith("$"):
        return f"<{value[1:]}>"
    if isinstance(value, str) and value.startswith("="):
        return _plain(value[1:], config)
    return json.dumps(value)


def _answer(message: str | None, config) -> str:
    """How a step that stops the agent tells the user: its message template, or an explanation."""
    return f'answer: "{_template(message, config)}"' if message else "tell the user why."


def render_procedure(steps: list[dict], config) -> str:
    """The expanded steps of a procedure (``SkillLoader.expand``) as numbered sentences for a model: the
    same workflow the simulated backend executes, with every setting it reads shown with its value from
    ``config``. The step keys are documented in the simulated backend."""
    lines = []
    for step in steps:
        if "set" in step:  # the agent notes a value for later steps
            text = "; ".join(f"{k} = {_value(v, config)}" for k, v in step["set"].items()) + "."
        elif "say" in step:  # the final answer
            text = f'Answer: "{_template(step["say"], config)}" This ends your work.'
        elif "route" in step:  # the orchestrator's hand-off
            text = "Hand the request to the specialist that owns it, with `route_to_agent`."
        elif "call" in step:
            args = ", ".join(f"{k}={_value(v, config)}" for k, v in (step.get("args") or {}).items())
            text = f"Call `{step['call']}`" + (f" with {args}" if args else "") + "."
            # A condition on the result that stops the agent when it fails (unless on_fail says to go on).
            if "require" in step and not str(step.get("on_fail", "")).startswith("continue"):
                text += f" Go on only if {_plain(step['require'], config)}; otherwise stop and "
                text += _answer(step.get("fail_message"), config)
            # A call after which the agent is done.
            if str(step.get("then", "")).startswith("stop"):
                text += " Then stop and " + _answer(step.get("then_message"), config)
            if step.get("on_error") == "continue":
                text += " If the call fails, go on."
        else:
            continue
        # Later steps refer to a result by the step's id ("fetch.path").
        if "id" in step and ("call" in step or "route" in step):
            text += f" Its result is called `{step['id']}`."
        # A guarded step: "If <condition>: call ...".
        if "when" in step:
            text = f"If {_plain(step['when'], config)}: {text[0].lower()}{text[1:]}"
        lines.append(f"{len(lines) + 1}. {text}")
    return PROCEDURE_INTRO + "\n\n" + "\n".join(lines)


def replace_procedure(text: str, replacement: str) -> str:
    """``text`` (a SKILL.md) with its ``## Procedure`` block replaced by ``replacement``, a markdown body."""
    return _PROC.sub(lambda m: "## Procedure\n" + replacement.rstrip() + "\n", text, count=1)


def parse_skill(text: str, path: str = "") -> Skill:
    """Parse the text of a SKILL.md into a Skill. The front matter gives name, version, description and
    tools; the ``## Procedure`` block gives the steps. Both are optional: without a name the skill is
    named after the folder that holds the file at ``path`` (or "unknown" when there is no path), and
    without a procedure it has no steps."""
    # The front matter at the top of the file, if there is one.
    m = _FRONT.match(text)
    meta = yaml.safe_load(m.group(1)) if m else {}
    # The steps of the procedure block, if the skill has one.
    pm = _PROC.search(text)
    procedure = yaml.safe_load(pm.group(1)) if pm else []
    # Missing fields get defaults; the version is kept as a string even when the YAML gives a number.
    return Skill(
        name=meta.get("name", Path(path).parent.name if path else "unknown"),
        version=str(meta.get("version", "0")),
        description=meta.get("description", ""),
        tools=list(meta.get("tools", [])),
        text=text,
        procedure=procedure or [],
        path=path,
    )
