# The live check against the replay

`traceeval check <change> --history runs/gemma7 --budget 0.2 --backend vllm` run live with Gemma on every controlled
change, one check at a time, against the five replayed seeds of `adaptive_bayes` at the same budget
(`runs/gemma7/results/replay.csv`). Tokens are shares of the full suite (2,084,733 tokens).

- checks: 43 of 43; the live verdict is one the replay gave in at least one seed on 42, and the replay's
  majority verdict on 42;
- regressions (29): the live check found 23, the replay's majority 23;
- changes no test reveals (14): false regression verdicts live 1, in the replay 0;
- tests per check: live 10.6 on average; tokens: live 4.9% of the suite on average.

| change | regression | revealing tests | live verdict | live tests | live tokens | live failed | replay verdicts (5 seeds) | replay tests | replay tokens |
|---|---|---|---|---|---|---|---|---|---|
| `code_approval_gate_bypass` | yes | 1 | regression | 9 | 2.7% | PUB-07 | regression ×5 | 9 | 2.7–2.7% |
| `code_audit_ignores_alt_text` | yes | 1 | regression | 1 | 0.3% | OPT-01 | regression ×5 | 1 | 0.3% |
| `code_brand_case_sensitive` | yes | 1 | regression | 1 | 0.3% | BRD-02 | regression ×5 | 1 | 0.3% |
| `code_delegation_drops_context` | yes | 4 | clean | 20 | 8.4% |  | clean ×5 | 20 | 8.4–8.4% |
| `code_delegation_truncates_answer` | yes | 25 | regression | 5 | 1.6% | INS-02 | regression ×5 | 5 | 1.6–1.6% |
| `code_get_page_review_flag` | yes | 4 | regression | 6 | 3.1% | PUB-01 | regression ×5 | 6 | 3.1–3.1% |
| `code_insights_rank_reversed` | yes | 4 | regression | 1 | 0.3% | INS-01 | regression ×5 | 1 | 0.3% |
| `code_links_external_lenient` | yes | 6 | regression | 1 | 0.9% | AUT-02 | regression ×5 | 1 | 0.9% |
| `code_metadata_arg_swap` | yes | 5 | regression | 2 | 1.4% | AUT-02 | regression ×5 | 2 | 1.4% |
| `code_retry_drop_idempotency` | yes | 5 | clean | 22 | 8.1% |  | clean ×5 | 22 | 8.1–8.1% |
| `code_search_case_sensitive` | yes | 3 | regression | 1 | 0.3% | BRD-05 | regression ×5 | 1 | 0.3–0.3% |
| `code_termination_off_by_six` | yes | 5 | clean | 17 | 5.0% |  | clean ×5 | 17 | 5.0–5.0% |
| `combined_seo_keyword_limit` | yes | 1 | budget | 44 | 19.9% |  | budget ×5 | 44 | 19.9–19.9% |
| `config_default_agent_publishing` | yes | 3 | regression | 1 | 0.2% | DS-ROUTING/r39 | regression ×5 | 1 | 0.2% |
| `config_disable_validate_links` | yes | 49 | regression | 5 | 1.9% | PUB-11 | regression ×5 | 5 | 1.9% |
| `config_max_tool_calls_5` | yes | 10 | regression | 7 | 4.3% | ORC-03 | regression ×5 | 7 | 4.3% |
| `config_retries_0` | yes | 8 | regression | 1 | 0.7% | PUB-11 | regression ×5 | 1 | 0.7% |
| `config_unpublish_no_approval` | yes | 1 | regression | 7 | 2.8% | PUB-07 | regression ×5 | 7 | 2.8–2.8% |
| `prompt_governance_consent_tool_removed` | yes | 7 | regression | 1 | 0.2% | DS-INTENTS/i20 | regression ×5 | 1 | 0.2% |
| `prompt_seo_tool_removed` | yes | 8 | regression | 1 | 0.3% | SEO-06 | regression ×5 | 1 | 0.3% |
| `skill_authoring_drop_metadata` | yes | 1 | clean | 13 | 4.9% |  | clean ×5 | 13 | 4.9% |
| `skill_governance_drop_consent` | yes | 5 | regression | 3 | 0.5% | GOV-02 | regression ×5 | 2–3 | 0.2–0.5% |
| `skill_publish_drop_link_validation` | yes | 4 | regression | 10 | 5.1% | PUB-03 | regression ×5 | 10 | 5.1% |
| `skill_publish_drop_permission_check` | yes | 3 | regression | 6 | 1.4% | PUB-08 | regression ×5 | 6 | 1.4% |
| `skill_rollback_drop_permission_check` | yes | 1 | regression | 1 | 0.4% | MNT-03 | regression ×5 | 1 | 0.4% |
| `skill_rollback_restores_latest` | yes | 3 | regression | 2 | 0.9% | MNT-02 | regression ×5 | 2 | 0.9% |
| `skill_routing_drop_approval` | yes | 11 | regression | 2 | 1.1% | WF3-03 | regression ×5 | 2 | 0.9–0.9% |
| `skill_routing_drop_brand_gate` | yes | 1 | clean | 9 | 5.0% |  | clean ×5 | 9 | 5.0–5.5% |
| `skill_translation_wrong_default` | yes | 4 | regression | 4 | 1.1% | TRN-02 | regression ×5 | 4 | 1.1% |
| `benign_brand_skill_prose_reworded` | no | 0 | clean | 6 | 4.2% |  | clean ×5 | 6 | 4.1–4.6% |
| `benign_code_comment_docstring` | no | 0 | nothing to test | 0 | 0.0% |  | nothing to test ×5 | 0 | 0.0% |
| `benign_code_rename_locals` | no | 0 | clean | 12 | 14.9% |  | clean ×5 | 12 | 15.0–15.0% |
| `benign_config_comments_reordered` | no | 0 | nothing to test | 0 | 0.0% |  | nothing to test ×5 | 0 | 0.0% |
| `benign_new_unused_tool` | no | 0 | budget | 52 | 20.0% |  | budget ×5 | 52 | 19.9–20.0% |
| `benign_orchestrator_prompt_wording` | no | 0 | regression | 2 | 1.4% | WF3-03 | clean ×5 | 21 | 8.8–8.8% |
| `benign_routing_guidance_reordered` | no | 0 | clean | 10 | 4.0% |  | clean ×5 | 10 | 4.0–4.0% |
| `benign_skill_prose_reflow` | no | 0 | clean | 9 | 4.5% |  | clean ×5 | 9 | 4.5–4.5% |
| `benign_translation_intents_reordered` | no | 0 | clean | 6 | 1.9% |  | clean ×5 | 6 | 1.9% |
| `code_edit_keeps_review` | no | 0 | clean | 14 | 9.8% |  | clean ×5 | 14 | 9.8–9.8% |
| `config_require_review_false` | no | 0 | budget | 34 | 20.0% |  | budget ×5 | 34 | 19.9–19.9% |
| `config_seo_title_20` | no | 0 | budget | 48 | 20.0% |  | budget ×5 | 48 | 20.0–20.0% |
| `skill_linkval_ignore_assets` | no | 0 | clean | 19 | 9.2% |  | clean ×5 | 19 | 9.2–9.2% |
| `skill_seo_drop_length_guard` | no | 0 | budget | 41 | 20.0% |  | budget ×5 | 41–43 | 20.0–20.0% |
