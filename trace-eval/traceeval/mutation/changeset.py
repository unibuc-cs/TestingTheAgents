"""Change-set extraction: baseline SUT tree vs. variant tree -> changed *components*.

This is the only information about a change that the selectors receive (they never see the
mutation label). Components use the same identifiers as observed/declared dependencies:

    code:<relpath>::<qualname>      function-level code change (AST-normalised, docstrings ignored)
    code:<relpath>                  module-level change outside any function
    tool:<name>                     a changed function is a registered tool adapter
    line:<relpath>:<n>              baseline code line <n> inside a changed hunk
    skill:<name>#procedure|#prose|#meta
    agent:<name>.<key>              changed key of an agent definition (tools, triggers, system_prompt, ...)
    config:<dotted.key>             changed effective configuration value
    fixture:<name>

Comments do not count. An edit that provably cannot change what the harness does (comments, docstrings,
blank lines and formatting, YAML comments, the order of config mappings) adds nothing to the change set:
no component, no file and no diff line, so no selector and no probability depends on it. For the same
reason the diff and the line components are computed on the code alone, with comments, docstrings and
blank lines removed. Skill files are prompts that the model reads word for word, so all of their text
counts."""

import ast
import difflib
import io
import json
import re
import tokenize
from dataclasses import dataclass, field
from pathlib import Path

import yaml

TEXT_SUFFIXES = {".py", ".md", ".yaml", ".yml", ".json"}


@dataclass
class ChangedComponent:
    id: str
    kind: str
    file: str
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
    diff: str = ""  # unified diff of the code only (no comments, docstrings or blank lines)

    def ids(self) -> set[str]:
        return {c.id for c in self.components}

    def base_ids(self) -> set[str]:
        return {c.base for c in self.components}

    def is_provably_benign(self) -> bool:
        """Nothing that can change behaviour was edited: at most comments, docstrings or formatting."""
        return not self.components

    def to_dict(self) -> dict:
        return {
            "variant": self.variant,
            "files": self.files,
            "components": [c.__dict__ for c in self.components],
            "diff": self.diff,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ChangeSet":
        # change sets saved by older versions also list comment-only edits, marked "semantic": false
        comps = [
            ChangedComponent(c["id"], c["kind"], c["file"], c.get("detail", ""))
            for c in d["components"]
            if c.get("semantic", True)
        ]
        return cls(d["variant"], d["files"], comps, d.get("diff", ""))


# ---------------------------------------------------------------------------- python helpers
_DOCUMENTED = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
_OPENS_STRING = re.compile(r"\s*[rRuUbBfF]{0,2}['\"]")


def _docstring(node: ast.AST) -> ast.Expr | None:
    """The docstring statement of a module, class or function, or None."""
    body = getattr(node, "body", [])
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(getattr(body[0], "value", None), ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        return body[0]
    return None


def _strip_docstrings(tree: ast.AST) -> ast.AST:
    for node in ast.walk(tree):
        if isinstance(node, _DOCUMENTED) and _docstring(node) is not None:
            node.body = node.body[1:] or [ast.Pass()]
    return tree


def _python_code_lines(source: str) -> list[tuple[int, str]]:
    """(line number, text) of every line of ``source`` that holds code. Docstrings, comments and blank
    lines are left out and a trailing comment is cut off, so editing a comment changes nothing here."""
    lines = source.split("\n")
    docstring_lines: set[int] = set()
    try:
        for node in ast.walk(ast.parse(source)):
            doc = _docstring(node) if isinstance(node, _DOCUMENTED) else None
            if doc is not None and _OPENS_STRING.match(lines[doc.lineno - 1]):  # a docstring on lines of its own
                docstring_lines.update(range(doc.lineno, doc.end_lineno + 1))
    except SyntaxError:
        pass  # a variant that does not parse still has its comments removed below
    try:
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        comment_at = {t.start[0]: t.start[1] for t in tokens if t.type == tokenize.COMMENT}
    except (SyntaxError, tokenize.TokenError):
        comment_at = {n: line.index("#") for n, line in enumerate(lines, 1) if line.lstrip().startswith("#")}
    code = []
    for n, line in enumerate(lines, 1):
        text = line[: comment_at[n]] if n in comment_at else line
        if n not in docstring_lines and text.strip():
            code.append((n, text.rstrip()))
    return code


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


def _line_components(rel: str, old: list[tuple[int, str]], new: list[tuple[int, str]]) -> list[ChangedComponent]:
    """Baseline code lines of every changed hunk (an insertion anchors to the code lines around it)."""
    sm = difflib.SequenceMatcher(a=[t for _, t in old], b=[t for _, t in new], autojunk=False)
    touched: set[int] = set()
    for tag, i1, i2, _j1, _j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        if i2 > i1:
            touched.update(range(i1, i2))
        else:  # pure insertion: the code lines just before and after it
            touched.update(k for k in (i1 - 1, i1) if 0 <= k < len(old))
    return [ChangedComponent(f"line:{rel}:{old[k][0]}", "line", rel, old[k][1].strip()[:80]) for k in sorted(touched)]


def _python_components(rel: str, old: str, new: str) -> list[ChangedComponent]:
    comps: list[ChangedComponent] = []
    try:
        od, om, ot = _function_dumps(old)
        nd, nm, nt = _function_dumps(new)
    except SyntaxError as exc:
        return [ChangedComponent(f"code:{rel}", "code", rel, f"syntax error: {exc}")]
    if od == nd and om == nm:
        return []  # AST-equivalent: only comments, docstrings or formatting changed
    for name in sorted(set(od) | set(nd)):
        if od.get(name) != nd.get(name):
            status = "added" if name not in od else "removed" if name not in nd else "modified"
            comps.append(ChangedComponent(f"code:{rel}::{name}", "code", rel, status))
            tool_name = nt.get(name) or ot.get(name)
            if tool_name:
                comps.append(ChangedComponent(f"tool:{tool_name}", "tool", rel, f"adapter {status}"))
    if om != nm:
        comps.append(ChangedComponent(f"code:{rel}", "code", rel, "module-level change"))
    comps.extend(_line_components(rel, _python_code_lines(old), _python_code_lines(new)))
    return comps


# ---------------------------------------------------------------------------- skills / agents / config
_FRONT = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
_PROC = re.compile(r"## Procedure\s*```yaml\n(.*?)```", re.DOTALL)


def _yaml_code_lines(source: str) -> list[tuple[int, str]]:
    """(line number, text) of every line of ``source`` that holds YAML data; comments and blank lines are
    left out. A '#' opens a comment only outside the scanner's tokens, so a '#' inside a quoted or block
    scalar (a system prompt, say) is kept."""
    try:
        spans = [
            (t.start_mark.line + 1, t.start_mark.column, t.end_mark.line + 1, t.end_mark.column)
            for t in yaml.scan(source)
        ]
    except yaml.YAMLError:
        spans = []

    def opens_comment(n: int, line: str, col: int) -> bool:
        return (col == 0 or line[col - 1] in " \t") and not any((a, b) <= (n, col) < (c, d) for a, b, c, d in spans)

    code = []
    for n, line in enumerate(source.split("\n"), 1):
        cut = next((m.start() for m in re.finditer("#", line) if opens_comment(n, line, m.start())), len(line))
        if line[:cut].strip():
            code.append((n, line[:cut].rstrip()))
    return code


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
        comps.append(ChangedComponent(f"skill:{name}#procedure", "skill", rel, "procedure block changed"))
    if yaml.safe_load(of or "{}") != yaml.safe_load(nf or "{}"):
        comps.append(ChangedComponent(f"skill:{name}#meta", "skill", rel, "front matter changed"))
    if " ".join(opr.split()) != " ".join(npr.split()):
        comps.append(ChangedComponent(f"skill:{name}#prose", "skill-prose", rel, "instruction prose changed"))
    return comps  # empty for a whitespace-only change


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
            comps.append(ChangedComponent(f"agent:{name}.{key}", kind, rel, f"{key} changed"))
    return comps  # empty for a comment- or format-only change


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
            comps.append(ChangedComponent(f"config:{key}", "config", rel, f"{status}: {of.get(key)} -> {nf.get(key)}"))
    return comps  # empty when only comments or the order of sections changed


# ---------------------------------------------------------------------------- driver
def _read(path: Path) -> str | None:
    try:
        return path.read_text()
    except (FileNotFoundError, UnicodeDecodeError):
        return None


def _components(rel: str, old: str, new: str) -> list[ChangedComponent]:
    if rel.endswith(".py"):
        return _python_components(rel, old, new)
    if rel.startswith("skills/") and rel.endswith("SKILL.md"):
        return _skill_components(rel, old, new)
    if rel.startswith("agents/") and rel.endswith((".yaml", ".yml")):
        return _agent_components(rel, old, new)
    if rel.startswith("config/"):
        return _config_components(rel, old, new)
    if rel.startswith("fixtures/"):
        return [ChangedComponent(f"fixture:{Path(rel).stem}", "fixture", rel, "fixture changed")]
    return [ChangedComponent(f"file:{rel}", "other", rel, "changed")]


def _code_lines(rel: str, text: str) -> list[tuple[int, str]]:
    """The lines of a file that the diff shows: code and YAML data without their comments. Any other file
    (skill prompts, fixtures) counts word for word."""
    if rel.endswith(".py"):
        return _python_code_lines(text)
    if rel.endswith((".yaml", ".yml")):
        return _yaml_code_lines(text)
    return list(enumerate(text.splitlines(), 1))


def compute_changeset(baseline: Path, variant: Path, name: str = "variant") -> ChangeSet:
    baseline, variant = Path(baseline), Path(variant)
    rels = set()
    for root in (baseline, variant):
        for p in root.rglob("*"):
            if p.is_file() and p.suffix in TEXT_SUFFIXES and "__pycache__" not in p.parts:
                rels.add(p.relative_to(root).as_posix())
    cs = ChangeSet(variant=name)
    diffs = []
    for rel in sorted(rels):
        old, new = _read(baseline / rel), _read(variant / rel)
        if old == new:
            continue
        old, new = old or "", new or ""
        comps = _components(rel, old, new)
        if not comps:  # nothing that can change behaviour: the file stays out of the change set
            continue
        cs.files.append(rel)
        cs.components.extend(comps)
        a = [text + "\n" for _, text in _code_lines(rel, old)]
        b = [text + "\n" for _, text in _code_lines(rel, new)]
        diffs.append("".join(difflib.unified_diff(a, b, f"a/{rel}", f"b/{rel}")))
    cs.diff = "".join(diffs)
    return cs
