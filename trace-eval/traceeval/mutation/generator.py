"""Generated changes: every edit of a few kinds that the app's own files allow, made mechanically.

The 43 changes of ``catalog.py`` were written by hand, each to make a point, and each carries a label. The changes
here are enumerated from the app as it is, one per place an edit applies to, and nobody decides beforehand whether
one is a regression: the recording does (some test reveals it, or none).

    kind       the edit                                                        files
    stepdel    a step of a skill's procedure deleted                           skills/*/SKILL.md
    stepswap   two adjacent steps of a procedure swapped
    whennot    the condition of a step negated
    guarddel   the guard of a step deleted (require, on_fail, fail_message)
    ruledel    a bullet deleted from a skill's prose (its rules)
    rewrap     two lines of a skill's prose joined: the same words             (meant to break nothing)
    tooldrop   a tool removed from an agent                                    agents/*.yaml
    setting    a setting at another value: a switch flipped, a number at 0,    config/runtime.yaml
               one less and one more, a list without one item, a tool
               switched off, another default agent
    argswap    two arguments of the same type swapped in a call                tools/*.py
    tooldesc   a tool's description cut to its first three words
    condnot    the condition of an ``if`` negated                              services, tools, harness
    comment    a comment added at the top of a module                          (meant to break nothing)
    fixture    a value of the starting data replaced by another value the      fixtures/base.json
               same key has elsewhere in the data

An id reads ``g_<kind>_<where>_<n>``. Every edit names the line it starts at and the text it expects there
(``operators.replace_lines``), so a change generated from one version of the app cannot be applied to another:
the operator raises. ``generate`` lists them all, ``sample`` draws a fixed number per kind, and ``split`` halves
them into the changes a strategy may learn from and those it is evaluated on.
"""

import ast
import hashlib
import json
import re
from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

import yaml

from traceeval.sut import SUT_ROOT

from .catalog import BENIGN, CODE, CONFIG, PROMPT, RUNTIME, SKILL, Mutation

FIXTURE = "fixture"  # the category of an edit to the starting data; the others are catalog.py's


def _read(root: Path, rel: str) -> list[str]:
    """The lines of a file of the app, each with its line ending."""
    return (Path(root) / rel).read_text().splitlines(keepends=True)


def _change(name: str, category: str, description: str, *edits: tuple) -> Mutation:
    """One generated change, ``g_<name>`` with ``name`` its kind, where it applies and a number. ``edits`` are
    (file, first line, old text, new text), in the order to apply them: the lowest line last, so that an earlier
    edit moves no line a later one names. The label is None: a generated change has none."""
    return Mutation(f"g_{name}", category, description, None, [("lines", *edit) for edit in edits])


def kind_of(mutation_id: str) -> str:
    """The kind of a generated change, from its id."""
    return mutation_id.split("_")[1]


# ---------------------------------------------------------------------------- skills
def _steps(lines: list[str]) -> list[tuple[int, int]]:
    """Where each step of a SKILL.md's ``## Procedure`` block is: (index of its first line, index after its last).
    A step starts at a line that opens a list item, ``- ``."""
    head = next((i for i, line in enumerate(lines) if line.startswith("## Procedure")), None)
    if head is None:
        return []
    start = next(i for i in range(head, len(lines)) if lines[i].startswith("```yaml")) + 1
    end = next(i for i in range(start, len(lines)) if lines[i].startswith("```"))
    firsts = [i for i in range(start, end) if lines[i].startswith("- ")]
    return list(zip(firsts, [*firsts[1:], end], strict=True))


def _skill_changes(root: Path) -> Iterator[Mutation]:
    """The edits to the skills: to the steps of each procedure, and to the prose around it."""
    for path in sorted((root / "skills").glob("*/SKILL.md")):
        skill, rel = path.parent.name, path.relative_to(root).as_posix()
        lines = _read(root, rel)
        steps = _steps(lines)

        # ---- one step at a time: deleted, its condition negated, its guard deleted
        for k, (a, b) in enumerate(steps, 1):
            step = f"step {k} of the {skill} procedure ({lines[a].strip()[2:]})"
            yield _change(f"stepdel_{skill}_{k}", SKILL, f"Deleted: {step}.", (rel, a + 1, "".join(lines[a:b]), ""))
            for i in range(a, b):
                when = re.match(r"^(- |  )when: (.+)\n$", lines[i])
                if when:
                    negated = f"{when.group(1)}when: not ({when.group(2)})\n"
                    what = f"The condition negated ({when.group(2)}): {step}."
                    yield _change(f"whennot_{skill}_{k}", SKILL, what, (rel, i + 1, lines[i], negated))
            # the guard: the condition on the step's result, and what the agent does and says when it fails
            guard = [i for i in range(a, b) if re.match(r"^  (require|on_fail|fail_message): ", lines[i])]
            if guard:
                edits = [(rel, i + 1, lines[i], "") for i in reversed(guard)]
                yield _change(f"guarddel_{skill}_{k}", SKILL, f"The guard deleted: {step}.", *edits)

        # ---- two adjacent steps swapped
        for k, ((a, b), (_, c)) in enumerate(zip(steps, steps[1:], strict=False), 1):
            first, second = "".join(lines[a:b]), "".join(lines[b:c])
            what = f"Steps {k} and {k + 1} of the {skill} procedure swapped."
            yield _change(f"stepswap_{skill}_{k}", SKILL, what, (rel, a + 1, first + second, second + first))

        # ---- the prose, everything outside the procedure block: each bullet deleted, with the lines it wraps onto
        inside = range(steps[0][0], steps[-1][1]) if steps else range(0)
        bullets = [i for i, line in enumerate(lines) if line.startswith("- ") and i not in inside]
        for k, i in enumerate(bullets, 1):
            j = i + 1
            while j < len(lines) and lines[j].startswith("  ") and lines[j].strip():
                j += 1
            what = f"A rule deleted from the {skill} skill's prose ({lines[i].strip()[2:60]})."
            yield _change(f"ruledel_{skill}_{k}", SKILL, what, (rel, i + 1, "".join(lines[i:j]), ""))

        # ---- the first line of a paragraph that another one follows, joined with it: the same words, other lines
        front = next((i for i, line in enumerate(lines[1:], 1) if line.startswith("---")), 0)
        plain = [i for i, line in enumerate(lines) if i > front and i not in inside and re.match(r"^[A-Za-z`]", line)]
        pair = next((i for i in plain if i + 1 in plain), None)
        if pair is not None:
            old, joined = lines[pair] + lines[pair + 1], lines[pair].rstrip("\n") + " " + lines[pair + 1]
            what = f"Two lines of the {skill} skill's prose joined."
            yield _change(f"rewrap_{skill}_1", BENIGN, what, (rel, pair + 1, old, joined))


# ---------------------------------------------------------------------------- agents and settings
def _agent_changes(root: Path) -> Iterator[Mutation]:
    """Each tool of each agent taken off its list. The list is rewritten on one line."""
    for path in sorted((root / "agents").glob("*.yaml")):
        agent, rel = path.stem, path.relative_to(root).as_posix()
        lines = _read(root, rel)
        first = next((i for i, line in enumerate(lines) if line.startswith("tools: [")), None)
        if first is None:
            continue
        last = next(i for i in range(first, len(lines)) if "]" in lines[i])
        block = "".join(lines[first : last + 1])
        tools = yaml.safe_load(block)["tools"]
        for k, tool in enumerate(tools, 1):
            kept = ", ".join(t for t in tools if t != tool)
            what = f"The {agent} agent loses the `{tool}` tool."
            yield _change(f"tooldrop_{agent}_{k}", PROMPT, what, (rel, first + 1, block, f"tools: [{kept}]\n"))


def _yaml_value(value) -> str:
    """A setting's value as the config file writes it."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return f"[{', '.join(value)}]" if isinstance(value, list) else str(value)


def _setting_changes(root: Path) -> Iterator[Mutation]:
    """Each setting of ``config/runtime.yaml`` at other values, one change per value. The line keeps its comment."""
    rel = "config/runtime.yaml"
    lines = _read(root, rel)
    tools = sorted(name for _, _, name, _ in _tool_decorators(root))
    agents = {p.stem: yaml.safe_load(p.read_text()) or {} for p in (root / "agents").glob("*.yaml")}
    specialists = sorted(name for name, definition in agents.items() if not definition.get("orchestrator"))
    section = ""
    for i, line in enumerate(lines):
        if re.match(r"^\w+:\s*$", line):
            section = line.strip()[:-1]
        # a setting's line: its indent, its key, its value (a list in brackets or one word), and the rest (a comment)
        leaf = re.match(r"^(\s+)(\w+):(\s*)(\[[^\]]*\]|\S+)(.*\n)$", line)
        if not leaf:
            continue
        indent, key, gap, text, rest = leaf.groups()
        value = yaml.safe_load(text)
        # the other values to try, by the type of the setting
        if isinstance(value, bool):
            others = [not value]
        elif isinstance(value, int):
            others = sorted({0, value - 1, value + 1} - {value})
        elif isinstance(value, list) and value:
            others = [[x for x in value if x != item] for item in value]  # the list without each of its items
        elif isinstance(value, list):
            others = [[tool] for tool in tools]  # tools.disabled: each tool switched off in turn
        else:
            others = [a for a in specialists if a != value]  # routing.default_agent: every other specialist
        for k, other in enumerate(others, 1):
            new = f"{indent}{key}:{gap}{_yaml_value(other)}{rest}"
            what = f"{section}.{key} set to {_yaml_value(other)} (it is {text})."
            yield _change(f"setting_{key}_{k}", CONFIG, what, (rel, i + 1, line, new))


# ---------------------------------------------------------------------------- code
def _tool_decorators(root: Path) -> Iterator[tuple[str, ast.FunctionDef, str, ast.Call]]:
    """Every tool adapter of the app: (file, its function, the tool's name, its ``@tool(...)`` decorator)."""
    for path in sorted((root / "tools").glob("*.py")):
        rel = path.relative_to(root).as_posix()
        for node in ast.walk(ast.parse(path.read_text())):
            for deco in getattr(node, "decorator_list", []):
                if isinstance(deco, ast.Call) and getattr(deco.func, "id", "") == "tool":
                    yield rel, node, deco.args[0].value, deco


def _splice(lines: list[str], node: ast.AST, text: str) -> None:
    """Replace the source of ``node`` by ``text``, in ``lines`` (ast counts lines from 1 and columns from 0). The
    lines the node spans become one entry of the list. The files are plain ASCII, so ast's byte columns are
    character columns."""
    a, b = node.lineno - 1, node.end_lineno - 1
    lines[a : b + 1] = [lines[a][: node.col_offset] + text + lines[b][node.end_col_offset :]]


def _edit(rel: str, lines: list[str], first: ast.AST, last: ast.AST, edited: list[str]) -> tuple:
    """The edit that turns the lines from ``first`` to ``last`` into what ``edited`` has in their place. ``edited``
    is a copy of ``lines`` in which only nodes on those lines were spliced."""
    a, b = first.lineno - 1, last.end_lineno
    return rel, a + 1, "".join(lines[a:b]), "".join(edited[a : len(edited) - (len(lines) - b)])


def _tool_changes(root: Path) -> Iterator[Mutation]:
    """The edits to the tool adapters: a description cut short, and two arguments swapped in a call."""
    swaps: dict[str, int] = {}  # tool -> the swaps generated for it so far, to number them
    for rel, fn, name, deco in _tool_decorators(root):
        lines = _read(root, rel)
        # what the model is told about the tool (the decorator's third argument), cut to its first three words
        described = deco.args[2]
        words = described.value.split()
        if len(words) > 3:
            edited = list(lines)
            _splice(edited, described, json.dumps(" ".join(words[:3]).rstrip(",;:") + "."))
            what = f"The description of the `{name}` tool cut to its first three words."
            yield _change(f"tooldesc_{name}_1", PROMPT, what, _edit(rel, lines, described, described, edited))
        # the adapter's own parameters, by type: two of the same type can be passed in each other's place
        types = {a.arg: ast.dump(a.annotation) for a in fn.args.args[1:] if a.annotation is not None}
        for call in [n for n in ast.walk(fn) if isinstance(n, ast.Call)]:
            given = [*call.args, *(k.value for k in call.keywords)]
            passed = [v for v in given if isinstance(v, ast.Name) and v.id in types]
            for x, y in zip(passed, passed[1:], strict=False):
                if x.id == y.id or types[x.id] != types[y.id]:
                    continue
                edited = list(lines)
                _splice(edited, y, x.id)  # the later name first, so that the earlier one's columns still hold
                _splice(edited, x, y.id)
                swaps[name] = swaps.get(name, 0) + 1
                what = f"`{x.id}` and `{y.id}` swapped in a call of the `{name}` adapter."
                yield _change(f"argswap_{name}_{swaps[name]}", CODE, what, _edit(rel, lines, x, y, edited))


def _condition_changes(root: Path) -> Iterator[Mutation]:
    """The condition of every ``if`` of the services, the tools and the harness, negated."""
    for folder, category in (("services", CODE), ("tools", CODE), ("harness", RUNTIME)):
        for path in sorted((root / folder).rglob("*.py")):
            rel = path.relative_to(root).as_posix()
            lines = _read(root, rel)
            ifs = [n.test for n in ast.walk(ast.parse("".join(lines))) if isinstance(n, ast.If)]
            for k, test in enumerate(sorted(ifs, key=lambda t: (t.lineno, t.col_offset)), 1):
                condition = ast.get_source_segment("".join(lines), test)
                edited = list(lines)
                _splice(edited, test, f"not ({condition})")
                what = f"The condition at {rel}:{test.lineno} negated ({condition[:60]})."
                yield _change(f"condnot_{path.stem}_{k}", category, what, _edit(rel, lines, test, test, edited))


def _comment_changes(root: Path) -> Iterator[Mutation]:
    """A comment in front of every module of the services, the tools and the harness: no code changes."""
    for folder in ("services", "tools", "harness"):
        for path in sorted((root / folder).rglob("*.py")):
            rel = path.relative_to(root).as_posix()
            first = _read(root, rel)[0]
            name = path.parent.name if path.stem == "__init__" else path.stem
            what = f"A comment added at the top of {rel}."
            yield _change(f"comment_{name}_1", BENIGN, what, (rel, 1, first, "# Reviewed.\n" + first))


# ---------------------------------------------------------------------------- the starting data
def _set_in_fixture(path: tuple, value):
    """The edit that sets one value of ``fixtures/base.json``, as a function of the app's folder (a ``custom``
    edit). The file is written the way it is kept, so that nothing else in it changes."""

    def edit(sut_dir: Path):
        file = Path(sut_dir) / "fixtures" / "base.json"
        data = json.loads(file.read_text())
        node = data
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value
        file.write_text(json.dumps(data, indent=2) + "\n")

    return edit


def _fixture_changes(root: Path) -> Iterator[Mutation]:
    """A value of the starting data replaced by the next value the same key has elsewhere in the data, for the
    keys that take a few values and repeat them (a page's status, a review's, a link's reachability, ...) and
    for the switches (a consent)."""
    data = json.loads((root / "fixtures" / "base.json").read_text())

    def leaves(node, path=()):
        """Every value of the data that is text or a switch, with the path of keys that leads to it."""
        if isinstance(node, dict):
            for key, child in node.items():
                yield from leaves(child, (*path, key))
        elif isinstance(node, (str, bool)):
            yield path, node

    # The values each key takes, over the whole file. A key is a path without the record it is in: the status
    # of the review of page p4 is a ``pages.review.status``, and the consent of subject s1 one of the ``consents``.
    def key_of(path):
        return ".".join(path[:1] + path[2:])

    taken: dict[str, list] = {}
    for path, value in leaves(data):
        taken.setdefault(key_of(path), []).append(value)
    counts: dict[str, int] = {}
    for path, value in leaves(data):
        key = key_of(path)
        options = sorted(set(taken[key]), key=str)
        # a key with a few values that come back is a choice among them; free text (a title, an e-mail) is not
        if not (isinstance(value, bool) or (2 <= len(options) <= 4 and len(taken[key]) > len(options))):
            continue
        other = (not value) if isinstance(value, bool) else options[(options.index(value) + 1) % len(options)]
        counts[key] = counts.get(key, 0) + 1
        what = f"{'.'.join(path)} set to {json.dumps(other)} in the starting data (it is {json.dumps(value)})."
        edit = ("custom", _set_in_fixture(path, other))  # not a text edit: the file is read, changed and written
        yield Mutation(f"g_fixture_{key}_{counts[key]}", FIXTURE, what, None, [edit])


# ---------------------------------------------------------------------------- the whole set
MAKERS = (
    _skill_changes,
    _agent_changes,
    _setting_changes,
    _tool_changes,
    _condition_changes,
    _comment_changes,
    _fixture_changes,
)


def generate(root: Path = SUT_ROOT) -> list[Mutation]:
    """Every generated change of the app at ``root``, in a fixed order."""
    changes = [m for make in MAKERS for m in make(Path(root))]
    assert len({m.id for m in changes}) == len(changes), "two generated changes share an id"
    return changes


@lru_cache(maxsize=4)
def generated(root: Path = SUT_ROOT) -> dict[str, Mutation]:
    """The generated changes of the app at ``root``, by id; ``catalog.get_mutation`` looks an id up among those of
    ``traceeval/sut``. Kept after the first call: generating reads and parses every file of the app."""
    return {m.id: m for m in generate(root)}


def _rank(mutation_id: str, seed: int) -> str:
    """Where a change falls in a fixed shuffle of the ids: a hash of the id and the seed, the same in every
    process (``hash()`` is not)."""
    return hashlib.sha256(f"{seed}:{mutation_id}".encode()).hexdigest()


def sample(changes: list[Mutation], per_kind: int, seed: int = 0) -> list[Mutation]:
    """At most ``per_kind`` changes of each kind. Which ones is fixed by the ids and the seed alone, so the same
    call always draws the same changes."""
    kept: dict[str, list[str]] = {}
    for m in sorted(changes, key=lambda m: _rank(m.id, seed)):
        if len(kept.setdefault(kind_of(m.id), [])) < per_kind:
            kept[kind_of(m.id)].append(m.id)
    chosen = {mid for ids in kept.values() for mid in ids}
    return [m for m in changes if m.id in chosen]  # in the order they were generated


def split(ids: list[str], seed: int = 0) -> tuple[list[str], list[str]]:
    """Generated changes in two halves, kind by kind: those a strategy may learn from, and those it is evaluated
    on, which it has never seen. The half a change falls in is fixed by the ids and the seed: within each kind,
    in the order of the fixed shuffle, every other change is held out."""
    by_kind: dict[str, list[str]] = {}
    for mid in sorted(ids, key=lambda mid: _rank(mid, seed)):
        by_kind.setdefault(kind_of(mid), []).append(mid)
    held_out = {mid for members in by_kind.values() for mid in members[1::2]}
    return [mid for mid in ids if mid not in held_out], [mid for mid in ids if mid in held_out]
