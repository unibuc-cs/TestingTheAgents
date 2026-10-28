"""Agent definitions (YAML): system prompt, skills, tools, routing triggers and intents."""

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class AgentDef:
    name: str
    version: str
    description: str
    system_prompt: str
    skills: list[str]
    tools: list[str]
    entry_skill: str | None = None
    triggers: list[str] = field(default_factory=list)  # routing keywords (orchestrator uses them)
    intents: dict[str, list[str]] = field(default_factory=dict)
    is_orchestrator: bool = False
    raw: dict = field(default_factory=dict)

    @property
    def digest(self) -> str:
        return hashlib.sha256(yaml.safe_dump(self.raw, sort_keys=True).encode()).hexdigest()[:12]

    @property
    def prompt_tokens(self) -> int:
        return max(1, len(self.system_prompt) // 4)


class AgentLoader:
    def __init__(self, agents_dir: str | Path):
        self.agents_dir = Path(agents_dir)
        self._cache: dict[str, AgentDef] = {}

    def available(self) -> list[str]:
        return sorted(p.stem for p in self.agents_dir.glob("*.yaml"))

    def load(self, name: str) -> AgentDef:
        if name not in self._cache:
            path = self.agents_dir / f"{name}.yaml"
            if not path.exists():
                raise FileNotFoundError(f"agent '{name}' not found under {self.agents_dir}")
            raw = yaml.safe_load(path.read_text())
            self._cache[name] = AgentDef(
                name=raw["name"],
                version=str(raw.get("version", "0")),
                description=raw.get("description", ""),
                system_prompt=raw.get("system_prompt", ""),
                skills=list(raw.get("skills", [])),
                tools=list(raw.get("tools", [])),
                entry_skill=raw.get("entry_skill"),
                triggers=list(raw.get("triggers", [])),
                intents=dict(raw.get("intents", {})),
                is_orchestrator=bool(raw.get("orchestrator", False)),
                raw=raw,
            )
        return self._cache[name]

    def load_all(self) -> dict[str, AgentDef]:
        return {n: self.load(n) for n in self.available()}
