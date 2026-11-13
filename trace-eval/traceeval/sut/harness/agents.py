"""Agent definitions (YAML): system prompt, skills, tools, routing triggers and intents."""

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class AgentDef:
    """One agent definition, as read from ``agents/<name>.yaml``."""

    name: str
    version: str  # always kept as a string; "0" when the YAML has none
    description: str  # what the agent owns, in one line; the orchestrator reads it when it routes
    system_prompt: str
    skills: list[str]  # skills loaded when the agent starts; the LLM backend puts their text in the prompt
    tools: list[str]  # the only tools this agent may call; the dispatcher refuses any other
    entry_skill: str | None = None  # skill whose procedure is written out as steps in the agent's prompt
    triggers: list[str] = field(default_factory=list)  # routing keywords (orchestrator uses them)
    intents: dict[str, list[str]] = field(default_factory=dict)  # intent name -> keywords that signal it
    is_orchestrator: bool = False  # "orchestrator: true" in the YAML; it routes, and is never routed to
    raw: dict = field(default_factory=dict)  # the YAML document as loaded, kept for the digest

    @property
    def digest(self) -> str:
        """Short fingerprint of the definition (the first 12 hex digits of a SHA-256). It is computed from
        the parsed YAML with sorted keys, so reformatting the file or editing its comments leaves it
        unchanged, while a change to any value changes it."""
        return hashlib.sha256(yaml.safe_dump(self.raw, sort_keys=True).encode()).hexdigest()[:12]


class AgentLoader:
    """Reads agent definitions from ``<agents_dir>/<name>.yaml`` and keeps each one after its first load."""

    def __init__(self, agents_dir: str | Path):
        self.agents_dir = Path(agents_dir)
        self._cache: dict[str, AgentDef] = {}  # file name without ".yaml" -> parsed definition

    def available(self) -> list[str]:
        """Names of all agent definitions on disk (the YAML file names without extension), sorted."""
        return sorted(p.stem for p in self.agents_dir.glob("*.yaml"))

    def load(self, name: str) -> AgentDef:
        """Return the definition in ``<name>.yaml``, reading the file on first use. Raises
        FileNotFoundError for an agent that does not exist."""
        if name not in self._cache:
            path = self.agents_dir / f"{name}.yaml"
            if not path.exists():
                raise FileNotFoundError(f"agent '{name}' not found under {self.agents_dir}")
            # Only "name" is required. A missing version reads as "0", and any other missing key gives an
            # empty value (no skills, tools, triggers or intents; not an orchestrator).
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
        """Every agent definition keyed by file name, in alphabetical order."""
        return {n: self.load(n) for n in self.available()}
