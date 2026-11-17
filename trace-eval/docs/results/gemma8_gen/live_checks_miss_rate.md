# The live checks with a target miss rate

`traceeval check <change> --history runs/gemma8_gen --budget 1.0 --miss-rate R --confirm --backend vllm`, run on
each of the 43 hand-written changes, one check at a time, for R = 0.1 and R = 0.2.

- A check replays the changed copy against the recording's cassette, then runs the adaptive method live over the
  tests that diverge.
- Its clean verdict comes at a threshold set on the generated changes of `runs/gemma8_gen`, for the group of the
  change ([RESEARCH_PLAN.md](../../RESEARCH_PLAN.md) §3.4).
- A test that fails is run again before its failure counts (`--confirm`).
- Whether a change is a regression is its label in `runs/gemma8`, where the 43 changes are recorded with five
  repetitions.

Tokens are shares of the full suite (2,083,624 tokens). A verdict "clean, stopped" is a clean verdict given before
every reached test had run. A test in brackets failed at least once in the check.

**Target miss rate 10%.**

- regressions found: 28 of 28;
- regression verdicts on the 15 changes no test reveals: 0;
- clean verdicts given before every reached test had run: 7;
- tokens per check: 2.8% of the suite on average, 6.4% on the changes no test reveals;
- tests run with the model: 327, of which 27 are repetitions after a failure; 411 seconds of model time for the 43
  checks.

| group of the change | changes | its threshold |
|---|---|---|
| a skill's steps | 9 | 0.292 (on 27) |
| an agent's tools and skills | 3 | 0.0756 (on 23) |
| code | 11 | 7.55e-15 (on 43) |
| text the model reads | 6 | 0.0442 (on 15) |
| the configuration | 6 | 0.45 (on 26) |

**Target miss rate 20%.**

- regressions found: 25 of 28; called clean: `code_delegation_truncates_answer`, `code_get_page_review_flag`,
  `skill_authoring_drop_metadata`;
- regression verdicts on the 15 changes no test reveals: 0;
- clean verdicts given before every reached test had run: 10;
- tokens per check: 2.0% of the suite on average, 4.5% on the changes no test reveals;
- tests run with the model: 237, of which 22 are repetitions after a failure; 293 seconds of model time for the 43
  checks.

| group of the change | changes | its threshold |
|---|---|---|
| a skill's steps | 9 | 0.387 (on 27) |
| an agent's tools and skills | 3 | 0.45 (on 23) |
| code | 11 | 0.00107 (on 43) |
| text the model reads | 6 | 0.0667 (on 15) |
| the configuration | 6 | 0.45 (on 26) |

| change | group | regression | tests that diverge | verdict at 10% | tests | tokens | verdict at 20% | tests | tokens |
|---|---|---|---|---|---|---|---|---|---|
| `benign_brand_skill_prose_reworded` | text the model reads | no | 12 | clean | 11 | 2.1% | clean | 11 | 2.1% |
| `benign_code_comment_docstring` | code | no | 0 | clean | 0 | 0.0% | clean | 0 | 0.0% |
| `benign_code_rename_locals` | code | no | 0 | clean | 0 | 0.0% | clean | 0 | 0.0% |
| `benign_config_comments_reordered` | code | no | 0 | clean | 0 | 0.0% | clean | 0 | 0.0% |
| `benign_new_unused_tool` | text the model reads | no | 0 | clean | 0 | 0.0% | clean | 0 | 0.0% |
| `benign_orchestrator_prompt_wording` | text the model reads | no | 153 | clean, stopped (WF3-03) | 57 | 18.8% | clean, stopped | 37 | 9.9% |
| `benign_routing_guidance_reordered` | text the model reads | no | 153 | clean, stopped | 54 | 14.1% | clean, stopped | 33 | 9.0% |
| `benign_skill_prose_reflow` | text the model reads | no | 46 | clean | 41 | 23.2% | clean | 41 | 23.3% |
| `benign_translation_intents_reordered` | an agent's tools and skills | no | 14 | clean, stopped | 3 | 0.5% | clean, stopped | 1 | 0.1% |
| `code_approval_gate_bypass` | code | yes | 2 | regression (PUB-07) | 2 | 0.6% | regression (PUB-07) | 2 | 0.6% |
| `code_audit_ignores_alt_text` | code | yes | 4 | regression (OPT-01) | 1 | 0.3% | regression (OPT-01) | 1 | 0.3% |
| `code_brand_case_sensitive` | code | yes | 1 | regression (BRD-02) | 1 | 0.3% | regression (BRD-02) | 1 | 0.3% |
| `code_delegation_drops_context` | code | yes | 12 | regression (WF1-02) | 1 | 0.9% | regression (WF1-02) | 1 | 0.9% |
| `code_delegation_truncates_answer` | code | yes | 80 | regression (INS-02) | 8 | 0.9% | clean, stopped | 7 | 0.7% |
| `code_edit_keeps_review` | code | no | 0 | clean | 0 | 0.0% | clean | 0 | 0.0% |
| `code_get_page_review_flag` | code | yes | 65 | regression (PUB-01) | 9 | 2.3% | clean, stopped | 7 | 1.4% |
| `code_insights_rank_reversed` | code | yes | 5 | regression (INS-01) | 1 | 0.3% | regression (INS-01) | 1 | 0.3% |
| `code_links_external_lenient` | code | yes | 7 | regression (AUT-02) | 1 | 0.6% | regression (AUT-02) | 1 | 0.6% |
| `code_metadata_arg_swap` | code | yes | 21 | regression (SEO-08) | 2 | 0.4% | regression (SEO-08) | 2 | 0.4% |
| `code_retry_drop_idempotency` | code | yes | 5 | regression (TRN-06) | 1 | 0.3% | regression (TRN-06) | 1 | 0.3% |
| `code_search_case_sensitive` | code | yes | 4 | regression (BRD-05) | 1 | 0.3% | regression (BRD-05) | 1 | 0.3% |
| `code_termination_off_by_six` | code | yes | 3 | regression (WF4-01, WF4-02, WF6-01) | 0 | 0.0% | regression (WF4-01, WF4-02, WF6-01) | 0 | 0.0% |
| `combined_seo_keyword_limit` | the configuration | yes | 2 | regression (SEO-07) | 2 | 0.5% | regression (SEO-07) | 2 | 0.5% |
| `config_default_agent_publishing` | the configuration | yes | 153 | regression (DS-ROUTING/r39) | 1 | 0.4% | regression (DS-ROUTING/r39) | 1 | 0.4% |
| `config_disable_validate_links` | the configuration | yes | 48 | regression (PUB-01, PUB-11, PUB-12, ...) | 0 | 0.0% | regression (PUB-01, PUB-11, PUB-12, ...) | 0 | 0.0% |
| `config_max_tool_calls_5` | the configuration | yes | 14 | regression (WF4-01, WF4-02, WF6-01) | 0 | 0.0% | regression (WF4-01, WF4-02, WF6-01) | 0 | 0.0% |
| `config_require_review_false` | the configuration | no | 45 | clean, stopped | 2 | 1.0% | clean, stopped | 2 | 1.0% |
| `config_retries_0` | the configuration | yes | 8 | regression (PUB-11) | 1 | 0.4% | regression (PUB-11) | 1 | 0.4% |
| `config_seo_title_20` | the configuration | no | 11 | clean, stopped | 1 | 0.5% | clean, stopped | 1 | 0.5% |
| `config_unpublish_no_approval` | the configuration | yes | 1 | regression (PUB-07) | 1 | 0.4% | regression (PUB-07) | 1 | 0.4% |
| `prompt_governance_consent_tool_removed` | an agent's tools and skills | yes | 12 | regression (GOV-02) | 1 | 0.5% | regression (GOV-02) | 1 | 0.5% |
| `prompt_seo_tool_removed` | an agent's tools and skills | yes | 11 | regression (SEO-01) | 1 | 0.8% | regression (SEO-01) | 1 | 0.8% |
| `skill_authoring_drop_metadata` | a skill's steps | yes | 27 | regression (AUT-02) | 16 | 7.3% | clean, stopped | 7 | 2.6% |
| `skill_governance_drop_consent` | a skill's steps | yes | 12 | regression (GOV-02) | 1 | 0.5% | regression (GOV-02) | 1 | 0.5% |
| `skill_linkval_ignore_assets` | a skill's steps | no | 74 | clean, stopped | 28 | 14.3% | clean, stopped | 14 | 6.9% |
| `skill_publish_drop_link_validation` | a skill's steps | yes | 46 | regression (PUB-03) | 1 | 1.2% | regression (PUB-03) | 1 | 1.2% |
| `skill_publish_drop_permission_check` | a skill's steps | yes | 46 | regression (PUB-08) | 1 | 0.7% | regression (PUB-08) | 1 | 0.7% |
| `skill_rollback_drop_permission_check` | a skill's steps | yes | 7 | regression (MNT-03) | 1 | 0.7% | regression (MNT-03) | 1 | 0.7% |
| `skill_rollback_restores_latest` | a skill's steps | yes | 7 | regression (MNT-02) | 3 | 1.6% | regression (MNT-02) | 3 | 1.6% |
| `skill_routing_drop_approval` | text the model reads | yes | 153 | regression (WF3-03) | 2 | 1.9% | regression (WF3-03) | 2 | 1.6% |
| `skill_routing_drop_brand_gate` | text the model reads | no | 153 | clean, stopped | 54 | 13.5% | clean, stopped | 33 | 6.9% |
| `skill_seo_drop_length_guard` | a skill's steps | no | 11 | clean | 9 | 7.3% | clean | 9 | 7.3% |
| `skill_translation_wrong_default` | a skill's steps | yes | 14 | regression (TRN-02) | 7 | 1.7% | regression (TRN-02) | 7 | 1.7% |

## Reading

- At a 10% target the check finds all 28 regressions and calls none of the 15 other changes a regression.
- The edits to a prompt that every request reads (`benign_orchestrator_prompt_wording`,
  `benign_routing_guidance_reordered`, `skill_routing_drop_brand_gate`) reach 145 runnable tests each. At a 10%
  target the check stops after 54 to 57 of them, for 14% to 19% of the suite's tokens.
- On `benign_orchestrator_prompt_wording` WF3-03 fails once at the 10% target and passes when it is run again,
  so the failure does not count.
- A change to the configuration is cleared once its first test passes: in all 26 recorded regressions of that
  group, the first test the method runs is one that reveals the change.
- For code the threshold is next to zero. The method is at times sure that a code change broke nothing when it
  did, and the threshold makes up for it: a code change runs nearly every test it reaches.
- At a 20% target three regressions are called clean, which is 3 of 28 and within the target. In each the
  method's probability is under its group's threshold after seven passing tests.
