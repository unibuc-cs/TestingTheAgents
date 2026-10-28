"""The 35 controlled changes ("mutations"), written as data.

A mutation is a controlled change to the system under test, applied as a real file edit. The
experiment never shows the selectors the mutation label - only the diff. ``regression`` says whether
we *expect* at least one test to reveal it; the report checks that expectation (sanity line).

Each entry: id, category, description, regression?, edits. An edit is one of
    ("replace",      file, old, new)             exact text replacement (old must occur exactly once)
    ("delete_line",  file, text_in_line)         delete the single line containing the text
    ("delete_block", file, start_text, end_text) delete from the start line up to (not incl.) the end line
    ("append",       file, text)                 append text to the file
Anchors are literal text: if a SUT source is reformatted, re-anchor here (the operators raise).
"""

from dataclasses import dataclass
from pathlib import Path

from . import operators as op

CODE, RUNTIME, SKILL, PROMPT, CONFIG, COMBINED, BENIGN = (
    "code",
    "runtime",
    "skill",
    "prompt",
    "config",
    "combined",
    "benign",
)


@dataclass
class Mutation:
    id: str
    category: str
    description: str
    expected_regression: bool
    edits: list[tuple]

    def apply(self, sut_dir: Path):
        for edit in self.edits:
            kind, args = edit[0], edit[1:]
            if kind == "replace":
                op.replace(sut_dir, *args)
            elif kind == "delete_line":
                op.delete_line(sut_dir, *args)
            elif kind == "delete_block":
                op.delete_block(sut_dir, *args)
            elif kind == "append":
                op.append(sut_dir, *args)
            elif kind == "custom":
                args[0](sut_dir)
            else:
                raise ValueError(f"unknown edit kind {kind}")


def _reorder_config_sections(sut_dir: Path):
    """Rewrite config comments and reverse the order of the top-level sections (values unchanged)."""
    path = sut_dir / "config" / "runtime.yaml"
    head = "# Runtime configuration of the ContentOps agent platform.\n"
    body = path.read_text()[len(head) :]
    sections = [s for s in body.split("\n\n") if s.strip()]
    path.write_text(
        "# Runtime configuration of the ContentOps agent platform (sections re-ordered; values unchanged).\n"
        + "\n\n".join(reversed(sections))
        + "\n"
    )


_NEW_TOOL = """

@tool("get_page_stats", "read", "Basic statistics about a page (versions, links, assets).", {"page_id": "page identifier"})
def get_page_stats(ctx: ToolContext, page_id: str):
    page = repository.get_page(ctx.state, page_id)
    return {"page_id": page_id, "versions": len(page["versions"]), "links": len(page.get("links", [])),
            "assets": len(page.get("assets", []))}
"""

_SEO_SIG_OLD = (
    "def get_seo_report(state, page_id: str, max_title_length: int = 60, require_description: bool = True) -> dict:"
)
_SEO_SIG_NEW = (
    "def get_seo_report(\n"
    "    state, page_id: str, max_title_length: int = 60, require_description: bool = True, max_keywords: int = 5\n"
    ") -> dict:"
)
_SEO_KW_OLD = '    if not meta.get("keywords"):\n        issues.append({"field": "keywords", "issue": "missing"})'
_SEO_KW_NEW = _SEO_KW_OLD + (
    '\n    elif len(meta.get("keywords", [])) > max_keywords:\n'
    '        issues.append({"field": "keywords", "issue": "too_many", "count": len(meta["keywords"])})'
)
_SEO_CALL_OLD = '        require_description=bool(ctx.config.get("seo.require_description")),\n'
_SEO_CALL_NEW = _SEO_CALL_OLD + '        max_keywords=int(ctx.config.get("seo.max_keywords") or 5),\n'

# fmt: off
MUTATIONS: list[Mutation] = [
    # ---------------------------------------------------------------- code: tool adapters, services, harness
    Mutation('code_metadata_arg_swap', CODE, 'Tool adapter maps the title into the description argument.', True,
             [('replace', 'tools/content_tools.py', 'title=title, description=description,', 'title=title, description=title,')]),
    Mutation('code_retry_drop_idempotency', CODE, 'Retries no longer carry idempotency keys (duplicates after lost acks).', True,
             [('replace', 'harness/retry.py', 'key = new_idempotency_key() if (is_write and idempotency_enabled) else None', 'key = None')]),
    Mutation('code_retry_disabled', CODE, 'Retry helper gives up after the first transient failure.', True,
             [('replace', 'harness/retry.py', 'if attempt > retries:', 'if attempt > 0:')]),
    Mutation('code_approval_gate_bypass', CODE, 'Dispatcher no longer enforces approval tokens for guarded tools.', True,
             [('replace', 'harness/dispatcher.py', 'return spec.kind == "guarded" and name in gated', 'return False')]),
    Mutation('code_links_external_lenient', CODE, 'Link validation treats every external URL as reachable.', True,
             [('replace', 'services/links.py', 'status = _external_status(state, link)', 'status = "ok"')]),
    Mutation('code_router_phrase_weight', CODE, 'Router no longer gives phrase triggers extra weight.', True,
             [('replace', 'harness/router.py', 'score += 2  # multi-word trigger matched as a phrase', 'score += 1  # multi-word trigger matched as a phrase')]),
    Mutation('code_get_page_review_flag', CODE, 'Shared get_page reports review_approved for merely requested reviews.', True,
             [('replace', 'tools/content_tools.py', '"review_approved": page["review"]["status"] == "approved",', '"review_approved": page["review"]["status"] == "requested",')]),
    Mutation('code_edit_keeps_review', CODE, 'Editing a page no longer invalidates its approved review.', True,
             [('delete_line', 'services/repository.py', 'page["review"] = {"status": "none", "reviewer": None}  # edits invalidate')]),
    # ---------------------------------------------------------------- runtime (agent loop)
    Mutation('code_termination_off_by_six', RUNTIME, 'Agent loop stops six tool calls before the configured budget.', True,
             [('replace', 'harness/runtime.py', 'if self.steps >= max_tool_calls:', 'if self.steps >= max_tool_calls - 6:')]),
    Mutation('code_delegation_depth_zero', RUNTIME, 'Delegation depth zero: the orchestrator cannot hand off to specialists.', True,
             [('replace', 'harness/runtime.py', 'MAX_DELEGATION_DEPTH = 2', 'MAX_DELEGATION_DEPTH = 0')]),
    # ---------------------------------------------------------------- skills
    Mutation('skill_publish_drop_link_validation', SKILL, 'Publishing skill no longer validates links before publishing.', True,
             [('delete_line', 'skills/publishing-workflow/SKILL.md', '- include: link-validation')]),
    Mutation('skill_publish_drop_permission_check', SKILL, 'Publishing skill no longer checks the permission.', True,
             [('delete_line', 'skills/publishing-workflow/SKILL.md', '- include: governance-checks')]),
    Mutation('skill_authoring_drop_metadata', SKILL, 'Authoring skill no longer sets SEO metadata when creating a page.', True,
             [('delete_block', 'skills/page-authoring/SKILL.md', '- id: meta', '- include: link-validation')]),
    Mutation('skill_translation_wrong_default', SKILL, 'Translation skill hard-codes en-US instead of the configured locales.', True,
             [('replace', 'skills/translation/SKILL.md', "set: {locales: =config('translation.default_locales')}", "set: {locales: ['en-US']}")]),
    Mutation('skill_rollback_restores_latest', SKILL, 'Rollback skill restores the latest version instead of the requested one.', True,
             [('replace', 'skills/rollback/SKILL.md', 'args: {page_id: $page_id, version: $version}', 'args: {page_id: $page_id, version: =len(result.versions.versions)}')]),
    Mutation('skill_linkval_ignore_assets', SKILL, 'Shared link-validation skill tolerates broken asset references.', True,
             [('replace', 'skills/link-validation/SKILL.md', 'require: last.broken_count == 0', "require: last.broken_count == 0 or all(b['kind'] == 'asset' for b in last.broken)")]),
    Mutation('skill_governance_drop_consent', SKILL, 'Governance skill no longer checks consent before exporting.', True,
             [('delete_block', 'skills/governance-ops/SKILL.md', '- id: consent', '- id: export')]),
    Mutation('skill_seo_drop_length_guard', SKILL, 'SEO skill no longer refuses over-long titles.', True,
             [('delete_block', 'skills/seo-metadata/SKILL.md', "- when: ctx.get('seo_title') is not None and len(", '- id: meta')]),
    # ---------------------------------------------------------------- prompts / agent definitions
    Mutation('prompt_publishing_triggers_removed', PROMPT, "Publishing agent loses its 'take down' routing triggers.", True,
             [('replace', 'agents/publishing.yaml', 'triggers: [publish, "go live", live, unpublish, "take down", "take it down", schedule, release, launch, retract]', 'triggers: [publish, "go live", live, unpublish, schedule, release, launch, retract]')]),
    Mutation('prompt_seo_tool_removed', PROMPT, 'SEO agent loses access to set_page_metadata.', True,
             [('replace', 'agents/seo.yaml', 'tools: [get_page, get_seo_report, set_page_metadata, check_permission]', 'tools: [get_page, get_seo_report, check_permission]')]),
    Mutation('prompt_translation_intents_reordered', PROMPT, "Translation intents re-ordered: 'create' now wins ties.", True,
             [('replace', 'agents/translation.yaml', 'intents:\n  status: [status, progress, "how far", done]\n  create: [translate, localize, localise, translation, into]', 'intents:\n  create: [translate, localize, localise, translation, into]\n  status: [status, progress, "how far", done]')]),
    # ---------------------------------------------------------------- configuration
    Mutation('config_disable_validate_links', CONFIG, 'Feature flag disables validate_links platform-wide.', True,
             [('replace', 'config/runtime.yaml', 'disabled: []', 'disabled: [validate_links]')]),
    Mutation('config_require_review_false', CONFIG, 'Pages no longer need an approved review before publishing.', True,
             [('replace', 'config/runtime.yaml', 'require_review: true', 'require_review: false')]),
    Mutation('config_max_tool_calls_5', CONFIG, 'Step budget reduced from 12 to 5 tool calls.', True,
             [('replace', 'config/runtime.yaml', 'max_tool_calls: 12', 'max_tool_calls: 5')]),
    Mutation('config_retries_0', CONFIG, 'Transient failures are no longer retried.', True,
             [('replace', 'config/runtime.yaml', 'retries: 2 ', 'retries: 0 ')]),
    Mutation('config_seo_title_20', CONFIG, 'Maximum SEO title length reduced from 60 to 20.', True,
             [('replace', 'config/runtime.yaml', 'max_title_length: 60', 'max_title_length: 20')]),
    Mutation('config_default_agent_publishing', CONFIG, 'Untriggered requests go to publishing instead of authoring.', True,
             [('replace', 'config/runtime.yaml', 'default_agent: authoring', 'default_agent: publishing')]),
    Mutation('config_approval_drop_unpublish', CONFIG, 'unpublish_page no longer requires an approval token.', True,
             [('replace', 'config/runtime.yaml', 'requires_approval: [approve_review, export_user_data, unpublish_page]', 'requires_approval: [approve_review, export_user_data]')]),
    # ---------------------------------------------------------------- combined (code + config; each alone is harmless)
    Mutation('combined_seo_keyword_limit', COMBINED, 'SEO report gains a keyword-count rule (code) and a very low limit (config).', True,
             [('replace', 'services/seo.py', _SEO_SIG_OLD, _SEO_SIG_NEW), ('replace', 'services/seo.py', _SEO_KW_OLD, _SEO_KW_NEW), ('replace', 'tools/translation_tools.py', _SEO_CALL_OLD, _SEO_CALL_NEW), ('replace', 'config/runtime.yaml', '  require_description: true\n', '  require_description: true\n  max_keywords: 2\n')]),
    # ---------------------------------------------------------------- benign (must not be revealed by any test)
    Mutation('benign_skill_prose_reflow', BENIGN, 'Prose of the publishing skill reworded; procedure untouched.', False,
             [('replace', 'skills/publishing-workflow/SKILL.md', 'Use this skill when the user wants a page published, scheduled for publication, or taken down.', 'Apply this skill whenever a user asks to publish a page, to schedule its publication, or to take a page down.')]),
    Mutation('benign_code_comment_docstring', BENIGN, 'Comment and docstring edits in the links service (AST-equivalent).', False,
             [('replace', 'services/links.py', '"""Link validation: internal page links, external URLs and asset references."""', '"""Link validation.\n\nChecks internal page links, external URLs (via the reachability table) and asset references.\n"""'), ('replace', 'services/links.py', '    for asset_id in page.get("assets", []):', '    # attached assets are validated as well, not only inline asset links\n    for asset_id in page.get("assets", []):')]),
    Mutation('benign_code_rename_locals', BENIGN, 'Local variables renamed in the workflow service.', False,
             [('replace', 'services/workflow.py', '    cached = state.idempotent(idempotency_key)\n    if cached:\n        return cached\n    page = get_page(state, page_id)\n    page["status"] = "published"', '    previous = state.idempotent(idempotency_key)\n    if previous:\n        return previous\n    target = get_page(state, page_id)\n    page = target\n    page["status"] = "published"')]),
    Mutation('benign_config_comments_reordered', BENIGN, 'Config comments rewritten and sections re-ordered (same values).', False,
             [('custom', _reorder_config_sections)]),
    Mutation('benign_new_unused_tool', BENIGN, 'A new tool is registered but no agent may use it.', False,
             [('append', 'tools/content_tools.py', _NEW_TOOL)]),
    Mutation('benign_orchestrator_prompt_wording', BENIGN, 'Orchestrator system prompt reworded.', False,
             [('replace', 'agents/orchestrator.yaml', 'You never perform content operations yourself:', 'You do not carry out content operations on your own:')]),
]
# fmt: on


def get_mutation(mid: str) -> Mutation:
    for m in MUTATIONS:
        if m.id == mid:
            return m
    raise KeyError(mid)
