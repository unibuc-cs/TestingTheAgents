"""The product model: what the harness knows about the system without reading it all.

Static part (from the SUT tree, tool-extracted): files and their token counts, functions per file (AST),
registered tools and their kinds, skill procedures (parsed ``## Procedure`` blocks), the effective
configuration. Dynamic part (from recorded baseline runs): which cases exercise which tools and which
code functions each case executed. Both are queried by the checkers and by the agent brief; neither
replaces running the code ("the model is not the code")."""

import ast
import re
from pathlib import Path

import yaml

from traceeval.tracing.codecov import function_index

SOURCE_SUFFIXES = {".py", ".md", ".yaml", ".json"}


def approx_tokens(text: str) -> int:
    """Cheap token estimate (4 characters per token), enough to compare context sizes."""
    return max(1, len(text) // 4)


class ProductModel:
    def __init__(self, sut_dir: Path, baseline_runs: dict[str, dict], baseline_deps: dict[str, set[str]]):
        self.sut_dir = Path(sut_dir)
        self.baseline_runs = baseline_runs  # test_id -> record (with events / states)
        self.baseline_deps = baseline_deps  # test_id -> observed components incl. code functions
        self.files = {
            str(p.relative_to(self.sut_dir)): p.read_text()
            for p in sorted(self.sut_dir.rglob("*"))
            if p.is_file() and p.suffix in SOURCE_SUFFIXES and "__pycache__" not in p.parts
        }
        self.functions = function_index(self.sut_dir)  # relpath -> [(qualname, first, last)]
        self.config = yaml.safe_load(self.files["config/runtime.yaml"]) or {}

    # ---------------------------------------------------------------- static queries
    def config_value(self, key: str):
        """Dotted lookup in the effective configuration (None when the key does not exist)."""
        node = self.config
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                return None
            node = node[part]
        return node

    @property
    def catalog_ids(self) -> set[str]:
        return set(self.baseline_runs)

    def repo_tokens(self) -> int:
        return sum(approx_tokens(t) for t in self.files.values())

    def tokens_of(self, rel_files) -> int:
        return sum(approx_tokens(self.files[f]) for f in rel_files if f in self.files)

    def tools(self, sut) -> dict[str, str]:
        """tool name -> kind, from the loaded variant's registry."""
        return {name: spec.kind for name, spec in sut.tools.items()}

    def write_tools(self, sut) -> list[str]:
        return sorted(n for n, k in self.tools(sut).items() if k in ("write", "guarded"))

    def skill_write_tools(self, skill: str) -> list[str]:
        """The write/guarded tools a skill's procedure calls directly."""
        kinds = {n: k for n, (k, _, _) in self.tools_static().items()}
        calls = {s.get("call") for s in self.skill_procedure(skill) if isinstance(s, dict)}
        return sorted(t for t in calls if kinds.get(t) in ("write", "guarded"))

    def model_set(self, domain, catalog: dict | None = None) -> list | None:
        """Resolve the finite domain of a ``forall``: a literal list, ``write_tools``, ``catalog_cases`` or
        ``{skill_write_tools: <skill>}``. None when the domain is a Hypothesis strategy instead."""
        if isinstance(domain, list):
            return list(domain)
        if domain == "write_tools":
            return self.write_tools_static()
        if domain == "catalog_cases":
            return list(catalog or [])
        if isinstance(domain, dict) and "skill_write_tools" in domain:
            return self.skill_write_tools(domain["skill_write_tools"])
        return None

    def tools_static(self) -> dict[str, tuple[str, str, str]]:
        """tool name -> (kind, adapter file, adapter function), from the ``@tool(name, kind, ...)`` decorators."""
        out = {}
        for rel, text in self.files.items():
            if not (rel.startswith("tools/") and rel.endswith(".py")):
                continue
            for node in ast.walk(ast.parse(text)):
                if not isinstance(node, ast.FunctionDef):
                    continue
                for deco in node.decorator_list:
                    if (
                        isinstance(deco, ast.Call)
                        and isinstance(deco.func, ast.Name)
                        and deco.func.id == "tool"
                        and len(deco.args) >= 2
                        and all(isinstance(a, ast.Constant) for a in deco.args[:2])
                    ):
                        out[deco.args[0].value] = (deco.args[1].value, rel, node.name)
        return out

    def write_tools_static(self) -> list[str]:
        return sorted(n for n, (k, _, _) in self.tools_static().items() if k in ("write", "guarded"))

    def locate(self, tool_names) -> dict[str, list[str]]:
        """Where the given tools live: adapter functions, the service functions those adapters call, and
        the skills whose procedures call the tools. relpath -> [function or step names]."""
        out: dict[str, set[str]] = {}
        tools = self.tools_static()
        for name in tool_names:
            if name not in tools:
                continue
            _, rel, fn_name = tools[name]
            out.setdefault(rel, set()).add(fn_name)
            tree = ast.parse(self.files[rel])
            imported = {
                a.asname or a.name: node.module
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom) and node.module and "services" in node.module
                for a in node.names
            }
            fdef = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == fn_name)
            for call in ast.walk(fdef):
                if (
                    isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Attribute)
                    and isinstance(call.func.value, ast.Name)
                ):
                    mod = call.func.value.id
                    if mod in imported:
                        out.setdefault(f"services/{mod}.py", set()).add(call.func.attr)
        for rel in self.files:
            if rel.startswith("skills/") and rel.endswith("SKILL.md"):
                steps = self.skill_procedure(rel.split("/")[1])
                hits = {s["call"] for s in steps if isinstance(s, dict) and s.get("call") in tool_names}
                if hits:
                    out.setdefault(rel, set()).update(f"call: {h}" for h in sorted(hits))
        return {k: sorted(v) for k, v in sorted(out.items())}

    def skill_procedure(self, skill: str) -> list[dict]:
        text = self.files.get(f"skills/{skill}/SKILL.md", "")
        m = re.search(r"## Procedure\s*```yaml\n(.*?)```", text, re.S)
        return yaml.safe_load(m.group(1)) if m else []

    def status_setters(self) -> dict[str, list[str]]:
        """Service functions that assign ``page["status"]`` -> the tools whose adapters call them.
        Used to check that a rule about "going live" covers every code path that can change a status."""
        setters: list[str] = []
        for rel, text in self.files.items():
            if not rel.startswith("services/") or not rel.endswith(".py"):
                continue
            tree = ast.parse(text)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and any(
                    isinstance(n, ast.Assign)
                    and isinstance(n.targets[0], ast.Subscript)
                    and isinstance(n.targets[0].slice, ast.Constant)
                    and n.targets[0].slice.value == "status"
                    and isinstance(n.targets[0].value, ast.Name)
                    and n.targets[0].value.id == "page"
                    for n in ast.walk(node)
                ):
                    setters.append(node.name)
        out: dict[str, list[str]] = {}
        for rel, text in self.files.items():
            if not rel.startswith("tools/") or not rel.endswith(".py"):
                continue
            for node in ast.walk(ast.parse(text)):
                if isinstance(node, ast.FunctionDef):
                    called = {
                        n.func.attr
                        for n in ast.walk(node)
                        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    }
                    hits = sorted(called & set(setters))
                    if hits:
                        out[node.name] = hits
        return out

    # ---------------------------------------------------------------- dynamic queries (baseline runs)
    def cases_calling(self, tools: list[str] | None = None, kinds: list[str] | None = None, ok_only=False) -> list[str]:
        """Catalog cases whose recorded baseline run called one of ``tools`` (or a tool of one of ``kinds``)."""
        out = []
        for tid, rec in self.baseline_runs.items():
            for ev in rec.get("events", []):
                if ev.get("kind") != "tool.call":
                    continue
                if ok_only and ev.get("status") != "ok":
                    continue
                if (tools and ev.get("tool") in tools) or (kinds and ev.get("tool_kind") in kinds):
                    out.append(tid)
                    break
        return out
