"""Probe (read-only on the repo): edits whose change set is empty or links to no test, on scratch copies."""

import json
import sys
from pathlib import Path

from traceeval.experiment.sutloader import copy_sut
from traceeval.mutation.changeset import compute_changeset
from traceeval.selection.base import matches
from traceeval.sut import SUT_ROOT
from traceeval.sut.harness.config import Config
from traceeval.sut.harness.skills import SkillLoader, render_procedure, replace_procedure

scratch = Path(sys.argv[1])
history = Path(sys.argv[2])

# baseline deps per test (union over reps)
deps: dict[str, set[str]] = {}
agents_of: dict[str, set[str]] = {}
with open(history / "history" / "baseline.jsonl", encoding="utf-8") as fh:
    for line in fh:
        if line.strip():
            r = json.loads(line)
            deps.setdefault(r["test_id"], set()).update(r["deps"])
            agents_of.setdefault(r["test_id"], set()).update(r["agents"])


def affected(cs):
    return sorted(t for t, d in deps.items() if any(matches(c, d) for c in cs.components))


def prompt_of(sut_dir: Path, agent_skill: str) -> str:
    cfg = Config.load(sut_dir / "config" / "runtime.yaml")
    loader = SkillLoader(sut_dir / "skills")
    skill = loader.load(agent_skill)
    return replace_procedure(skill.text, render_procedure(loader.expand(agent_skill), cfg))


def edit(name: str, rel: str, old: str, new: str, count_ok: bool = True) -> Path:
    d = copy_sut(scratch / name)
    p = d / rel
    text = p.read_text()
    assert text.count(old) == 1, (name, text.count(old))
    p.write_text(text.replace(old, new))
    return d


base_prompt = prompt_of(SUT_ROOT, "publishing-workflow")

# 1. reorder the keys of a step's args in a skill procedure
d = edit(
    "args_order",
    "skills/publishing-workflow/SKILL.md",
    "args: {page_id: $page_id, reviewer_id: $approver}",
    "args: {reviewer_id: $approver, page_id: $page_id}",
)
cs = compute_changeset(SUT_ROOT, d)
print(
    "1 args reordered: components",
    sorted(cs.ids()),
    "| prompt changed:",
    prompt_of(d, "publishing-workflow") != base_prompt,
)

# 2. quote a value in the front matter (same parsed YAML)
d = edit(
    "front_quote",
    "skills/publishing-workflow/SKILL.md",
    "description: Publish, schedule or unpublish a page safely (permission, link and review gates).",
    'description: "Publish, schedule or unpublish a page safely (permission, link and review gates)."',
)
cs = compute_changeset(SUT_ROOT, d)
print(
    "2 front matter quoted: components",
    sorted(cs.ids()),
    "| prompt changed:",
    prompt_of(d, "publishing-workflow") != base_prompt,
)

# 3. re-wrap a prose paragraph (whitespace only)
d = edit(
    "prose_wrap",
    "skills/publishing-workflow/SKILL.md",
    "Order of operations: fetch the page, check the permission for the requested action, then (for\npublishing",
    "Order of operations: fetch the page, check the permission for the requested action,\nthen (for publishing",
)
cs = compute_changeset(SUT_ROOT, d)
print(
    "3 prose re-wrapped: components",
    sorted(cs.ids()),
    "| prompt changed:",
    prompt_of(d, "publishing-workflow") != base_prompt,
)

# 3b. turn the rules list into one paragraph (whitespace only: newlines and the list markers stay as words)
d = edit(
    "prose_blank",
    "skills/publishing-workflow/SKILL.md",
    "## Rules\n- Never publish a page whose links failed validation.\n- Never call",
    "## Rules\n- Never publish a page whose links failed validation. - Never call",
)
cs = compute_changeset(SUT_ROOT, d)
print(
    "3b list items joined: components",
    sorted(cs.ids()),
    "| prompt changed:",
    prompt_of(d, "publishing-workflow") != base_prompt,
)

# 4. the description of a tool the publishing agent is offered
d = edit(
    "tool_desc",
    "tools/publish_tools.py",
    '"Schedule a page to be published at a given time."',
    '"Publish a page, now or at a given time (preferred)."',
)
cs = compute_changeset(SUT_ROOT, d)
hit = affected(cs)
offered = sorted(t for t, a in agents_of.items() if "publishing" in a)
print("4 tool description: components", sorted(cs.ids()))
print("   tests linked by observed deps:", len(hit), hit)
print("   tests in which the publishing agent ran (and saw the schema):", len(offered))

# 5. the description of the delegation tool
d = edit(
    "route_desc",
    "tools/control_tools.py",
    '"Delegate work to a specialist agent: the whole request, or one step of a plan."',
    '"Delegate one step of a plan to a specialist agent."',
)
cs = compute_changeset(SUT_ROOT, d)
hit = affected(cs)
print("5 route_to_agent description: components", sorted(cs.ids()), "| tests linked:", len(hit), hit[:5])
print("   tests in which the orchestrator ran:", sum("orchestrator" in a for a in agents_of.values()))
print("   any test with tool:route_to_agent dep:", any("tool:route_to_agent" in d_ for d_ in deps.values()))

# 6. a tool module dropped from tools/__init__.py
d = edit("init_drop", "tools/__init__.py", "    site_tools,\n", "")
cs = compute_changeset(SUT_ROOT, d)
hit = affected(cs)
print("6 site_tools no longer imported: components", sorted(cs.ids()), "| tests linked:", len(hit))
print(
    "   tests that call a site tool:",
    sum(bool({"tool:audit_site", "tool:get_page_metrics", "tool:fix_alt_text"} & d_) for d_ in deps.values()),
)

# 7. a module-level constant in a file with functions (the file-level fallback)
d = edit(
    "role_table",
    "services/permissions.py",
    '"publisher": {"read", "publish", "unpublish", "schedule", "request_review"},',
    '"publisher": {"read", "publish", "schedule", "request_review"},',
)
cs = compute_changeset(SUT_ROOT, d)
hit = affected(cs)
print("7 ROLE_ACTIONS edited: components", sorted(cs.ids()), "| tests linked:", len(hit))

# 8. a default argument on a def line
d = edit("default_arg", "tools/content_tools.py", 'template: str = "article"):', 'template: str = "landing"):')
cs = compute_changeset(SUT_ROOT, d)
hit = affected(cs)
line_ids = [c.id for c in cs.components if c.kind == "line"]
line_hit = sorted(t for t, d_ in deps.items() if any(i in d_ for i in line_ids))
print(
    "8 default argument: components",
    sorted(cs.ids()),
    "| tests linked:",
    len(hit),
    "| tests that executed a changed line:",
    len(line_hit),
)

# 9. second line of an implicitly concatenated prompt string inside a function
d = edit(
    "prompt_const",
    "harness/backends/llm_openai.py",
    '"- When a step of a procedure fails, stop and explain; do not improvise around guards.\\n"',
    '"- When a step of a procedure fails, explain.\\n"',
)
cs = compute_changeset(SUT_ROOT, d)
line_ids = [c.id for c in cs.components if c.kind == "line"]
line_hit = sorted(t for t, d_ in deps.items() if any(i in d_ for i in line_ids))
print(
    "9 operating rule edited: components",
    sorted(cs.ids()),
    "| tests linked:",
    len(affected(cs)),
    "| tests that executed a changed line:",
    len(line_hit),
)

# 10. fixture
d = edit("fixture", "fixtures/base.json", '"decision": "approve"', '"decision": "refuse"')
cs = compute_changeset(SUT_ROOT, d)
print("10 fixture edited: components", sorted(cs.ids()), "| tests linked:", len(affected(cs)))

# 11. a new agent definition
d = copy_sut(scratch / "new_agent")
(d / "agents" / "legal.yaml").write_text(
    "name: legal\nversion: 1\ndescription: Publishes, schedules and takes pages down for legal reasons.\n"
    "system_prompt: |\n  You are the legal agent.\nskills: []\ntools: []\ntriggers: [publish, legal]\n"
)
cs = compute_changeset(SUT_ROOT, d)
print("11 new agent file: components", sorted(cs.ids()), "| tests linked:", len(affected(cs)))
