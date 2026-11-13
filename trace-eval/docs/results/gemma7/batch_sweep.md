# Batch-size sweep

Twenty batches of catalog changes drawn at random (`scripts/batch_sweep.py`, `random.Random(0)`): three each of
sizes 2 to 7 and two of size 8, with members drawn from the 41 changes whose edits name their file (the change with
a custom edit and the two comment-only changes are left out), no two members of a batch editing the same file, and
four batches drawn from the seven harmless changes only. Each batch is recorded with Gemma like the single changes,
five repetitions, 32 tests at a time, into a copy of `runs/gemma7` (`runs/gemma7_sweep`), and replayed with every
strategy; each is also checked live, one check at a time (`traceeval check <batch> --history runs/gemma7 --budget
0.2 --backend vllm`). Tokens are shares of the full suite (2,084,733 tokens). A member is a regression alone when
at least one test reveals it in its own recording in `runs/gemma7`.

| batch | size | members | regressions: labelled, revealed alone |
|---|---|---|---|
| `batch_sweep_2_1` | 2 | `code_retry_drop_idempotency`, `code_insights_rank_reversed` | 2, 2 |
| `batch_sweep_2_2` | 2 | `benign_translation_intents_reordered`, `benign_code_rename_locals` | 0, 0 |
| `batch_sweep_2_3` | 2 | `skill_publish_drop_link_validation`, `code_delegation_truncates_answer` | 2, 2 |
| `batch_sweep_3_1` | 3 | `config_retries_0`, `code_delegation_drops_context`, `benign_orchestrator_prompt_wording` | 2, 2 |
| `batch_sweep_3_2` | 3 | `benign_orchestrator_prompt_wording`, `benign_translation_intents_reordered`, `benign_new_unused_tool` | 0, 0 |
| `batch_sweep_3_3` | 3 | `code_delegation_drops_context`, `benign_routing_guidance_reordered`, `skill_publish_drop_link_validation` | 2, 2 |
| `batch_sweep_4_1` | 4 | `benign_routing_guidance_reordered`, `benign_code_rename_locals`, `config_default_agent_publishing`, `code_termination_off_by_six` | 2, 2 |
| `batch_sweep_4_2` | 4 | `code_links_external_lenient`, `benign_code_rename_locals`, `prompt_governance_consent_tool_removed`, `code_delegation_drops_context` | 3, 3 |
| `batch_sweep_4_3` | 4 | `config_require_review_false`, `code_brand_case_sensitive`, `skill_publish_drop_permission_check`, `benign_code_rename_locals` | 3, 2 |
| `batch_sweep_5_1` | 5 | `code_brand_case_sensitive`, `config_default_agent_publishing`, `benign_skill_prose_reflow`, `benign_orchestrator_prompt_wording`, `benign_code_rename_locals` | 2, 2 |
| `batch_sweep_5_2` | 5 | `code_get_page_review_flag`, `config_retries_0`, `skill_linkval_ignore_assets`, `code_termination_off_by_six`, `benign_translation_intents_reordered` | 4, 3 |
| `batch_sweep_5_3` | 5 | `combined_seo_keyword_limit`, `code_audit_ignores_alt_text`, `benign_brand_skill_prose_reworded`, `benign_orchestrator_prompt_wording`, `benign_skill_prose_reflow` | 2, 2 |
| `batch_sweep_6_1` | 6 | `benign_code_rename_locals`, `benign_translation_intents_reordered`, `benign_routing_guidance_reordered`, `benign_new_unused_tool`, `benign_brand_skill_prose_reworded`, `benign_orchestrator_prompt_wording` | 0, 0 |
| `batch_sweep_6_2` | 6 | `benign_orchestrator_prompt_wording`, `benign_new_unused_tool`, `benign_skill_prose_reflow`, `benign_brand_skill_prose_reworded`, `benign_translation_intents_reordered`, `benign_code_rename_locals` | 0, 0 |
| `batch_sweep_6_3` | 6 | `code_retry_drop_idempotency`, `skill_linkval_ignore_assets`, `prompt_seo_tool_removed`, `skill_rollback_drop_permission_check`, `code_links_external_lenient`, `skill_translation_wrong_default` | 6, 5 |
| `batch_sweep_7_1` | 7 | `skill_routing_drop_brand_gate`, `code_insights_rank_reversed`, `code_delegation_drops_context`, `config_retries_0`, `benign_translation_intents_reordered`, `code_edit_keeps_review`, `code_links_external_lenient` | 6, 5 |
| `batch_sweep_7_2` | 7 | `code_edit_keeps_review`, `code_delegation_drops_context`, `prompt_governance_consent_tool_removed`, `skill_publish_drop_link_validation`, `skill_rollback_drop_permission_check`, `skill_routing_drop_brand_gate`, `config_retries_0` | 7, 6 |
| `batch_sweep_7_3` | 7 | `code_approval_gate_bypass`, `code_retry_drop_idempotency`, `prompt_governance_consent_tool_removed`, `benign_orchestrator_prompt_wording`, `benign_new_unused_tool`, `skill_publish_drop_link_validation`, `skill_rollback_restores_latest` | 5, 5 |
| `batch_sweep_8_1` | 8 | `combined_seo_keyword_limit`, `skill_publish_drop_link_validation`, `skill_rollback_drop_permission_check`, `benign_orchestrator_prompt_wording`, `skill_translation_wrong_default`, `benign_brand_skill_prose_reworded`, `prompt_governance_consent_tool_removed`, `code_delegation_truncates_answer` | 6, 6 |
| `batch_sweep_8_2` | 8 | `combined_seo_keyword_limit`, `code_retry_drop_idempotency`, `skill_seo_drop_length_guard`, `skill_rollback_drop_permission_check`, `benign_translation_intents_reordered`, `skill_publish_drop_link_validation`, `skill_authoring_drop_metadata`, `skill_routing_drop_brand_gate` | 7, 6 |

Per batch: the revealing tests (where they differ from the union of the members' revealing tests alone, that union
and the tests gained, +, or lost, −); the adaptive method in the replay at a 5% and a 20% budget (detection as the
share of the five seeds, tests run, tokens); the live check (verdict, tests, tokens); and the component the live
check blames most (the first of the posterior's list; the check prints the components at 0.2 or more), with the
member whose change set holds it.

| batch | revealing tests | adaptive, 5% | adaptive, 20% | live verdict | live tests, tokens | top blamed | its member: a regression alone? |
|---|---|---|---|---|---|---|---|
| `batch_sweep_2_1` | 9 | 1.0, 1 test, 0.3% | 1.0, 1 test, 0.3% | regression: INS-01 | 1, 0.3% | `code:harness/retry.py::with_retry` 0.72, tied with `code:services/site.py::page_metrics` 0.72 | `code_retry_drop_idempotency`: yes; the failed test reveals `code_insights_rank_reversed` alone |
| `batch_sweep_2_2` | 0 | 0.0, 15 tests, 4.9% | 0.0, 28 tests, 18.5% | no failure; $P = 0.05$ | 30, 19.9% | `code:services/workflow.py::publish_page` 0.05 | `benign_code_rename_locals`: no (harmless) |
| `batch_sweep_2_3` | 26 | 1.0, 1 test, 0.7% | 1.0, 1 test, 0.7% | regression: PUB-03 | 2, 1.2% | `skill:publishing-workflow#procedure` 0.92 | `skill_publish_drop_link_validation`: yes |
| `batch_sweep_3_1` | 12 | 1.0, 2 tests, 0.9% | 1.0, 2 tests, 0.9% | regression: PUB-11 | 3, 0.9% | `config:runtime.retries` 0.88 | `config_retries_0`: yes |
| `batch_sweep_3_2` | 0 | 0.0, 17 tests, 4.9% | 0.0, 51 tests, 20.0% | no failure; $P = 0.18$ | 52, 20.0% | `code:tools/content_tools.py::get_page_stats` 0.15 | `benign_new_unused_tool`: no (harmless) |
| `batch_sweep_3_3` | 7 | 1.0, 1 test, 0.8% | 1.0, 1 test, 0.8% | regression: PUB-03 | 2, 1.2% | `skill:publishing-workflow#procedure` 0.90 | `skill_publish_drop_link_validation`: yes |
| `batch_sweep_4_1` | 9 (members: 8; + PUB-02) | 1.0, 1 test, 0.2% | 1.0, 1 test, 0.2% | regression: DS-ROUTING/r40 | 1, 0.2% | `config:routing.default_agent` 0.82 | `config_default_agent_publishing`: yes |
| `batch_sweep_4_2` | 17 | 1.0, 1 test, 0.2% | 1.0, 1 test, 0.2% | regression: DS-INTENTS/i20 | 1, 0.2% | `agent:governance.tools` 0.94 | `prompt_governance_consent_tool_removed`: yes |
| `batch_sweep_4_3` | 4 | 1.0, 2 tests, 0.7% | 1.0, 2 tests, 0.7% | regression: PUB-08 | 2, 0.6% | `skill:publishing-workflow#procedure` 0.70 | `skill_publish_drop_permission_check`: yes |
| `batch_sweep_5_1` | 4 | 1.0, 1 test, 0.2% | 1.0, 1 test, 0.2% | regression: BRD-02 | 1, 0.3% | `code:services/brand.py::check_page` 0.86 | `code_brand_case_sensitive`: yes |
| `batch_sweep_5_2` | 14 | 1.0, 1 test, 0.5% | 1.0, 1 test, 0.5% | regression: TRN-06 | 4, 1.1% | `code:tools/content_tools.py::get_page` 0.68 | `code_get_page_review_flag`: yes; the failed test reveals `config_retries_0` alone |
| `batch_sweep_5_3` | 2 | 1.0, 1 test, 0.3% | 1.0, 1 test, 0.3% | regression: OPT-01 | 1, 0.3% | `code:services/site.py::audit_site` 0.89 | `code_audit_ignores_alt_text`: yes |
| `batch_sweep_6_1` | 1 (members: 0; + PUB-02) | 0.0, 15 tests, 4.9% | 0.0, 35 tests, 20.0% | no failure; $P = 0.30$ | 34, 20.0% | `code:tools/content_tools.py::get_page_stats` 0.20 | `benign_new_unused_tool`: no (harmless) |
| `batch_sweep_6_2` | 0 | 0.0, 15 tests, 5.0% | 0.0, 33 tests, 19.9% | no failure; $P = 0.33$ | 33, 20.0% | `code:tools/content_tools.py::get_page_stats` 0.23 | `benign_new_unused_tool`: no (harmless) |
| `batch_sweep_6_3` | 24 | 1.0, 1 test, 0.3% | 1.0, 1 test, 0.3% | regression: SEO-06 | 1, 0.3% | `agent:seo.tools` 0.79 | `prompt_seo_tool_removed`: yes |
| `batch_sweep_7_1` | 20 | 1.0, 2 tests, 0.9% | 1.0, 2 tests, 0.9% | regression: INS-01 | 5, 1.0% | `code:services/site.py::page_metrics` 0.80 | `code_insights_rank_reversed`: yes |
| `batch_sweep_7_2` | 23 | 1.0, 1 test, 0.2% | 1.0, 1 test, 0.2% | regression: GOV-02 | 1, 0.4% | `agent:governance.tools` 0.80 | `prompt_governance_consent_tool_removed`: yes |
| `batch_sweep_7_3` | 20 | 1.0, 1 test, 0.2% | 1.0, 1 test, 0.2% | regression: DS-INTENTS/i20 | 1, 0.2% | `agent:governance.tools` 0.79 | `prompt_governance_consent_tool_removed`: yes |
| `batch_sweep_8_1` | 35 (members: 36; − WF4-01) | 1.0, 1 test, 0.2% | 1.0, 1 test, 0.2% | regression: DS-INTENTS/i20 | 1, 0.2% | `agent:governance.tools` 0.77 | `prompt_governance_consent_tool_removed`: yes |
| `batch_sweep_8_2` | 12 (members: 13; − WF1-02) | 1.0, 1 test, 0.4% | 1.0, 1 test, 0.4% | regression: MNT-03 | 1, 0.4% | `skill:rollback#procedure` 0.65 | `skill_rollback_drop_permission_check`: yes |

| batch size | batches | with a revealing test | adaptive, 5% | adaptive, 20% | live regression verdicts |
|---|---|---|---|---|---|
| 2 | 3 | 2 | 1.0 | 1.0 | 2 |
| 3 | 3 | 2 | 1.0 | 1.0 | 2 |
| 4 | 3 | 3 | 1.0 | 1.0 | 3 |
| 5 | 3 | 3 | 1.0 | 1.0 | 3 |
| 6 | 3 | 2 | 0.5 | 0.5 | 1 |
| 7 | 3 | 3 | 1.0 | 1.0 | 3 |
| 8 | 2 | 2 | 1.0 | 1.0 | 2 |

- Detection by batch size: the size makes no difference. Every batch with a regression member (16 of 16) is found
  in all five seeds at 5% and at 20%, after one or two tests and 0.2% to 0.9% of the suite, and the live check
  finds all sixteen, after one to five tests and at most 1.2%. The one batch with a revealing test that no strategy
  but the bandit reaches is the harmless `batch_sweep_6_1` (below). Over the 17 batches with a revealing test, the
  other strategies detect 40% (`declared`) to 76% (`observed`, `ir_tfidf`) at 5%, and at most 94% (`observed`,
  `ir_tfidf`) at 20%, spending the budget; the adaptive method detects 94% at both budgets for 1.6% of the suite on
  average at 20%.
- Live against the replay: the live verdict is the replay's on 19 of 20 batches. On `batch_sweep_2_2` the replay
  ends clean after 28 tests and the live check spends the budget on 30 with $P(\text{something broke}) = 0.05$. The
  live check learns from the 43 single changes of `runs/gemma7` and the replay from the 62 other recordings of
  `runs/gemma7_sweep`, so the first tests differ on a few batches (`batch_sweep_5_2`: four tests live, one in the
  replay).
- Blame: on all 16 regression verdicts the top-blamed component belongs to a member that is a regression alone, and
  on 14 the failed test is one that reveals that very member alone. On `batch_sweep_2_1` the two members tie at
  0.72 and the order puts the retry code first, while INS-01 reveals the insights ranking; on `batch_sweep_5_2` the
  check blames `get_page` (0.68) while TRN-06 reveals `config_retries_0` alone (`config:runtime.retries` 0.48). The
  members no test touched stay near their prior, 0.5. On the four harmless batches nothing is blamed above 0.23;
  the first is the tool no agent may use (`get_page_stats`) on three of them.
- Harmless edits harmful together: one of the four harmless batches is revealed. `batch_sweep_6_1` fails PUB-02 in
  all five runs; it holds both the orchestrator's prompt reworded and the routing guidance reordered, the pair that
  breaks PUB-02 in `batch_benign` (`docs/results/gemma7/batches.md`). `batch_sweep_6_2`, which has the publishing
  skill's prose reflowed in place of the routing guidance, is clean, as are `batch_sweep_2_2` and
  `batch_sweep_3_2`. The routing guidance reordered alone fails PUB-02 in one run of five; with three other edits
  (`batch_sweep_4_1`, two of them regressions on other tests) PUB-02 fails in three runs of five and becomes a
  revealing test no member has alone. No strategy reaches PUB-02 under `batch_sweep_6_1` except the bandit, in two
  seeds of five at 20%; the live check spends the budget on 34 tests without it, at
  $P(\text{something broke}) = 0.30$.
- Batches also hide what their members reveal: under `batch_sweep_8_1` WF4-01 passes in all five runs, where
  `skill_translation_wrong_default` alone fails it in three of five; under `batch_sweep_8_2` WF1-02, the one test
  that reveals `skill_routing_drop_brand_gate` alone (five failures of five), fails in two of five. Sixteen of the
  20 batches have exactly the union of their members' revealing tests.
