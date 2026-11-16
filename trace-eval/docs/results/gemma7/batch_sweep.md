# Batch-size sweep

Twenty batches of catalog changes drawn at random (`scripts/batch_sweep.py`, `random.Random(0)`): three each of
sizes 2 to 7 and two of size 8, with members drawn from the 41 changes whose edits name their file (the change with
a custom edit and the two comment-only changes are left out), no two members of a batch editing the same file, and
four batches drawn from the seven harmless changes only. Each batch is recorded with Gemma like the single changes,
five repetitions, 32 tests at a time, into a copy of `runs/gemma7` (`runs/gemma7_sweep`), and replayed with every
strategy; each was also checked live, one check at a time. Tokens are shares of the full suite (2,084,733 tokens).
A member is a regression alone when at least one test reveals it in its own recording in `runs/gemma7`.

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

## The replay

A strategy does not learn from a batch's members, nor from the batches that share one
(`History.training_variants`), and every run ends at its first failure. Per batch:

- the revealing tests (where they differ from the union of the members' revealing tests alone, that union and the
  tests gained, +, or lost, −);
- the adaptive method at a 5% and a 20% budget: detection as the share of the five seeds, tests run, tokens (one
  cell where the two budgets agree);
- at a 20% budget, the test that failed and the component the method then blames most, with the member whose
  change set holds it (`scripts/analysis/batch_calibration.py`).

| batch | revealing tests | adaptive, 5% | adaptive, 20% | failed test | blamed most | its member: a regression alone? |
|---|---|---|---|---|---|---|
| `batch_sweep_2_1` | 9 | 1.0, 1 test, 0.3% | | INS-01 | `code:harness/retry.py::with_retry` | `code_retry_drop_idempotency`: yes; the failed test reveals `code_insights_rank_reversed` alone |
| `batch_sweep_2_2` | 0 | 0.0, 12 tests, 4.9% | 0.0, 18 tests, 12.8%: clean | | | |
| `batch_sweep_2_3` | 26 | 1.0, 6 tests, 3.5% | | PUB-02 | `skill:publishing-workflow#procedure` | `skill_publish_drop_link_validation`: yes |
| `batch_sweep_3_1` | 12 | 1.0, 8 tests, 3.0% | | PUB-12 | `config:runtime.retries` | `config_retries_0`: yes |
| `batch_sweep_3_2` | 0 | 0.0, 16 tests, 5.0% | 0.0, 51 tests, 20.0% | | | |
| `batch_sweep_3_3` | 7 | 1.0, 7 tests, 3.7% | | PUB-02 | `skill:publishing-workflow#procedure` | `skill_publish_drop_link_validation`: yes |
| `batch_sweep_4_1` | 9 (members: 8; + PUB-02) | 1.0, 9 tests, 4.1% | 1.0, 9 tests, 4.5% | PUB-02 in four seeds, WF2-02 in one | `config:routing.default_agent`; with WF2-02, `code:services/workflow.py::publish_page` | `config_default_agent_publishing`: yes, though no member reveals PUB-02 alone; `benign_code_rename_locals`: no |
| `batch_sweep_4_2` | 17 | 1.0, 1 test, 0.2% | | DS-INTENTS/i20 | `agent:governance.tools` | `prompt_governance_consent_tool_removed`: yes |
| `batch_sweep_4_3` | 4 | 1.0, 4 tests, 1.6% | | BRD-02 | `code:services/brand.py::check_page` | `code_brand_case_sensitive`: yes |
| `batch_sweep_5_1` | 4 | 1.0, 2 tests, 1.0% | | BRD-02 | `code:services/brand.py::check_page` | `code_brand_case_sensitive`: yes |
| `batch_sweep_5_2` | 14 | 1.0, 4 tests, 1.2% | | TRN-06 | `code:tools/content_tools.py::get_page` | `code_get_page_review_flag`: yes; the failed test reveals `config_retries_0` alone |
| `batch_sweep_5_3` | 2 | 1.0, 1 test, 0.3% | | OPT-01 | `code:services/site.py::audit_site` | `code_audit_ignores_alt_text`: yes |
| `batch_sweep_6_1` | 1 (members: 0; + PUB-02) | 0.0, 12 tests, 4.9% | 0.0, 37 tests, 20.0% | | | |
| `batch_sweep_6_2` | 0 | 0.0, 13 tests, 4.9% | 0.0, 35 tests, 19.9% | | | |
| `batch_sweep_6_3` | 24 | 1.0, 1 test, 0.5% | | SEO-01 | `agent:seo.tools` | `prompt_seo_tool_removed`: yes |
| `batch_sweep_7_1` | 20 | 1.0, 6 tests, 1.5% | | INS-01 | `code:services/site.py::page_metrics` | `code_insights_rank_reversed`: yes |
| `batch_sweep_7_2` | 23 | 1.0, 1 test, 0.2% | | DS-INTENTS/i20 | `agent:governance.tools` | `prompt_governance_consent_tool_removed`: yes |
| `batch_sweep_7_3` | 20 | 1.0, 1 test, 0.2% | | DS-INTENTS/i20 | `agent:governance.tools` | `prompt_governance_consent_tool_removed`: yes |
| `batch_sweep_8_1` | 35 (members: 36; − WF4-01) | 1.0, 1 test, 0.2% | | DS-INTENTS/i20 | `agent:governance.tools` | `prompt_governance_consent_tool_removed`: yes |
| `batch_sweep_8_2` | 12 (members: 13; − WF1-02) | 1.0, 5 tests, 1.7% | | MNT-03 | `skill:rollback#procedure` | `skill_rollback_drop_permission_check`: yes |

Detection of the adaptive method over the batches with a revealing test, by size:

| batch size | batches | with a revealing test | adaptive, 5% | adaptive, 20% |
|---|---|---|---|---|
| 2 | 3 | 2 | 1.0 | 1.0 |
| 3 | 3 | 2 | 1.0 | 1.0 |
| 4 | 3 | 3 | 1.0 | 1.0 |
| 5 | 3 | 3 | 1.0 | 1.0 |
| 6 | 3 | 2 | 0.5 | 0.5 |
| 7 | 3 | 3 | 1.0 | 1.0 |
| 8 | 2 | 2 | 1.0 | 1.0 |

Every strategy over the 17 batches with a revealing test (detection, and the tokens spent on them):

| strategy | detected, 5% | tokens | detected, 20% | tokens |
|---|---|---|---|---|
| `full` | 0.47 | 3.9% | 0.82 | 8.9% |
| `random` | 0.52 | 3.7% | 0.84 | 7.6% |
| `declared` | 0.59 | 3.0% | 0.76 | 6.6% |
| `ir_tfidf` | 0.76 | 2.3% | 0.94 | 4.0% |
| `observed` | 0.82 | 2.2% | 0.94 | 4.5% |
| `observed_diverse` | 0.29 | 4.5% | 0.82 | 9.1% |
| `cost_aware` | 0.82 | 2.2% | 0.94 | 4.0% |
| `history_ml` | 0.59 | 2.7% | 0.94 | 5.8% |
| `casper_slices` | 0.59 | 2.8% | 0.86 | 6.6% |
| `risk_aware_ts` | 0.60 | 3.5% | 0.82 | 6.7% |
| `adaptive_bayes` | 0.94 | 1.6% | 0.94 | 2.6% |

- Detection by batch size: the size makes no difference. Every batch with a regression member (16 of 16) is found
  in all five seeds at 5% and at 20%, after one to eleven tests, for 1.4% of the suite on average and 6.3% at most.
  The one batch with a revealing test that the adaptive method misses is the harmless `batch_sweep_6_1` (below).
- The other strategies: at a 20% budget `ir_tfidf`, `observed`, `cost_aware` and `history_ml` find the same
  sixteen batches, for 4.0% to 5.8% of the suite against the adaptive method's 2.6%. At 5% it finds the most.
- Holding the members out costs tests, not detection. With the members among the changes it learns from, the
  method finds the same batches after 3.4 tests on average at a 5% budget instead of 4.1; learning from the other
  batches as well, after 2.2 (`scripts/analysis/batch_calibration.py`).
- Blame: in 79 of the 80 runs that end at a failure, the component blamed most belongs to a member that is a
  regression alone, and in 65 the failed test is one that reveals that very member alone. The three batches where
  it is not: `batch_sweep_2_1`, where the retry code is blamed while INS-01 reveals the insights ranking;
  `batch_sweep_5_2`, where `get_page` is blamed while TRN-06 reveals `config_retries_0`; and `batch_sweep_4_1`,
  where PUB-02 is a test no member reveals alone. The one wrong blame is a seed of `batch_sweep_4_1` in which
  WF2-02 fails and the renamed locals, a harmless member, are blamed.
- Harmless edits harmful together: one of the four harmless batches is revealed. `batch_sweep_6_1` fails PUB-02 in
  all five runs; it holds both the orchestrator's prompt reworded and the routing guidance reordered, the pair that
  breaks PUB-02 in `batch_benign` (`docs/results/gemma7/batches.md`). `batch_sweep_6_2`, which has the publishing
  skill's prose reflowed in place of the routing guidance, is clean, as are `batch_sweep_2_2` and
  `batch_sweep_3_2`. The routing guidance reordered alone fails PUB-02 in one run of five; with three other edits
  (`batch_sweep_4_1`, two of them regressions on other tests) PUB-02 fails in three runs of five and becomes a
  revealing test no member has alone. No strategy reaches PUB-02 under `batch_sweep_6_1` except the bandit, in four
  seeds of five at 20%.
- Batches also hide what their members reveal: under `batch_sweep_8_1` WF4-01 passes in all five runs, where
  `skill_translation_wrong_default` alone fails it in three of five; under `batch_sweep_8_2` WF1-02, the one test
  that reveals `skill_routing_drop_brand_gate` alone (five failures of five), fails in two of five. Sixteen of the
  20 batches have exactly the union of their members' revealing tests.

## The live check

`traceeval check <batch> --history runs/gemma7 --budget 0.2 --backend vllm`, one check at a time. These checks were
run with the batch's members still among the changes the check learned from, which is why most of them needed
fewer tests than the replay above. The component is the first of the posterior's list (the check prints the
components at 0.2 or more).

| batch | live verdict | live tests, tokens | top blamed | its member: a regression alone? |
|---|---|---|---|---|
| `batch_sweep_2_1` | regression: INS-01 | 1, 0.3% | `code:harness/retry.py::with_retry` 0.72, tied with `code:services/site.py::page_metrics` 0.72 | `code_retry_drop_idempotency`: yes; the failed test reveals `code_insights_rank_reversed` alone |
| `batch_sweep_2_2` | no failure; $P = 0.05$ | 30, 19.9% | `code:services/workflow.py::publish_page` 0.05 | `benign_code_rename_locals`: no (harmless) |
| `batch_sweep_2_3` | regression: PUB-03 | 2, 1.2% | `skill:publishing-workflow#procedure` 0.92 | `skill_publish_drop_link_validation`: yes |
| `batch_sweep_3_1` | regression: PUB-11 | 3, 0.9% | `config:runtime.retries` 0.88 | `config_retries_0`: yes |
| `batch_sweep_3_2` | no failure; $P = 0.18$ | 52, 20.0% | `code:tools/content_tools.py::get_page_stats` 0.15 | `benign_new_unused_tool`: no (harmless) |
| `batch_sweep_3_3` | regression: PUB-03 | 2, 1.2% | `skill:publishing-workflow#procedure` 0.90 | `skill_publish_drop_link_validation`: yes |
| `batch_sweep_4_1` | regression: DS-ROUTING/r40 | 1, 0.2% | `config:routing.default_agent` 0.82 | `config_default_agent_publishing`: yes |
| `batch_sweep_4_2` | regression: DS-INTENTS/i20 | 1, 0.2% | `agent:governance.tools` 0.94 | `prompt_governance_consent_tool_removed`: yes |
| `batch_sweep_4_3` | regression: PUB-08 | 2, 0.6% | `skill:publishing-workflow#procedure` 0.70 | `skill_publish_drop_permission_check`: yes |
| `batch_sweep_5_1` | regression: BRD-02 | 1, 0.3% | `code:services/brand.py::check_page` 0.86 | `code_brand_case_sensitive`: yes |
| `batch_sweep_5_2` | regression: TRN-06 | 4, 1.1% | `code:tools/content_tools.py::get_page` 0.68 | `code_get_page_review_flag`: yes; the failed test reveals `config_retries_0` alone |
| `batch_sweep_5_3` | regression: OPT-01 | 1, 0.3% | `code:services/site.py::audit_site` 0.89 | `code_audit_ignores_alt_text`: yes |
| `batch_sweep_6_1` | no failure; $P = 0.30$ | 34, 20.0% | `code:tools/content_tools.py::get_page_stats` 0.20 | `benign_new_unused_tool`: no (harmless) |
| `batch_sweep_6_2` | no failure; $P = 0.33$ | 33, 20.0% | `code:tools/content_tools.py::get_page_stats` 0.23 | `benign_new_unused_tool`: no (harmless) |
| `batch_sweep_6_3` | regression: SEO-06 | 1, 0.3% | `agent:seo.tools` 0.79 | `prompt_seo_tool_removed`: yes |
| `batch_sweep_7_1` | regression: INS-01 | 5, 1.0% | `code:services/site.py::page_metrics` 0.80 | `code_insights_rank_reversed`: yes |
| `batch_sweep_7_2` | regression: GOV-02 | 1, 0.4% | `agent:governance.tools` 0.80 | `prompt_governance_consent_tool_removed`: yes |
| `batch_sweep_7_3` | regression: DS-INTENTS/i20 | 1, 0.2% | `agent:governance.tools` 0.79 | `prompt_governance_consent_tool_removed`: yes |
| `batch_sweep_8_1` | regression: DS-INTENTS/i20 | 1, 0.2% | `agent:governance.tools` 0.77 | `prompt_governance_consent_tool_removed`: yes |
| `batch_sweep_8_2` | regression: MNT-03 | 1, 0.4% | `skill:rollback#procedure` 0.65 | `skill_rollback_drop_permission_check`: yes |

- All sixteen batches with a regression member end with a regression verdict, after one to five tests and at most
  1.2% of the suite; the four harmless batches end without a failure, `batch_sweep_6_1` among them, at
  $P(\text{something broke}) = 0.30$ after 34 tests.
- On all sixteen the component blamed most belongs to a member that is a regression alone, and on fourteen the
  failed test reveals that very member alone. On the four harmless batches nothing is blamed above 0.23; the first
  is the tool no agent may use (`get_page_stats`) on three of them.

## Replay-first

The same batches with the replay in front (`traceeval replay-first`; `docs/RESEARCH_PLAN.md` §5.7): the tests
that diverge on the batch's copy, what is left of them after their divergence points as a share of the suite's
tokens, and the adaptive method over those tests at a 5% and a 20% budget (detection as the share of the five
seeds, tests run, tokens; how the run ended when not at a failure; one cell where the two budgets agree).

| batch | diverged tests | their tokens after the divergence | adaptive, 5% | adaptive, 20% |
|---|---|---|---|---|
| `batch_sweep_2_1` | 10 | 0.099 | 1.0, 1 test, 0.2% |  |
| `batch_sweep_2_2` | 14 | 0.082 | 0.0, 11 tests, 4.7%: uninformative | 0.0, 13 tests, 7.0%: exhausted |
| `batch_sweep_2_3` | 92 | 0.432 | 1.0, 2 tests, 0.2% |  |
| `batch_sweep_3_1` | 153 | 0.901 | 1.0, 7 tests, 2.9% |  |
| `batch_sweep_3_2` | 156 | 0.906 | 0.0, 14 tests, 4.9%: uninformative | 0.0, 43 tests, 20.0%: budget |
| `batch_sweep_3_3` | 162 | 0.943 | 1.0, 7 tests, 3.7% |  |
| `batch_sweep_4_1` | 153 | 0.901 | 1.0, 6 tests, 3.2% | 1.0, 6 tests, 3.6% |
| `batch_sweep_4_2` | 30 | 0.268 | 1.0, 1 test, 0.3% |  |
| `batch_sweep_4_3` | 47 | 0.304 | 1.0, 1 test, 0.1% |  |
| `batch_sweep_5_1` | 162 | 0.943 | 1.0, 2 tests, 1.0% |  |
| `batch_sweep_5_2` | 100 | 0.659 | 1.0, 3 tests, 0.7% |  |
| `batch_sweep_5_3` | 162 | 0.943 | 1.0, 1 test, 0.3% |  |
| `batch_sweep_6_1` | 156 | 0.906 | 0.0, 12 tests, 4.8%: uninformative | 0.0, 28 tests, 20.0%: budget |
| `batch_sweep_6_2` | 165 | 0.949 | 0.0, 12 tests, 5.0%: budget | 0.0, 32 tests, 19.9%: budget |
| `batch_sweep_6_3` | 93 | 0.661 | 1.0, 1 test, 0.4% |  |
| `batch_sweep_7_1` | 157 | 0.908 | 1.0, 6 tests, 1.5% |  |
| `batch_sweep_7_2` | 166 | 0.949 | 1.0, 1 test, 0.2% |  |
| `batch_sweep_7_3` | 166 | 0.949 | 1.0, 1 test, 0.2% |  |
| `batch_sweep_8_1` | 169 | 0.955 | 1.0, 1 test, 0.2% |  |
| `batch_sweep_8_2` | 172 | 0.983 | 1.0, 5 tests, 1.7% |  |

- The replay is exact on the batches: 0 of its 1115 replayed outcomes differ from the recorded majority, and 0
  replayed tests fail.
- With no budget, the strategies that run every diverged test find all 17 batches a test reveals, the harmless
  `batch_sweep_6_1` included, and end with every diverged test passed on the other 3, for 12% to 19% of the suite's
  tokens per batch.
