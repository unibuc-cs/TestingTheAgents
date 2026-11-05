"""Skill loading. A skill is a SKILL.md with YAML front matter, prose instructions (read by the LLM
backend) and a machine-readable ``## Procedure`` block (executed by the simulated backend and rendered
verbatim to the LLM). The procedure block is the canonical statement of the workflow, so a mutation of
the procedure changes the behaviour of *both* backends."""

import hashlib
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
