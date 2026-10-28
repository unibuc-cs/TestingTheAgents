"""placement clause -> static lint over the variant's files (L4): where code must and must not live.

    rules:
      - define: {function: review_age_ok, in: services/workflow.py}      the function exists there
      - forbid_import: {module: datetime, in: [tools, harness]}           no import of the module there
      - forbid_name: {name: TransientError, in: [tools]}                  identifier not used there
      - forbid_literal: {value: 60, in: [tools, skills/seo-metadata/SKILL.md]}   literal not written there
      - skill_order: {skill: publishing-workflow, first: {include: link-validation}, then: {call: publish_page}}
            in the skill's procedure, the step matching `first` comes before the step matching `then`
`in` is a file or a directory prefix (list allowed). Python files are inspected via their AST; other
files textually.
"""

import ast
import re

from ..model import ClauseResult


def check(clause, ctx) -> ClauseResult:
    problems, notes = [], []
    for rule in clause["rules"]:
        ((kind, spec),) = rule.items()
        fn = _RULES[kind]
        problems += fn(spec, ctx.model)
        notes.append(f"{kind} {spec}")
    status = "fail" if problems else "pass"
    summary = f"{len(clause['rules'])} rules hold" if not problems else "; ".join(problems[:3])
    return ClauseResult(clause.id, "placement", "L4", status, summary, notes + problems)


def _files(model, where) -> list[str]:
    wheres = where if isinstance(where, list) else [where]
    out = []
    for rel in model.files:
        for w in wheres:
            if rel == w or rel.startswith(w.rstrip("/") + "/"):
                out.append(rel)
                break
    return out


def _define(spec, model) -> list[str]:
    rel = spec["in"]
    names = {q for q, _, _ in model.functions.get(rel, [])}
    return [] if spec["function"] in names else [f"{spec['function']} is not defined in {rel}"]


def _forbid_import(spec, model) -> list[str]:
    out = []
    for rel in _files(model, spec["in"]):
        if not rel.endswith(".py"):
            continue
        for node in ast.walk(ast.parse(model.files[rel])):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                mods = [node.module or ""]
            if any(m == spec["module"] or m.startswith(spec["module"] + ".") for m in mods):
                out.append(f"{rel} imports {spec['module']} (line {node.lineno})")
    return out


def _forbid_name(spec, model) -> list[str]:
    out = []
    for rel in _files(model, spec["in"]):
        if rel.endswith(".py"):
            for node in ast.walk(ast.parse(model.files[rel])):
                if (isinstance(node, ast.Name) and node.id == spec["name"]) or (
                    isinstance(node, ast.Attribute) and node.attr == spec["name"]
                ):
                    out.append(f"{rel} uses {spec['name']} (line {node.lineno})")
                    break
        elif re.search(rf"\b{re.escape(spec['name'])}\b", model.files[rel]):
            out.append(f"{rel} mentions {spec['name']}")
    return out


def _forbid_literal(spec, model) -> list[str]:
    out, value = [], spec["value"]
    for rel in _files(model, spec["in"]):
        if rel.endswith(".py"):
            for node in ast.walk(ast.parse(model.files[rel])):
                if isinstance(node, ast.Constant) and type(node.value) is type(value) and node.value == value:
                    out.append(f"{rel} hard-codes {value!r} (line {node.lineno})")
                    break
        else:
            text = model.files[rel]
            body = re.search(r"```yaml\n(.*?)```", text, re.S)
            text = body.group(1) if body else text
            if re.search(rf"(?<![\w.]){re.escape(str(value))}(?![\w.])", text):
                out.append(f"{rel} hard-codes {value!r}")
    return out


def _skill_order(spec, model) -> list[str]:
    steps = model.skill_procedure(spec["skill"])

    def index(pattern):
        for i, step in enumerate(steps):
            if all(step.get(k) == v for k, v in pattern.items()):
                return i
        return None

    first, then = index(spec["first"]), index(spec["then"])
    if first is None:
        return [f"skill {spec['skill']}: no step {spec['first']}"]
    if then is None:
        return [f"skill {spec['skill']}: no step {spec['then']}"]
    return [] if first < then else [f"skill {spec['skill']}: {spec['first']} comes after {spec['then']}"]


_RULES = {
    "define": _define,
    "forbid_import": _forbid_import,
    "forbid_name": _forbid_name,
    "forbid_literal": _forbid_literal,
    "skill_order": _skill_order,
}
