# The live checks with a target miss rate, under Qwen

`traceeval check <change> --history runs/qwen8_gen --budget 1.0 --miss-rate R --confirm --backend llm`, run on
each of the 43 hand-written changes, for R = 0.1 and R = 0.2, one check at a time on each of two servers.

- A check replays the changed copy against the recording's cassette, then runs the adaptive method live over the
  tests that diverge.
- Its clean verdict comes at a threshold set on the generated changes of `runs/qwen8_gen`, for the group of the
  change ([RESEARCH_PLAN.md](../../RESEARCH_PLAN.md) §3.4).
- A test that fails is run again before its failure counts (`--confirm`).
- Whether a change is a regression is its label in `runs/qwen8_exact`, where the 43 changes are recorded with
  Qwen served so that every answer repeats: one test at a time and without the prefix cache.

Tokens are shares of the full suite (2,309,051 tokens). A verdict "clean, stopped" is a clean verdict given before
every reached test had run. A test in brackets failed at least once in the check.

**Target miss rate 10%.**

- regressions found: 32 of 32;
- regression verdicts on the 11 changes no test reveals: 0;
- clean verdicts given before every reached test had run: 2;
- tokens per check: 2.8% of the suite on average, 2.1% on the changes no test reveals;
- tests run with the model: 256, of which 28 are repetitions after a failure; 1403 seconds of model time for the 43
  checks.

| group of the change | changes | its threshold |
|---|---|---|
| a skill's steps | 9 | 0.234 (on 30) |
| an agent's tools and skills | 3 | 0.0756 (on 22) |
| code | 11 | 0 (on 44) |
| text the model reads | 6 | 0.0363 (on 35) |
| the configuration | 6 | 0.45 (on 25) |

**Target miss rate 20%.**

- regressions found: 28 of 32; called clean: `benign_routing_guidance_reordered`,
  `code_delegation_truncates_answer`, `code_get_page_review_flag`, `skill_authoring_drop_metadata`;
- regression verdicts on the 11 changes no test reveals: 0;
- clean verdicts given before every reached test had run: 6;
- tokens per check: 2.1% of the suite on average, 2.1% on the changes no test reveals;
- tests run with the model: 188, of which 24 are repetitions after a failure; 1112 seconds of model time for the 43
  checks.

| group of the change | changes | its threshold |
|---|---|---|
| a skill's steps | 9 | 0.422 (on 30) |
| an agent's tools and skills | 3 | 0.45 (on 22) |
| code | 11 | 0.000264 (on 44) |
| text the model reads | 6 | 0.063 (on 35) |
| the configuration | 6 | 0.45 (on 25) |

| change | group | regression | tests that diverge | verdict at 10% | tests | tokens | verdict at 20% | tests | tokens |
|---|---|---|---|---|---|---|---|---|---|
| `benign_brand_skill_prose_reworded` | text the model reads | no | 12 | clean | 12 | 4.3% | clean | 12 | 4.3% |
| `benign_code_comment_docstring` | code | no | 0 | clean | 0 | 0.0% | clean | 0 | 0.0% |
| `benign_code_rename_locals` | code | no | 0 | clean | 0 | 0.0% | clean | 0 | 0.0% |
| `benign_config_comments_reordered` | code | no | 0 | clean | 0 | 0.0% | clean | 0 | 0.0% |
| `benign_new_unused_tool` | text the model reads | no | 0 | clean | 0 | 0.0% | clean | 0 | 0.0% |
| `benign_orchestrator_prompt_wording` | text the model reads | yes | 153 | regression (WF4-01) | 10 | 4.7% | regression (WF4-01) | 10 | 4.7% |
| `benign_routing_guidance_reordered` | text the model reads | yes | 153 | regression (AUT-08) | 46 | 13.1% | clean, stopped | 34 | 10.1% |
| `benign_skill_prose_reflow` | text the model reads | yes | 44 | regression (CFG-03) | 2 | 1.9% | regression (CFG-03) | 2 | 1.9% |
| `benign_translation_intents_reordered` | an agent's tools and skills | no | 14 | clean, stopped | 3 | 0.5% | clean, stopped | 1 | 0.1% |
| `code_approval_gate_bypass` | code | no | 2 | clean | 1 | 0.2% | clean | 1 | 0.2% |
| `code_audit_ignores_alt_text` | code | yes | 4 | regression (OPT-01) | 1 | 0.3% | regression (OPT-01) | 1 | 0.3% |
| `code_brand_case_sensitive` | code | yes | 1 | regression (BRD-02) | 1 | 0.3% | regression (BRD-02) | 1 | 0.3% |
| `code_delegation_drops_context` | code | no | 15 | clean | 11 | 17.1% | clean | 11 | 17.1% |
| `code_delegation_truncates_answer` | code | yes | 83 | regression (AUT-02) | 22 | 2.4% | clean, stopped | 8 | 0.8% |
| `code_edit_keeps_review` | code | yes | 4 | regression (AUT-04) | 0 | 0.0% | regression (AUT-04) | 0 | 0.0% |
| `code_get_page_review_flag` | code | yes | 61 | regression (PUB-01) | 10 | 2.8% | clean, stopped | 8 | 1.7% |
| `code_insights_rank_reversed` | code | yes | 5 | regression (INS-01) | 1 | 0.3% | regression (INS-01) | 1 | 0.3% |
| `code_links_external_lenient` | code | yes | 7 | regression (PUB-02) | 1 | 0.6% | regression (PUB-02) | 1 | 0.6% |
| `code_metadata_arg_swap` | code | yes | 21 | regression (SEO-08) | 2 | 0.5% | regression (SEO-08) | 2 | 0.5% |
| `code_retry_drop_idempotency` | code | yes | 5 | regression (AST-06) | 1 | 0.6% | regression (AST-06) | 1 | 0.6% |
| `code_search_case_sensitive` | code | yes | 4 | regression (BRD-05) | 1 | 0.3% | regression (BRD-05) | 1 | 0.3% |
| `code_termination_off_by_six` | code | yes | 0 | regression (WF1-01, WF1-03, WF4-01, ...) | 0 | 0.0% | regression (WF1-01, WF1-03, WF4-01, ...) | 0 | 0.0% |
| `combined_seo_keyword_limit` | the configuration | no | 2 | clean | 1 | 0.2% | clean | 1 | 0.2% |
| `config_default_agent_publishing` | the configuration | yes | 153 | regression (DS-ROUTING/r39) | 1 | 0.4% | regression (DS-ROUTING/r39) | 1 | 0.4% |
| `config_disable_validate_links` | the configuration | yes | 51 | regression (PUB-01, PUB-11, PUB-12, ...) | 0 | 0.0% | regression (PUB-01, PUB-11, PUB-12, ...) | 0 | 0.0% |
| `config_max_tool_calls_5` | the configuration | yes | 2 | regression (WF1-01, WF1-03, WF4-01, ...) | 0 | 0.0% | regression (WF1-01, WF1-03, WF4-01, ...) | 0 | 0.0% |
| `config_require_review_false` | the configuration | no | 43 | clean, stopped | 2 | 1.1% | clean, stopped | 2 | 1.1% |
| `config_retries_0` | the configuration | yes | 8 | regression (PUB-11) | 1 | 0.4% | regression (PUB-11) | 1 | 0.4% |
| `config_seo_title_20` | the configuration | yes | 11 | regression (SEO-05) | 1 | 0.8% | regression (SEO-05) | 1 | 0.8% |
| `config_unpublish_no_approval` | the configuration | no | 1 | clean | 0 | 0.0% | clean | 0 | 0.0% |
| `prompt_governance_consent_tool_removed` | an agent's tools and skills | yes | 12 | regression (GOV-02) | 1 | 0.5% | regression (GOV-02) | 1 | 0.5% |
| `prompt_seo_tool_removed` | an agent's tools and skills | yes | 11 | regression (SEO-01) | 1 | 0.9% | regression (SEO-01) | 1 | 0.9% |
| `skill_authoring_drop_metadata` | a skill's steps | yes | 28 | regression (AUT-02) | 20 | 10.3% | clean, stopped | 6 | 1.9% |
| `skill_governance_drop_consent` | a skill's steps | yes | 12 | regression (GOV-02) | 1 | 0.5% | regression (GOV-02) | 1 | 0.5% |
| `skill_linkval_ignore_assets` | a skill's steps | yes | 72 | regression (PUB-03) | 35 | 18.7% | regression (PUB-03) | 11 | 4.9% |
| `skill_publish_drop_link_validation` | a skill's steps | yes | 44 | regression (CFG-03) | 1 | 1.2% | regression (CFG-03) | 1 | 1.2% |
| `skill_publish_drop_permission_check` | a skill's steps | yes | 44 | regression (PUB-08) | 1 | 0.7% | regression (PUB-08) | 1 | 0.7% |
| `skill_rollback_drop_permission_check` | a skill's steps | yes | 7 | regression (MNT-03) | 1 | 0.7% | regression (MNT-03) | 1 | 0.7% |
| `skill_rollback_restores_latest` | a skill's steps | yes | 7 | regression (WF5-01) | 4 | 9.8% | regression (WF5-01) | 4 | 9.8% |
| `skill_routing_drop_approval` | text the model reads | yes | 153 | regression (WF3-03) | 23 | 7.4% | regression (WF3-03) | 23 | 7.4% |
| `skill_routing_drop_brand_gate` | text the model reads | yes | 153 | regression (WF4-01) | 27 | 10.3% | regression (WF4-01) | 27 | 10.3% |
| `skill_seo_drop_length_guard` | a skill's steps | yes | 11 | regression (SEO-02) | 3 | 1.8% | regression (SEO-02) | 3 | 1.8% |
| `skill_translation_wrong_default` | a skill's steps | yes | 14 | regression (WF4-02) | 7 | 4.5% | regression (WF4-02) | 7 | 4.5% |

## Reading

- At a 10% target the check finds all 32 regressions and calls none of the 11 other changes a regression.
- Every failure repeats when the test is run again: 28 failures at the 10% target and 24 at 20%, none taken back.
  Served this way an answer is a function of its request, so a second run says what the first said.
- Three changes written as harmless are regressions under Qwen: the reworded orchestrator prompt, the reordered
  routing guidance and the reflowed skill prose. The check finds all three at a 10% target.
- For code the threshold at a 10% target is zero: the method is at times sure that a code change broke nothing
  when it did, so a code change runs every test it reaches. `code_delegation_drops_context`, which no test
  reveals, costs 17.1% of the suite that way.
- At a 20% target four regressions are called clean, which is 4 of 32 and within the target.
