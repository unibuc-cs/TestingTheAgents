"""Change-set extraction: baseline SUT tree vs. variant tree -> changed *components*.

This is the only information about a change that the selectors receive (they never see the
mutation label). Components use the same identifiers as observed/declared dependencies:

    code:<relpath>::<qualname>      function-level code change (AST-normalised, docstrings ignored)
    code:<relpath>                  module-level change outside any function
    tool:<name>                     a changed function is a registered tool adapter
    skill:<name>#procedure|#prose|#meta
    agent:<name>.<key>              changed key of an agent definition (tools, triggers, system_prompt, ...)
    config:<dotted.key>             changed effective configuration value
    config:<file>#comments          text changed but no effective value changed
    fixture:<name>

``semantic`` is False when the change is provably behaviour-preserving for the harness (comments,
docstrings, whitespace, YAML comments/ordering of mappings). Such static facts are legitimate inputs
for a selector; anything beyond that must be learned by running tests."""

import ast
import difflib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

TEXT_SUFFIXES = {".py", ".md", ".yaml", ".yml", ".json"}


@dataclass
class ChangedComponent:
    id: str
    kind: str
    file: str
    semantic: bool = True
    detail: str = ""

    @property
    def base(self) -> str:
        """Identifier without the sub-component qualifier (skill:x#procedure -> skill:x, agent:x.tools -> agent:x)."""
        cid = self.id.split("#", 1)[0]
        if cid.startswith("agent:") and "." in cid:
            cid = cid.split(".", 1)[0]
        return cid


@dataclass
class ChangeSet:
    variant: str
    files: list[str] = field(default_factory=list)
    components: list[ChangedComponent] = field(default_factory=list)
    diff: str = ""

    def ids(self, semantic_only: bool = False) -> set[str]:
        return {c.id for c in self.components if (c.semantic or not semantic_only)}

    def base_ids(self, semantic_only: bool = False) -> set[str]:
        return {c.base for c in self.components if (c.semantic or not semantic_only)}

    def is_provably_benign(self) -> bool:
        return all(not c.semantic for c in self.components)

    def to_dict(self) -> dict:
        return {
            "variant": self.variant,
            "files": self.files,
            "components": [c.__dict__ for c in self.components],
            "diff": self.diff,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ChangeSet":
        return cls(d["variant"], d["files"], [ChangedComponent(**c) for c in d["components"]], d.get("diff", ""))


# ---------------------------------------------------------------------------- python helpers
def _strip_docstrings(tree: ast.AST) -> ast.AST:
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", [])
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(getattr(body[0], "value", None), ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                node.body = body[1:] or [ast.Pass()]
    return tree


def _function_dumps(source: str) -> tuple[dict[str, str], str, dict[str, str]]:
    """qualname -> normalised dump; module-level dump (functions/classes removed); tool-name map."""
    tree = _strip_docstrings(ast.parse(source))
    dumps: dict[str, str] = {}
    tools: dict[str, str] = {}

    def visit(node, prefix=""):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = f"{prefix}{child.name}"
                dumps[name] = ast.dump(child, include_attributes=False)
                for deco in child.decorator_list:
                    if (
                        isinstance(deco, ast.Call)
                        and getattr(deco.func, "id", "") == "tool"
                        and deco.args
                        and isinstance(deco.args[0], ast.Constant)
                    ):
                        tools[name] = deco.args[0].value
                visit(child, name + ".")
            elif isinstance(child, ast.ClassDef):
                visit(child, f"{prefix}{child.name}.")
            else:
                visit(child, prefix)

    visit(tree)
    module_level = [n for n in tree.body if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
    module_dump = ast.dump(ast.Module(body=module_level, type_ignores=[]), include_attributes=False)
    return dumps, module_dump, tools


def _python_components(rel: str, old: str, new: str) -> list[ChangedComponent]:
    comps: list[ChangedComponent] = []
    try:
        od, om, ot = _function_dumps(old)
        nd, nm, nt = _function_dumps(new)
    except SyntaxError as exc:
        return [ChangedComponent(f"code:{rel}", "code", rel, True, f"syntax error: {exc}")]
    equivalent = od == nd and om == nm
    for name in sorted(set(od) | set(nd)):
        if od.get(name) != nd.get(name):
            status = "added" if name not in od else "removed" if name not in nd else "modified"
            comps.append(ChangedComponent(f"code:{rel}::{name}", "code", rel, True, status))
            tool_name = nt.get(name) or ot.get(name)
            if tool_name:
                comps.append(ChangedComponent(f"tool:{tool_name}", "tool", rel, True, f"adapter {status}"))
    if om != nm:
        comps.append(ChangedComponent(f"code:{rel}", "code", rel, True, "module-level change"))
    if equivalent:
        comps.append(
            ChangedComponent(
                f"code:{rel}#text", "code", rel, False, "comment/docstring/whitespace-only change (AST-equivalent)"
            )
        )
    # line-level components: baseline lines of every changed hunk (an insertion anchors to its neighbours)
    old_lines, new_lines = old.splitlines(), new.splitlines()
    sm = difflib.SequenceMatcher(a=old_lines, b=new_lines, autojunk=False)
    touched: set[int] = set()
    for tag, i1, i2, _j1, _j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        if i2 > i1:
            touched.update(range(i1 + 1, i2 + 1))
        else:  # pure insertion: previous and next baseline lines
            touched.update(n for n in (i1, i1 + 1) if 1 <= n <= len(old_lines))
    for n in sorted(touched):
        comps.append(ChangedComponent(f"line:{rel}:{n}", "line", rel, not equivalent, old_lines[n - 1].strip()[:80]))
    return comps


# ---------------------------------------------------------------------------- skills / agents / config
_FRONT = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
_PROC = re.compile(r"## Procedure\s*```yaml\n(.*?)```", re.DOTALL)


def _skill_parts(text: str) -> tuple[str, str, str]:
    m = _FRONT.match(text)
    front = m.group(1) if m else ""
    pm = _PROC.search(text)
    proc = pm.group(1) if pm else ""
    prose = _PROC.sub("", _FRONT.sub("", text, count=1), count=1)
    return front, proc, prose


def _skill_components(rel: str, old: str, new: str) -> list[ChangedComponent]:
    name = Path(rel).parent.name
    of, op_, opr = _skill_parts(old)
    nf, np_, npr = _skill_parts(new)
    comps = []
    if yaml.safe_load(op_ or "[]") != yaml.safe_load(np_ or "[]"):
        comps.append(ChangedComponent(f"skill:{name}#procedure", "skill", rel, True, "procedure block changed"))
    if yaml.safe_load(of or "{}") != yaml.safe_load(nf or "{}"):
        comps.append(ChangedComponent(f"skill:{name}#meta", "skill", rel, True, "front matter changed"))
    if " ".join(opr.split()) != " ".join(npr.split()):
        comps.append(ChangedComponent(f"skill:{name}#prose", "skill-prose", rel, True, "instruction prose changed"))
    if not comps:
        comps.append(ChangedComponent(f"skill:{name}#text", "skill", rel, False, "whitespace-only change"))
    return comps


def _ordered(value) -> str:
    """JSON with insertion order preserved: mapping order is significant for intents / triggers."""
    return json.dumps(value, sort_keys=False, default=str)


def _agent_components(rel: str, old: str, new: str) -> list[ChangedComponent]:
    name = Path(rel).stem
    od, nd = yaml.safe_load(old) or {}, yaml.safe_load(new) or {}
    comps = []
    for key in sorted(set(od) | set(nd)):
        if _ordered(od.get(key)) != _ordered(nd.get(key)):
            kind = "agent-prompt" if key in ("system_prompt", "description") else "agent"
            comps.append(ChangedComponent(f"agent:{name}.{key}", kind, rel, True, f"{key} changed"))
    if not comps:
        comps.append(ChangedComponent(f"agent:{name}#text", "agent", rel, False, "comment/format-only change"))
    return comps


def _flatten(d, prefix="") -> dict[str, str]:
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            out.update(_flatten(v, f"{prefix}{k}."))
    else:
        out[prefix[:-1]] = json.dumps(d, sort_keys=True, default=str)
    return out


def _config_components(rel: str, old: str, new: str) -> list[ChangedComponent]:
    of, nf = _flatten(yaml.safe_load(old) or {}), _flatten(yaml.safe_load(new) or {})
    comps = []
    for key in sorted(set(of) | set(nf)):
        if of.get(key) != nf.get(key):
            status = "added" if key not in of else "removed" if key not in nf else "modified"
            comps.append(
                ChangedComponent(f"config:{key}", "config", rel, True, f"{status}: {of.get(key)} -> {nf.get(key)}")
            )
    if not comps:
        comps.append(
            ChangedComponent(
                f"config:{Path(rel).stem}#comments",
                "config",
                rel,
                False,
                "comments/ordering only; effective values unchanged",
            )
        )
    return comps


# ---------------------------------------------------------------------------- driver
def _read(path: Path) -> str | None:
    try:
        return path.read_text()
    except (FileNotFoundError, UnicodeDecodeError):
        return None


def compute_changeset(baseline: Path, variant: Path, name: str = "variant") -> ChangeSet:
    baseline, variant = Path(baseline), Path(variant)
    rels = set()
    for root in (baseline, variant):
        for p in root.rglob("*"):
            if p.is_file() and p.suffix in TEXT_SUFFIXES and "__pycache__" not in p.parts:
                rels.add(str(p.relative_to(root)))
    cs = ChangeSet(variant=name)
    diffs = []
    for rel in sorted(rels):
        old, new = _read(baseline / rel), _read(variant / rel)
        if old == new:
            continue
        cs.files.append(rel)
        diffs.append(
            "".join(
                difflib.unified_diff((old or "").splitlines(True), (new or "").splitlines(True), f"a/{rel}", f"b/{rel}")
            )
        )
        old, new = old or "", new or ""
        if rel.endswith(".py"):
            cs.components.extend(_python_components(rel, old, new))
        elif rel.startswith("skills/") and rel.endswith("SKILL.md"):
            cs.components.extend(_skill_components(rel, old, new))
        elif rel.startswith("agents/") and rel.endswith((".yaml", ".yml")):
            cs.components.extend(_agent_components(rel, old, new))
        elif rel.startswith("config/"):
            cs.components.extend(_config_components(rel, old, new))
        elif rel.startswith("fixtures/"):
            cs.components.append(ChangedComponent(f"fixture:{Path(rel).stem}", "fixture", rel, True, "fixture changed"))
        else:
            cs.components.append(ChangedComponent(f"file:{rel}", "other", rel, True, "changed"))
    cs.diff = "".join(diffs)
    return cs
