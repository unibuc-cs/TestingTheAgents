# TRACE-Eval experiment report

`runs/qwen7` · 180 tests · 43 changes · 5 baseline repetitions · full suite = 2,470,194 tokens · tests failing on the original app: 7 · runs the environment broke, left out: 116

## 1. Ground truth — which changes are revealed by how many tests

| change | category | expected | revealing tests |
|---|---|---|---|
| `benign_brand_skill_prose_reworded` | benign | benign | 6 |
| `benign_code_comment_docstring` | benign | benign | 3 |
| `benign_code_rename_locals` | benign | benign | 3 |
| `benign_config_comments_reordered` | benign | benign | 4 |
| `benign_new_unused_tool` | benign | benign | 3 |
| `benign_orchestrator_prompt_wording` | benign | benign | 5 |
| `benign_routing_guidance_reordered` | benign | benign | 4 |
| `benign_skill_prose_reflow` | benign | benign | 3 |
| `benign_translation_intents_reordered` | benign | benign | 3 |
| `code_approval_gate_bypass` | code | regression | 5 |
| `code_audit_ignores_alt_text` | code | regression | 5 |
| `code_brand_case_sensitive` | code | regression | 3 |
| `code_edit_keeps_review` | code | regression | 7 |
| `code_get_page_review_flag` | code | regression | 18 |
| `code_insights_rank_reversed` | code | regression | 8 |
| `code_links_external_lenient` | code | regression | 10 |
| `code_metadata_arg_swap` | code | regression | 8 |
| `code_retry_drop_idempotency` | code | regression | 8 |
| `code_search_case_sensitive` | code | regression | 8 |
| `combined_seo_keyword_limit` | combined | regression | 4 |
| `config_default_agent_publishing` | config | regression | 6 |
| `config_disable_validate_links` | config | regression | 56 |
| `config_max_tool_calls_5` | config | regression | 12 |
| `config_require_review_false` | config | regression | 3 |
| `config_retries_0` | config | regression | 9 |
| `config_seo_title_20` | config | regression | 4 |
| `config_unpublish_no_approval` | config | regression | 4 |
| `prompt_governance_consent_tool_removed` | prompt | regression | 9 |
| `prompt_seo_tool_removed` | prompt | regression | 8 |
| `code_delegation_drops_context` | runtime | regression | 3 |
| `code_delegation_truncates_answer` | runtime | regression | 26 |
| `code_termination_off_by_six` | runtime | regression | 9 |
| `skill_authoring_drop_metadata` | skill | regression | 5 |
| `skill_governance_drop_consent` | skill | regression | 9 |
| `skill_linkval_ignore_assets` | skill | regression | 4 |
| `skill_publish_drop_link_validation` | skill | regression | 4 |
| `skill_publish_drop_permission_check` | skill | regression | 7 |
| `skill_rollback_drop_permission_check` | skill | regression | 4 |
| `skill_rollback_restores_latest` | skill | regression | 7 |
| `skill_routing_drop_approval` | skill | regression | 11 |
| `skill_routing_drop_brand_gate` | skill | regression | 5 |
| `skill_seo_drop_length_guard` | skill | regression | 4 |
| `skill_translation_wrong_default` | skill | regression | 6 |

Testbed sanity (every regression revealed by at least one test, no benign change revealed): **VIOLATED**.

## 2. Detection within a budget

Every strategy is run the same way: a test that fails on the original app is not run, and a run ends at its first failure.

Fraction of the revealed regressions detected, by nominal budget (% of full-suite tokens):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.00 | 0.12 | 0.80 | 0.85 | 0.85 | 0.94 | 0.95 |
| random | 0.13 | 0.29 | 0.46 | 0.61 | 0.76 | 0.84 | 0.86 |
| declared | 0.33 | 0.37 | 0.39 | 0.44 | 0.44 | 0.44 | 0.44 |
| ir_tfidf | 0.38 | 0.52 | 0.69 | 0.76 | 0.80 | 0.87 | 0.90 |
| observed | 0.38 | 0.49 | 0.57 | 0.70 | 0.75 | 0.84 | 0.86 |
| observed_diverse | 0.37 | 0.41 | 0.57 | 0.74 | 0.77 | 0.79 | 0.79 |
| cost_aware | 0.38 | 0.49 | 0.57 | 0.70 | 0.75 | 0.87 | 0.93 |
| history_ml | 0.42 | 0.52 | 0.64 | 0.71 | 0.84 | 0.93 | 0.94 |
| casper_slices | 0.16 | 0.19 | 0.84 | 0.92 | 0.93 | 0.93 | 0.93 |
| risk_aware_ts | 0.08 | 0.31 | 0.48 | 0.62 | 0.72 | 0.76 | 0.78 |
| adaptive_bayes | 0.54 | 0.67 | 0.75 | 0.75 | 0.75 | 0.75 | 0.75 |

Tokens spent, as a mean over all changes, revealed or not (fraction of the full suite):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.020 | 0.049 | 0.068 | 0.083 | 0.094 | 0.100 | 0.101 |
| random | 0.018 | 0.042 | 0.071 | 0.107 | 0.126 | 0.136 | 0.139 |
| declared | 0.008 | 0.016 | 0.022 | 0.025 | 0.025 | 0.026 | 0.026 |
| ir_tfidf | 0.015 | 0.030 | 0.048 | 0.068 | 0.082 | 0.101 | 0.105 |
| observed | 0.014 | 0.028 | 0.049 | 0.074 | 0.088 | 0.106 | 0.109 |
| observed_diverse | 0.014 | 0.036 | 0.058 | 0.074 | 0.078 | 0.081 | 0.081 |
| cost_aware | 0.015 | 0.032 | 0.055 | 0.088 | 0.111 | 0.145 | 0.152 |
| history_ml | 0.015 | 0.030 | 0.050 | 0.081 | 0.097 | 0.103 | 0.104 |
| casper_slices | 0.019 | 0.044 | 0.055 | 0.062 | 0.063 | 0.064 | 0.064 |
| risk_aware_ts | 0.019 | 0.039 | 0.061 | 0.085 | 0.095 | 0.102 | 0.106 |
| adaptive_bayes | 0.011 | 0.018 | 0.022 | 0.026 | 0.030 | 0.035 | 0.038 |

At a budget of 5%, over the 43 revealed regressions (intervals: bootstrap over the changes; a difference whose interval holds 0 is not established):

| strategy | detected | 95% interval | tokens, all changes | difference to the best | 95% interval |
|---|---|---|---|---|---|
| full | 0.12 | 0.02 to 0.23 | 0.049 | -0.56 | -0.70 to -0.41 |
| random | 0.29 | 0.21 to 0.38 | 0.042 | -0.38 | -0.51 to -0.25 |
| declared | 0.37 | 0.23 to 0.51 | 0.016 | -0.31 | -0.45 to -0.16 |
| ir_tfidf | 0.52 | 0.38 to 0.67 | 0.030 | -0.15 | -0.28 to -0.03 |
| observed | 0.49 | 0.35 to 0.64 | 0.028 | -0.18 | -0.31 to -0.06 |
| observed_diverse | 0.41 | 0.28 to 0.55 | 0.036 | -0.26 | -0.41 to -0.12 |
| cost_aware | 0.49 | 0.35 to 0.64 | 0.032 | -0.18 | -0.31 to -0.06 |
| history_ml | 0.52 | 0.37 to 0.66 | 0.030 | -0.16 | -0.28 to -0.04 |
| casper_slices | 0.19 | 0.09 to 0.30 | 0.044 | -0.49 | -0.63 to -0.34 |
| risk_aware_ts | 0.31 | 0.22 to 0.41 | 0.039 | -0.36 | -0.49 to -0.23 |
| adaptive_bayes | 0.67 | 0.54 to 0.80 | 0.018 | best |  |

At a budget of 20%, over the 43 revealed regressions (intervals: bootstrap over the changes; a difference whose interval holds 0 is not established):

| strategy | detected | 95% interval | tokens, all changes | difference to the best | 95% interval |
|---|---|---|---|---|---|
| full | 0.85 | 0.76 to 0.92 | 0.083 | -0.07 | -0.15 to -0.00 |
| random | 0.61 | 0.53 to 0.69 | 0.107 | -0.31 | -0.40 to -0.22 |
| declared | 0.44 | 0.30 to 0.58 | 0.025 | -0.48 | -0.62 to -0.34 |
| ir_tfidf | 0.76 | 0.64 to 0.87 | 0.068 | -0.16 | -0.27 to -0.06 |
| observed | 0.70 | 0.56 to 0.82 | 0.074 | -0.22 | -0.36 to -0.09 |
| observed_diverse | 0.74 | 0.63 to 0.84 | 0.074 | -0.18 | -0.28 to -0.09 |
| cost_aware | 0.70 | 0.56 to 0.82 | 0.088 | -0.22 | -0.36 to -0.09 |
| history_ml | 0.71 | 0.58 to 0.83 | 0.081 | -0.21 | -0.34 to -0.09 |
| casper_slices | 0.92 | 0.88 to 0.96 | 0.062 | best |  |
| risk_aware_ts | 0.62 | 0.53 to 0.71 | 0.085 | -0.30 | -0.39 to -0.21 |
| adaptive_bayes | 0.75 | 0.63 to 0.87 | 0.026 | -0.17 | -0.27 to -0.07 |

Tokens spent on the revealed regressions only:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.020 | 0.049 | 0.068 | 0.083 | 0.094 | 0.100 | 0.101 |
| random | 0.018 | 0.042 | 0.071 | 0.107 | 0.126 | 0.136 | 0.139 |
| declared | 0.008 | 0.016 | 0.022 | 0.025 | 0.025 | 0.026 | 0.026 |
| ir_tfidf | 0.015 | 0.030 | 0.048 | 0.068 | 0.082 | 0.101 | 0.105 |
| observed | 0.014 | 0.028 | 0.049 | 0.074 | 0.088 | 0.106 | 0.109 |
| observed_diverse | 0.014 | 0.036 | 0.058 | 0.074 | 0.078 | 0.081 | 0.081 |
| cost_aware | 0.015 | 0.032 | 0.055 | 0.088 | 0.111 | 0.145 | 0.152 |
| history_ml | 0.015 | 0.030 | 0.050 | 0.081 | 0.097 | 0.103 | 0.104 |
| casper_slices | 0.019 | 0.044 | 0.055 | 0.062 | 0.063 | 0.064 | 0.064 |
| risk_aware_ts | 0.019 | 0.039 | 0.061 | 0.085 | 0.095 | 0.102 | 0.106 |
| adaptive_bayes | 0.011 | 0.018 | 0.022 | 0.026 | 0.030 | 0.035 | 0.038 |

Time spent on those changes (fraction of the full suite's run time, from each test's mean time on the original app):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.020 | 0.048 | 0.069 | 0.084 | 0.092 | 0.098 | 0.099 |
| random | 0.017 | 0.041 | 0.071 | 0.109 | 0.128 | 0.140 | 0.143 |
| declared | 0.008 | 0.018 | 0.027 | 0.031 | 0.031 | 0.032 | 0.032 |
| ir_tfidf | 0.014 | 0.029 | 0.050 | 0.073 | 0.087 | 0.104 | 0.107 |
| observed | 0.013 | 0.026 | 0.048 | 0.072 | 0.084 | 0.101 | 0.103 |
| observed_diverse | 0.014 | 0.040 | 0.070 | 0.095 | 0.099 | 0.102 | 0.102 |
| cost_aware | 0.014 | 0.029 | 0.054 | 0.086 | 0.106 | 0.136 | 0.144 |
| history_ml | 0.015 | 0.030 | 0.051 | 0.079 | 0.095 | 0.100 | 0.101 |
| casper_slices | 0.022 | 0.047 | 0.059 | 0.069 | 0.072 | 0.072 | 0.072 |
| risk_aware_ts | 0.019 | 0.046 | 0.074 | 0.104 | 0.118 | 0.125 | 0.128 |
| adaptive_bayes | 0.012 | 0.019 | 0.023 | 0.028 | 0.031 | 0.035 | 0.038 |

Critical regressions: the same detection rate, over the changes that break a safety property only:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.00 | 0.12 | 0.80 | 0.85 | 0.85 | 0.94 | 0.95 |
| random | 0.13 | 0.29 | 0.46 | 0.61 | 0.76 | 0.84 | 0.86 |
| declared | 0.33 | 0.37 | 0.39 | 0.44 | 0.44 | 0.44 | 0.44 |
| ir_tfidf | 0.38 | 0.52 | 0.69 | 0.76 | 0.80 | 0.87 | 0.90 |
| observed | 0.38 | 0.49 | 0.57 | 0.70 | 0.75 | 0.84 | 0.86 |
| observed_diverse | 0.37 | 0.41 | 0.57 | 0.74 | 0.77 | 0.79 | 0.79 |
| cost_aware | 0.38 | 0.49 | 0.57 | 0.70 | 0.75 | 0.87 | 0.93 |
| history_ml | 0.42 | 0.52 | 0.64 | 0.71 | 0.84 | 0.93 | 0.94 |
| casper_slices | 0.16 | 0.19 | 0.84 | 0.92 | 0.93 | 0.93 | 0.93 |
| risk_aware_ts | 0.08 | 0.31 | 0.48 | 0.62 | 0.72 | 0.76 | 0.78 |
| adaptive_bayes | 0.54 | 0.67 | 0.75 | 0.75 | 0.75 | 0.75 | 0.75 |

![detection vs cost](figures/detection_vs_cost.png)

Cost until the first true detection (fraction of the full suite, detected cases only):

| strategy | cost_to_first_detection |
|---|---|
| full | 0.077 |
| random | 0.093 |
| declared | 0.029 |
| ir_tfidf | 0.051 |
| observed | 0.058 |
| observed_diverse | 0.063 |
| cost_aware | 0.068 |
| history_ml | 0.060 |
| casper_slices | 0.056 |
| risk_aware_ts | 0.074 |
| adaptive_bayes | 0.016 |

## 3. Changes no test reveals, and verdicts

Tokens spent on the changes no test reveals:

| strategy |
|---|

![tokens spent on changes no test reveals](figures/benign_waste.png)

Verdicts at a budget of 5% (shares of the runs):

| strategy | regressions: found | called clean | no verdict | other changes: called clean | called regression | no verdict | clean verdicts on a regression |
|---|---|---|---|---|---|---|---|
| full | 0.12 | 0.00 | 0.88 |  |  |  |  |
| random | 0.31 | 0.00 | 0.69 |  |  |  |  |
| declared | 0.38 | 0.45 | 0.17 |  |  |  | 1.00 |
| ir_tfidf | 0.54 | 0.00 | 0.46 |  |  |  |  |
| observed | 0.49 | 0.05 | 0.46 |  |  |  | 1.00 |
| observed_diverse | 0.43 | 0.06 | 0.52 |  |  |  | 1.00 |
| cost_aware | 0.49 | 0.00 | 0.51 |  |  |  |  |
| history_ml | 0.52 | 0.00 | 0.48 |  |  |  |  |
| casper_slices | 0.20 | 0.00 | 0.80 |  |  |  |  |
| risk_aware_ts | 0.40 | 0.00 | 0.60 |  |  |  |  |
| adaptive_bayes | 0.68 | 0.20 | 0.11 |  |  |  | 1.00 |

Verdicts at a budget of 20% (shares of the runs):

| strategy | regressions: found | called clean | no verdict | other changes: called clean | called regression | no verdict | clean verdicts on a regression |
|---|---|---|---|---|---|---|---|
| full | 0.88 | 0.00 | 0.12 |  |  |  |  |
| random | 0.73 | 0.00 | 0.27 |  |  |  |  |
| declared | 0.50 | 0.49 | 0.00 |  |  |  | 1.00 |
| ir_tfidf | 0.83 | 0.00 | 0.17 |  |  |  |  |
| observed | 0.72 | 0.09 | 0.19 |  |  |  | 1.00 |
| observed_diverse | 0.84 | 0.11 | 0.05 |  |  |  | 1.00 |
| cost_aware | 0.71 | 0.00 | 0.29 |  |  |  |  |
| history_ml | 0.75 | 0.00 | 0.25 |  |  |  |  |
| casper_slices | 0.98 | 0.00 | 0.02 |  |  |  |  |
| risk_aware_ts | 0.82 | 0.00 | 0.18 |  |  |  |  |
| adaptive_bayes | 0.73 | 0.23 | 0.04 |  |  |  | 1.00 |

## 4. Prioritization and selection quality

APFD / cost-cognizant APFD of the complete order, each change one fault found by the first of its revealing tests (an order drawn at random: the mean over the seeds); selection recall = revealing tests inside the selected subset; selected cost = what that subset costs:

| strategy | apfd | apfdc | selection_recall | selected_cost_fraction |
|---|---|---|---|---|
| full | 0.918 | 0.921 | 1.000 | 0.900 |
| random | 0.852 | 0.857 | 1.000 | 0.900 |
| declared | 0.943 | 0.932 | 0.246 | 0.106 |
| ir_tfidf | 0.884 | 0.882 | 1.000 | 0.900 |
| observed | 0.843 | 0.884 | 0.705 | 0.404 |
| observed_diverse | 0.950 | 0.911 | 0.705 | 0.404 |
| cost_aware | 0.777 | 0.840 | 1.000 | 0.900 |
| history_ml | 0.903 | 0.894 | 1.000 | 0.900 |
| casper_slices | 0.912 | 0.943 | 1.000 | 0.900 |
| risk_aware_ts | 0.892 | 0.857 | 1.000 | 0.900 |
| adaptive_bayes | 0.913 | 0.921 | 1.000 | 0.900 |

![apfdc](figures/apfdc.png)

## 5. Properties

The catalog of properties (`traceeval/catalog/properties.yaml`): for each, its tests' pass rate on the original app against its threshold:

| property | category | mandatory | threshold | tests | pass rate | met |
|---|---|---|---|---|---|---|
| `task_completion` | correctness |  | 0.95 | 71 | 0.94 | **no** |
| `correct_routing` | correctness |  | 0.95 | 65 | 0.98 | yes |
| `tool_trajectory` | correctness |  | 0.95 | 45 | 0.98 | yes |
| `answer_quality` | quality |  | 0.90 | 2 | 0.50 | **no** |
| `safety_authorization` | safety | yes | 1.00 | 9 | 1.00 | yes |
| `safety_guarded_mutation` | safety | yes | 1.00 | 6 | 0.83 | **no** |
| `safety_no_broken_publish` | safety | yes | 1.00 | 6 | 0.75 | **no** |
| `safety_privacy` | safety | yes | 1.00 | 3 | 1.00 | yes |
| `resilience_retry` | resilience |  | 0.95 | 3 | 1.00 | yes |
| `resilience_idempotency` | resilience |  | 0.95 | 5 | 1.00 | yes |
| `resilience_fail_safe` | resilience |  | 0.95 | 3 | 1.00 | yes |
| `efficiency` | efficiency |  | 0.90 | 1 | 1.00 | yes |
| `workflow_completion` | orchestration |  | 0.95 | 15 | 0.77 | **no** |
| `safety_human_approval` | safety | yes | 1.00 | 13 | 0.85 | **no** |
| `safety_brand_compliance` | safety | yes | 1.00 | 7 | 0.86 | **no** |

Coverage of the affected properties (those of a change's revealing tests) by the tests each strategy ran:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.27 | 0.29 | 0.29 | 0.29 | 0.31 | 0.34 | 0.34 |
| random | 0.29 | 0.43 | 0.57 | 0.65 | 0.66 | 0.66 | 0.67 |
| declared | 0.20 | 0.28 | 0.29 | 0.30 | 0.30 | 0.30 | 0.30 |
| ir_tfidf | 0.27 | 0.33 | 0.41 | 0.45 | 0.45 | 0.48 | 0.49 |
| observed | 0.18 | 0.23 | 0.35 | 0.49 | 0.50 | 0.50 | 0.51 |
| observed_diverse | 0.27 | 0.49 | 0.64 | 0.63 | 0.64 | 0.64 | 0.64 |
| cost_aware | 0.18 | 0.23 | 0.37 | 0.53 | 0.55 | 0.55 | 0.55 |
| history_ml | 0.30 | 0.37 | 0.53 | 0.54 | 0.55 | 0.55 | 0.55 |
| casper_slices | 0.25 | 0.54 | 0.56 | 0.58 | 0.58 | 0.58 | 0.58 |
| risk_aware_ts | 0.40 | 0.63 | 0.67 | 0.69 | 0.69 | 0.69 | 0.69 |
| adaptive_bayes | 0.24 | 0.34 | 0.37 | 0.37 | 0.37 | 0.37 | 0.37 |

## 6. Coverage

Coverage of the test suite: per dimension, how many components the tests declare and the traces show, and what no test covers. A feature (`catalog/features.yaml`) is covered by the tests that declare or call one of its tools. A tool error path is a place in the code where a tool call is refused, reached when a run executes it. A workflow is declared by the tests that name it and observed when a run delegates to exactly its agents in order. Execution paths are the distinct agent and tool sequences; risk lists tests per level.

| dimension | components | declared | observed | not covered |
|---|---|---|---|---|
| agent | 11 | 11 | 11 |  |
| feature | 19 | 18 | 19 |  |
| skill | 13 | 12 | 13 |  |
| tool | 32 | 30 | 31 | get_asset |
| tool error path | 31 |  | 14 | harness/dispatcher.py:60 Dispatcher.call unknown_tool, harness/dispatcher.py:66 Dispatcher.call tool_not_available, harness/dispatcher.py:77 Dispatcher.call invalid_arguments, harness/runtime.py:188 Runtime._delegate unknown_agent, harness/runtime.py:191 Runtime._delegate invalid_arguments, harness/runtime.py:195 Runtime._delegate max_delegation_depth, services/governance.py:39 export_user_data approval_required, services/governance.py:44 export_user_data not_found ... |
| configuration | 13 | 10 | 13 |  |
| setting value | 5 | 3 | 3 | runtime.idempotency_keys=false, seo.require_description=false |
| property | 15 | 15 | 15 |  |
| workflow | 6 | 6 | 6 |  |
| execution path | 81 |  | 81 |  |
| risk | 4 | 4 | 4 | critical 32, high 77, low 22, medium 49 |

Per component: how many tests declare it in their metadata, and how many invoke it in their recorded runs. A component few tests invoke is thinly covered. A difference between the two counts is where the hand-written metadata and the runs disagree.

| agent | declared | invoked |
|---|---|---|
| assets | 37 | 17 |
| authoring | 46 | 29 |
| brand | 12 | 12 |
| governance | 32 | 12 |
| insights | 6 | 6 |
| maintenance | 7 | 7 |
| optimizer | 6 | 7 |
| orchestrator | 67 | 153 |
| publishing | 63 | 47 |
| seo | 11 | 11 |
| translation | 35 | 15 |

| skill | declared | invoked |
|---|---|---|
| asset-management | 35 | 17 |
| brand-governance | 9 | 12 |
| data-insights | 6 | 6 |
| governance-checks | 0 | 120 |
| governance-ops | 32 | 12 |
| link-validation | 5 | 74 |
| page-authoring | 44 | 29 |
| publishing-workflow | 62 | 47 |
| rollback | 7 | 7 |
| routing | 67 | 153 |
| seo-metadata | 11 | 11 |
| site-optimization | 6 | 7 |
| translation | 34 | 15 |

| tool | declared | invoked |
|---|---|---|
| approve_review | 7 | 10 |
| attach_asset | 8 | 12 |
| audit_site | 4 | 4 |
| check_brand_policy | 6 | 7 |
| check_consent | 5 | 8 |
| check_permission | 9 | 112 |
| create_page | 11 | 15 |
| create_translation_job | 9 | 12 |
| export_user_data | 7 | 4 |
| fix_alt_text | 2 | 1 |
| get_asset | 0 | 0 |
| get_audit_log | 1 | 3 |
| get_brand_guidelines | 1 | 1 |
| get_page | 2 | 78 |
| get_page_metrics | 6 | 6 |
| get_seo_report | 2 | 9 |
| get_translation_status | 1 | 2 |
| list_versions | 2 | 6 |
| make_plan | 13 | 15 |
| publish_page | 29 | 21 |
| request_approval | 14 | 15 |
| request_review | 4 | 6 |
| rollback_page | 7 | 5 |
| route_to_agent | 0 | 152 |
| schedule_publish | 6 | 6 |
| search_assets | 2 | 5 |
| search_pages | 3 | 5 |
| set_page_metadata | 12 | 22 |
| unpublish_page | 7 | 7 |
| update_page_content | 10 | 25 |
| upload_asset | 4 | 5 |
| validate_links | 18 | 59 |

| feature | declared | invoked |
|---|---|---|
| show a page | 2 | 78 |
| create or edit a page | 20 | 26 |
| request and approve a page's review | 11 | 16 |
| publish a page | 29 | 21 |
| schedule a page | 6 | 6 |
| take a page down | 7 | 7 |
| check a page's links | 18 | 59 |
| set a page's SEO metadata | 12 | 23 |
| translate a page | 10 | 14 |
| upload, find and attach assets | 11 | 14 |
| check pages against the brand rules and find the pages that use a term | 10 | 13 |
| run a site health check and fix alt text | 6 | 5 |
| read page analytics | 6 | 6 |
| roll a page back to an earlier version | 7 | 6 |
| answer a privacy request (consent, data export) and show the audit history | 8 | 11 |
| refuse what the user may not do | 9 | 112 |
| hand a request to the specialist that owns it | 0 | 152 |
| plan a request that needs several specialists | 13 | 15 |
| ask a person before publishing, scheduling or taking pages down | 14 | 15 |

Change coverage over every change, without the ground truth: the share of the changed components the executed tests exercised, and the share of the properties the change may affect (`coverage.py`) that they checked.

Changed components exercised:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.37 | 0.49 | 0.51 | 0.54 | 0.57 | 0.57 | 0.57 |
| random | 0.58 | 0.72 | 0.81 | 0.85 | 0.87 | 0.87 | 0.87 |
| declared | 0.67 | 0.67 | 0.67 | 0.67 | 0.67 | 0.67 | 0.67 |
| ir_tfidf | 0.92 | 0.95 | 0.94 | 0.95 | 0.95 | 0.95 | 0.95 |
| observed | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 |
| observed_diverse | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 |
| cost_aware | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 |
| history_ml | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 |
| casper_slices | 0.61 | 0.78 | 0.87 | 0.87 | 0.87 | 0.87 | 0.87 |
| risk_aware_ts | 0.61 | 0.71 | 0.81 | 0.84 | 0.85 | 0.85 | 0.85 |
| adaptive_bayes | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 |

Affected properties checked:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.29 | 0.40 | 0.41 | 0.41 | 0.42 | 0.43 | 0.43 |
| random | 0.31 | 0.42 | 0.53 | 0.60 | 0.62 | 0.62 | 0.62 |
| declared | 0.20 | 0.25 | 0.25 | 0.26 | 0.26 | 0.26 | 0.26 |
| ir_tfidf | 0.30 | 0.38 | 0.43 | 0.45 | 0.46 | 0.46 | 0.47 |
| observed | 0.27 | 0.35 | 0.43 | 0.54 | 0.55 | 0.55 | 0.56 |
| observed_diverse | 0.30 | 0.50 | 0.57 | 0.57 | 0.58 | 0.58 | 0.58 |
| cost_aware | 0.27 | 0.35 | 0.45 | 0.54 | 0.55 | 0.55 | 0.56 |
| history_ml | 0.33 | 0.41 | 0.51 | 0.54 | 0.54 | 0.54 | 0.54 |
| casper_slices | 0.28 | 0.50 | 0.54 | 0.56 | 0.56 | 0.56 | 0.56 |
| risk_aware_ts | 0.38 | 0.53 | 0.58 | 0.61 | 0.61 | 0.61 | 0.61 |
| adaptive_bayes | 0.30 | 0.37 | 0.40 | 0.40 | 0.40 | 0.40 | 0.40 |

Runs that found no regression and tested every affected mandatory property (the method's step 5):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.05 | 0.05 | 0.08 | 0.12 | 0.13 | 1.00 | nan |
| random | 0.05 | 0.06 | 0.16 | 0.46 | 0.81 | 1.00 | nan |
| declared | 0.10 | 0.13 | 0.15 | 0.17 | 0.18 | 0.17 | 0.17 |
| ir_tfidf | 0.08 | 0.18 | 0.35 | 0.54 | 0.59 | 0.38 | nan |
| observed | 0.07 | 0.14 | 0.41 | 0.84 | 0.98 | 1.00 | 1.00 |
| observed_diverse | 0.08 | 0.23 | 0.82 | 1.00 | 1.00 | 1.00 | 1.00 |
| cost_aware | 0.07 | 0.14 | 0.47 | 0.84 | 0.98 | 1.00 | nan |
| history_ml | 0.08 | 0.14 | 0.65 | 0.66 | 0.83 | 1.00 | nan |
| casper_slices | 0.05 | 0.05 | 0.03 | 0.25 | 1.00 | nan | nan |
| risk_aware_ts | 0.06 | 0.19 | 0.31 | 0.76 | 0.94 | 1.00 | nan |
| adaptive_bayes | 0.21 | 0.63 | 0.95 | 1.00 | 1.00 | 1.00 | 1.00 |

Affected workflows run (the workflows of the tests that exercised a changed component):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.01 |
| random | 0.01 | 0.05 | 0.12 | 0.20 | 0.25 | 0.26 | 0.27 |
| declared | 0.07 | 0.22 | 0.28 | 0.29 | 0.29 | 0.29 | 0.29 |
| ir_tfidf | 0.03 | 0.10 | 0.17 | 0.21 | 0.23 | 0.24 | 0.24 |
| observed | 0.02 | 0.07 | 0.13 | 0.17 | 0.18 | 0.18 | 0.19 |
| observed_diverse | 0.10 | 0.38 | 0.52 | 0.60 | 0.60 | 0.60 | 0.60 |
| cost_aware | 0.02 | 0.07 | 0.14 | 0.17 | 0.18 | 0.18 | 0.19 |
| history_ml | 0.04 | 0.09 | 0.18 | 0.20 | 0.21 | 0.22 | 0.22 |
| casper_slices | 0.00 | 0.09 | 0.14 | 0.20 | 0.20 | 0.20 | 0.20 |
| risk_aware_ts | 0.05 | 0.20 | 0.34 | 0.45 | 0.47 | 0.47 | 0.47 |
| adaptive_bayes | 0.03 | 0.09 | 0.10 | 0.10 | 0.10 | 0.10 | 0.10 |

Affected features reached (the features with a tool or a part the change touches), over the changes that affect one:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.13 | 0.29 | 0.31 | 0.35 | 0.38 | 0.39 | 0.39 |
| random | 0.35 | 0.61 | 0.77 | 0.82 | 0.85 | 0.85 | 0.85 |
| declared | 0.59 | 0.60 | 0.61 | 0.62 | 0.62 | 0.62 | 0.62 |
| ir_tfidf | 0.85 | 0.91 | 0.93 | 0.94 | 0.94 | 0.94 | 0.94 |
| observed | 0.71 | 0.73 | 0.82 | 0.91 | 0.91 | 0.91 | 0.91 |
| observed_diverse | 0.74 | 0.76 | 0.94 | 0.94 | 0.94 | 0.94 | 0.94 |
| cost_aware | 0.71 | 0.73 | 0.84 | 0.91 | 0.91 | 0.91 | 0.91 |
| history_ml | 0.80 | 0.82 | 0.91 | 0.91 | 0.91 | 0.91 | 0.91 |
| casper_slices | 0.27 | 0.58 | 0.80 | 0.80 | 0.80 | 0.80 | 0.80 |
| risk_aware_ts | 0.39 | 0.63 | 0.76 | 0.80 | 0.81 | 0.81 | 0.81 |
| adaptive_bayes | 0.82 | 0.84 | 0.85 | 0.85 | 0.85 | 0.85 | 0.85 |

## How to read this

`detected` counts *changes* (one failing revealing test is enough). Compare strategies at equal tokens *spent*, not equal nominal budget: every run ends at its first failure, the selecting strategies also run out of tests, and `adaptive_bayes` also stops when it is confident. A good strategy is high in the first table of section 2 and low in the second. The sample is the changes: the seeds only draw which recorded run answers a test and the choices of the strategies that draw at random, so an interval is over the changes. A clean verdict is worth what the last column of the verdict tables says.
