# TRACE-Eval experiment report

`runs/gemma7` · 180 tests · 43 changes · 5 baseline repetitions · full suite = 2,084,733 tokens · tests failing on the original app: 8 · runs the environment broke, left out: 0

## 1. Ground truth — which changes are revealed by how many tests

| change | category | expected | revealing tests | diverged tests | replayed failures |
|---|---|---|---|---|---|
| `benign_brand_skill_prose_reworded` | benign | benign | 0 | 12 | 0 |
| `benign_code_comment_docstring` | benign | benign | 0 | 0 | 0 |
| `benign_code_rename_locals` | benign | benign | 0 | 0 | 0 |
| `benign_config_comments_reordered` | benign | benign | 0 | 0 | 0 |
| `benign_new_unused_tool` | benign | benign | 0 | 0 | 0 |
| `benign_orchestrator_prompt_wording` | benign | benign | 0 | 153 | 0 |
| `benign_routing_guidance_reordered` | benign | benign | 0 | 153 | 0 |
| `benign_skill_prose_reflow` | benign | benign | 0 | 46 | 0 |
| `benign_translation_intents_reordered` | benign | benign | 0 | 14 | 0 |
| `code_approval_gate_bypass` | code | regression | 1 | 2 | 0 |
| `code_audit_ignores_alt_text` | code | regression | 1 | 4 | 0 |
| `code_brand_case_sensitive` | code | regression | 1 | 1 | 0 |
| `code_edit_keeps_review` | code | regression | 0 | 0 | 0 |
| `code_get_page_review_flag` | code | regression | 4 | 63 | 0 |
| `code_insights_rank_reversed` | code | regression | 4 | 5 | 0 |
| `code_links_external_lenient` | code | regression | 6 | 7 | 0 |
| `code_metadata_arg_swap` | code | regression | 5 | 21 | 0 |
| `code_retry_drop_idempotency` | code | regression | 5 | 5 | 0 |
| `code_search_case_sensitive` | code | regression | 3 | 4 | 0 |
| `combined_seo_keyword_limit` | combined | regression | 1 | 2 | 0 |
| `config_default_agent_publishing` | config | regression | 3 | 153 | 0 |
| `config_disable_validate_links` | config | regression | 49 | 48 | 7 |
| `config_max_tool_calls_5` | config | regression | 10 | 12 | 3 |
| `config_require_review_false` | config | regression | 0 | 45 | 0 |
| `config_retries_0` | config | regression | 8 | 8 | 0 |
| `config_seo_title_20` | config | regression | 0 | 11 | 0 |
| `config_unpublish_no_approval` | config | regression | 1 | 1 | 0 |
| `prompt_governance_consent_tool_removed` | prompt | regression | 7 | 12 | 0 |
| `prompt_seo_tool_removed` | prompt | regression | 8 | 11 | 0 |
| `code_delegation_drops_context` | runtime | regression | 4 | 12 | 0 |
| `code_delegation_truncates_answer` | runtime | regression | 25 | 80 | 0 |
| `code_termination_off_by_six` | runtime | regression | 5 | 3 | 3 |
| `skill_authoring_drop_metadata` | skill | regression | 1 | 27 | 0 |
| `skill_governance_drop_consent` | skill | regression | 5 | 12 | 0 |
| `skill_linkval_ignore_assets` | skill | regression | 0 | 74 | 0 |
| `skill_publish_drop_link_validation` | skill | regression | 4 | 46 | 0 |
| `skill_publish_drop_permission_check` | skill | regression | 3 | 46 | 0 |
| `skill_rollback_drop_permission_check` | skill | regression | 1 | 7 | 0 |
| `skill_rollback_restores_latest` | skill | regression | 3 | 7 | 0 |
| `skill_routing_drop_approval` | skill | regression | 11 | 153 | 0 |
| `skill_routing_drop_brand_gate` | skill | regression | 1 | 153 | 0 |
| `skill_seo_drop_length_guard` | skill | regression | 0 | 11 | 0 |
| `skill_translation_wrong_default` | skill | regression | 4 | 14 | 0 |

Testbed sanity (every regression revealed by at least one test, no benign change revealed): **VIOLATED**.

## 2. Detection within a budget

Every strategy is run the same way: a test that fails on the original app is not run, and a run ends at its first failure.

Fraction of the revealed regressions detected, by nominal budget (% of full-suite tokens):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.00 | 0.14 | 0.24 | 0.41 | 0.69 | 0.97 | 1.00 |
| random | 0.09 | 0.24 | 0.38 | 0.63 | 0.72 | 0.89 | 1.00 |
| declared | 0.52 | 0.59 | 0.62 | 0.62 | 0.62 | 0.62 | 0.62 |
| ir_tfidf | 0.59 | 0.69 | 0.76 | 0.93 | 0.97 | 1.00 | 1.00 |
| observed | 0.47 | 0.61 | 0.74 | 0.85 | 0.85 | 0.85 | 0.99 |
| observed_diverse | 0.34 | 0.52 | 0.83 | 0.94 | 0.98 | 1.00 | 1.00 |
| cost_aware | 0.47 | 0.61 | 0.74 | 0.85 | 0.85 | 0.85 | 0.99 |
| history_ml | 0.59 | 0.69 | 0.83 | 0.90 | 0.90 | 0.94 | 1.00 |
| casper_slices | 0.17 | 0.28 | 0.54 | 0.65 | 0.78 | 0.88 | 1.00 |
| risk_aware_ts | 0.12 | 0.34 | 0.50 | 0.63 | 0.79 | 0.89 | 1.00 |
| adaptive_bayes | 0.61 | 0.74 | 0.78 | 0.78 | 0.81 | 0.81 | 0.81 |

Tokens spent, as a mean over all changes, revealed or not (fraction of the full suite):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.020 | 0.048 | 0.092 | 0.169 | 0.228 | 0.325 | 0.454 |
| random | 0.019 | 0.046 | 0.086 | 0.152 | 0.206 | 0.294 | 0.435 |
| declared | 0.007 | 0.015 | 0.024 | 0.033 | 0.040 | 0.046 | 0.046 |
| ir_tfidf | 0.015 | 0.033 | 0.059 | 0.099 | 0.135 | 0.201 | 0.330 |
| observed | 0.014 | 0.029 | 0.054 | 0.084 | 0.107 | 0.143 | 0.168 |
| observed_diverse | 0.015 | 0.039 | 0.065 | 0.092 | 0.110 | 0.130 | 0.144 |
| cost_aware | 0.015 | 0.033 | 0.062 | 0.106 | 0.148 | 0.230 | 0.369 |
| history_ml | 0.015 | 0.032 | 0.056 | 0.098 | 0.138 | 0.214 | 0.347 |
| casper_slices | 0.019 | 0.044 | 0.081 | 0.144 | 0.200 | 0.287 | 0.434 |
| risk_aware_ts | 0.019 | 0.045 | 0.082 | 0.145 | 0.197 | 0.284 | 0.427 |
| adaptive_bayes | 0.014 | 0.027 | 0.038 | 0.051 | 0.060 | 0.069 | 0.084 |

At a budget of 5%, over the 29 revealed regressions (intervals: bootstrap over the changes; a difference whose interval holds 0 is not established):

| strategy | detected | 95% interval | tokens, all changes | difference to the best | 95% interval |
|---|---|---|---|---|---|
| full | 0.14 | 0.03 to 0.28 | 0.048 | -0.61 | -0.79 to -0.40 |
| random | 0.24 | 0.15 to 0.34 | 0.046 | -0.50 | -0.65 to -0.34 |
| declared | 0.59 | 0.41 to 0.76 | 0.015 | -0.16 | -0.38 to +0.06 |
| ir_tfidf | 0.69 | 0.52 to 0.86 | 0.033 | -0.06 | -0.19 to +0.08 |
| observed | 0.61 | 0.43 to 0.78 | 0.029 | -0.14 | -0.34 to +0.07 |
| observed_diverse | 0.52 | 0.34 to 0.69 | 0.039 | -0.23 | -0.41 to -0.04 |
| cost_aware | 0.61 | 0.43 to 0.78 | 0.033 | -0.14 | -0.34 to +0.07 |
| history_ml | 0.69 | 0.52 to 0.86 | 0.032 | -0.06 | -0.24 to +0.14 |
| casper_slices | 0.28 | 0.14 to 0.45 | 0.044 | -0.47 | -0.66 to -0.28 |
| risk_aware_ts | 0.34 | 0.22 to 0.48 | 0.045 | -0.40 | -0.57 to -0.23 |
| adaptive_bayes | 0.74 | 0.59 to 0.90 | 0.027 | best |  |

At a budget of 20%, over the 29 revealed regressions (intervals: bootstrap over the changes; a difference whose interval holds 0 is not established):

| strategy | detected | 95% interval | tokens, all changes | difference to the best | 95% interval |
|---|---|---|---|---|---|
| full | 0.41 | 0.24 to 0.59 | 0.169 | -0.52 | -0.71 to -0.32 |
| random | 0.63 | 0.51 to 0.74 | 0.152 | -0.31 | -0.46 to -0.17 |
| declared | 0.62 | 0.45 to 0.79 | 0.033 | -0.32 | -0.52 to -0.12 |
| ir_tfidf | 0.93 | 0.83 to 1.00 | 0.099 | -0.01 | -0.12 to +0.10 |
| observed | 0.85 | 0.71 to 0.97 | 0.084 | -0.09 | -0.24 to +0.06 |
| observed_diverse | 0.94 | 0.86 to 1.00 | 0.092 | best |  |
| cost_aware | 0.85 | 0.71 to 0.97 | 0.106 | -0.09 | -0.24 to +0.06 |
| history_ml | 0.90 | 0.79 to 1.00 | 0.098 | -0.04 | -0.18 to +0.10 |
| casper_slices | 0.65 | 0.49 to 0.80 | 0.144 | -0.29 | -0.46 to -0.12 |
| risk_aware_ts | 0.63 | 0.50 to 0.76 | 0.145 | -0.30 | -0.44 to -0.18 |
| adaptive_bayes | 0.78 | 0.62 to 0.92 | 0.051 | -0.16 | -0.32 to +0.01 |

Tokens spent on the revealed regressions only:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.020 | 0.047 | 0.089 | 0.155 | 0.195 | 0.242 | 0.244 |
| random | 0.019 | 0.044 | 0.079 | 0.130 | 0.163 | 0.198 | 0.216 |
| declared | 0.006 | 0.011 | 0.015 | 0.015 | 0.015 | 0.015 | 0.015 |
| ir_tfidf | 0.013 | 0.024 | 0.040 | 0.051 | 0.055 | 0.057 | 0.057 |
| observed | 0.013 | 0.025 | 0.043 | 0.061 | 0.075 | 0.103 | 0.117 |
| observed_diverse | 0.015 | 0.037 | 0.058 | 0.073 | 0.080 | 0.081 | 0.081 |
| cost_aware | 0.013 | 0.025 | 0.044 | 0.061 | 0.075 | 0.103 | 0.117 |
| history_ml | 0.012 | 0.024 | 0.035 | 0.049 | 0.059 | 0.077 | 0.086 |
| casper_slices | 0.018 | 0.041 | 0.073 | 0.117 | 0.153 | 0.185 | 0.213 |
| risk_aware_ts | 0.019 | 0.043 | 0.073 | 0.120 | 0.149 | 0.183 | 0.205 |
| adaptive_bayes | 0.012 | 0.021 | 0.025 | 0.029 | 0.029 | 0.029 | 0.029 |

Time spent on those changes (fraction of the full suite's run time, from each test's mean time on the original app):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.026 | 0.054 | 0.098 | 0.166 | 0.209 | 0.249 | 0.252 |
| random | 0.019 | 0.045 | 0.080 | 0.132 | 0.164 | 0.200 | 0.218 |
| declared | 0.006 | 0.012 | 0.016 | 0.016 | 0.016 | 0.016 | 0.016 |
| ir_tfidf | 0.012 | 0.023 | 0.038 | 0.050 | 0.055 | 0.057 | 0.057 |
| observed | 0.013 | 0.025 | 0.044 | 0.064 | 0.076 | 0.104 | 0.118 |
| observed_diverse | 0.015 | 0.037 | 0.060 | 0.077 | 0.083 | 0.084 | 0.084 |
| cost_aware | 0.013 | 0.026 | 0.045 | 0.063 | 0.076 | 0.104 | 0.118 |
| history_ml | 0.013 | 0.024 | 0.036 | 0.049 | 0.059 | 0.077 | 0.086 |
| casper_slices | 0.021 | 0.052 | 0.084 | 0.135 | 0.171 | 0.200 | 0.228 |
| risk_aware_ts | 0.018 | 0.045 | 0.077 | 0.125 | 0.155 | 0.188 | 0.209 |
| adaptive_bayes | 0.014 | 0.023 | 0.028 | 0.032 | 0.032 | 0.032 | 0.032 |

Critical regressions: the same detection rate, over the changes that break a safety property only:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.00 | 0.05 | 0.14 | 0.33 | 0.67 | 0.95 | 1.00 |
| random | 0.10 | 0.27 | 0.42 | 0.67 | 0.76 | 0.90 | 1.00 |
| declared | 0.48 | 0.52 | 0.57 | 0.57 | 0.57 | 0.57 | 0.57 |
| ir_tfidf | 0.62 | 0.76 | 0.86 | 1.00 | 1.00 | 1.00 | 1.00 |
| observed | 0.46 | 0.55 | 0.65 | 0.79 | 0.79 | 0.79 | 0.98 |
| observed_diverse | 0.38 | 0.52 | 0.90 | 1.00 | 1.00 | 1.00 | 1.00 |
| cost_aware | 0.46 | 0.55 | 0.65 | 0.79 | 0.79 | 0.79 | 0.98 |
| history_ml | 0.52 | 0.67 | 0.76 | 0.86 | 0.86 | 0.92 | 1.00 |
| casper_slices | 0.19 | 0.33 | 0.62 | 0.74 | 0.80 | 0.86 | 1.00 |
| risk_aware_ts | 0.14 | 0.45 | 0.61 | 0.76 | 0.92 | 0.98 | 1.00 |
| adaptive_bayes | 0.60 | 0.79 | 0.84 | 0.84 | 0.84 | 0.84 | 0.84 |

![detection vs cost](figures/detection_vs_cost.png)

Cost until the first true detection (fraction of the full suite, detected cases only):

| strategy | cost_to_first_detection |
|---|---|
| full | 0.182 |
| random | 0.131 |
| declared | 0.021 |
| ir_tfidf | 0.038 |
| observed | 0.046 |
| observed_diverse | 0.063 |
| cost_aware | 0.046 |
| history_ml | 0.038 |
| casper_slices | 0.118 |
| risk_aware_ts | 0.117 |
| adaptive_bayes | 0.017 |

## 3. Changes no test reveals, and verdicts

Tokens spent on the changes no test reveals:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.020 | 0.049 | 0.100 | 0.199 | 0.298 | 0.496 | 0.889 |
| random | 0.020 | 0.050 | 0.100 | 0.199 | 0.297 | 0.494 | 0.887 |
| declared | 0.009 | 0.023 | 0.043 | 0.072 | 0.093 | 0.110 | 0.110 |
| ir_tfidf | 0.020 | 0.050 | 0.100 | 0.199 | 0.299 | 0.499 | 0.895 |
| observed | 0.016 | 0.037 | 0.077 | 0.130 | 0.172 | 0.227 | 0.273 |
| observed_diverse | 0.016 | 0.041 | 0.079 | 0.131 | 0.174 | 0.231 | 0.275 |
| cost_aware | 0.019 | 0.050 | 0.100 | 0.199 | 0.298 | 0.495 | 0.890 |
| history_ml | 0.020 | 0.050 | 0.100 | 0.200 | 0.300 | 0.499 | 0.887 |
| casper_slices | 0.020 | 0.049 | 0.100 | 0.200 | 0.299 | 0.498 | 0.892 |
| risk_aware_ts | 0.020 | 0.049 | 0.099 | 0.198 | 0.296 | 0.493 | 0.887 |
| adaptive_bayes | 0.017 | 0.039 | 0.066 | 0.098 | 0.123 | 0.153 | 0.198 |

![tokens spent on changes no test reveals](figures/benign_waste.png)

Verdicts at a budget of 5% (shares of the runs):

| strategy | regressions: found | called clean | no verdict | other changes: called clean | called regression | no verdict | clean verdicts on a regression |
|---|---|---|---|---|---|---|---|
| full | 0.14 | 0.00 | 0.86 | 0.00 | 0.00 | 1.00 |  |
| random | 0.25 | 0.00 | 0.75 | 0.00 | 0.00 | 1.00 |  |
| declared | 0.59 | 0.38 | 0.03 | 0.57 | 0.00 | 0.43 | 0.58 |
| ir_tfidf | 0.69 | 0.00 | 0.31 | 0.00 | 0.00 | 1.00 |  |
| observed | 0.62 | 0.00 | 0.38 | 0.21 | 0.00 | 0.79 | 0.00 |
| observed_diverse | 0.52 | 0.00 | 0.48 | 0.21 | 0.00 | 0.79 | 0.00 |
| cost_aware | 0.62 | 0.00 | 0.38 | 0.00 | 0.00 | 1.00 |  |
| history_ml | 0.69 | 0.00 | 0.31 | 0.00 | 0.00 | 1.00 |  |
| casper_slices | 0.28 | 0.00 | 0.72 | 0.00 | 0.00 | 1.00 |  |
| risk_aware_ts | 0.34 | 0.00 | 0.66 | 0.00 | 0.00 | 1.00 |  |
| adaptive_bayes | 0.76 | 0.14 | 0.10 | 0.43 | 0.00 | 0.57 | 0.40 |

Verdicts at a budget of 20% (shares of the runs):

| strategy | regressions: found | called clean | no verdict | other changes: called clean | called regression | no verdict | clean verdicts on a regression |
|---|---|---|---|---|---|---|---|
| full | 0.41 | 0.00 | 0.59 | 0.00 | 0.00 | 1.00 |  |
| random | 0.63 | 0.00 | 0.37 | 0.00 | 0.01 | 0.99 |  |
| declared | 0.62 | 0.38 | 0.00 | 0.79 | 0.00 | 0.21 | 0.50 |
| ir_tfidf | 0.93 | 0.00 | 0.07 | 0.00 | 0.00 | 1.00 |  |
| observed | 0.86 | 0.00 | 0.14 | 0.50 | 0.00 | 0.50 | 0.00 |
| observed_diverse | 0.94 | 0.00 | 0.06 | 0.50 | 0.00 | 0.50 | 0.00 |
| cost_aware | 0.86 | 0.00 | 0.14 | 0.00 | 0.00 | 1.00 |  |
| history_ml | 0.90 | 0.00 | 0.10 | 0.00 | 0.00 | 1.00 |  |
| casper_slices | 0.65 | 0.00 | 0.35 | 0.00 | 0.00 | 1.00 |  |
| risk_aware_ts | 0.63 | 0.00 | 0.37 | 0.00 | 0.01 | 0.99 |  |
| adaptive_bayes | 0.79 | 0.17 | 0.03 | 0.71 | 0.00 | 0.29 | 0.33 |

## 4. Prioritization and selection quality

APFD / cost-cognizant APFD of the complete order, each change one fault found by the first of its revealing tests (an order drawn at random: the mean over the seeds); selection recall = revealing tests inside the selected subset; selected cost = what that subset costs:

| strategy | apfd | apfdc | selection_recall | selected_cost_fraction |
|---|---|---|---|---|
| full | 0.746 | 0.733 | 1.000 | 0.899 |
| random | 0.757 | 0.762 | 1.000 | 0.899 |
| declared | 0.909 | 0.896 | 0.528 | 0.096 |
| ir_tfidf | 0.957 | 0.940 | 1.000 | 0.899 |
| observed | 0.830 | 0.875 | 1.000 | 0.444 |
| observed_diverse | 0.950 | 0.917 | 1.000 | 0.444 |
| cost_aware | 0.830 | 0.875 | 1.000 | 0.899 |
| history_ml | 0.889 | 0.911 | 1.000 | 0.899 |
| casper_slices | 0.806 | 0.808 | 1.000 | 0.899 |
| risk_aware_ts | 0.768 | 0.748 | 1.000 | 0.899 |
| adaptive_bayes | 0.934 | 0.934 | 1.000 | 0.899 |

![apfdc](figures/apfdc.png)

## 5. Properties

The catalog of properties (`traceeval/catalog/properties.yaml`): for each, its tests' pass rate on the original app against its threshold:

| property | category | mandatory | threshold | tests | pass rate | met |
|---|---|---|---|---|---|---|
| `task_completion` | correctness |  | 0.95 | 71 | 0.90 | **no** |
| `correct_routing` | correctness |  | 0.95 | 65 | 1.00 | yes |
| `tool_trajectory` | correctness |  | 0.95 | 45 | 0.96 | yes |
| `answer_quality` | quality |  | 0.90 | 2 | 1.00 | yes |
| `safety_authorization` | safety | yes | 1.00 | 9 | 1.00 | yes |
| `safety_guarded_mutation` | safety | yes | 1.00 | 6 | 1.00 | yes |
| `safety_no_broken_publish` | safety | yes | 1.00 | 6 | 0.67 | **no** |
| `safety_privacy` | safety | yes | 1.00 | 3 | 0.67 | **no** |
| `resilience_retry` | resilience |  | 0.95 | 3 | 1.00 | yes |
| `resilience_idempotency` | resilience |  | 0.95 | 5 | 1.00 | yes |
| `resilience_fail_safe` | resilience |  | 0.95 | 3 | 1.00 | yes |
| `efficiency` | efficiency |  | 0.90 | 1 | 1.00 | yes |
| `workflow_completion` | orchestration |  | 0.95 | 15 | 0.73 | **no** |
| `safety_human_approval` | safety | yes | 1.00 | 13 | 0.77 | **no** |
| `safety_brand_compliance` | safety | yes | 1.00 | 7 | 0.86 | **no** |

Coverage of the affected properties (those of a change's revealing tests) by the tests each strategy ran:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.42 | 0.52 | 0.59 | 0.59 | 0.70 | 0.73 | 0.74 |
| random | 0.41 | 0.54 | 0.66 | 0.77 | 0.81 | 0.82 | 0.83 |
| declared | 0.33 | 0.38 | 0.40 | 0.40 | 0.40 | 0.40 | 0.40 |
| ir_tfidf | 0.46 | 0.54 | 0.57 | 0.60 | 0.60 | 0.63 | 0.63 |
| observed | 0.39 | 0.51 | 0.58 | 0.71 | 0.73 | 0.73 | 0.73 |
| observed_diverse | 0.28 | 0.51 | 0.64 | 0.69 | 0.75 | 0.75 | 0.75 |
| cost_aware | 0.39 | 0.51 | 0.60 | 0.72 | 0.73 | 0.73 | 0.73 |
| history_ml | 0.47 | 0.57 | 0.66 | 0.70 | 0.71 | 0.71 | 0.71 |
| casper_slices | 0.40 | 0.64 | 0.68 | 0.71 | 0.76 | 0.77 | 0.77 |
| risk_aware_ts | 0.41 | 0.60 | 0.72 | 0.77 | 0.80 | 0.81 | 0.83 |
| adaptive_bayes | 0.51 | 0.58 | 0.61 | 0.61 | 0.63 | 0.63 | 0.63 |

## 6. Coverage

Coverage of the test suite: per dimension, how many components the tests declare and the traces show, and what no test covers. A feature (`catalog/features.yaml`) is covered by the tests that declare or call one of its tools. A tool error path is a place in the code where a tool call is refused, reached when a run executes it. A workflow is declared by the tests that name it and observed when a run delegates to exactly its agents in order. Execution paths are the distinct agent and tool sequences; risk lists tests per level.

| dimension | components | declared | observed | not covered |
|---|---|---|---|---|
| agent | 11 | 11 | 11 |  |
| feature | 19 | 18 | 19 |  |
| skill | 13 | 12 | 13 |  |
| tool | 32 | 30 | 31 | get_asset |
| tool error path | 31 |  | 15 | harness/dispatcher.py:60 Dispatcher.call unknown_tool, harness/dispatcher.py:66 Dispatcher.call tool_not_available, harness/dispatcher.py:77 Dispatcher.call invalid_arguments, harness/runtime.py:188 Runtime._delegate unknown_agent, harness/runtime.py:191 Runtime._delegate invalid_arguments, harness/runtime.py:195 Runtime._delegate max_delegation_depth, services/governance.py:39 export_user_data approval_required, services/governance.py:44 export_user_data not_found ... |
| configuration | 13 | 10 | 13 |  |
| setting value | 5 | 3 | 3 | runtime.idempotency_keys=false, seo.require_description=false |
| property | 15 | 15 | 15 |  |
| workflow | 6 | 6 | 6 |  |
| execution path | 78 |  | 78 |  |
| risk | 4 | 4 | 4 | critical 32, high 77, low 22, medium 49 |

Per component: how many tests declare it in their metadata, and how many invoke it in their recorded runs. A component few tests invoke is thinly covered. A difference between the two counts is where the hand-written metadata and the runs disagree.

| agent | declared | invoked |
|---|---|---|
| assets | 37 | 17 |
| authoring | 46 | 27 |
| brand | 12 | 12 |
| governance | 32 | 12 |
| insights | 6 | 6 |
| maintenance | 7 | 7 |
| optimizer | 6 | 6 |
| orchestrator | 67 | 153 |
| publishing | 63 | 46 |
| seo | 11 | 11 |
| translation | 35 | 14 |

| skill | declared | invoked |
|---|---|---|
| asset-management | 35 | 17 |
| brand-governance | 9 | 12 |
| data-insights | 6 | 6 |
| governance-checks | 0 | 120 |
| governance-ops | 32 | 12 |
| link-validation | 5 | 74 |
| page-authoring | 44 | 27 |
| publishing-workflow | 62 | 46 |
| rollback | 7 | 7 |
| routing | 67 | 153 |
| seo-metadata | 11 | 11 |
| site-optimization | 6 | 6 |
| translation | 34 | 14 |

| tool | declared | invoked |
|---|---|---|
| approve_review | 7 | 6 |
| attach_asset | 8 | 12 |
| audit_site | 4 | 4 |
| check_brand_policy | 6 | 7 |
| check_consent | 5 | 8 |
| check_permission | 9 | 110 |
| create_page | 11 | 15 |
| create_translation_job | 9 | 11 |
| export_user_data | 7 | 4 |
| fix_alt_text | 2 | 1 |
| get_asset | 0 | 0 |
| get_audit_log | 1 | 3 |
| get_brand_guidelines | 1 | 1 |
| get_page | 2 | 76 |
| get_page_metrics | 6 | 6 |
| get_seo_report | 2 | 10 |
| get_translation_status | 1 | 2 |
| list_versions | 2 | 6 |
| make_plan | 13 | 15 |
| publish_page | 29 | 19 |
| request_approval | 14 | 14 |
| request_review | 4 | 23 |
| rollback_page | 7 | 6 |
| route_to_agent | 0 | 153 |
| schedule_publish | 6 | 6 |
| search_assets | 2 | 5 |
| search_pages | 3 | 4 |
| set_page_metadata | 12 | 24 |
| unpublish_page | 7 | 7 |
| update_page_content | 10 | 23 |
| upload_asset | 4 | 5 |
| validate_links | 18 | 56 |

| feature | declared | invoked |
|---|---|---|
| show a page | 2 | 76 |
| create or edit a page | 20 | 24 |
| request and approve a page's review | 11 | 26 |
| publish a page | 29 | 19 |
| schedule a page | 6 | 6 |
| take a page down | 7 | 7 |
| check a page's links | 18 | 56 |
| set a page's SEO metadata | 12 | 24 |
| translate a page | 10 | 13 |
| upload, find and attach assets | 11 | 14 |
| check pages against the brand rules and find the pages that use a term | 10 | 12 |
| run a site health check and fix alt text | 6 | 5 |
| read page analytics | 6 | 6 |
| roll a page back to an earlier version | 7 | 6 |
| answer a privacy request (consent, data export) and show the audit history | 8 | 11 |
| refuse what the user may not do | 9 | 110 |
| hand a request to the specialist that owns it | 0 | 153 |
| plan a request that needs several specialists | 13 | 15 |
| ask a person before publishing, scheduling or taking pages down | 14 | 14 |

Change coverage over every change, without the ground truth: the share of the changed components the executed tests exercised, and the share of the properties the change may affect (`coverage.py`) that they checked.

Changed components exercised:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.41 | 0.53 | 0.63 | 0.69 | 0.87 | 0.97 | 0.97 |
| random | 0.59 | 0.75 | 0.84 | 0.94 | 0.96 | 0.97 | 0.97 |
| declared | 0.67 | 0.67 | 0.67 | 0.67 | 0.67 | 0.67 | 0.67 |
| ir_tfidf | 0.92 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 |
| observed | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 |
| observed_diverse | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 |
| cost_aware | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 |
| history_ml | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 |
| casper_slices | 0.46 | 0.75 | 0.89 | 0.96 | 0.96 | 0.96 | 0.97 |
| risk_aware_ts | 0.57 | 0.71 | 0.81 | 0.93 | 0.96 | 0.97 | 0.97 |
| adaptive_bayes | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 |

Affected properties checked:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.29 | 0.40 | 0.49 | 0.52 | 0.60 | 0.68 | 0.71 |
| random | 0.32 | 0.45 | 0.59 | 0.70 | 0.74 | 0.78 | 0.79 |
| declared | 0.18 | 0.24 | 0.26 | 0.27 | 0.27 | 0.27 | 0.27 |
| ir_tfidf | 0.29 | 0.37 | 0.45 | 0.50 | 0.52 | 0.55 | 0.56 |
| observed | 0.27 | 0.36 | 0.45 | 0.57 | 0.60 | 0.62 | 0.63 |
| observed_diverse | 0.25 | 0.47 | 0.57 | 0.63 | 0.65 | 0.66 | 0.67 |
| cost_aware | 0.27 | 0.36 | 0.46 | 0.57 | 0.61 | 0.62 | 0.64 |
| history_ml | 0.28 | 0.40 | 0.48 | 0.55 | 0.57 | 0.59 | 0.60 |
| casper_slices | 0.28 | 0.53 | 0.60 | 0.63 | 0.70 | 0.74 | 0.75 |
| risk_aware_ts | 0.35 | 0.57 | 0.65 | 0.71 | 0.74 | 0.75 | 0.78 |
| adaptive_bayes | 0.32 | 0.43 | 0.49 | 0.50 | 0.51 | 0.51 | 0.51 |

Runs that found no regression and tested every affected mandatory property (the method's step 5):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.05 | 0.05 | 0.06 | 0.06 | 0.09 | 0.20 | 1.00 |
| random | 0.05 | 0.07 | 0.13 | 0.42 | 0.61 | 0.88 | 1.00 |
| declared | 0.11 | 0.15 | 0.16 | 0.16 | 0.16 | 0.16 | 0.16 |
| ir_tfidf | 0.08 | 0.17 | 0.24 | 0.50 | 0.60 | 0.86 | 1.00 |
| observed | 0.07 | 0.12 | 0.24 | 0.33 | 0.72 | 0.72 | 0.71 |
| observed_diverse | 0.06 | 0.18 | 0.26 | 0.68 | 0.73 | 0.71 | 0.70 |
| cost_aware | 0.07 | 0.12 | 0.24 | 0.39 | 0.83 | 0.83 | 1.00 |
| history_ml | 0.08 | 0.13 | 0.32 | 0.47 | 0.71 | 0.96 | 1.00 |
| casper_slices | 0.05 | 0.06 | 0.22 | 0.30 | 0.82 | 1.00 | 1.00 |
| risk_aware_ts | 0.07 | 0.23 | 0.37 | 0.68 | 0.93 | 1.00 | 1.00 |
| adaptive_bayes | 0.12 | 0.48 | 0.85 | 0.90 | 0.95 | 0.95 | 1.00 |

Affected workflows run (the workflows of the tests that exercised a changed component):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.06 | 0.30 |
| random | 0.01 | 0.05 | 0.12 | 0.25 | 0.34 | 0.43 | 0.52 |
| declared | 0.05 | 0.17 | 0.22 | 0.24 | 0.26 | 0.26 | 0.26 |
| ir_tfidf | 0.03 | 0.10 | 0.20 | 0.28 | 0.33 | 0.37 | 0.39 |
| observed | 0.04 | 0.06 | 0.18 | 0.24 | 0.27 | 0.30 | 0.38 |
| observed_diverse | 0.14 | 0.36 | 0.50 | 0.63 | 0.67 | 0.67 | 0.67 |
| cost_aware | 0.04 | 0.06 | 0.18 | 0.24 | 0.27 | 0.30 | 0.38 |
| history_ml | 0.04 | 0.09 | 0.20 | 0.27 | 0.32 | 0.36 | 0.39 |
| casper_slices | 0.00 | 0.09 | 0.24 | 0.37 | 0.47 | 0.47 | 0.61 |
| risk_aware_ts | 0.04 | 0.18 | 0.34 | 0.54 | 0.68 | 0.71 | 0.71 |
| adaptive_bayes | 0.03 | 0.13 | 0.18 | 0.20 | 0.21 | 0.21 | 0.21 |

Affected features reached (the features with a tool or a part the change touches), over the changes that affect one:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.19 | 0.33 | 0.46 | 0.53 | 0.70 | 0.88 | 0.88 |
| random | 0.35 | 0.64 | 0.79 | 0.91 | 0.94 | 0.95 | 0.95 |
| declared | 0.59 | 0.59 | 0.60 | 0.60 | 0.61 | 0.61 | 0.61 |
| ir_tfidf | 0.85 | 0.92 | 0.93 | 0.94 | 0.94 | 0.94 | 0.94 |
| observed | 0.72 | 0.74 | 0.82 | 0.91 | 0.91 | 0.91 | 0.91 |
| observed_diverse | 0.72 | 0.78 | 0.87 | 0.88 | 0.88 | 0.88 | 0.88 |
| cost_aware | 0.72 | 0.74 | 0.84 | 0.91 | 0.91 | 0.91 | 0.91 |
| history_ml | 0.81 | 0.79 | 0.90 | 0.91 | 0.91 | 0.91 | 0.91 |
| casper_slices | 0.19 | 0.63 | 0.82 | 0.95 | 0.96 | 0.97 | 0.98 |
| risk_aware_ts | 0.34 | 0.64 | 0.78 | 0.90 | 0.94 | 0.95 | 0.95 |
| adaptive_bayes | 0.80 | 0.87 | 0.89 | 0.89 | 0.89 | 0.89 | 0.89 |

## 7. Replay-first

Every test was run on every changed copy with the model's calls answered from the answers recorded on the original app (`traceeval replay-first`; no model is called). A test either replays to the end, and its outcome on the changed copy is known for no tokens, or diverges at the first request the original app never made, and needs the model from there on.

What the replay settles alone, by kind of change:

| kind of change | changes | no test diverges | a replayed test fails | diverged tests, mean | their share of the suite's tokens | after the divergence point |
|---|---|---|---|---|---|---|
| benign | 9 | 4 | 0 | 42 of 180 | 0.283 | 0.250 |
| code | 10 | 1 | 0 | 11 of 180 | 0.106 | 0.068 |
| combined | 1 | 0 | 0 | 2 of 180 | 0.012 | 0.004 |
| config | 7 | 0 | 2 | 40 of 180 | 0.331 | 0.245 |
| prompt | 2 | 0 | 0 | 12 of 180 | 0.097 | 0.079 |
| runtime | 3 | 0 | 1 | 32 of 180 | 0.330 | 0.167 |
| skill | 11 | 0 | 0 | 50 of 180 | 0.382 | 0.325 |
| all | 43 | 5 | 3 | 33 of 180 | 0.264 | 0.207 |

Over the 1438 diverged (change, test) pairs, the change first reaches the model in what an agent is sent up front (its prompt, skills, tools or task) on 1172, and in a tool result on 266.

The replay against the recorded ground truth:

- replayed outcomes that differ from the recorded majority: 1 of 6302 (`WF3-01` under `config_max_tool_calls_5`);
- the 184 revealing (change, test) pairs: 13 replay to a failure, 170 diverge, 1 replay to a pass;
- revealed regressions with a revealing test that fails in the replay or diverges: 29 of 29;
- changes no test reveals on which a replayed test fails: 0.

The replay against the recorded runs, one by one, over the tests that replay to the end. A run is identical to the replay when it has the same tool calls, final answer, final state and token count:

| recorded runs of | runs | end like the replay | identical to the replay |
|---|---|---|---|
| the original app | 900 | 900 | 777 |
| the changed copies | 31510 | 31506 | 27312 |

The strategies run replay-first: a test that replays to the end is not run, a replayed failure of a test that passes on the original app ends the run for no tokens, and a diverged test costs its tokens after the divergence point. A run that ends because every diverged test has run and passed is a clean verdict that leaves no reachable test untested.

Fraction of the revealed regressions detected, by nominal budget:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.86 | 0.90 | 0.90 | 0.90 | 0.93 | 1.00 | 1.00 |
| random | 0.74 | 0.83 | 0.90 | 0.95 | 0.95 | 0.97 | 0.99 |
| cheapest | 0.83 | 0.83 | 0.86 | 0.93 | 0.97 | 0.97 | 1.00 |
| late_divergence | 0.79 | 0.90 | 0.93 | 0.93 | 0.97 | 0.97 | 1.00 |
| declared | 0.59 | 0.66 | 0.69 | 0.69 | 0.69 | 0.69 | 0.69 |
| ir_tfidf | 0.83 | 0.86 | 0.93 | 1.00 | 1.00 | 1.00 | 1.00 |
| observed | 0.83 | 0.90 | 0.93 | 0.97 | 0.97 | 0.97 | 1.00 |
| observed_diverse | 0.76 | 0.90 | 0.93 | 0.97 | 0.98 | 1.00 | 1.00 |
| cost_aware | 0.83 | 0.90 | 0.93 | 0.97 | 0.97 | 0.97 | 1.00 |
| history_ml | 0.90 | 0.93 | 0.97 | 1.00 | 1.00 | 1.00 | 1.00 |
| casper_slices | 0.83 | 0.86 | 0.93 | 1.00 | 1.00 | 1.00 | 1.00 |
| risk_aware_ts | 0.76 | 0.88 | 0.93 | 0.97 | 0.97 | 1.00 | 1.00 |
| adaptive_bayes | 0.86 | 0.93 | 0.93 | 0.93 | 0.93 | 0.93 | 0.93 |

Tokens spent, as a mean over all changes (fraction of the full suite):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.008 | 0.016 | 0.028 | 0.047 | 0.062 | 0.084 | 0.098 |
| random | 0.010 | 0.020 | 0.033 | 0.048 | 0.061 | 0.078 | 0.093 |
| cheapest | 0.008 | 0.017 | 0.030 | 0.047 | 0.061 | 0.079 | 0.097 |
| late_divergence | 0.009 | 0.019 | 0.030 | 0.046 | 0.059 | 0.077 | 0.095 |
| declared | 0.006 | 0.012 | 0.019 | 0.026 | 0.032 | 0.034 | 0.034 |
| ir_tfidf | 0.008 | 0.018 | 0.029 | 0.041 | 0.051 | 0.065 | 0.079 |
| observed | 0.008 | 0.015 | 0.028 | 0.043 | 0.055 | 0.072 | 0.087 |
| observed_diverse | 0.009 | 0.022 | 0.034 | 0.048 | 0.060 | 0.075 | 0.088 |
| cost_aware | 0.008 | 0.015 | 0.028 | 0.043 | 0.055 | 0.072 | 0.087 |
| history_ml | 0.007 | 0.015 | 0.025 | 0.038 | 0.048 | 0.062 | 0.073 |
| casper_slices | 0.008 | 0.017 | 0.029 | 0.043 | 0.053 | 0.067 | 0.080 |
| risk_aware_ts | 0.009 | 0.020 | 0.031 | 0.046 | 0.056 | 0.069 | 0.079 |
| adaptive_bayes | 0.007 | 0.014 | 0.018 | 0.019 | 0.019 | 0.019 | 0.019 |

The same tests run whole, without the replayed part taken off:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.011 | 0.021 | 0.035 | 0.057 | 0.075 | 0.098 | 0.112 |
| random | 0.014 | 0.028 | 0.043 | 0.061 | 0.076 | 0.094 | 0.109 |
| cheapest | 0.013 | 0.023 | 0.039 | 0.059 | 0.076 | 0.095 | 0.113 |
| late_divergence | 0.018 | 0.033 | 0.048 | 0.065 | 0.078 | 0.097 | 0.115 |
| declared | 0.008 | 0.016 | 0.025 | 0.033 | 0.039 | 0.041 | 0.041 |
| ir_tfidf | 0.011 | 0.024 | 0.038 | 0.054 | 0.065 | 0.080 | 0.093 |
| observed | 0.012 | 0.022 | 0.038 | 0.055 | 0.069 | 0.088 | 0.102 |
| observed_diverse | 0.015 | 0.031 | 0.047 | 0.064 | 0.077 | 0.092 | 0.105 |
| cost_aware | 0.012 | 0.022 | 0.038 | 0.055 | 0.069 | 0.088 | 0.102 |
| history_ml | 0.012 | 0.022 | 0.036 | 0.052 | 0.063 | 0.077 | 0.089 |
| casper_slices | 0.011 | 0.025 | 0.042 | 0.059 | 0.070 | 0.085 | 0.098 |
| risk_aware_ts | 0.014 | 0.029 | 0.043 | 0.060 | 0.072 | 0.085 | 0.095 |
| adaptive_bayes | 0.012 | 0.021 | 0.026 | 0.028 | 0.028 | 0.028 | 0.028 |

At a budget of 5%, over the 29 revealed regressions (intervals: bootstrap over the changes; a difference whose interval holds 0 is not established):

| strategy | detected | 95% interval | tokens, all changes | difference to the best | 95% interval |
|---|---|---|---|---|---|
| full | 0.90 | 0.79 to 1.00 | 0.016 | -0.03 | -0.14 to +0.07 |
| random | 0.83 | 0.71 to 0.93 | 0.020 | -0.10 | -0.21 to -0.01 |
| cheapest | 0.83 | 0.69 to 0.97 | 0.017 | -0.10 | -0.21 to +0.00 |
| late_divergence | 0.90 | 0.76 to 1.00 | 0.019 | -0.03 | -0.14 to +0.07 |
| declared | 0.66 | 0.48 to 0.83 | 0.012 | -0.28 | -0.48 to -0.10 |
| ir_tfidf | 0.86 | 0.72 to 0.97 | 0.018 | -0.07 | -0.21 to +0.07 |
| observed | 0.90 | 0.79 to 1.00 | 0.015 | -0.03 | -0.10 to +0.00 |
| observed_diverse | 0.90 | 0.79 to 1.00 | 0.022 | -0.03 | -0.14 to +0.07 |
| cost_aware | 0.90 | 0.79 to 1.00 | 0.015 | -0.03 | -0.10 to +0.00 |
| history_ml | 0.93 | 0.83 to 1.00 | 0.015 | best |  |
| casper_slices | 0.86 | 0.72 to 0.97 | 0.017 | -0.07 | -0.17 to +0.00 |
| risk_aware_ts | 0.88 | 0.77 to 0.97 | 0.020 | -0.05 | -0.16 to +0.06 |
| adaptive_bayes | 0.93 | 0.83 to 1.00 | 0.014 | +0.00 | -0.10 to +0.10 |

At a budget of 20%, over the 29 revealed regressions (intervals: bootstrap over the changes; a difference whose interval holds 0 is not established):

| strategy | detected | 95% interval | tokens, all changes | difference to the best | 95% interval |
|---|---|---|---|---|---|
| full | 0.90 | 0.79 to 1.00 | 0.047 | -0.10 | -0.21 to +0.00 |
| random | 0.95 | 0.88 to 1.00 | 0.048 | -0.05 | -0.12 to +0.00 |
| cheapest | 0.93 | 0.83 to 1.00 | 0.047 | -0.07 | -0.17 to +0.00 |
| late_divergence | 0.93 | 0.83 to 1.00 | 0.046 | -0.07 | -0.17 to +0.00 |
| declared | 0.69 | 0.52 to 0.86 | 0.026 | -0.31 | -0.48 to -0.14 |
| ir_tfidf | 1.00 | 1.00 to 1.00 | 0.041 | best |  |
| observed | 0.97 | 0.90 to 1.00 | 0.043 | -0.03 | -0.10 to +0.00 |
| observed_diverse | 0.97 | 0.90 to 1.00 | 0.048 | -0.03 | -0.10 to +0.00 |
| cost_aware | 0.97 | 0.90 to 1.00 | 0.043 | -0.03 | -0.10 to +0.00 |
| history_ml | 1.00 | 1.00 to 1.00 | 0.038 | +0.00 | +0.00 to +0.00 |
| casper_slices | 1.00 | 1.00 to 1.00 | 0.043 | +0.00 | +0.00 to +0.00 |
| risk_aware_ts | 0.97 | 0.90 to 1.00 | 0.046 | -0.03 | -0.10 to +0.00 |
| adaptive_bayes | 0.93 | 0.83 to 1.00 | 0.019 | -0.07 | -0.17 to +0.00 |

![replay-first: detection vs cost](figures/replay_first.png)

Verdicts at a budget of 20% (shares of the runs):

| strategy | regressions: found | called clean | no verdict | other changes: called clean | called regression | no verdict | clean verdicts on a regression |
|---|---|---|---|---|---|---|---|
| full | 0.90 | 0.00 | 0.10 | 0.64 | 0.00 | 0.36 | 0.00 |
| random | 0.96 | 0.00 | 0.04 | 0.64 | 0.01 | 0.34 | 0.00 |
| cheapest | 0.93 | 0.00 | 0.07 | 0.64 | 0.00 | 0.36 | 0.00 |
| late_divergence | 0.93 | 0.00 | 0.07 | 0.64 | 0.00 | 0.36 | 0.00 |
| declared | 0.69 | 0.31 | 0.00 | 0.79 | 0.00 | 0.21 | 0.45 |
| ir_tfidf | 1.00 | 0.00 | 0.00 | 0.64 | 0.00 | 0.36 | 0.00 |
| observed | 0.97 | 0.00 | 0.03 | 0.64 | 0.00 | 0.36 | 0.00 |
| observed_diverse | 0.97 | 0.00 | 0.03 | 0.64 | 0.00 | 0.36 | 0.00 |
| cost_aware | 0.97 | 0.00 | 0.03 | 0.64 | 0.00 | 0.36 | 0.00 |
| history_ml | 1.00 | 0.00 | 0.00 | 0.64 | 0.00 | 0.36 | 0.00 |
| casper_slices | 1.00 | 0.00 | 0.00 | 0.64 | 0.00 | 0.36 | 0.00 |
| risk_aware_ts | 0.97 | 0.00 | 0.03 | 0.64 | 0.03 | 0.33 | 0.00 |
| adaptive_bayes | 0.93 | 0.07 | 0.00 | 1.00 | 0.00 | 0.00 | 0.12 |

Verdicts at a budget of 100% (shares of the runs):

| strategy | regressions: found | called clean | no verdict | other changes: called clean | called regression | no verdict | clean verdicts on a regression |
|---|---|---|---|---|---|---|---|
| full | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 |
| random | 1.00 | 0.00 | 0.00 | 0.99 | 0.01 | 0.00 | 0.00 |
| cheapest | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 |
| late_divergence | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 |
| declared | 0.69 | 0.31 | 0.00 | 1.00 | 0.00 | 0.00 | 0.39 |
| ir_tfidf | 1.00 | 0.00 | 0.00 | 0.99 | 0.01 | 0.00 | 0.00 |
| observed | 1.00 | 0.00 | 0.00 | 0.99 | 0.01 | 0.00 | 0.00 |
| observed_diverse | 1.00 | 0.00 | 0.00 | 0.96 | 0.04 | 0.00 | 0.00 |
| cost_aware | 1.00 | 0.00 | 0.00 | 0.99 | 0.01 | 0.00 | 0.00 |
| history_ml | 1.00 | 0.00 | 0.00 | 0.97 | 0.03 | 0.00 | 0.00 |
| casper_slices | 1.00 | 0.00 | 0.00 | 0.99 | 0.01 | 0.00 | 0.00 |
| risk_aware_ts | 1.00 | 0.00 | 0.00 | 0.96 | 0.04 | 0.00 | 0.00 |
| adaptive_bayes | 0.93 | 0.07 | 0.00 | 1.00 | 0.00 | 0.00 | 0.12 |

## How to read this

`detected` counts *changes* (one failing revealing test is enough). Compare strategies at equal tokens *spent*, not equal nominal budget: every run ends at its first failure, the selecting strategies also run out of tests, and `adaptive_bayes` also stops when it is confident. A good strategy is high in the first table of section 2 and low in the second. The sample is the changes: the seeds only draw which recorded run answers a test and the choices of the strategies that draw at random, so an interval is over the changes. A clean verdict is worth what the last column of the verdict tables says.

Section 7 reads like section 2, with the replay in front: compare a strategy's row there with its row here. Replay-first, a strategy that orders the whole suite gives a clean verdict once every diverged test has run and passed; that verdict holds as far as the replay agrees with the recording, which the first lines of the section measure.
