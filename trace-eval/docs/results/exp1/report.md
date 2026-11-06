# TRACE-Eval experiment report

`runs/exp1` · 136 tests · 38 changes · 3 baseline repetitions · full suite = 483,281 tokens · 0 flaky tests at baseline

## 1. Ground truth — which changes are revealed by how many tests

| change | category | expected | revealing tests |
|---|---|---|---|
| `benign_code_comment_docstring` | benign | benign | 0 |
| `benign_code_rename_locals` | benign | benign | 0 |
| `benign_config_comments_reordered` | benign | benign | 0 |
| `benign_new_unused_tool` | benign | benign | 0 |
| `benign_orchestrator_prompt_wording` | benign | benign | 0 |
| `benign_skill_prose_reflow` | benign | benign | 0 |
| `code_approval_gate_bypass` | code | regression | 1 |
| `code_edit_keeps_review` | code | regression | 1 |
| `code_get_page_review_flag` | code | regression | 15 |
| `code_links_external_lenient` | code | regression | 6 |
| `code_links_unknown_url_crash` | code | regression | 1 |
| `code_metadata_arg_swap` | code | regression | 5 |
| `code_metadata_keywords_crash` | code | regression | 1 |
| `code_retry_disabled` | code | regression | 8 |
| `code_retry_drop_idempotency` | code | regression | 5 |
| `code_router_phrase_weight` | code | regression | 3 |
| `combined_seo_keyword_limit` | combined | regression | 1 |
| `config_approval_drop_unpublish` | config | regression | 1 |
| `config_default_agent_publishing` | config | regression | 3 |
| `config_disable_validate_links` | config | regression | 43 |
| `config_max_tool_calls_5` | config | regression | 11 |
| `config_require_review_false` | config | regression | 3 |
| `config_retries_0` | config | regression | 8 |
| `config_seo_title_20` | config | regression | 2 |
| `prompt_publishing_triggers_removed` | prompt | regression | 6 |
| `prompt_seo_tool_removed` | prompt | regression | 6 |
| `prompt_translation_intents_reordered` | prompt | regression | 1 |
| `code_delegation_depth_zero` | runtime | regression | 109 |
| `code_termination_off_by_six` | runtime | regression | 2 |
| `skill_authoring_drop_metadata` | skill | regression | 3 |
| `skill_governance_drop_consent` | skill | regression | 5 |
| `skill_linkval_ignore_assets` | skill | regression | 2 |
| `skill_publish_drop_link_validation` | skill | regression | 8 |
| `skill_publish_drop_permission_check` | skill | regression | 3 |
| `skill_rollback_drop_permission_check` | skill | regression | 1 |
| `skill_rollback_restores_latest` | skill | regression | 3 |
| `skill_seo_drop_length_guard` | skill | regression | 1 |
| `skill_translation_wrong_default` | skill | regression | 2 |

Testbed sanity (every regression revealed by ≥1 test, no benign change revealed): **OK**.

## 2. Detection within a budget

Fraction of regression-inducing changes detected, by nominal budget (% of full-suite tokens):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.03 | 0.12 | 0.28 | 0.50 | 0.56 | 0.75 | 1.00 |
| random | 0.11 | 0.22 | 0.38 | 0.56 | 0.70 | 0.82 | 1.00 |
| declared | 0.44 | 0.56 | 0.66 | 0.66 | 0.66 | 0.66 | 0.66 |
| ir_tfidf | 0.64 | 0.84 | 0.94 | 0.97 | 1.00 | 1.00 | 1.00 |
| observed | 0.50 | 0.66 | 0.78 | 0.91 | 0.94 | 0.97 | 1.00 |
| observed_diverse | 0.34 | 0.72 | 0.81 | 0.88 | 0.94 | 0.97 | 1.00 |
| cost_aware | 0.53 | 0.66 | 0.78 | 0.91 | 0.94 | 0.97 | 1.00 |
| history_ml | 0.41 | 0.56 | 0.78 | 0.91 | 0.94 | 0.97 | 1.00 |
| adaptive_bayes | 0.53 | 0.69 | 0.81 | 0.84 | 0.84 | 0.84 | 0.84 |

Tokens actually spent on those changes (fraction of the full suite):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.020 | 0.049 | 0.100 | 0.199 | 0.299 | 0.497 | 0.972 |
| random | 0.019 | 0.049 | 0.099 | 0.199 | 0.299 | 0.497 | 0.970 |
| declared | 0.011 | 0.025 | 0.042 | 0.064 | 0.078 | 0.090 | 0.090 |
| ir_tfidf | 0.019 | 0.049 | 0.099 | 0.199 | 0.298 | 0.496 | 0.970 |
| observed | 0.017 | 0.046 | 0.088 | 0.155 | 0.214 | 0.306 | 0.458 |
| observed_diverse | 0.018 | 0.047 | 0.088 | 0.157 | 0.215 | 0.307 | 0.458 |
| cost_aware | 0.019 | 0.049 | 0.099 | 0.199 | 0.298 | 0.496 | 0.969 |
| history_ml | 0.019 | 0.049 | 0.099 | 0.199 | 0.299 | 0.497 | 0.969 |
| adaptive_bayes | 0.018 | 0.031 | 0.041 | 0.047 | 0.050 | 0.056 | 0.070 |

![detection vs cost](figures/detection_vs_cost.png)

Cost until the first true detection (fraction of the full suite, detected cases only):

| strategy | cost_to_first_detection |
|---|---|
| full | 0.171 |
| random | 0.144 |
| declared | 0.024 |
| ir_tfidf | 0.026 |
| observed | 0.045 |
| observed_diverse | 0.049 |
| cost_aware | 0.044 |
| history_ml | 0.052 |
| adaptive_bayes | 0.025 |

## 3. Benign changes — wasted budget and stopping

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.020 | 0.050 | 0.100 | 0.199 | 0.299 | 0.498 | 0.999 |
| random | 0.019 | 0.049 | 0.099 | 0.199 | 0.299 | 0.499 | 0.995 |
| declared | 0.007 | 0.017 | 0.033 | 0.049 | 0.065 | 0.091 | 0.091 |
| ir_tfidf | 0.019 | 0.049 | 0.098 | 0.197 | 0.297 | 0.498 | 0.995 |
| observed | 0.010 | 0.031 | 0.055 | 0.100 | 0.133 | 0.176 | 0.224 |
| observed_diverse | 0.011 | 0.032 | 0.055 | 0.099 | 0.133 | 0.176 | 0.224 |
| cost_aware | 0.019 | 0.049 | 0.099 | 0.198 | 0.298 | 0.497 | 0.989 |
| history_ml | 0.020 | 0.049 | 0.099 | 0.199 | 0.299 | 0.498 | 0.989 |
| adaptive_bayes | 0.013 | 0.033 | 0.066 | 0.112 | 0.145 | 0.212 | 0.338 |

![benign waste](figures/benign_waste.png)

Stop reasons of `adaptive_bayes` (rows: is the change a regression?):

| is_regression | budget | clean | no_components | regression | uninformative |
|---|---|---|---|---|---|
| False | 179 | 90 | 140 | 0 | 11 |
| True | 420 | 260 | 0 | 1550 | 10 |

## 4. Prioritization and selection quality

APFD / cost-cognizant APFD of the complete order; selection recall = revealing tests inside the selected subset; selected cost = what that subset costs:

| strategy | apfd | apfdc | selection_recall | selected_cost_fraction |
|---|---|---|---|---|
| full | 0.673 | 0.570 | 1.000 | 1.000 |
| random | 0.491 | 0.500 | 1.000 | 1.000 |
| declared | 0.809 | 0.762 | 0.522 | 0.096 |
| ir_tfidf | 0.807 | 0.827 | 1.000 | 1.000 |
| observed | 0.820 | 0.846 | 1.000 | 0.486 |
| observed_diverse | 0.832 | 0.799 | 1.000 | 0.486 |
| cost_aware | 0.822 | 0.848 | 1.000 | 1.000 |
| history_ml | 0.809 | 0.827 | 1.000 | 1.000 |
| adaptive_bayes | 0.813 | 0.790 | 1.000 | 1.000 |

![apfdc](figures/apfdc.png)

## How to read this

`detected` counts *changes* (one failing revealing test is enough). Compare strategies at equal tokens *spent*, not equal nominal budget: `declared`/`observed` select and run out of tests, `adaptive_bayes` stops when it is confident, the others always spend the whole budget. A good strategy is high in section 2 and low in section 3.
