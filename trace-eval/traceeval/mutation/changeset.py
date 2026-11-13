"""Change-set extraction: baseline SUT tree vs. variant tree -> changed *components*.

This is the only information about a change that the selectors receive (they never see the
mutation label). Components use the same identifiers as observed/declared dependencies:

    code:<relpath>::<qualname>      function-level code change (AST-normalised, docstrings ignored)
    code:<relpath>                  module-level change outside any function (class attributes included)
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
import copy
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
    """One part of the application a diff touched, named as the traces name it (``code:<file>::<fn>``,
    ``line:<file>:<n>``, ``tool:<name>``, ``skill:<name>#procedure``, ``agent:<name>.<field>``, ``config:<key>``,
    ``fixture:<name>``)."""

    id: str  # the component id, the same vocabulary as a test's dependencies
    kind: str  # code | line | tool | skill | agent | config | fixture | other; sets the method's prior and ratio
    file: str  # the file the diff touched, relative to the application root
    detail: str = ""  # the changed code line, the removed items of a list, or the sub-part of a skill or agent

    @property
    def base(self) -> str:
        """Identifier without the sub-component qualifier (skill:x#procedure -> skill:x, agent:x.tools -> agent:x)."""
        cid = self.id.split("#", 1)[0]
        if cid.startswith("agent:") and "." in cid:
            cid = cid.split(".", 1)[0]
        return cid


@dataclass
class ChangeSet:
    """What a diff of two copies of the application comes to: the files and the components it touched. Comments,
    docstrings, blank lines and formatting add nothing, so a change set can be empty."""

    variant: str  # the name of the changed copy (a mutation id, or "variant" for a user's own edit)
    files: list[str] = field(default_factory=list)  # the files that differ, relative to the application root
    components: list[ChangedComponent] = field(default_factory=list)
    diff: str = ""  # unified diff of the code only (no comments, docstrings or blank lines)

    def ids(self) -> set[str]:
        """The ids of the changed components: what a strategy intersects with a test's dependencies."""
        return {c.id for c in self.components}

    def is_provably_benign(self) -> bool:
        """Nothing that can change behaviour was edited: at most comments, docstrings or formatting."""
        return not self.components

    def to_dict(self) -> dict:
        """The change set as plain data, the form the history keeps it in."""
        return {
            "variant": self.variant,
            "files": self.files,
            "components": [c.__dict__ for c in self.components],
            "diff": self.diff,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ChangeSet":
        """A change set read back from the form ``to_dict`` writes."""
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
    """Drop every docstring, so that editing one leaves the AST dump unchanged."""
    for node in ast.walk(tree):
        if isinstance(node, _DOCUMENTED) and _docstring(node) is not None:
            node.body = node.body[1:] or [ast.Pass()]
    return tree


def _python_code_lines(source: str) -> list[tuple[int, str]]:
    """(line number, text) of every line of ``source`` that holds code. Docstrings, comments and blank
    lines are left out and a trailing comment is cut off, so editing a comment changes nothing here."""
    lines = source.split("\n")
    # The lines every docstring spans, from the AST.
    docstring_lines: set[int] = set()
    try:
        for node in ast.walk(ast.parse(source)):
            doc = _docstring(node) if isinstance(node, _DOCUMENTED) else None
            # only a docstring that starts its line: one written after ``def f():`` must not take that code along
            if doc is not None and _OPENS_STRING.match(lines[doc.lineno - 1]):
                docstring_lines.update(range(doc.lineno, doc.end_lineno + 1))
    except SyntaxError:
        pass  # a variant that does not parse still has its comments removed below
    # Where each comment starts (line -> column), from the tokenizer: a '#' inside a string is not a comment.
    try:
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        comment_at = {t.start[0]: t.start[1] for t in tokens if t.type == tokenize.COMMENT}
    except (SyntaxError, tokenize.TokenError):  # untokenizable variant: drop whole-line comments only
        comment_at = {n: line.index("#") for n, line in enumerate(lines, 1) if line.lstrip().startswith("#")}
    # What is left of each line once its comment is cut off, unless it is blank or part of a docstring.
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

    # qualified names as tracing/codecov.py builds them (Class.method, outer.inner), so the ids match
    def visit(node, prefix=""):
        """Dump every function below ``node`` under its qualified name, and note the ones that are tool adapters."""
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = f"{prefix}{child.name}"
                dumps[name] = ast.dump(child, include_attributes=False)  # no line numbers: formatting is no change
                for deco in child.decorator_list:  # @tool("name", ...) marks a tool adapter
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
    # The module level on its own: what runs at import, with the functions (dumped above) taken out.
    module_dump = ast.dump(ast.Module(body=_without_functions(tree.body), type_ignores=[]), include_attributes=False)
    return dumps, module_dump, tools


def _without_functions(body: list[ast.stmt]) -> list[ast.stmt]:
    """The statements that run at import time: functions dropped (they have their own dumps), classes kept
    with their own statements only, so that a changed class attribute (a dataclass default) still counts."""
    out = []
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if isinstance(node, ast.ClassDef):
            node = copy.copy(node)
            node.body = _without_functions(node.body)
        out.append(node)
    return out


def _line_components(rel: str, old: list[tuple[int, str]], new: list[tuple[int, str]]) -> list[ChangedComponent]:
    """Baseline code lines of every changed hunk (an insertion anchors to the code lines around it)."""
    # diff the code lines only, then map positions back to the baseline file's own line numbers
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
    """code:, tool: and line: components of a Python file; a variant that does not parse is one module change."""
    comps: list[ChangedComponent] = []
    try:
        od, om, ot = _function_dumps(old)
        nd, nm, nt = _function_dumps(new)
    except SyntaxError as exc:
        return [ChangedComponent(f"code:{rel}", "code", rel, f"syntax error: {exc}")]
    if od == nd and om == nm:
        return []  # AST-equivalent: only comments, docstrings or formatting changed
    # one component per changed function (a nested function changes its parent's dump too, so both are
    # listed) and its tool if it is an adapter; then the module level; then the changed lines
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
    # The scanner's tokens say where the YAML data is: a '#' that falls inside a token (a quoted string, a
    # block scalar such as a system prompt) is content, not a comment. Each span is (line, column) of a
    # token's start and end, 1-based lines, so that it can be compared with a position as a tuple.
    try:
        spans = [
            (t.start_mark.line + 1, t.start_mark.column, t.end_mark.line + 1, t.end_mark.column)
            for t in yaml.scan(source)
        ]
    except yaml.YAMLError:
        spans = []  # a variant that does not scan: every '#' outside a token position is still a comment

    def opens_comment(n: int, line: str, col: int) -> bool:
        """Whether the '#' at column ``col`` of line ``n`` starts a comment."""
        # YAML's rule: a comment starts at a '#' that is at the start of the line or follows a space, and that
        # is not inside a token.
        return (col == 0 or line[col - 1] in " \t") and not any((a, b) <= (n, col) < (c, d) for a, b, c, d in spans)

    # Each line up to its first real comment, kept when anything but whitespace is left.
    code = []
    for n, line in enumerate(source.split("\n"), 1):
        cut = next((m.start() for m in re.finditer("#", line) if opens_comment(n, line, m.start())), len(line))
        if line[:cut].strip():
            code.append((n, line[:cut].rstrip()))
    return code


def _skill_parts(text: str) -> tuple[str, str, str]:
    """A SKILL.md split into front matter, the YAML of its ``## Procedure`` block, and the remaining prose."""
    m = _FRONT.match(text)
    front = m.group(1) if m else ""
    pm = _PROC.search(text)
    proc = pm.group(1) if pm else ""
    prose = _PROC.sub("", _FRONT.sub("", text, count=1), count=1)
    return front, proc, prose


def _skill_components(rel: str, old: str, new: str) -> list[ChangedComponent]:
    """The ``skill:<name>#procedure``, ``#meta`` and ``#prose`` components of a SKILL.md, each part on its own."""
    name = Path(rel).parent.name
    of, op_, opr = _skill_parts(old)
    nf, np_, npr = _skill_parts(new)
    comps = []
    # procedure and front matter are compared as parsed YAML; prose word for word, whitespace collapsed
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
    """The ``agent:<name>.<key>`` components of an agent definition: one per top-level key whose value changed."""
    name = Path(rel).stem
    od, nd = yaml.safe_load(old) or {}, yaml.safe_load(new) or {}
    comps = []
    for key in sorted(set(od) | set(nd)):
        if _ordered(od.get(key)) != _ordered(nd.get(key)):
            # The prompt fields are their own kind: the model reads them, where the harness acts on the other keys.
            kind = "agent-prompt" if key in ("system_prompt", "description") else "agent"
            detail = f"{key} changed"
            if key in ("tools", "skills"):
                # A list that only lost items affects only the runs that used one of them: name them, as the
                # dependency ids the traces record (tool:<name>, skill:<name>).
                old_items, new_items = set(od.get(key) or []), set(nd.get(key) or [])
                if old_items > new_items:
                    detail = "removed: " + " ".join(f"{key[:-1]}:{x}" for x in sorted(old_items - new_items))
            comps.append(ChangedComponent(f"agent:{name}.{key}", kind, rel, detail))
    return comps  # empty for a comment- or format-only change


def _flatten(d, prefix="") -> dict[str, str]:
    """Nested config -> {dotted.key: JSON of the value}; the dotted keys are the ids the harness reads."""
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            out.update(_flatten(v, f"{prefix}{k}."))
    else:
        out[prefix[:-1]] = json.dumps(d, sort_keys=True, default=str)
    return out


def _config_components(rel: str, old: str, new: str) -> list[ChangedComponent]:
    """The ``config:<dotted.key>`` components of a configuration file: one per setting whose value changed."""
    of, nf = _flatten(yaml.safe_load(old) or {}), _flatten(yaml.safe_load(new) or {})
    comps = []
    for key in sorted(set(of) | set(nf)):
        if of.get(key) != nf.get(key):
            status = "added" if key not in of else "removed" if key not in nf else "modified"
            comps.append(ChangedComponent(f"config:{key}", "config", rel, f"{status}: {of.get(key)} -> {nf.get(key)}"))
    return comps  # empty when only comments or the order of sections changed


# ---------------------------------------------------------------------------- driver
def _read(path: Path) -> str | None:
    """The text of ``path``, or None when the file is not there (added or removed) or is not text."""
    try:
        return path.read_text()
    except (FileNotFoundError, UnicodeDecodeError):
        return None


def _components(rel: str, old: str, new: str) -> list[ChangedComponent]:
    """The changed components of one file, by where it lives in the SUT tree."""
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
    """Compare two SUT trees file by file (added and removed files included)."""
    baseline, variant = Path(baseline), Path(variant)
    # Every text file of either tree, so that an added or a removed file is seen too.
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
        # The diff is over the code lines alone, so an edited comment adds no diff line either.
        a = [text + "\n" for _, text in _code_lines(rel, old)]
        b = [text + "\n" for _, text in _code_lines(rel, new)]
        diffs.append("".join(difflib.unified_diff(a, b, f"a/{rel}", f"b/{rel}")))
    cs.diff = "".join(diffs)
    return cs
