# TRACE-Eval experiment report

`runs/qwen8` · 180 tests · 43 changes · 5 baseline repetitions · full suite = 2,461,491 tokens · tests failing on the original app: 7 · runs the environment broke, left out: 0

- Recorded with `Qwen/Qwen3.8-27B-FP8` (judge: qwen) at commit `3f240f3`, with uncommitted edits; the original app 5 times, one case at a time; the changed copies 5 times, 1 cases at a time.
- The empty change (the original app, run as the changed copies are): 0 of 180 tests end otherwise than in the baseline; of its 5580 requests, 5580 are the baseline's, 20 of them answered otherwise.

## 1. Ground truth — which changes are revealed by how many tests

| change | category | expected | revealing tests | diverged tests | replayed failures |
|---|---|---|---|---|---|
| `benign_brand_skill_prose_reworded` | benign | benign | 0 | 12 | 0 |
| `benign_code_comment_docstring` | benign | benign | 0 | 0 | 0 |
| `benign_code_rename_locals` | benign | benign | 0 | 0 | 0 |
| `benign_config_comments_reordered` | benign | benign | 0 | 0 | 0 |
| `benign_new_unused_tool` | benign | benign | 0 | 0 | 0 |
| `benign_orchestrator_prompt_wording` | benign | benign | 2 | 153 | 0 |
| `benign_routing_guidance_reordered` | benign | benign | 3 | 153 | 0 |
| `benign_skill_prose_reflow` | benign | benign | 1 | 46 | 0 |
| `benign_translation_intents_reordered` | benign | benign | 0 | 15 | 0 |
| `code_approval_gate_bypass` | code | regression | 0 | 2 | 0 |
| `code_audit_ignores_alt_text` | code | regression | 1 | 4 | 0 |
| `code_brand_case_sensitive` | code | regression | 1 | 1 | 0 |
| `code_edit_keeps_review` | code | regression | 4 | 4 | 1 |
| `code_get_page_review_flag` | code | regression | 18 | 61 | 0 |
| `code_insights_rank_reversed` | code | regression | 4 | 5 | 0 |
| `code_links_external_lenient` | code | regression | 6 | 7 | 0 |
| `code_metadata_arg_swap` | code | regression | 5 | 19 | 0 |
| `code_retry_drop_idempotency` | code | regression | 5 | 5 | 0 |
| `code_search_case_sensitive` | code | regression | 3 | 5 | 0 |
| `combined_seo_keyword_limit` | combined | regression | 0 | 2 | 0 |
| `config_default_agent_publishing` | config | regression | 5 | 153 | 0 |
| `config_disable_validate_links` | config | regression | 54 | 53 | 5 |
| `config_max_tool_calls_5` | config | regression | 9 | 5 | 5 |
| `config_require_review_false` | config | regression | 0 | 45 | 0 |
| `config_retries_0` | config | regression | 5 | 8 | 0 |
| `config_seo_title_20` | config | regression | 2 | 11 | 0 |
| `config_unpublish_no_approval` | config | regression | 0 | 1 | 0 |
| `prompt_governance_consent_tool_removed` | prompt | regression | 7 | 12 | 0 |
| `prompt_seo_tool_removed` | prompt | regression | 7 | 11 | 0 |
| `code_delegation_drops_context` | runtime | regression | 0 | 15 | 0 |
| `code_delegation_truncates_answer` | runtime | regression | 23 | 84 | 0 |
| `code_termination_off_by_six` | runtime | regression | 6 | 3 | 4 |
| `skill_authoring_drop_metadata` | skill | regression | 1 | 29 | 0 |
| `skill_governance_drop_consent` | skill | regression | 7 | 12 | 0 |
| `skill_linkval_ignore_assets` | skill | regression | 1 | 74 | 0 |
| `skill_publish_drop_link_validation` | skill | regression | 1 | 46 | 0 |
| `skill_publish_drop_permission_check` | skill | regression | 4 | 46 | 0 |
| `skill_rollback_drop_permission_check` | skill | regression | 1 | 7 | 0 |
| `skill_rollback_restores_latest` | skill | regression | 3 | 7 | 0 |
| `skill_routing_drop_approval` | skill | regression | 12 | 153 | 0 |
| `skill_routing_drop_brand_gate` | skill | regression | 1 | 153 | 0 |
| `skill_seo_drop_length_guard` | skill | regression | 3 | 11 | 0 |
| `skill_translation_wrong_default` | skill | regression | 5 | 15 | 0 |

Testbed sanity (every change labelled a regression revealed by at least one test, none labelled benign revealed): **VIOLATED**.

## 2. Detection within a budget

Every strategy is run the same way: a test that fails on the original app is not run, and a run ends at its first failure.

Fraction of the revealed regressions detected, by nominal budget (% of full-suite tokens):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.00 | 0.12 | 0.34 | 0.53 | 0.66 | 1.00 | 1.00 |
| random | 0.12 | 0.25 | 0.38 | 0.58 | 0.71 | 0.88 | 1.00 |
| declared | 0.47 | 0.50 | 0.50 | 0.56 | 0.56 | 0.59 | 0.59 |
| ir_tfidf | 0.56 | 0.66 | 0.78 | 0.84 | 0.88 | 1.00 | 1.00 |
| observed | 0.53 | 0.66 | 0.66 | 0.81 | 0.84 | 0.84 | 1.00 |
| observed_diverse | 0.50 | 0.53 | 0.69 | 0.75 | 0.84 | 0.94 | 1.00 |
| cost_aware | 0.53 | 0.66 | 0.66 | 0.81 | 0.84 | 0.84 | 1.00 |
| history_ml | 0.59 | 0.66 | 0.78 | 0.81 | 0.81 | 0.84 | 1.00 |
| casper_slices | 0.19 | 0.25 | 0.50 | 0.59 | 0.69 | 0.88 | 1.00 |
| risk_aware_ts | 0.13 | 0.37 | 0.46 | 0.66 | 0.76 | 0.86 | 1.00 |
| adaptive_bayes | 0.72 | 0.78 | 0.81 | 0.81 | 0.81 | 0.81 | 0.81 |

Tokens spent, as a mean over all changes, revealed or not (fraction of the full suite):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.020 | 0.049 | 0.090 | 0.159 | 0.212 | 0.284 | 0.379 |
| random | 0.019 | 0.045 | 0.084 | 0.148 | 0.200 | 0.281 | 0.388 |
| declared | 0.008 | 0.015 | 0.023 | 0.034 | 0.041 | 0.046 | 0.046 |
| ir_tfidf | 0.015 | 0.032 | 0.056 | 0.095 | 0.130 | 0.188 | 0.283 |
| observed | 0.014 | 0.028 | 0.049 | 0.080 | 0.103 | 0.143 | 0.178 |
| observed_diverse | 0.014 | 0.036 | 0.064 | 0.097 | 0.122 | 0.151 | 0.178 |
| cost_aware | 0.015 | 0.032 | 0.057 | 0.100 | 0.139 | 0.213 | 0.324 |
| history_ml | 0.014 | 0.031 | 0.053 | 0.093 | 0.132 | 0.207 | 0.319 |
| casper_slices | 0.019 | 0.044 | 0.080 | 0.143 | 0.198 | 0.285 | 0.385 |
| risk_aware_ts | 0.019 | 0.043 | 0.079 | 0.136 | 0.183 | 0.264 | 0.383 |
| adaptive_bayes | 0.013 | 0.022 | 0.031 | 0.038 | 0.043 | 0.052 | 0.066 |

At a budget of 5%, over the 32 revealed regressions (intervals: bootstrap over the changes; a difference whose interval holds 0 is not established):

| strategy | detected | 95% interval | tokens, all changes | difference to the best | 95% interval |
|---|---|---|---|---|---|
| full | 0.12 | 0.03 to 0.25 | 0.049 | -0.66 | -0.81 to -0.47 |
| random | 0.25 | 0.16 to 0.35 | 0.045 | -0.53 | -0.68 to -0.39 |
| declared | 0.50 | 0.31 to 0.69 | 0.015 | -0.28 | -0.44 to -0.12 |
| ir_tfidf | 0.66 | 0.50 to 0.81 | 0.032 | -0.12 | -0.28 to +0.00 |
| observed | 0.66 | 0.50 to 0.81 | 0.028 | -0.12 | -0.28 to +0.03 |
| observed_diverse | 0.53 | 0.34 to 0.72 | 0.036 | -0.25 | -0.44 to -0.09 |
| cost_aware | 0.66 | 0.50 to 0.81 | 0.032 | -0.12 | -0.28 to +0.03 |
| history_ml | 0.66 | 0.50 to 0.81 | 0.031 | -0.12 | -0.28 to +0.00 |
| casper_slices | 0.25 | 0.09 to 0.41 | 0.044 | -0.53 | -0.72 to -0.34 |
| risk_aware_ts | 0.37 | 0.26 to 0.49 | 0.043 | -0.41 | -0.59 to -0.24 |
| adaptive_bayes | 0.78 | 0.62 to 0.91 | 0.022 | best |  |

At a budget of 20%, over the 32 revealed regressions (intervals: bootstrap over the changes; a difference whose interval holds 0 is not established):

| strategy | detected | 95% interval | tokens, all changes | difference to the best | 95% interval |
|---|---|---|---|---|---|
| full | 0.53 | 0.34 to 0.69 | 0.159 | -0.31 | -0.50 to -0.12 |
| random | 0.58 | 0.47 to 0.69 | 0.148 | -0.26 | -0.41 to -0.11 |
| declared | 0.56 | 0.38 to 0.72 | 0.034 | -0.28 | -0.44 to -0.12 |
| ir_tfidf | 0.84 | 0.72 to 0.97 | 0.095 | best |  |
| observed | 0.81 | 0.66 to 0.94 | 0.080 | -0.03 | -0.16 to +0.09 |
| observed_diverse | 0.75 | 0.59 to 0.88 | 0.097 | -0.09 | -0.22 to +0.03 |
| cost_aware | 0.81 | 0.66 to 0.94 | 0.100 | -0.03 | -0.16 to +0.09 |
| history_ml | 0.81 | 0.66 to 0.94 | 0.093 | -0.03 | -0.16 to +0.09 |
| casper_slices | 0.59 | 0.44 to 0.75 | 0.143 | -0.25 | -0.44 to -0.09 |
| risk_aware_ts | 0.66 | 0.52 to 0.78 | 0.136 | -0.19 | -0.32 to -0.07 |
| adaptive_bayes | 0.81 | 0.66 to 0.94 | 0.038 | -0.03 | -0.16 to +0.09 |

Tokens spent on the revealed regressions only:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.020 | 0.048 | 0.087 | 0.145 | 0.182 | 0.209 | 0.209 |
| random | 0.018 | 0.043 | 0.078 | 0.131 | 0.165 | 0.205 | 0.222 |
| declared | 0.009 | 0.017 | 0.025 | 0.037 | 0.046 | 0.053 | 0.053 |
| ir_tfidf | 0.014 | 0.025 | 0.041 | 0.059 | 0.072 | 0.081 | 0.081 |
| observed | 0.013 | 0.025 | 0.042 | 0.066 | 0.084 | 0.115 | 0.136 |
| observed_diverse | 0.014 | 0.034 | 0.060 | 0.088 | 0.108 | 0.126 | 0.136 |
| cost_aware | 0.013 | 0.025 | 0.043 | 0.066 | 0.084 | 0.115 | 0.136 |
| history_ml | 0.013 | 0.025 | 0.037 | 0.056 | 0.075 | 0.106 | 0.129 |
| casper_slices | 0.019 | 0.043 | 0.074 | 0.123 | 0.164 | 0.212 | 0.217 |
| risk_aware_ts | 0.019 | 0.041 | 0.072 | 0.114 | 0.143 | 0.184 | 0.215 |
| adaptive_bayes | 0.012 | 0.018 | 0.020 | 0.020 | 0.020 | 0.020 | 0.020 |

Time spent on those changes (fraction of the full suite's run time, from each test's mean time on the original app):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.020 | 0.049 | 0.088 | 0.148 | 0.176 | 0.201 | 0.201 |
| random | 0.018 | 0.042 | 0.078 | 0.130 | 0.164 | 0.205 | 0.221 |
| declared | 0.008 | 0.019 | 0.029 | 0.044 | 0.052 | 0.058 | 0.058 |
| ir_tfidf | 0.013 | 0.025 | 0.043 | 0.063 | 0.077 | 0.086 | 0.086 |
| observed | 0.012 | 0.024 | 0.042 | 0.066 | 0.081 | 0.111 | 0.132 |
| observed_diverse | 0.014 | 0.038 | 0.070 | 0.102 | 0.119 | 0.137 | 0.147 |
| cost_aware | 0.012 | 0.024 | 0.042 | 0.066 | 0.082 | 0.111 | 0.132 |
| history_ml | 0.012 | 0.025 | 0.038 | 0.057 | 0.075 | 0.104 | 0.130 |
| casper_slices | 0.018 | 0.047 | 0.077 | 0.135 | 0.172 | 0.222 | 0.227 |
| risk_aware_ts | 0.020 | 0.046 | 0.080 | 0.126 | 0.158 | 0.199 | 0.227 |
| adaptive_bayes | 0.012 | 0.018 | 0.021 | 0.021 | 0.021 | 0.021 | 0.021 |

Critical regressions: the same detection rate, over the changes that break a safety property only:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.00 | 0.05 | 0.27 | 0.50 | 0.64 | 1.00 | 1.00 |
| random | 0.15 | 0.31 | 0.46 | 0.70 | 0.81 | 0.92 | 1.00 |
| declared | 0.55 | 0.55 | 0.55 | 0.59 | 0.59 | 0.59 | 0.59 |
| ir_tfidf | 0.68 | 0.82 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| observed | 0.64 | 0.73 | 0.73 | 0.86 | 0.86 | 0.86 | 1.00 |
| observed_diverse | 0.64 | 0.64 | 0.86 | 0.95 | 0.95 | 1.00 | 1.00 |
| cost_aware | 0.64 | 0.73 | 0.73 | 0.86 | 0.86 | 0.86 | 1.00 |
| history_ml | 0.73 | 0.77 | 0.82 | 0.86 | 0.86 | 0.86 | 1.00 |
| casper_slices | 0.27 | 0.36 | 0.50 | 0.77 | 0.77 | 0.95 | 1.00 |
| risk_aware_ts | 0.15 | 0.47 | 0.60 | 0.85 | 0.95 | 1.00 | 1.00 |
| adaptive_bayes | 0.77 | 0.86 | 0.91 | 0.91 | 0.91 | 0.91 | 0.91 |

![detection vs cost](figures/detection_vs_cost.png)

Cost until the first true detection (fraction of the full suite, detected cases only):

| strategy | cost_to_first_detection |
|---|---|
| full | 0.157 |
| random | 0.132 |
| declared | 0.030 |
| ir_tfidf | 0.045 |
| observed | 0.049 |
| observed_diverse | 0.072 |
| cost_aware | 0.049 |
| history_ml | 0.041 |
| casper_slices | 0.125 |
| risk_aware_ts | 0.112 |
| adaptive_bayes | 0.012 |

## 3. Changes no test reveals, and verdicts

Tokens spent on the changes no test reveals:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.020 | 0.050 | 0.099 | 0.200 | 0.300 | 0.500 | 0.872 |
| random | 0.020 | 0.050 | 0.100 | 0.199 | 0.300 | 0.499 | 0.872 |
| declared | 0.005 | 0.011 | 0.017 | 0.025 | 0.025 | 0.025 | 0.025 |
| ir_tfidf | 0.019 | 0.049 | 0.099 | 0.199 | 0.300 | 0.499 | 0.872 |
| observed | 0.016 | 0.036 | 0.070 | 0.120 | 0.160 | 0.225 | 0.300 |
| observed_diverse | 0.015 | 0.039 | 0.074 | 0.122 | 0.162 | 0.225 | 0.300 |
| cost_aware | 0.020 | 0.049 | 0.099 | 0.199 | 0.299 | 0.499 | 0.872 |
| history_ml | 0.020 | 0.050 | 0.100 | 0.200 | 0.300 | 0.500 | 0.872 |
| casper_slices | 0.020 | 0.049 | 0.100 | 0.200 | 0.300 | 0.499 | 0.872 |
| risk_aware_ts | 0.020 | 0.050 | 0.100 | 0.200 | 0.300 | 0.500 | 0.872 |
| adaptive_bayes | 0.016 | 0.035 | 0.060 | 0.089 | 0.109 | 0.145 | 0.199 |

![tokens spent on changes no test reveals](figures/benign_waste.png)

Verdicts at a budget of 5% (shares of the runs):

| strategy | regressions: found | called clean | no verdict | other changes: called clean | called regression | no verdict | clean verdicts on a regression |
|---|---|---|---|---|---|---|---|
| full | 0.12 | 0.00 | 0.88 | 0.00 | 0.00 | 1.00 |  |
| random | 0.25 | 0.00 | 0.75 | 0.00 | 0.00 | 1.00 |  |
| declared | 0.50 | 0.34 | 0.16 | 0.82 | 0.00 | 0.18 | 0.55 |
| ir_tfidf | 0.66 | 0.00 | 0.34 | 0.00 | 0.00 | 1.00 |  |
| observed | 0.66 | 0.00 | 0.34 | 0.27 | 0.00 | 0.73 | 0.00 |
| observed_diverse | 0.53 | 0.00 | 0.47 | 0.27 | 0.00 | 0.73 | 0.00 |
| cost_aware | 0.66 | 0.00 | 0.34 | 0.00 | 0.00 | 1.00 |  |
| history_ml | 0.66 | 0.00 | 0.34 | 0.00 | 0.00 | 1.00 |  |
| casper_slices | 0.25 | 0.00 | 0.75 | 0.00 | 0.00 | 1.00 |  |
| risk_aware_ts | 0.37 | 0.00 | 0.63 | 0.00 | 0.00 | 1.00 |  |
| adaptive_bayes | 0.78 | 0.12 | 0.09 | 0.45 | 0.00 | 0.55 | 0.44 |

Verdicts at a budget of 20% (shares of the runs):

| strategy | regressions: found | called clean | no verdict | other changes: called clean | called regression | no verdict | clean verdicts on a regression |
|---|---|---|---|---|---|---|---|
| full | 0.53 | 0.00 | 0.47 | 0.00 | 0.00 | 1.00 |  |
| random | 0.58 | 0.00 | 0.42 | 0.00 | 0.00 | 1.00 |  |
| declared | 0.56 | 0.34 | 0.09 | 1.00 | 0.00 | 0.00 | 0.50 |
| ir_tfidf | 0.84 | 0.00 | 0.16 | 0.00 | 0.00 | 1.00 |  |
| observed | 0.81 | 0.00 | 0.19 | 0.55 | 0.00 | 0.45 | 0.00 |
| observed_diverse | 0.75 | 0.00 | 0.25 | 0.55 | 0.00 | 0.45 | 0.00 |
| cost_aware | 0.81 | 0.00 | 0.19 | 0.00 | 0.00 | 1.00 |  |
| history_ml | 0.81 | 0.00 | 0.19 | 0.00 | 0.00 | 1.00 |  |
| casper_slices | 0.59 | 0.00 | 0.41 | 0.00 | 0.00 | 1.00 |  |
| risk_aware_ts | 0.66 | 0.00 | 0.34 | 0.00 | 0.00 | 1.00 |  |
| adaptive_bayes | 0.81 | 0.19 | 0.00 | 0.82 | 0.00 | 0.18 | 0.40 |

## 4. Prioritization and selection quality

APFD / cost-cognizant APFD of the complete order, each change one fault found by the first of its revealing tests (an order drawn at random: the mean over the seeds); selection recall = revealing tests inside the selected subset; selected cost = what that subset costs:

| strategy | apfd | apfdc | selection_recall | selected_cost_fraction |
|---|---|---|---|---|
| full | 0.771 | 0.764 | 1.000 | 0.875 |
| random | 0.747 | 0.748 | 1.000 | 0.875 |
| declared | 0.877 | 0.856 | 0.453 | 0.129 |
| ir_tfidf | 0.939 | 0.908 | 1.000 | 0.875 |
| observed | 0.807 | 0.847 | 1.000 | 0.418 |
| observed_diverse | 0.911 | 0.847 | 1.000 | 0.418 |
| cost_aware | 0.807 | 0.847 | 1.000 | 0.875 |
| history_ml | 0.839 | 0.853 | 1.000 | 0.875 |
| casper_slices | 0.712 | 0.749 | 1.000 | 0.875 |
| risk_aware_ts | 0.716 | 0.701 | 1.000 | 0.875 |
| adaptive_bayes | 0.924 | 0.916 | 1.000 | 0.875 |

![apfdc](figures/apfdc.png)

## 5. Properties

The catalog of properties (`traceeval/catalog/properties.yaml`): for each, its tests' pass rate on the original app against its threshold:

| property | category | mandatory | threshold | tests | pass rate | met |
|---|---|---|---|---|---|---|
| `task_completion` | correctness |  | 0.95 | 71 | 0.94 | **no** |
| `correct_routing` | correctness |  | 0.95 | 65 | 1.00 | yes |
| `tool_trajectory` | correctness |  | 0.95 | 45 | 0.98 | yes |
| `answer_quality` | quality |  | 0.90 | 2 | 0.50 | **no** |
| `safety_authorization` | safety | yes | 1.00 | 9 | 1.00 | yes |
| `safety_guarded_mutation` | safety | yes | 1.00 | 6 | 0.83 | **no** |
| `safety_no_broken_publish` | safety | yes | 1.00 | 6 | 0.67 | **no** |
| `safety_privacy` | safety | yes | 1.00 | 3 | 1.00 | yes |
| `resilience_retry` | resilience |  | 0.95 | 3 | 1.00 | yes |
| `resilience_idempotency` | resilience |  | 0.95 | 5 | 1.00 | yes |
| `resilience_fail_safe` | resilience |  | 0.95 | 3 | 1.00 | yes |
| `efficiency` | efficiency |  | 0.90 | 1 | 1.00 | yes |
| `workflow_completion` | orchestration |  | 0.95 | 15 | 0.73 | **no** |
| `safety_human_approval` | safety | yes | 1.00 | 13 | 0.85 | **no** |
| `safety_brand_compliance` | safety | yes | 1.00 | 7 | 0.86 | **no** |

Coverage of the affected properties (those of a change's revealing tests) by the tests each strategy ran:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.40 | 0.49 | 0.53 | 0.53 | 0.57 | 0.67 | 0.67 |
| random | 0.41 | 0.55 | 0.66 | 0.74 | 0.78 | 0.79 | 0.81 |
| declared | 0.29 | 0.41 | 0.41 | 0.41 | 0.41 | 0.43 | 0.43 |
| ir_tfidf | 0.47 | 0.49 | 0.51 | 0.51 | 0.51 | 0.58 | 0.58 |
| observed | 0.34 | 0.44 | 0.44 | 0.63 | 0.65 | 0.65 | 0.68 |
| observed_diverse | 0.40 | 0.53 | 0.64 | 0.64 | 0.72 | 0.74 | 0.76 |
| cost_aware | 0.34 | 0.44 | 0.44 | 0.63 | 0.65 | 0.65 | 0.68 |
| history_ml | 0.37 | 0.46 | 0.53 | 0.61 | 0.62 | 0.64 | 0.67 |
| casper_slices | 0.38 | 0.44 | 0.59 | 0.55 | 0.60 | 0.66 | 0.70 |
| risk_aware_ts | 0.44 | 0.67 | 0.71 | 0.75 | 0.77 | 0.78 | 0.82 |
| adaptive_bayes | 0.45 | 0.53 | 0.54 | 0.54 | 0.54 | 0.54 | 0.54 |

## 6. Coverage

Coverage of the test suite: per dimension, how many components the tests declare and the traces show, and what no test covers. A feature (`catalog/features.yaml`) is covered by the tests that declare or call one of its tools. A tool error path is a place in the code where a tool call is refused, reached when a run executes it. A workflow is declared by the tests that name it and observed when a run delegates to exactly its agents in order. Execution paths are the distinct agent and tool sequences; risk lists tests per level.

| dimension | components | declared | observed | not covered |
|---|---|---|---|---|
| agent | 11 | 11 | 11 |  |
| feature | 19 | 18 | 19 |  |
| skill | 13 | 12 | 13 |  |
| tool | 32 | 30 | 31 | get_asset |
| tool error path | 32 |  | 14 | harness/dispatcher.py:73 Dispatcher.call invalid_arguments, harness/dispatcher.py:156 Dispatcher.gate unknown_tool, harness/dispatcher.py:162 Dispatcher.gate tool_not_available, harness/runtime.py:195 Runtime._delegate invalid_arguments, harness/runtime.py:208 Runtime._delegate unknown_agent, harness/runtime.py:211 Runtime._delegate invalid_arguments, harness/runtime.py:218 Runtime._delegate max_delegation_depth, services/governance.py:39 export_user_data approval_required ... |
| configuration | 13 | 10 | 13 |  |
| setting value | 5 | 3 | 3 | runtime.idempotency_keys=false, seo.require_description=false |
| property | 15 | 15 | 15 |  |
| workflow | 6 | 6 | 6 |  |
| execution path | 75 |  | 75 |  |
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
| publishing | 63 | 46 |
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
| publishing-workflow | 62 | 46 |
| rollback | 7 | 7 |
| routing | 67 | 153 |
| seo-metadata | 11 | 11 |
| site-optimization | 6 | 7 |
| translation | 34 | 15 |

| tool | declared | invoked |
|---|---|---|
| approve_review | 7 | 9 |
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
| publish_page | 29 | 20 |
| request_approval | 14 | 14 |
| request_review | 4 | 6 |
| rollback_page | 7 | 5 |
| route_to_agent | 0 | 153 |
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
| request and approve a page's review | 11 | 15 |
| publish a page | 29 | 20 |
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
| hand a request to the specialist that owns it | 0 | 153 |
| plan a request that needs several specialists | 13 | 15 |
| ask a person before publishing, scheduling or taking pages down | 14 | 14 |

Change coverage over every change, without the ground truth: the share of the changed components the executed tests exercised, and the share of the properties the change may affect (`coverage.py`) that they checked.

Changed components exercised:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.37 | 0.53 | 0.58 | 0.72 | 0.87 | 0.97 | 0.97 |
| random | 0.59 | 0.74 | 0.85 | 0.93 | 0.96 | 0.97 | 0.97 |
| declared | 0.67 | 0.67 | 0.67 | 0.67 | 0.67 | 0.67 | 0.67 |
| ir_tfidf | 0.92 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 |
| observed | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 |
| observed_diverse | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 |
| cost_aware | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 |
| history_ml | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 |
| casper_slices | 0.61 | 0.73 | 0.85 | 0.94 | 0.94 | 0.97 | 0.97 |
| risk_aware_ts | 0.58 | 0.76 | 0.86 | 0.95 | 0.96 | 0.97 | 0.97 |
| adaptive_bayes | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 |

Affected properties checked:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.29 | 0.40 | 0.45 | 0.47 | 0.51 | 0.63 | 0.63 |
| random | 0.32 | 0.44 | 0.58 | 0.69 | 0.73 | 0.76 | 0.77 |
| declared | 0.18 | 0.23 | 0.24 | 0.26 | 0.27 | 0.27 | 0.27 |
| ir_tfidf | 0.28 | 0.36 | 0.44 | 0.48 | 0.49 | 0.52 | 0.54 |
| observed | 0.26 | 0.33 | 0.41 | 0.54 | 0.56 | 0.57 | 0.59 |
| observed_diverse | 0.28 | 0.48 | 0.57 | 0.61 | 0.65 | 0.67 | 0.68 |
| cost_aware | 0.26 | 0.33 | 0.42 | 0.54 | 0.56 | 0.57 | 0.59 |
| history_ml | 0.27 | 0.38 | 0.45 | 0.53 | 0.56 | 0.56 | 0.59 |
| casper_slices | 0.28 | 0.37 | 0.60 | 0.62 | 0.65 | 0.67 | 0.71 |
| risk_aware_ts | 0.38 | 0.57 | 0.64 | 0.70 | 0.72 | 0.74 | 0.76 |
| adaptive_bayes | 0.31 | 0.40 | 0.45 | 0.46 | 0.46 | 0.46 | 0.47 |

Runs that found no regression and tested every affected mandatory property (the method's step 5):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.05 | 0.05 | 0.06 | 0.08 | 0.09 | 1.00 | 1.00 |
| random | 0.05 | 0.06 | 0.14 | 0.44 | 0.70 | 0.96 | 1.00 |
| declared | 0.11 | 0.11 | 0.15 | 0.16 | 0.20 | 0.17 | 0.17 |
| ir_tfidf | 0.08 | 0.18 | 0.28 | 0.44 | 0.47 | 0.82 | 1.00 |
| observed | 0.08 | 0.14 | 0.36 | 0.76 | 0.88 | 0.94 | 0.91 |
| observed_diverse | 0.07 | 0.19 | 0.67 | 0.89 | 0.94 | 0.92 | 0.91 |
| cost_aware | 0.08 | 0.14 | 0.41 | 0.76 | 0.94 | 1.00 | 1.00 |
| history_ml | 0.08 | 0.14 | 0.39 | 0.71 | 0.88 | 1.00 | 1.00 |
| casper_slices | 0.05 | 0.06 | 0.26 | 0.67 | 0.86 | 0.95 | 1.00 |
| risk_aware_ts | 0.07 | 0.21 | 0.32 | 0.69 | 0.95 | 1.00 | 1.00 |
| adaptive_bayes | 0.20 | 0.50 | 0.82 | 1.00 | 1.00 | 1.00 | 1.00 |

Affected workflows run (the workflows of the tests that exercised a changed component):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.07 | 0.22 |
| random | 0.01 | 0.05 | 0.11 | 0.23 | 0.34 | 0.43 | 0.50 |
| declared | 0.05 | 0.18 | 0.23 | 0.26 | 0.27 | 0.27 | 0.27 |
| ir_tfidf | 0.03 | 0.09 | 0.18 | 0.27 | 0.33 | 0.35 | 0.37 |
| observed | 0.02 | 0.05 | 0.13 | 0.19 | 0.21 | 0.24 | 0.33 |
| observed_diverse | 0.08 | 0.34 | 0.52 | 0.66 | 0.69 | 0.69 | 0.69 |
| cost_aware | 0.02 | 0.05 | 0.14 | 0.19 | 0.21 | 0.24 | 0.33 |
| history_ml | 0.02 | 0.11 | 0.18 | 0.23 | 0.24 | 0.28 | 0.37 |
| casper_slices | 0.00 | 0.00 | 0.16 | 0.45 | 0.50 | 0.54 | 0.56 |
| risk_aware_ts | 0.06 | 0.22 | 0.40 | 0.57 | 0.65 | 0.69 | 0.69 |
| adaptive_bayes | 0.03 | 0.09 | 0.12 | 0.14 | 0.14 | 0.14 | 0.14 |

Affected features reached (the features with a tool or a part the change touches), over the changes that affect one:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.13 | 0.33 | 0.39 | 0.57 | 0.72 | 0.90 | 0.90 |
| random | 0.35 | 0.62 | 0.81 | 0.92 | 0.95 | 0.96 | 0.96 |
| declared | 0.57 | 0.58 | 0.59 | 0.60 | 0.60 | 0.60 | 0.60 |
| ir_tfidf | 0.85 | 0.93 | 0.94 | 0.96 | 0.96 | 0.96 | 0.96 |
| observed | 0.69 | 0.71 | 0.80 | 0.90 | 0.90 | 0.90 | 0.90 |
| observed_diverse | 0.71 | 0.73 | 0.94 | 0.94 | 0.94 | 0.94 | 0.94 |
| cost_aware | 0.69 | 0.71 | 0.81 | 0.90 | 0.90 | 0.90 | 0.90 |
| history_ml | 0.78 | 0.79 | 0.89 | 0.90 | 0.90 | 0.90 | 0.90 |
| casper_slices | 0.27 | 0.41 | 0.81 | 0.94 | 0.94 | 0.95 | 0.95 |
| risk_aware_ts | 0.36 | 0.66 | 0.78 | 0.91 | 0.92 | 0.94 | 0.94 |
| adaptive_bayes | 0.81 | 0.85 | 0.88 | 0.88 | 0.88 | 0.88 | 0.88 |

## 7. Replay-first

Every test was run on every changed copy with the model's calls answered from the answers recorded on the original app (`traceeval replay-first`; no model is called). A test either replays to the end, and its outcome on the changed copy is known for no tokens, or diverges at the first request the original app never made, and needs the model from there on.

What the replay settles alone, by kind of change:

| kind of change | changes | no test diverges | a replayed test fails | diverged tests, mean | their share of the suite's tokens | after the divergence point |
|---|---|---|---|---|---|---|
| benign | 9 | 4 | 0 | 42 of 180 | 0.293 | 0.255 |
| code | 10 | 0 | 1 | 11 of 180 | 0.105 | 0.067 |
| combined | 1 | 0 | 0 | 2 of 180 | 0.012 | 0.004 |
| config | 7 | 0 | 2 | 39 of 180 | 0.321 | 0.240 |
| prompt | 2 | 0 | 0 | 12 of 180 | 0.099 | 0.081 |
| runtime | 3 | 0 | 1 | 34 of 180 | 0.374 | 0.226 |
| skill | 11 | 0 | 0 | 50 of 180 | 0.398 | 0.336 |
| all | 43 | 4 | 4 | 34 of 180 | 0.271 | 0.214 |

Over the 1448 diverged (change, test) pairs, the change first reaches the model in what an agent is sent up front (its prompt, skills, tools or task) on 1179, and in a tool result on 269.

The replay against the recorded ground truth:

- the tests that replay to the end were not run on these copies: the replay's outcome is the one on record;
- the 210 revealing (change, test) pairs: 15 replay to a failure, 195 diverge, 0 replay to a pass;
- revealed regressions with a revealing test that fails in the replay or diverges: 32 of 32;
- changes no test reveals on which a replayed test fails: 0.

The replay against the recorded runs, one by one, over the tests that replay to the end. A run is identical to the replay when it has the same tool calls, final answer, final state and token count:

| recorded runs of | runs | end like the replay | identical to the replay |
|---|---|---|---|
| the original app | 900 | 900 | 883 |
| the original app, run as the changed copies are | 900 | 900 | 880 |
| the changed copies | 0 | 0 | 0 |

The condition itself, a model call being a function of its request, request by request:

| requests of | sent before | of which |
|---|---|---|
| the empty change | 5580 | 20 (0.36%) answered otherwise than the cassette |
| the changed copies | 27244 | 634 (2.33%) answered otherwise than the cassette |

The strategies run replay-first: a test that replays to the end is not run, a replayed failure of a test that passes on the original app ends the run for no tokens, and a diverged test costs its tokens after the divergence point. A run that ends because every diverged test has run and passed is a clean verdict that leaves no reachable test untested.

Fraction of the revealed regressions detected, by nominal budget:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.69 | 0.75 | 0.81 | 0.91 | 0.91 | 1.00 | 1.00 |
| random | 0.74 | 0.76 | 0.82 | 0.89 | 0.93 | 0.99 | 1.00 |
| cheapest | 0.72 | 0.72 | 0.84 | 0.88 | 0.91 | 1.00 | 1.00 |
| late_divergence | 0.69 | 0.72 | 0.72 | 0.88 | 0.91 | 1.00 | 1.00 |
| declared | 0.56 | 0.59 | 0.59 | 0.66 | 0.69 | 0.69 | 0.69 |
| ir_tfidf | 0.75 | 0.78 | 0.91 | 0.94 | 0.94 | 1.00 | 1.00 |
| observed | 0.75 | 0.81 | 0.84 | 0.88 | 0.91 | 0.91 | 1.00 |
| observed_diverse | 0.69 | 0.72 | 0.78 | 0.88 | 0.94 | 0.94 | 1.00 |
| cost_aware | 0.75 | 0.81 | 0.84 | 0.88 | 0.91 | 0.91 | 1.00 |
| history_ml | 0.75 | 0.84 | 0.88 | 0.88 | 0.91 | 0.91 | 1.00 |
| casper_slices | 0.69 | 0.75 | 0.81 | 0.84 | 0.97 | 1.00 | 1.00 |
| risk_aware_ts | 0.69 | 0.79 | 0.81 | 0.88 | 0.94 | 0.94 | 1.00 |
| adaptive_bayes | 0.81 | 0.84 | 0.84 | 0.84 | 0.84 | 0.84 | 0.84 |

Tokens spent, as a mean over all changes (fraction of the full suite):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.008 | 0.017 | 0.029 | 0.042 | 0.051 | 0.052 | 0.052 |
| random | 0.009 | 0.018 | 0.029 | 0.045 | 0.053 | 0.058 | 0.060 |
| cheapest | 0.008 | 0.016 | 0.028 | 0.043 | 0.053 | 0.062 | 0.062 |
| late_divergence | 0.008 | 0.018 | 0.032 | 0.050 | 0.060 | 0.070 | 0.070 |
| declared | 0.006 | 0.011 | 0.018 | 0.026 | 0.032 | 0.034 | 0.034 |
| ir_tfidf | 0.008 | 0.016 | 0.025 | 0.036 | 0.043 | 0.044 | 0.044 |
| observed | 0.008 | 0.015 | 0.025 | 0.040 | 0.050 | 0.064 | 0.072 |
| observed_diverse | 0.009 | 0.020 | 0.032 | 0.049 | 0.058 | 0.067 | 0.075 |
| cost_aware | 0.008 | 0.015 | 0.025 | 0.040 | 0.050 | 0.064 | 0.072 |
| history_ml | 0.007 | 0.015 | 0.024 | 0.037 | 0.047 | 0.061 | 0.072 |
| casper_slices | 0.009 | 0.018 | 0.029 | 0.046 | 0.053 | 0.054 | 0.054 |
| risk_aware_ts | 0.009 | 0.020 | 0.030 | 0.046 | 0.054 | 0.064 | 0.073 |
| adaptive_bayes | 0.007 | 0.010 | 0.013 | 0.016 | 0.016 | 0.016 | 0.016 |

For comparison, a cache of the original app's answers in front of the model, with the whole suite run again and no stop at a failure, pays every diverged test from its divergence point on: 0.214 of the suite's tokens per change (median 0.082) at most. After that point a run still sends requests the original app made; with those answered from the cache too, it pays 0.142 (median 0.050). It finds every revealed regression.

The same tests run whole, without the replayed part taken off:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.012 | 0.023 | 0.035 | 0.051 | 0.061 | 0.062 | 0.062 |
| random | 0.012 | 0.025 | 0.038 | 0.057 | 0.066 | 0.072 | 0.073 |
| cheapest | 0.011 | 0.021 | 0.035 | 0.051 | 0.063 | 0.073 | 0.073 |
| late_divergence | 0.017 | 0.033 | 0.053 | 0.072 | 0.082 | 0.092 | 0.092 |
| declared | 0.009 | 0.016 | 0.024 | 0.033 | 0.039 | 0.041 | 0.041 |
| ir_tfidf | 0.010 | 0.022 | 0.033 | 0.049 | 0.056 | 0.057 | 0.057 |
| observed | 0.010 | 0.020 | 0.032 | 0.050 | 0.062 | 0.076 | 0.084 |
| observed_diverse | 0.012 | 0.028 | 0.044 | 0.065 | 0.074 | 0.083 | 0.091 |
| cost_aware | 0.010 | 0.020 | 0.032 | 0.050 | 0.062 | 0.076 | 0.084 |
| history_ml | 0.010 | 0.020 | 0.032 | 0.048 | 0.060 | 0.074 | 0.085 |
| casper_slices | 0.012 | 0.023 | 0.039 | 0.058 | 0.069 | 0.069 | 0.069 |
| risk_aware_ts | 0.013 | 0.027 | 0.041 | 0.060 | 0.069 | 0.078 | 0.088 |
| adaptive_bayes | 0.010 | 0.014 | 0.017 | 0.022 | 0.022 | 0.022 | 0.022 |

The same tests charged for their new requests only. After its divergence point a run still sends requests the original app made, and a check answers those from the cassette too (`traceeval check`):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.006 | 0.013 | 0.022 | 0.031 | 0.036 | 0.036 | 0.036 |
| random | 0.007 | 0.014 | 0.023 | 0.034 | 0.040 | 0.043 | 0.044 |
| cheapest | 0.007 | 0.015 | 0.025 | 0.036 | 0.043 | 0.047 | 0.047 |
| late_divergence | 0.008 | 0.016 | 0.029 | 0.043 | 0.050 | 0.053 | 0.053 |
| declared | 0.006 | 0.010 | 0.015 | 0.021 | 0.026 | 0.028 | 0.028 |
| ir_tfidf | 0.007 | 0.014 | 0.022 | 0.031 | 0.036 | 0.037 | 0.037 |
| observed | 0.007 | 0.014 | 0.023 | 0.035 | 0.041 | 0.049 | 0.054 |
| observed_diverse | 0.007 | 0.016 | 0.025 | 0.039 | 0.044 | 0.049 | 0.054 |
| cost_aware | 0.007 | 0.014 | 0.023 | 0.035 | 0.041 | 0.049 | 0.054 |
| history_ml | 0.007 | 0.013 | 0.021 | 0.032 | 0.039 | 0.047 | 0.054 |
| casper_slices | 0.007 | 0.015 | 0.024 | 0.036 | 0.042 | 0.042 | 0.042 |
| risk_aware_ts | 0.008 | 0.015 | 0.023 | 0.035 | 0.041 | 0.047 | 0.053 |
| adaptive_bayes | 0.006 | 0.008 | 0.011 | 0.013 | 0.014 | 0.014 | 0.014 |

At a budget of 5%, over the 32 revealed regressions (intervals: bootstrap over the changes; a difference whose interval holds 0 is not established):

| strategy | detected | 95% interval | tokens, all changes | difference to the best | 95% interval |
|---|---|---|---|---|---|
| full | 0.75 | 0.59 to 0.88 | 0.017 | -0.09 | -0.22 to +0.03 |
| random | 0.76 | 0.62 to 0.88 | 0.018 | -0.09 | -0.22 to +0.04 |
| cheapest | 0.72 | 0.56 to 0.88 | 0.016 | -0.12 | -0.25 to -0.03 |
| late_divergence | 0.72 | 0.56 to 0.88 | 0.018 | -0.12 | -0.25 to -0.03 |
| declared | 0.59 | 0.41 to 0.75 | 0.011 | -0.25 | -0.44 to -0.09 |
| ir_tfidf | 0.78 | 0.62 to 0.91 | 0.016 | -0.06 | -0.19 to +0.06 |
| observed | 0.81 | 0.66 to 0.94 | 0.015 | -0.03 | -0.09 to +0.00 |
| observed_diverse | 0.72 | 0.56 to 0.88 | 0.020 | -0.12 | -0.28 to +0.00 |
| cost_aware | 0.81 | 0.66 to 0.94 | 0.015 | -0.03 | -0.09 to +0.00 |
| history_ml | 0.84 | 0.72 to 0.97 | 0.015 | best |  |
| casper_slices | 0.75 | 0.59 to 0.88 | 0.018 | -0.09 | -0.19 to +0.00 |
| risk_aware_ts | 0.79 | 0.66 to 0.91 | 0.020 | -0.05 | -0.15 to +0.05 |
| adaptive_bayes | 0.84 | 0.72 to 0.97 | 0.010 | +0.00 | -0.12 to +0.12 |

At a budget of 20%, over the 32 revealed regressions (intervals: bootstrap over the changes; a difference whose interval holds 0 is not established):

| strategy | detected | 95% interval | tokens, all changes | difference to the best | 95% interval |
|---|---|---|---|---|---|
| full | 0.91 | 0.78 to 1.00 | 0.042 | -0.03 | -0.16 to +0.06 |
| random | 0.89 | 0.79 to 0.96 | 0.045 | -0.05 | -0.14 to +0.03 |
| cheapest | 0.88 | 0.75 to 0.97 | 0.043 | -0.06 | -0.16 to +0.00 |
| late_divergence | 0.88 | 0.75 to 0.97 | 0.050 | -0.06 | -0.16 to +0.00 |
| declared | 0.66 | 0.47 to 0.81 | 0.026 | -0.28 | -0.44 to -0.12 |
| ir_tfidf | 0.94 | 0.84 to 1.00 | 0.036 | best |  |
| observed | 0.88 | 0.75 to 0.97 | 0.040 | -0.06 | -0.16 to +0.00 |
| observed_diverse | 0.88 | 0.75 to 0.97 | 0.049 | -0.06 | -0.16 to +0.00 |
| cost_aware | 0.88 | 0.75 to 0.97 | 0.040 | -0.06 | -0.16 to +0.00 |
| history_ml | 0.88 | 0.75 to 0.97 | 0.037 | -0.06 | -0.16 to +0.00 |
| casper_slices | 0.84 | 0.72 to 0.97 | 0.046 | -0.09 | -0.22 to +0.03 |
| risk_aware_ts | 0.88 | 0.76 to 0.97 | 0.046 | -0.06 | -0.14 to +0.00 |
| adaptive_bayes | 0.84 | 0.72 to 0.97 | 0.016 | -0.09 | -0.19 to +0.00 |

![replay-first: detection vs cost](figures/replay_first.png)

Verdicts at a budget of 20% (shares of the runs):

| strategy | regressions: found | called clean | no verdict | other changes: called clean | called regression | no verdict | clean verdicts on a regression |
|---|---|---|---|---|---|---|---|
| full | 0.91 | 0.00 | 0.09 | 0.82 | 0.00 | 0.18 | 0.00 |
| random | 0.89 | 0.00 | 0.11 | 0.82 | 0.00 | 0.18 | 0.00 |
| cheapest | 0.88 | 0.00 | 0.12 | 0.82 | 0.00 | 0.18 | 0.00 |
| late_divergence | 0.88 | 0.00 | 0.12 | 0.82 | 0.00 | 0.18 | 0.00 |
| declared | 0.66 | 0.25 | 0.09 | 1.00 | 0.00 | 0.00 | 0.42 |
| ir_tfidf | 0.94 | 0.00 | 0.06 | 0.82 | 0.00 | 0.18 | 0.00 |
| observed | 0.88 | 0.00 | 0.12 | 0.82 | 0.00 | 0.18 | 0.00 |
| observed_diverse | 0.88 | 0.00 | 0.12 | 0.82 | 0.00 | 0.18 | 0.00 |
| cost_aware | 0.88 | 0.00 | 0.12 | 0.82 | 0.00 | 0.18 | 0.00 |
| history_ml | 0.88 | 0.00 | 0.12 | 0.82 | 0.00 | 0.18 | 0.00 |
| casper_slices | 0.84 | 0.00 | 0.16 | 0.82 | 0.00 | 0.18 | 0.00 |
| risk_aware_ts | 0.88 | 0.00 | 0.12 | 0.82 | 0.00 | 0.18 | 0.00 |
| adaptive_bayes | 0.84 | 0.16 | 0.00 | 0.91 | 0.00 | 0.09 | 0.33 |

Verdicts at a budget of 100% (shares of the runs):

| strategy | regressions: found | called clean | no verdict | other changes: called clean | called regression | no verdict | clean verdicts on a regression |
|---|---|---|---|---|---|---|---|
| full | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 |
| random | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 |
| cheapest | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 |
| late_divergence | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 |
| declared | 0.69 | 0.31 | 0.00 | 1.00 | 0.00 | 0.00 | 0.48 |
| ir_tfidf | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 |
| observed | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 |
| observed_diverse | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 |
| cost_aware | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 |
| history_ml | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 |
| casper_slices | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 |
| risk_aware_ts | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 |
| adaptive_bayes | 0.84 | 0.16 | 0.00 | 1.00 | 0.00 | 0.00 | 0.31 |

## How to read this

`detected` counts *changes* (one failing revealing test is enough). Compare strategies at equal tokens *spent*, not equal nominal budget: every run ends at its first failure, the selecting strategies also run out of tests, and `adaptive_bayes` also stops when it is confident. A good strategy is high in the first table of section 2 and low in the second. The sample is the changes: the seeds only draw which recorded run answers a test and the choices of the strategies that draw at random, so an interval is over the changes. A clean verdict is worth what the last column of the verdict tables says.

Section 7 reads like section 2, with the replay in front: compare a strategy's row there with its row here. Replay-first, a strategy that orders the whole suite gives a clean verdict once every diverged test has run and passed; that verdict holds as far as the replay agrees with the recording, which the first lines of the section measure.
