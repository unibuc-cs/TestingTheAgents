"""The 43 controlled changes ("mutations"), written as data.

A mutation is a controlled change to the system under test, applied as a real file edit. The
experiment never shows the selectors the mutation label - only the diff. ``regression`` says whether
we *expect* at least one test to reveal it; the report checks that expectation (sanity line).

Each entry: id, category, description, regression?, edits. An edit is one of
    ("replace",      file, old, new)             exact text replacement (old must occur exactly once)
    ("delete_line",  file, text_in_line)         delete the single line containing the text
    ("delete_block", file, start_text, end_text) delete from the start line up to (not incl.) the end line
    ("append",       file, text)                 append text to the file
    ("custom",       function)                   call function(sut_dir), for an edit no anchor can express
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
             [('replace', 'harness/retry.py', 'key = idempotency_key(operation) if (is_write and idempotency_enabled) else None', 'key = None')]),
    Mutation('code_approval_gate_bypass', CODE, 'Dispatcher no longer enforces approval tokens for guarded tools.', True,
             [('replace', 'harness/dispatcher.py', 'return spec.kind == "guarded" and name in gated', 'return False')]),
    Mutation('code_links_external_lenient', CODE, 'Link validation treats every external URL as reachable.', True,
             [('replace', 'services/links.py', 'status = _external_status(state, link)', 'status = "ok"')]),
    Mutation('code_get_page_review_flag', CODE, 'Shared get_page reports review_approved for merely requested reviews.', True,
             [('replace', 'tools/content_tools.py', '"review_approved": page["review"]["status"] == "approved",', '"review_approved": page["review"]["status"] == "requested",')]),
    Mutation('code_edit_keeps_review', CODE, 'Editing a page no longer invalidates its approved review.', True,
             [('delete_line', 'services/repository.py', 'page["review"] = {"status": "none", "reviewer": None}  # edits invalidate')]),
    # ---------------------------------------------------------------- runtime (agent loop)
    Mutation('code_termination_off_by_six', RUNTIME, "Agent loop stops each agent six tool calls before its configured budget.", True,
             [('replace', 'harness/runtime.py', 'if steps >= max_tool_calls or', 'if steps >= max_tool_calls - 6 or')]),
    Mutation('code_delegation_truncates_answer', RUNTIME, "Delegation passes on only the first 40 characters of the specialist's answer.", True,
             [('replace', 'harness/runtime.py', 'return {"agent": target, "delegated_response": message}', 'return {"agent": target, "delegated_response": message[:40]}')]),
    # ---------------------------------------------------------------- skills
    Mutation('skill_publish_drop_link_validation', SKILL, 'Publishing skill no longer validates links before publishing.', True,
             [('delete_line', 'skills/publishing-workflow/SKILL.md', '- include: link-validation')]),
    Mutation('skill_publish_drop_permission_check', SKILL, 'Publishing no longer checks the permission (procedure step, prose and the shared permission skill removed).', True,
             [('delete_line', 'skills/publishing-workflow/SKILL.md', '- include: governance-checks'),
              ('replace', 'skills/publishing-workflow/SKILL.md', 'fetch the page, check the permission for the requested action, then (for', 'fetch the page, then (for'),
              ('replace', 'skills/publishing-workflow/SKILL.md', 'but does require the `unpublish` permission and an approval token.', 'but does require an approval token.'),
              ('delete_line', 'skills/publishing-workflow/SKILL.md', '- Never call `publish_page` or `schedule_publish` for a user without the matching permission.'),
              ('replace', 'agents/publishing.yaml', 'skills: [publishing-workflow, governance-checks, link-validation]', 'skills: [publishing-workflow, link-validation]')]),
    Mutation('skill_authoring_drop_metadata', SKILL, 'Authoring skill no longer sets SEO metadata when creating a page.', True,
             [('delete_block', 'skills/page-authoring/SKILL.md', '- id: meta', '- include: link-validation')]),
    Mutation('skill_translation_wrong_default', SKILL, 'Translation skill hard-codes en-US instead of the configured locales.', True,
             [('replace', 'skills/translation/SKILL.md', "set: {locales: =config('translation.default_locales')}", "set: {locales: ['en-US']}")]),
    Mutation('skill_rollback_drop_permission_check', SKILL, 'Rollback no longer checks the permission (procedure step, prose and the shared permission skill removed; the service still refuses).', True,
             [('delete_line', 'skills/rollback/SKILL.md', '- include: governance-checks'),
              ('replace', 'skills/rollback/SKILL.md', 'content change: check the permission, list the versions', 'content change: list the versions'),
              ('replace', 'agents/maintenance.yaml', 'skills: [rollback, governance-checks, link-validation]', 'skills: [rollback, link-validation]')]),
    Mutation('skill_rollback_restores_latest', SKILL, 'Rollback skill restores the latest version instead of the requested one.', True,
             [('replace', 'skills/rollback/SKILL.md', 'args: {page_id: $page_id, version: $version}', 'args: {page_id: $page_id, version: =len(result.versions.versions)}')]),
    Mutation('skill_linkval_ignore_assets', SKILL, 'Shared link-validation skill tolerates broken asset references (procedure and prose).', True,
             [('replace', 'skills/link-validation/SKILL.md', 'require: last.broken_count == 0', "require: last.broken_count == 0 or all(b['kind'] == 'asset' for b in last.broken)"),
              ('replace', 'skills/link-validation/SKILL.md', 'Internal links must resolve to existing pages, external URLs must be\nreachable and asset references must point to existing assets. If anything is broken, stop and report\nthe broken links; a page with broken links must never be published.', 'Internal links must resolve to existing pages and external URLs must be\nreachable. If one of them is broken, stop and report the broken links; a page with broken links must\nnever be published. A broken asset reference does not block: it is fixed later in the DAM.')]),
    Mutation('skill_governance_drop_consent', SKILL, 'Governance skill no longer checks consent before exporting (procedure step and prose).', True,
             [('delete_block', 'skills/governance-ops/SKILL.md', '- id: consent', '- id: export'),
              ('replace', 'skills/governance-ops/SKILL.md', 'permission, check that the data subject has given consent, and only then export. A subject without\nconsent must never be exported, even if the operator insists. Audit', 'permission, and only then export. Audit')]),
    Mutation('skill_seo_drop_length_guard', SKILL, 'SEO skill no longer refuses over-long titles (procedure step and prose).', True,
             [('delete_block', 'skills/seo-metadata/SKILL.md', "- when: ctx.get('seo_title') is not None and len(", '- id: meta'),
              ('replace', 'skills/seo-metadata/SKILL.md', 'apply the requested metadata. The SEO title must respect the\nconfigured maximum length; if the proposed title is too long, do not apply any change and tell the\nuser. After applying', 'apply the requested metadata. After applying')]),
    # ---------------------------------------------------------------- prompts / agent definitions
    Mutation('prompt_governance_consent_tool_removed', PROMPT, 'Governance agent loses access to check_consent.', True,
             [('replace', 'agents/governance.yaml', 'tools: [check_permission, check_consent, export_user_data, get_audit_log]', 'tools: [check_permission, export_user_data, get_audit_log]')]),
    Mutation('prompt_seo_tool_removed', PROMPT, 'SEO agent loses access to set_page_metadata.', True,
             [('replace', 'agents/seo.yaml', 'tools: [get_page, get_seo_report, set_page_metadata, check_permission]', 'tools: [get_page, get_seo_report, check_permission]')]),
    # ---------------------------------------------------------------- configuration
    Mutation('config_disable_validate_links', CONFIG, 'Feature flag disables validate_links platform-wide.', True,
             [('replace', 'config/runtime.yaml', 'disabled: []', 'disabled: [validate_links]')]),
    Mutation('config_require_review_false', CONFIG, 'Pages no longer need an approved review before publishing.', True,
             [('replace', 'config/runtime.yaml', 'require_review: true', 'require_review: false')]),
    Mutation('config_max_tool_calls_5', CONFIG, "Each agent's step budget reduced from 12 to 5 tool calls.", True,
             [('replace', 'config/runtime.yaml', 'max_tool_calls: 12', 'max_tool_calls: 5')]),
    Mutation('config_retries_0', CONFIG, 'Transient failures are no longer retried.', True,
             [('replace', 'config/runtime.yaml', 'retries: 2 ', 'retries: 0 ')]),
    Mutation('config_seo_title_20', CONFIG, 'Maximum SEO title length reduced from 60 to 20.', True,
             [('replace', 'config/runtime.yaml', 'max_title_length: 60', 'max_title_length: 20')]),
    Mutation('config_default_agent_publishing', CONFIG, 'Requests no specialist owns go to publishing instead of authoring.', True,
             [('replace', 'config/runtime.yaml', 'default_agent: authoring', 'default_agent: publishing')]),
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
    Mutation('benign_translation_intents_reordered', BENIGN, 'Translation intents re-ordered (a model picks the intent from the request, not from the order).', False,
             [('replace', 'agents/translation.yaml', 'intents:\n  status: [status, progress, "how far", done]\n  create: [translate, localize, localise, translation, into]', 'intents:\n  create: [translate, localize, localise, translation, into]\n  status: [status, progress, "how far", done]')]),
    # ---------------------------------------------------------------- aimed at the multi-agent workflows (planning, hand-offs, AEM-style agents)
    Mutation('skill_routing_drop_approval', SKILL, 'Routing skill no longer asks a person before a step that publishes, schedules or takes pages down (plan step and rule removed).', True,
             [('delete_block', 'skills/routing/SKILL.md', '3. Before a step that publishes, schedules or takes pages down', '4. A campaign page passes the brand check'),
              ('delete_line', 'skills/routing/SKILL.md', '- Never run a step that publishes, schedules or takes pages down without an approval in a plan.')]),
    Mutation('skill_routing_drop_brand_gate', SKILL, 'Routing skill drops the brand check before scheduling or publishing, and no longer stops a plan at a failed check (plan steps and rule).', True,
             [('delete_line', 'skills/routing/SKILL.md', '4. A campaign page passes the brand check before it is scheduled or published.'),
              ('replace', 'skills/routing/SKILL.md', '5. If a step fails (the specialist could not do it, or a check failed), stop:', '5. If a step fails (the specialist could not do it), stop:'),
              ('replace', 'skills/routing/SKILL.md', '- Never go on with steps that depend on a failed step or check.', '- Never go on with steps that depend on a failed step.')]),
    Mutation('code_delegation_drops_context', RUNTIME, "Delegation no longer passes the call's `context` (the ids of earlier steps) on to the specialist.", True,
             [('replace', 'harness/runtime.py', 'message = self._run_agent(target, task, {**ctx, **slots, "request": task}, depth + 1)', 'message = self._run_agent(target, task, {**ctx, "request": task}, depth + 1)')]),
    Mutation('code_insights_rank_reversed', CODE, 'Insights ranking sorted the wrong way: "worst" lists the most-viewed pages first, "best" the least-viewed.', True,
             [('replace', 'services/site.py', 'reverse=(order == "best")', 'reverse=(order == "worst")')]),
    Mutation('code_audit_ignores_alt_text', CODE, "The optimizer's site audit no longer reports images without alt text.", True,
             [('delete_block', 'services/site.py', '        issues += [', '        if not page.get("metadata", {}).get("description"):')]),
    Mutation('code_brand_case_sensitive', CODE, 'Brand check matches forbidden terms only as written (case-sensitive): "Guaranteed returns" passes.', True,
             [('replace', 'services/brand.py', '        if term.lower() in text:', '        if term in f"{page[\'title\']} {page[\'body\']}":')]),
    Mutation('code_search_case_sensitive', CODE, 'Page search lower-cases the query but not the page text, so a capitalised occurrence is missed.', True,
             [('replace', 'services/repository.py', 'hay = " ".join([page.get("title", ""), page.get("path", ""), page.get("body", "")]).lower()', 'hay = " ".join([page.get("title", ""), page.get("path", ""), page.get("body", "")])')]),
    Mutation('config_unpublish_no_approval', CONFIG, 'Taking a page down no longer needs an approval token (unpublish_page leaves tools.requires_approval).', True,
             [('replace', 'config/runtime.yaml', 'requires_approval: [approve_review, export_user_data, unpublish_page]', 'requires_approval: [approve_review, export_user_data]')]),
    Mutation('benign_brand_skill_prose_reworded', BENIGN, 'Prose of the brand-governance skill reworded; procedure and rules untouched.', False,
             [('replace', 'skills/brand-governance/SKILL.md', 'Use this skill to check whether a page meets the brand guidelines, to find the pages that use a term,\nor to tell the user what the guidelines say.', 'Apply this skill to check a page against the brand guidelines, to list the pages where a term appears,\nor to tell the user what the guidelines contain.')]),
    Mutation('benign_routing_guidance_reordered', BENIGN, "Routing skill's guidance list re-ordered: the bullets of the brand, insights and optimizer agents move to the top (same owners).", False,
             [('replace', 'skills/routing/SKILL.md', "- Publishing, scheduling and taking pages down belong to `publishing`.\n", "- Brand checks, the brand guidelines and finding the pages that use a term belong to `brand`.\n- Page views, traffic and the best or worst performing pages belong to `insights`.\n- The alt text of images, site health checks and slow pages belong to `optimizer`.\n- Publishing, scheduling and taking pages down belong to `publishing`.\n"),
              ('replace', 'skills/routing/SKILL.md', "- Restoring earlier versions belongs to `maintenance`.\n- Brand checks, the brand guidelines and finding the pages that use a term belong to `brand`.\n- Page views, traffic and the best or worst performing pages belong to `insights`.\n- The alt text of images, site health checks and slow pages belong to `optimizer`.\n", "- Restoring earlier versions belongs to `maintenance`.\n")]),
    # aimed at re-planning after a failed step (docs/AEM_ALIGNMENT.md, section 3.2)
    Mutation('skill_routing_replan_refusals', SKILL, 'Routing skill lets a failed brand check be repaired by a new plan too: the page is rewritten and the plan goes on.', True,
             [('replace', 'skills/routing/SKILL.md', '6. Broken links are the one failure a new plan repairs: when publishing refuses a page for broken\n   links, or a rollback' + "'" + 's link check fails,', '6. Broken links and a failed brand check can be repaired by a new plan. After a failed brand check, call\n   `make_plan` again with `authoring: rewrite the page so that it passes the brand check` and the steps\n   that remain. When publishing refuses a page for broken links, or a rollback' + "'" + 's link check fails,')]),
    Mutation('config_max_replans_0', CONFIG, 'Re-planning switched off: routing.max_replans is 0, so make_plan refuses any plan after the first.', True,
             [('replace', 'config/runtime.yaml', '  max_replans: 1 ', '  max_replans: 0 ')]),
    Mutation('code_make_plan_unlimited', CODE, 'make_plan no longer enforces routing.max_replans: a request may make any number of new plans.', True,
             [('delete_block', 'tools/control_tools.py', '    if number > 1 + limit:', '    return {"goal": goal')]),
    Mutation('code_fix_links_internal_only', CODE, "The optimizer's link repair unlinks only broken links to pages of the site, not broken external URLs.", True,
             [('replace', 'services/site.py', 'dead = [b["link"] for b in broken if b["link"] in page.get("links", [])]', 'dead = [b["link"] for b in broken if b["kind"] == "internal" and b["link"] in page.get("links", [])]')]),
    Mutation('benign_replan_rule_reworded', BENIGN, "Routing skill's re-planning rule reworded; same repair, same limit.", False,
             [('replace', 'skills/routing/SKILL.md', '6. Broken links are the one failure a new plan repairs: when publishing refuses a page for broken', '6. Only broken links are repaired by a new plan: when publishing turns down a page for broken')]),
]
# fmt: on


def get_mutation(mid: str) -> Mutation:
    for m in MUTATIONS:
        if m.id == mid:
            return m
    raise KeyError(mid)
