# TRACE-Eval experiment report

`runs/gemma8` · 180 tests · 43 changes · 5 baseline repetitions · full suite = 2,083,624 tokens · tests failing on the original app: 8 · runs the environment broke, left out: 0

- Recorded with `google/gemma-4-E4B-it` (judge: gemma) at commit `4f780e3`, with uncommitted edits; the original app 5 times, one case at a time; the changed copies 5 times, 32 cases at a time.
- The empty change (the original app, run as the changed copies are): 0 of 180 tests end otherwise than in the baseline; of its 5486 requests, 5218 are the baseline's, 104 of them answered otherwise.

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
| `code_get_page_review_flag` | code | regression | 4 | 65 | 0 |
| `code_insights_rank_reversed` | code | regression | 4 | 5 | 0 |
| `code_links_external_lenient` | code | regression | 6 | 7 | 0 |
| `code_metadata_arg_swap` | code | regression | 5 | 21 | 0 |
| `code_retry_drop_idempotency` | code | regression | 5 | 5 | 0 |
| `code_search_case_sensitive` | code | regression | 3 | 4 | 0 |
| `combined_seo_keyword_limit` | combined | regression | 1 | 2 | 0 |
| `config_default_agent_publishing` | config | regression | 3 | 153 | 0 |
| `config_disable_validate_links` | config | regression | 49 | 48 | 7 |
| `config_max_tool_calls_5` | config | regression | 11 | 14 | 3 |
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
| `skill_routing_drop_brand_gate` | skill | regression | 0 | 153 | 0 |
| `skill_seo_drop_length_guard` | skill | regression | 0 | 11 | 0 |
| `skill_translation_wrong_default` | skill | regression | 3 | 14 | 0 |

Testbed sanity (every change labelled a regression revealed by at least one test, none labelled benign revealed): **VIOLATED**.

## 2. Detection within a budget

Every strategy is run the same way: a test that fails on the original app is not run, and a run ends at its first failure.

Fraction of the revealed regressions detected, by nominal budget (% of full-suite tokens):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.00 | 0.14 | 0.25 | 0.43 | 0.71 | 0.96 | 1.00 |
| random | 0.09 | 0.24 | 0.39 | 0.64 | 0.74 | 0.91 | 1.00 |
| declared | 0.50 | 0.61 | 0.61 | 0.61 | 0.61 | 0.61 | 0.61 |
| ir_tfidf | 0.61 | 0.71 | 0.79 | 0.93 | 0.96 | 1.00 | 1.00 |
| observed | 0.46 | 0.64 | 0.79 | 0.86 | 0.89 | 0.89 | 1.00 |
| observed_diverse | 0.36 | 0.54 | 0.82 | 0.93 | 0.96 | 1.00 | 1.00 |
| cost_aware | 0.46 | 0.64 | 0.79 | 0.86 | 0.89 | 0.89 | 1.00 |
| history_ml | 0.57 | 0.71 | 0.86 | 0.89 | 0.89 | 0.96 | 1.00 |
| casper_slices | 0.18 | 0.36 | 0.48 | 0.65 | 0.74 | 0.81 | 1.00 |
| risk_aware_ts | 0.11 | 0.34 | 0.49 | 0.63 | 0.77 | 0.88 | 0.99 |
| adaptive_bayes | 0.60 | 0.78 | 0.81 | 0.81 | 0.85 | 0.85 | 0.85 |

Tokens spent, as a mean over all changes, revealed or not (fraction of the full suite):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.020 | 0.048 | 0.092 | 0.169 | 0.229 | 0.326 | 0.464 |
| random | 0.019 | 0.046 | 0.086 | 0.154 | 0.208 | 0.298 | 0.445 |
| declared | 0.008 | 0.016 | 0.026 | 0.038 | 0.047 | 0.054 | 0.054 |
| ir_tfidf | 0.015 | 0.033 | 0.059 | 0.100 | 0.136 | 0.205 | 0.339 |
| observed | 0.014 | 0.030 | 0.055 | 0.086 | 0.111 | 0.148 | 0.176 |
| observed_diverse | 0.015 | 0.038 | 0.066 | 0.094 | 0.114 | 0.139 | 0.161 |
| cost_aware | 0.015 | 0.034 | 0.063 | 0.109 | 0.151 | 0.235 | 0.378 |
| history_ml | 0.015 | 0.033 | 0.057 | 0.100 | 0.141 | 0.221 | 0.363 |
| casper_slices | 0.019 | 0.043 | 0.080 | 0.145 | 0.202 | 0.300 | 0.468 |
| risk_aware_ts | 0.019 | 0.045 | 0.082 | 0.147 | 0.201 | 0.294 | 0.447 |
| adaptive_bayes | 0.014 | 0.027 | 0.038 | 0.051 | 0.060 | 0.070 | 0.085 |

At a budget of 5%, over the 28 revealed regressions (intervals: bootstrap over the changes; a difference whose interval holds 0 is not established):

| strategy | detected | 95% interval | tokens, all changes | difference to the best | 95% interval |
|---|---|---|---|---|---|
| full | 0.14 | 0.04 to 0.29 | 0.048 | -0.64 | -0.82 to -0.42 |
| random | 0.24 | 0.15 to 0.34 | 0.046 | -0.54 | -0.69 to -0.38 |
| declared | 0.61 | 0.43 to 0.79 | 0.016 | -0.17 | -0.39 to +0.05 |
| ir_tfidf | 0.71 | 0.54 to 0.86 | 0.033 | -0.06 | -0.21 to +0.07 |
| observed | 0.64 | 0.46 to 0.82 | 0.030 | -0.14 | -0.35 to +0.08 |
| observed_diverse | 0.54 | 0.36 to 0.71 | 0.038 | -0.24 | -0.43 to -0.06 |
| cost_aware | 0.64 | 0.46 to 0.82 | 0.034 | -0.14 | -0.35 to +0.08 |
| history_ml | 0.71 | 0.54 to 0.86 | 0.033 | -0.06 | -0.25 to +0.14 |
| casper_slices | 0.36 | 0.18 to 0.54 | 0.043 | -0.42 | -0.61 to -0.24 |
| risk_aware_ts | 0.34 | 0.21 to 0.47 | 0.045 | -0.44 | -0.61 to -0.26 |
| adaptive_bayes | 0.78 | 0.61 to 0.92 | 0.027 | best |  |

At a budget of 20%, over the 28 revealed regressions (intervals: bootstrap over the changes; a difference whose interval holds 0 is not established):

| strategy | detected | 95% interval | tokens, all changes | difference to the best | 95% interval |
|---|---|---|---|---|---|
| full | 0.43 | 0.25 to 0.61 | 0.169 | -0.50 | -0.71 to -0.29 |
| random | 0.64 | 0.52 to 0.75 | 0.154 | -0.29 | -0.44 to -0.14 |
| declared | 0.61 | 0.43 to 0.79 | 0.038 | -0.32 | -0.50 to -0.14 |
| ir_tfidf | 0.93 | 0.82 to 1.00 | 0.100 | best |  |
| observed | 0.86 | 0.71 to 0.96 | 0.086 | -0.07 | -0.25 to +0.11 |
| observed_diverse | 0.93 | 0.84 to 1.00 | 0.094 | -0.00 | -0.11 to +0.11 |
| cost_aware | 0.86 | 0.71 to 0.96 | 0.109 | -0.07 | -0.25 to +0.11 |
| history_ml | 0.89 | 0.79 to 1.00 | 0.100 | -0.04 | -0.18 to +0.11 |
| casper_slices | 0.65 | 0.48 to 0.81 | 0.145 | -0.28 | -0.45 to -0.12 |
| risk_aware_ts | 0.63 | 0.49 to 0.76 | 0.147 | -0.30 | -0.44 to -0.16 |
| adaptive_bayes | 0.81 | 0.66 to 0.93 | 0.051 | -0.11 | -0.29 to +0.03 |

Tokens spent on the revealed regressions only:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.020 | 0.047 | 0.088 | 0.153 | 0.191 | 0.233 | 0.234 |
| random | 0.019 | 0.044 | 0.078 | 0.129 | 0.160 | 0.193 | 0.208 |
| declared | 0.006 | 0.011 | 0.015 | 0.015 | 0.015 | 0.015 | 0.015 |
| ir_tfidf | 0.012 | 0.024 | 0.038 | 0.048 | 0.053 | 0.055 | 0.055 |
| observed | 0.013 | 0.026 | 0.043 | 0.061 | 0.072 | 0.094 | 0.104 |
| observed_diverse | 0.015 | 0.037 | 0.057 | 0.073 | 0.080 | 0.084 | 0.084 |
| cost_aware | 0.013 | 0.026 | 0.043 | 0.061 | 0.072 | 0.094 | 0.104 |
| history_ml | 0.012 | 0.024 | 0.035 | 0.046 | 0.057 | 0.074 | 0.082 |
| casper_slices | 0.018 | 0.039 | 0.069 | 0.115 | 0.150 | 0.193 | 0.237 |
| risk_aware_ts | 0.019 | 0.042 | 0.073 | 0.119 | 0.148 | 0.183 | 0.205 |
| adaptive_bayes | 0.012 | 0.020 | 0.024 | 0.028 | 0.028 | 0.028 | 0.028 |

Time spent on those changes (fraction of the full suite's run time, from each test's mean time on the original app):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.020 | 0.048 | 0.092 | 0.158 | 0.199 | 0.236 | 0.239 |
| random | 0.019 | 0.044 | 0.079 | 0.131 | 0.162 | 0.195 | 0.210 |
| declared | 0.006 | 0.012 | 0.016 | 0.016 | 0.016 | 0.016 | 0.016 |
| ir_tfidf | 0.011 | 0.022 | 0.036 | 0.048 | 0.053 | 0.055 | 0.055 |
| observed | 0.013 | 0.026 | 0.044 | 0.063 | 0.073 | 0.094 | 0.105 |
| observed_diverse | 0.015 | 0.038 | 0.061 | 0.079 | 0.085 | 0.089 | 0.089 |
| cost_aware | 0.013 | 0.026 | 0.045 | 0.063 | 0.073 | 0.094 | 0.105 |
| history_ml | 0.013 | 0.025 | 0.035 | 0.047 | 0.056 | 0.073 | 0.081 |
| casper_slices | 0.027 | 0.047 | 0.081 | 0.133 | 0.168 | 0.213 | 0.253 |
| risk_aware_ts | 0.018 | 0.045 | 0.078 | 0.126 | 0.156 | 0.190 | 0.211 |
| adaptive_bayes | 0.014 | 0.022 | 0.026 | 0.030 | 0.031 | 0.031 | 0.031 |

Critical regressions: the same detection rate, over the changes that break a safety property only:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.00 | 0.05 | 0.15 | 0.35 | 0.70 | 0.95 | 1.00 |
| random | 0.10 | 0.27 | 0.44 | 0.68 | 0.78 | 0.93 | 1.00 |
| declared | 0.50 | 0.55 | 0.55 | 0.55 | 0.55 | 0.55 | 0.55 |
| ir_tfidf | 0.65 | 0.80 | 0.90 | 1.00 | 1.00 | 1.00 | 1.00 |
| observed | 0.50 | 0.60 | 0.70 | 0.80 | 0.85 | 0.85 | 1.00 |
| observed_diverse | 0.40 | 0.55 | 0.90 | 1.00 | 1.00 | 1.00 | 1.00 |
| cost_aware | 0.50 | 0.60 | 0.70 | 0.80 | 0.85 | 0.85 | 1.00 |
| history_ml | 0.55 | 0.70 | 0.80 | 0.85 | 0.85 | 0.95 | 1.00 |
| casper_slices | 0.20 | 0.45 | 0.55 | 0.77 | 0.77 | 0.80 | 1.00 |
| risk_aware_ts | 0.14 | 0.45 | 0.59 | 0.76 | 0.92 | 0.97 | 0.99 |
| adaptive_bayes | 0.59 | 0.84 | 0.89 | 0.89 | 0.89 | 0.89 | 0.89 |

![detection vs cost](figures/detection_vs_cost.png)

Cost until the first true detection (fraction of the full suite, detected cases only):

| strategy | cost_to_first_detection |
|---|---|
| full | 0.175 |
| random | 0.129 |
| declared | 0.021 |
| ir_tfidf | 0.036 |
| observed | 0.045 |
| observed_diverse | 0.063 |
| cost_aware | 0.045 |
| history_ml | 0.038 |
| casper_slices | 0.114 |
| risk_aware_ts | 0.117 |
| adaptive_bayes | 0.017 |

## 3. Changes no test reveals, and verdicts

Tokens spent on the changes no test reveals:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.020 | 0.049 | 0.100 | 0.199 | 0.299 | 0.500 | 0.893 |
| random | 0.019 | 0.050 | 0.100 | 0.199 | 0.298 | 0.495 | 0.888 |
| declared | 0.010 | 0.025 | 0.047 | 0.080 | 0.107 | 0.126 | 0.126 |
| ir_tfidf | 0.020 | 0.050 | 0.099 | 0.196 | 0.292 | 0.484 | 0.867 |
| observed | 0.016 | 0.038 | 0.078 | 0.134 | 0.182 | 0.248 | 0.309 |
| observed_diverse | 0.016 | 0.042 | 0.081 | 0.134 | 0.180 | 0.243 | 0.306 |
| cost_aware | 0.019 | 0.050 | 0.099 | 0.199 | 0.299 | 0.499 | 0.890 |
| history_ml | 0.020 | 0.050 | 0.099 | 0.199 | 0.298 | 0.495 | 0.888 |
| casper_slices | 0.020 | 0.049 | 0.100 | 0.199 | 0.299 | 0.499 | 0.898 |
| risk_aware_ts | 0.020 | 0.049 | 0.100 | 0.200 | 0.300 | 0.500 | 0.898 |
| adaptive_bayes | 0.017 | 0.039 | 0.065 | 0.095 | 0.120 | 0.149 | 0.191 |

![tokens spent on changes no test reveals](figures/benign_waste.png)

Verdicts at a budget of 5% (shares of the runs):

| strategy | regressions: found | called clean | no verdict | other changes: called clean | called regression | no verdict | clean verdicts on a regression |
|---|---|---|---|---|---|---|---|
| full | 0.14 | 0.00 | 0.86 | 0.00 | 0.00 | 1.00 |  |
| random | 0.24 | 0.00 | 0.76 | 0.00 | 0.00 | 1.00 |  |
| declared | 0.61 | 0.39 | 0.00 | 0.53 | 0.00 | 0.47 | 0.58 |
| ir_tfidf | 0.71 | 0.00 | 0.29 | 0.00 | 0.00 | 1.00 |  |
| observed | 0.64 | 0.00 | 0.36 | 0.20 | 0.00 | 0.80 | 0.00 |
| observed_diverse | 0.54 | 0.00 | 0.46 | 0.20 | 0.00 | 0.80 | 0.00 |
| cost_aware | 0.64 | 0.00 | 0.36 | 0.00 | 0.00 | 1.00 |  |
| history_ml | 0.71 | 0.00 | 0.29 | 0.00 | 0.00 | 1.00 |  |
| casper_slices | 0.36 | 0.00 | 0.64 | 0.00 | 0.00 | 1.00 |  |
| risk_aware_ts | 0.34 | 0.00 | 0.66 | 0.00 | 0.00 | 1.00 |  |
| adaptive_bayes | 0.79 | 0.11 | 0.11 | 0.47 | 0.00 | 0.53 | 0.30 |

Verdicts at a budget of 20% (shares of the runs):

| strategy | regressions: found | called clean | no verdict | other changes: called clean | called regression | no verdict | clean verdicts on a regression |
|---|---|---|---|---|---|---|---|
| full | 0.43 | 0.00 | 0.57 | 0.00 | 0.00 | 1.00 |  |
| random | 0.64 | 0.00 | 0.36 | 0.00 | 0.01 | 0.99 |  |
| declared | 0.61 | 0.39 | 0.00 | 0.73 | 0.00 | 0.27 | 0.50 |
| ir_tfidf | 0.93 | 0.00 | 0.07 | 0.00 | 0.04 | 0.96 |  |
| observed | 0.86 | 0.00 | 0.14 | 0.47 | 0.00 | 0.53 | 0.00 |
| observed_diverse | 0.93 | 0.00 | 0.07 | 0.47 | 0.01 | 0.52 | 0.00 |
| cost_aware | 0.86 | 0.00 | 0.14 | 0.00 | 0.00 | 1.00 |  |
| history_ml | 0.89 | 0.00 | 0.11 | 0.00 | 0.01 | 0.99 |  |
| casper_slices | 0.65 | 0.00 | 0.35 | 0.00 | 0.00 | 1.00 |  |
| risk_aware_ts | 0.64 | 0.00 | 0.36 | 0.00 | 0.00 | 1.00 |  |
| adaptive_bayes | 0.82 | 0.14 | 0.04 | 0.73 | 0.00 | 0.27 | 0.27 |

## 4. Prioritization and selection quality

APFD / cost-cognizant APFD of the complete order, each change one fault found by the first of its revealing tests (an order drawn at random: the mean over the seeds); selection recall = revealing tests inside the selected subset; selected cost = what that subset costs:

| strategy | apfd | apfdc | selection_recall | selected_cost_fraction |
|---|---|---|---|---|
| full | 0.755 | 0.742 | 1.000 | 0.899 |
| random | 0.766 | 0.772 | 1.000 | 0.899 |
| declared | 0.901 | 0.891 | 0.511 | 0.087 |
| ir_tfidf | 0.957 | 0.942 | 1.000 | 0.899 |
| observed | 0.836 | 0.887 | 1.000 | 0.435 |
| observed_diverse | 0.947 | 0.913 | 1.000 | 0.435 |
| cost_aware | 0.836 | 0.887 | 1.000 | 0.899 |
| history_ml | 0.891 | 0.912 | 1.000 | 0.899 |
| casper_slices | 0.723 | 0.756 | 1.000 | 0.899 |
| risk_aware_ts | 0.759 | 0.742 | 1.000 | 0.899 |
| adaptive_bayes | 0.938 | 0.940 | 1.000 | 0.899 |

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
| full | 0.43 | 0.54 | 0.59 | 0.59 | 0.70 | 0.72 | 0.73 |
| random | 0.41 | 0.55 | 0.67 | 0.77 | 0.80 | 0.82 | 0.82 |
| declared | 0.33 | 0.38 | 0.38 | 0.38 | 0.38 | 0.38 | 0.38 |
| ir_tfidf | 0.45 | 0.52 | 0.56 | 0.58 | 0.58 | 0.62 | 0.62 |
| observed | 0.41 | 0.52 | 0.60 | 0.70 | 0.72 | 0.72 | 0.72 |
| observed_diverse | 0.29 | 0.53 | 0.63 | 0.67 | 0.74 | 0.74 | 0.74 |
| cost_aware | 0.41 | 0.53 | 0.61 | 0.71 | 0.72 | 0.72 | 0.72 |
| history_ml | 0.46 | 0.57 | 0.66 | 0.69 | 0.70 | 0.70 | 0.70 |
| casper_slices | 0.46 | 0.46 | 0.52 | 0.57 | 0.67 | 0.69 | 0.70 |
| risk_aware_ts | 0.41 | 0.61 | 0.73 | 0.77 | 0.80 | 0.80 | 0.82 |
| adaptive_bayes | 0.50 | 0.57 | 0.60 | 0.60 | 0.62 | 0.62 | 0.62 |

## 6. Coverage

Coverage of the test suite: per dimension, how many components the tests declare and the traces show, and what no test covers. A feature (`catalog/features.yaml`) is covered by the tests that declare or call one of its tools. A tool error path is a place in the code where a tool call is refused, reached when a run executes it. A workflow is declared by the tests that name it and observed when a run delegates to exactly its agents in order. Execution paths are the distinct agent and tool sequences; risk lists tests per level.

| dimension | components | declared | observed | not covered |
|---|---|---|---|---|
| agent | 11 | 11 | 11 |  |
| feature | 19 | 18 | 19 |  |
| skill | 13 | 12 | 13 |  |
| tool | 32 | 30 | 31 | get_asset |
| tool error path | 32 |  | 15 | harness/dispatcher.py:73 Dispatcher.call invalid_arguments, harness/dispatcher.py:156 Dispatcher.gate unknown_tool, harness/dispatcher.py:162 Dispatcher.gate tool_not_available, harness/runtime.py:195 Runtime._delegate invalid_arguments, harness/runtime.py:208 Runtime._delegate unknown_agent, harness/runtime.py:211 Runtime._delegate invalid_arguments, harness/runtime.py:218 Runtime._delegate max_delegation_depth, services/governance.py:39 export_user_data approval_required ... |
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
| full | 0.41 | 0.53 | 0.63 | 0.70 | 0.87 | 0.97 | 0.97 |
| random | 0.58 | 0.75 | 0.83 | 0.94 | 0.96 | 0.97 | 0.97 |
| declared | 0.67 | 0.67 | 0.67 | 0.67 | 0.67 | 0.67 | 0.67 |
| ir_tfidf | 0.92 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 |
| observed | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 |
| observed_diverse | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 |
| cost_aware | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 |
| history_ml | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 |
| casper_slices | 0.46 | 0.85 | 0.90 | 0.91 | 0.92 | 0.95 | 0.97 |
| risk_aware_ts | 0.57 | 0.70 | 0.81 | 0.92 | 0.96 | 0.97 | 0.97 |
| adaptive_bayes | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 |

Affected properties checked:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.29 | 0.40 | 0.49 | 0.52 | 0.60 | 0.68 | 0.71 |
| random | 0.32 | 0.45 | 0.59 | 0.71 | 0.75 | 0.78 | 0.79 |
| declared | 0.18 | 0.24 | 0.26 | 0.27 | 0.28 | 0.28 | 0.28 |
| ir_tfidf | 0.29 | 0.37 | 0.45 | 0.50 | 0.52 | 0.55 | 0.57 |
| observed | 0.27 | 0.35 | 0.44 | 0.57 | 0.61 | 0.62 | 0.63 |
| observed_diverse | 0.25 | 0.47 | 0.57 | 0.63 | 0.66 | 0.67 | 0.68 |
| cost_aware | 0.27 | 0.36 | 0.45 | 0.57 | 0.61 | 0.62 | 0.64 |
| history_ml | 0.28 | 0.40 | 0.48 | 0.55 | 0.57 | 0.60 | 0.61 |
| casper_slices | 0.33 | 0.33 | 0.48 | 0.59 | 0.65 | 0.69 | 0.72 |
| risk_aware_ts | 0.35 | 0.57 | 0.65 | 0.72 | 0.74 | 0.76 | 0.79 |
| adaptive_bayes | 0.32 | 0.44 | 0.49 | 0.50 | 0.51 | 0.51 | 0.52 |

Runs that found no regression and tested every affected mandatory property (the method's step 5):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.05 | 0.05 | 0.06 | 0.06 | 0.09 | 0.20 | 1.00 |
| random | 0.05 | 0.07 | 0.13 | 0.42 | 0.61 | 0.89 | 1.00 |
| declared | 0.10 | 0.15 | 0.15 | 0.15 | 0.15 | 0.15 | 0.15 |
| ir_tfidf | 0.08 | 0.17 | 0.24 | 0.49 | 0.58 | 0.85 | 1.00 |
| observed | 0.07 | 0.12 | 0.24 | 0.32 | 0.72 | 0.72 | 0.73 |
| observed_diverse | 0.06 | 0.18 | 0.25 | 0.70 | 0.75 | 0.73 | 0.73 |
| cost_aware | 0.07 | 0.12 | 0.24 | 0.37 | 0.83 | 0.83 | 1.00 |
| history_ml | 0.07 | 0.13 | 0.32 | 0.45 | 0.67 | 0.96 | 1.00 |
| casper_slices | 0.05 | 0.06 | 0.07 | 0.34 | 0.71 | 0.77 | 1.00 |
| risk_aware_ts | 0.07 | 0.22 | 0.38 | 0.71 | 0.94 | 1.00 | 1.00 |
| adaptive_bayes | 0.12 | 0.50 | 0.85 | 0.90 | 0.95 | 0.95 | 1.00 |

Affected workflows run (the workflows of the tests that exercised a changed component):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.07 | 0.33 |
| random | 0.01 | 0.05 | 0.12 | 0.25 | 0.34 | 0.44 | 0.53 |
| declared | 0.05 | 0.17 | 0.22 | 0.25 | 0.27 | 0.27 | 0.27 |
| ir_tfidf | 0.03 | 0.10 | 0.20 | 0.28 | 0.33 | 0.37 | 0.39 |
| observed | 0.04 | 0.06 | 0.18 | 0.24 | 0.27 | 0.30 | 0.39 |
| observed_diverse | 0.14 | 0.36 | 0.50 | 0.65 | 0.69 | 0.69 | 0.69 |
| cost_aware | 0.04 | 0.06 | 0.18 | 0.24 | 0.27 | 0.30 | 0.39 |
| history_ml | 0.06 | 0.09 | 0.20 | 0.27 | 0.32 | 0.37 | 0.40 |
| casper_slices | 0.00 | 0.00 | 0.14 | 0.31 | 0.40 | 0.49 | 0.58 |
| risk_aware_ts | 0.04 | 0.18 | 0.34 | 0.55 | 0.68 | 0.72 | 0.72 |
| adaptive_bayes | 0.03 | 0.12 | 0.16 | 0.19 | 0.20 | 0.20 | 0.20 |

Affected features reached (the features with a tool or a part the change touches), over the changes that affect one:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.19 | 0.33 | 0.46 | 0.54 | 0.70 | 0.89 | 0.89 |
| random | 0.34 | 0.64 | 0.79 | 0.92 | 0.94 | 0.95 | 0.95 |
| declared | 0.59 | 0.59 | 0.60 | 0.60 | 0.61 | 0.61 | 0.61 |
| ir_tfidf | 0.85 | 0.92 | 0.93 | 0.94 | 0.94 | 0.94 | 0.94 |
| observed | 0.72 | 0.74 | 0.84 | 0.91 | 0.91 | 0.91 | 0.91 |
| observed_diverse | 0.72 | 0.78 | 0.88 | 0.89 | 0.89 | 0.89 | 0.89 |
| cost_aware | 0.72 | 0.74 | 0.84 | 0.91 | 0.91 | 0.91 | 0.91 |
| history_ml | 0.81 | 0.79 | 0.90 | 0.91 | 0.91 | 0.91 | 0.91 |
| casper_slices | 0.19 | 0.63 | 0.79 | 0.87 | 0.89 | 0.95 | 0.96 |
| risk_aware_ts | 0.33 | 0.63 | 0.78 | 0.91 | 0.94 | 0.95 | 0.95 |
| adaptive_bayes | 0.80 | 0.87 | 0.89 | 0.89 | 0.89 | 0.89 | 0.89 |

## 7. Replay-first

Every test was run on every changed copy with the model's calls answered from the answers recorded on the original app (`traceeval replay-first`; no model is called). A test either replays to the end, and its outcome on the changed copy is known for no tokens, or diverges at the first request the original app never made, and needs the model from there on.

What the replay settles alone, by kind of change:

| kind of change | changes | no test diverges | a replayed test fails | diverged tests, mean | their share of the suite's tokens | after the divergence point |
|---|---|---|---|---|---|---|
| benign | 9 | 4 | 0 | 42 of 180 | 0.283 | 0.250 |
| code | 10 | 1 | 0 | 11 of 180 | 0.109 | 0.069 |
| combined | 1 | 0 | 0 | 2 of 180 | 0.012 | 0.004 |
| config | 7 | 0 | 2 | 40 of 180 | 0.335 | 0.246 |
| prompt | 2 | 0 | 0 | 12 of 180 | 0.098 | 0.079 |
| runtime | 3 | 0 | 1 | 32 of 180 | 0.331 | 0.167 |
| skill | 11 | 0 | 0 | 50 of 180 | 0.382 | 0.325 |
| all | 43 | 5 | 3 | 34 of 180 | 0.265 | 0.207 |

Over the 1442 diverged (change, test) pairs, the change first reaches the model in what an agent is sent up front (its prompt, skills, tools or task) on 1172, and in a tool result on 270.

The replay against the recorded ground truth:

- replayed outcomes that differ from the recorded majority: 0 of 6298;
- the 183 revealing (change, test) pairs: 13 replay to a failure, 170 diverge, 0 replay to a pass;
- revealed regressions with a revealing test that fails in the replay or diverges: 28 of 28;
- changes no test reveals on which a replayed test fails: 0.

The replay against the recorded runs, one by one, over the tests that replay to the end. A run is identical to the replay when it has the same tool calls, final answer, final state and token count:

| recorded runs of | runs | end like the replay | identical to the replay |
|---|---|---|---|
| the original app | 900 | 900 | 887 |
| the original app, run as the changed copies are | 900 | 900 | 818 |
| the changed copies | 31490 | 31490 | 29051 |

The condition itself, a model call being a function of its request, request by request:

| requests of | sent before | of which |
|---|---|---|
| the baseline's repetitions, one test at a time | 914 | 15 (1.64%) got more than one answer |
| the empty change | 5218 | 104 (1.99%) answered otherwise than the cassette |
| the changed copies | 198655 | 3657 (1.84%) answered otherwise than the cassette |

The strategies run replay-first: a test that replays to the end is not run, a replayed failure of a test that passes on the original app ends the run for no tokens, and a diverged test costs its tokens after the divergence point. A run that ends because every diverged test has run and passed is a clean verdict that leaves no reachable test untested.

Fraction of the revealed regressions detected, by nominal budget:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.89 | 0.93 | 0.93 | 0.93 | 0.96 | 1.00 | 1.00 |
| random | 0.76 | 0.85 | 0.93 | 0.98 | 0.98 | 0.99 | 0.99 |
| cheapest | 0.80 | 0.84 | 0.87 | 0.94 | 0.98 | 0.98 | 0.98 |
| late_divergence | 0.79 | 0.93 | 0.96 | 0.96 | 1.00 | 1.00 | 1.00 |
| declared | 0.57 | 0.68 | 0.68 | 0.68 | 0.68 | 0.68 | 0.68 |
| ir_tfidf | 0.86 | 0.89 | 0.96 | 1.00 | 1.00 | 1.00 | 1.00 |
| observed | 0.82 | 0.93 | 0.96 | 1.00 | 1.00 | 1.00 | 1.00 |
| observed_diverse | 0.79 | 0.93 | 0.93 | 0.96 | 0.96 | 1.00 | 1.00 |
| cost_aware | 0.82 | 0.93 | 0.96 | 1.00 | 1.00 | 1.00 | 1.00 |
| history_ml | 0.89 | 0.96 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| casper_slices | 0.86 | 0.86 | 0.89 | 0.99 | 0.99 | 0.99 | 0.99 |
| risk_aware_ts | 0.79 | 0.90 | 0.95 | 0.97 | 0.97 | 1.00 | 1.00 |
| adaptive_bayes | 0.89 | 0.96 | 0.96 | 0.96 | 0.96 | 0.96 | 0.96 |

Tokens spent, as a mean over all changes (fraction of the full suite):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.008 | 0.016 | 0.029 | 0.047 | 0.062 | 0.084 | 0.102 |
| random | 0.010 | 0.021 | 0.033 | 0.049 | 0.062 | 0.082 | 0.103 |
| cheapest | 0.009 | 0.018 | 0.032 | 0.049 | 0.062 | 0.080 | 0.100 |
| late_divergence | 0.009 | 0.020 | 0.031 | 0.047 | 0.060 | 0.078 | 0.098 |
| declared | 0.006 | 0.013 | 0.020 | 0.030 | 0.038 | 0.042 | 0.042 |
| ir_tfidf | 0.008 | 0.018 | 0.029 | 0.042 | 0.053 | 0.069 | 0.086 |
| observed | 0.009 | 0.017 | 0.029 | 0.044 | 0.057 | 0.075 | 0.094 |
| observed_diverse | 0.010 | 0.022 | 0.035 | 0.051 | 0.065 | 0.085 | 0.105 |
| cost_aware | 0.009 | 0.017 | 0.029 | 0.044 | 0.057 | 0.075 | 0.094 |
| history_ml | 0.008 | 0.016 | 0.026 | 0.040 | 0.052 | 0.070 | 0.089 |
| casper_slices | 0.008 | 0.018 | 0.031 | 0.048 | 0.060 | 0.079 | 0.100 |
| risk_aware_ts | 0.010 | 0.021 | 0.032 | 0.048 | 0.062 | 0.081 | 0.100 |
| adaptive_bayes | 0.008 | 0.014 | 0.018 | 0.021 | 0.021 | 0.021 | 0.021 |

For comparison, a cache of the original app's answers in front of the model, with the whole suite run again and no stop at a failure, pays every diverged test from its divergence point on: 0.207 of the suite's tokens per change (median 0.083), less the requests after that point that the cache also knows. It finds every revealed regression.

The same tests run whole, without the replayed part taken off:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.012 | 0.022 | 0.035 | 0.058 | 0.075 | 0.098 | 0.116 |
| random | 0.014 | 0.028 | 0.043 | 0.062 | 0.078 | 0.098 | 0.119 |
| cheapest | 0.013 | 0.024 | 0.040 | 0.061 | 0.077 | 0.096 | 0.117 |
| late_divergence | 0.019 | 0.034 | 0.049 | 0.066 | 0.080 | 0.098 | 0.118 |
| declared | 0.009 | 0.018 | 0.027 | 0.037 | 0.046 | 0.049 | 0.049 |
| ir_tfidf | 0.010 | 0.024 | 0.038 | 0.055 | 0.067 | 0.083 | 0.100 |
| observed | 0.013 | 0.024 | 0.040 | 0.056 | 0.071 | 0.090 | 0.109 |
| observed_diverse | 0.015 | 0.032 | 0.048 | 0.066 | 0.081 | 0.102 | 0.122 |
| cost_aware | 0.013 | 0.024 | 0.040 | 0.056 | 0.071 | 0.090 | 0.109 |
| history_ml | 0.013 | 0.023 | 0.037 | 0.054 | 0.067 | 0.085 | 0.105 |
| casper_slices | 0.012 | 0.026 | 0.044 | 0.064 | 0.078 | 0.097 | 0.118 |
| risk_aware_ts | 0.015 | 0.029 | 0.044 | 0.063 | 0.078 | 0.098 | 0.117 |
| adaptive_bayes | 0.013 | 0.022 | 0.027 | 0.031 | 0.031 | 0.031 | 0.031 |

At a budget of 5%, over the 28 revealed regressions (intervals: bootstrap over the changes; a difference whose interval holds 0 is not established):

| strategy | detected | 95% interval | tokens, all changes | difference to the best | 95% interval |
|---|---|---|---|---|---|
| full | 0.93 | 0.82 to 1.00 | 0.016 | -0.04 | -0.14 to +0.07 |
| random | 0.85 | 0.74 to 0.95 | 0.021 | -0.11 | -0.23 to -0.01 |
| cheapest | 0.84 | 0.69 to 0.96 | 0.018 | -0.13 | -0.26 to -0.02 |
| late_divergence | 0.93 | 0.82 to 1.00 | 0.020 | -0.04 | -0.14 to +0.07 |
| declared | 0.68 | 0.50 to 0.86 | 0.013 | -0.29 | -0.50 to -0.11 |
| ir_tfidf | 0.89 | 0.79 to 1.00 | 0.018 | -0.07 | -0.21 to +0.07 |
| observed | 0.93 | 0.82 to 1.00 | 0.017 | -0.04 | -0.11 to +0.00 |
| observed_diverse | 0.93 | 0.82 to 1.00 | 0.022 | -0.04 | -0.14 to +0.07 |
| cost_aware | 0.93 | 0.82 to 1.00 | 0.017 | -0.04 | -0.11 to +0.00 |
| history_ml | 0.96 | 0.89 to 1.00 | 0.016 | best |  |
| casper_slices | 0.86 | 0.71 to 0.96 | 0.018 | -0.11 | -0.21 to +0.00 |
| risk_aware_ts | 0.90 | 0.79 to 0.99 | 0.021 | -0.06 | -0.17 to +0.01 |
| adaptive_bayes | 0.96 | 0.89 to 1.00 | 0.014 | +0.00 | -0.11 to +0.11 |

At a budget of 20%, over the 28 revealed regressions (intervals: bootstrap over the changes; a difference whose interval holds 0 is not established):

| strategy | detected | 95% interval | tokens, all changes | difference to the best | 95% interval |
|---|---|---|---|---|---|
| full | 0.93 | 0.82 to 1.00 | 0.047 | -0.07 | -0.18 to +0.00 |
| random | 0.98 | 0.94 to 1.00 | 0.049 | -0.02 | -0.06 to +0.00 |
| cheapest | 0.94 | 0.85 to 1.00 | 0.049 | -0.06 | -0.15 to +0.00 |
| late_divergence | 0.96 | 0.89 to 1.00 | 0.047 | -0.04 | -0.11 to +0.00 |
| declared | 0.68 | 0.50 to 0.86 | 0.030 | -0.32 | -0.50 to -0.14 |
| ir_tfidf | 1.00 | 1.00 to 1.00 | 0.042 | best |  |
| observed | 1.00 | 1.00 to 1.00 | 0.044 | +0.00 | +0.00 to +0.00 |
| observed_diverse | 0.96 | 0.89 to 1.00 | 0.051 | -0.04 | -0.11 to +0.00 |
| cost_aware | 1.00 | 1.00 to 1.00 | 0.044 | +0.00 | +0.00 to +0.00 |
| history_ml | 1.00 | 1.00 to 1.00 | 0.040 | +0.00 | +0.00 to +0.00 |
| casper_slices | 0.99 | 0.98 to 1.00 | 0.048 | -0.01 | -0.02 to +0.00 |
| risk_aware_ts | 0.97 | 0.91 to 1.00 | 0.048 | -0.03 | -0.09 to +0.00 |
| adaptive_bayes | 0.96 | 0.89 to 1.00 | 0.021 | -0.04 | -0.11 to +0.00 |

![replay-first: detection vs cost](figures/replay_first.png)

Verdicts at a budget of 20% (shares of the runs):

| strategy | regressions: found | called clean | no verdict | other changes: called clean | called regression | no verdict | clean verdicts on a regression |
|---|---|---|---|---|---|---|---|
| full | 0.93 | 0.00 | 0.07 | 0.60 | 0.00 | 0.40 | 0.00 |
| random | 0.99 | 0.00 | 0.01 | 0.60 | 0.00 | 0.40 | 0.00 |
| cheapest | 0.96 | 0.00 | 0.04 | 0.60 | 0.00 | 0.40 | 0.00 |
| late_divergence | 0.96 | 0.00 | 0.04 | 0.60 | 0.00 | 0.40 | 0.00 |
| declared | 0.68 | 0.32 | 0.00 | 0.73 | 0.00 | 0.27 | 0.45 |
| ir_tfidf | 1.00 | 0.00 | 0.00 | 0.60 | 0.04 | 0.36 | 0.00 |
| observed | 1.00 | 0.00 | 0.00 | 0.60 | 0.00 | 0.40 | 0.00 |
| observed_diverse | 0.96 | 0.00 | 0.04 | 0.60 | 0.01 | 0.39 | 0.00 |
| cost_aware | 1.00 | 0.00 | 0.00 | 0.60 | 0.00 | 0.40 | 0.00 |
| history_ml | 1.00 | 0.00 | 0.00 | 0.60 | 0.01 | 0.39 | 0.00 |
| casper_slices | 1.00 | 0.00 | 0.00 | 0.60 | 0.00 | 0.40 | 0.00 |
| risk_aware_ts | 0.97 | 0.00 | 0.03 | 0.60 | 0.01 | 0.39 | 0.00 |
| adaptive_bayes | 0.96 | 0.04 | 0.00 | 0.93 | 0.00 | 0.07 | 0.07 |

Verdicts at a budget of 100% (shares of the runs):

| strategy | regressions: found | called clean | no verdict | other changes: called clean | called regression | no verdict | clean verdicts on a regression |
|---|---|---|---|---|---|---|---|
| full | 1.00 | 0.00 | 0.00 | 0.97 | 0.03 | 0.00 | 0.00 |
| random | 1.00 | 0.00 | 0.00 | 0.99 | 0.01 | 0.00 | 0.00 |
| cheapest | 1.00 | 0.00 | 0.00 | 0.97 | 0.03 | 0.00 | 0.00 |
| late_divergence | 1.00 | 0.00 | 0.00 | 0.97 | 0.03 | 0.00 | 0.00 |
| declared | 0.68 | 0.32 | 0.00 | 1.00 | 0.00 | 0.00 | 0.38 |
| ir_tfidf | 1.00 | 0.00 | 0.00 | 0.96 | 0.04 | 0.00 | 0.00 |
| observed | 1.00 | 0.00 | 0.00 | 0.97 | 0.03 | 0.00 | 0.00 |
| observed_diverse | 1.00 | 0.00 | 0.00 | 0.99 | 0.01 | 0.00 | 0.00 |
| cost_aware | 1.00 | 0.00 | 0.00 | 0.97 | 0.03 | 0.00 | 0.00 |
| history_ml | 1.00 | 0.00 | 0.00 | 0.99 | 0.01 | 0.00 | 0.00 |
| casper_slices | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 |
| risk_aware_ts | 1.00 | 0.00 | 0.00 | 0.99 | 0.01 | 0.00 | 0.00 |
| adaptive_bayes | 0.96 | 0.04 | 0.00 | 1.00 | 0.00 | 0.00 | 0.06 |

## 8. Generated changes, replayed

The 598 changes that `mutation/generator.py` makes mechanically from the app (one per place an edit of its kind applies to), each applied to a copy of the original app and replayed against the recording's cassette (`traceeval replay-first --generated`). No model is called, and no change has a label.

| kind of change | changes | no test diverges | a replayed test fails | diverged tests, mean | their share of the suite's tokens | after the divergence point |
|---|---|---|---|---|---|---|
| argswap | 12 | 0 | 0 | 18 of 180 | 0.175 | 0.113 |
| comment | 32 | 32 | 0 | 0 of 180 | 0.000 | 0.000 |
| condnot | 120 | 36 | 30 | 47 of 180 | 0.308 | 0.250 |
| fixture | 85 | 45 | 3 | 3 of 180 | 0.034 | 0.023 |
| guarddel | 4 | 0 | 0 | 54 of 180 | 0.438 | 0.359 |
| rewrap | 13 | 0 | 0 | 39 of 180 | 0.314 | 0.261 |
| ruledel | 18 | 0 | 0 | 120 of 180 | 0.744 | 0.708 |
| setting | 65 | 11 | 3 | 33 of 180 | 0.241 | 0.198 |
| stepdel | 76 | 0 | 0 | 25 of 180 | 0.231 | 0.175 |
| stepswap | 63 | 0 | 0 | 22 of 180 | 0.214 | 0.157 |
| tooldesc | 32 | 0 | 0 | 43 of 180 | 0.348 | 0.288 |
| tooldrop | 50 | 0 | 0 | 28 of 180 | 0.249 | 0.196 |
| whennot | 28 | 0 | 0 | 30 of 180 | 0.284 | 0.213 |
| all | 598 | 124 | 36 | 30 of 180 | 0.233 | 0.187 |

- settled as clean, no test diverges and none fails: 97 of 598;
- settled as a regression, a test that passes on the original app replays to a failure: 36;
- left for the model: 465, whose diverged tests cost 23.9% of the suite's tokens after their divergence points on average (median 9.1%), and 29.5% run whole.

## How to read this

`detected` counts *changes* (one failing revealing test is enough). Compare strategies at equal tokens *spent*, not equal nominal budget: every run ends at its first failure, the selecting strategies also run out of tests, and `adaptive_bayes` also stops when it is confident. A good strategy is high in the first table of section 2 and low in the second. The sample is the changes: the seeds only draw which recorded run answers a test and the choices of the strategies that draw at random, so an interval is over the changes. A clean verdict is worth what the last column of the verdict tables says.

Section 7 reads like section 2, with the replay in front: compare a strategy's row there with its row here. Replay-first, a strategy that orders the whole suite gives a clean verdict once every diverged test has run and passed; that verdict holds as far as the replay agrees with the recording, which the first lines of the section measure.
