"""Skill loading. A skill is a SKILL.md with YAML front matter, prose instructions (read by the LLM
backend) and a machine-readable ``## Procedure`` block (executed by the simulated backend and rendered
verbatim to the LLM). The procedure block is the canonical statement of the workflow, so a mutation of
the procedure changes the behaviour of *both* backends."""

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

_FRONT = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
_PROC = re.compile(r"## Procedure\s*```yaml\n(.*?)```", re.DOTALL)


@dataclass
class Skill:
    name: str
    version: str
    description: str
    tools: list[str]
    text: str  # full markdown (for the LLM backend)
    procedure: list[dict] = field(default_factory=list)
    path: str = ""

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.text.encode()).hexdigest()[:12]

    @property
    def token_estimate(self) -> int:
        return max(1, len(self.text) // 4)


class SkillLoader:
    def __init__(self, skills_dir: str | Path, tracer=None):
        self.skills_dir = Path(skills_dir)
        self.tracer = tracer
        self._cache: dict[str, Skill] = {}

    def available(self) -> list[str]:
        return sorted(p.parent.name for p in self.skills_dir.glob("*/SKILL.md"))

    def load(self, name: str, record: bool = True) -> Skill:
        if name not in self._cache:
            path = self.skills_dir / name / "SKILL.md"
            if not path.exists():
                raise FileNotFoundError(f"skill '{name}' not found under {self.skills_dir}")
            self._cache[name] = parse_skill(path.read_text(), path=str(path))
        skill = self._cache[name]
        if record and self.tracer is not None:
            self.tracer.event(
                "skill.load", skill=skill.name, version=skill.version, digest=skill.digest, tokens=skill.token_estimate
            )
        return skill

    def expand(self, name: str, _seen=None) -> list[dict]:
        """Procedure of ``name`` with ``include:`` steps inlined (records every included skill load)."""
        _seen = _seen or set()
        if name in _seen:
            raise ValueError(f"cyclic include of skill '{name}'")
        skill = self.load(name)
        steps: list[dict] = []
        for step in skill.procedure:
            if "include" in step:
                steps.extend(self.expand(step["include"], _seen | {name}))
            else:
                steps.append(dict(step, _skill=name))
        return steps


def parse_skill(text: str, path: str = "") -> Skill:
    m = _FRONT.match(text)
    meta = yaml.safe_load(m.group(1)) if m else {}
    pm = _PROC.search(text)
    procedure = yaml.safe_load(pm.group(1)) if pm else []
    return Skill(
        name=meta.get("name", Path(path).parent.name if path else "unknown"),
        version=str(meta.get("version", "0")),
        description=meta.get("description", ""),
        tools=list(meta.get("tools", [])),
        text=text,
        procedure=procedure or [],
        path=path,
    )
