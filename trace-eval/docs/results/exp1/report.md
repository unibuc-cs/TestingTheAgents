# TRACE-Eval experiment report

`runs/exp1` · 136 tests · 37 changes · 3 baseline repetitions · full suite = 483,281 tokens · 0 flaky tests at baseline

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
| `skill_rollback_restores_latest` | skill | regression | 3 |
| `skill_seo_drop_length_guard` | skill | regression | 1 |
| `skill_translation_wrong_default` | skill | regression | 2 |

Testbed sanity (every regression revealed by ≥1 test, no benign change revealed): **OK**.

## 2. Detection within a budget

Fraction of regression-inducing changes detected, by nominal budget (% of full-suite tokens):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.03 | 0.13 | 0.29 | 0.52 | 0.58 | 0.77 | 1.00 |
| random | 0.11 | 0.22 | 0.39 | 0.57 | 0.71 | 0.84 | 1.00 |
| declared | 0.42 | 0.55 | 0.65 | 0.65 | 0.65 | 0.65 | 0.65 |
| ir_tfidf | 0.63 | 0.84 | 0.94 | 0.97 | 1.00 | 1.00 | 1.00 |
| observed | 0.48 | 0.65 | 0.77 | 0.90 | 0.94 | 0.97 | 1.00 |
| observed_diverse | 0.32 | 0.71 | 0.81 | 0.87 | 0.94 | 0.97 | 1.00 |
| cost_aware | 0.52 | 0.65 | 0.77 | 0.90 | 0.94 | 0.97 | 1.00 |
| history_ml | 0.39 | 0.55 | 0.77 | 0.90 | 0.94 | 0.97 | 1.00 |
| adaptive_bayes | 0.52 | 0.68 | 0.81 | 0.84 | 0.84 | 0.84 | 0.84 |

Tokens actually spent on those changes (fraction of the full suite):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.020 | 0.049 | 0.100 | 0.199 | 0.299 | 0.497 | 0.971 |
| random | 0.019 | 0.049 | 0.099 | 0.199 | 0.299 | 0.497 | 0.969 |
| declared | 0.011 | 0.024 | 0.042 | 0.064 | 0.079 | 0.091 | 0.091 |
| ir_tfidf | 0.019 | 0.049 | 0.099 | 0.199 | 0.298 | 0.496 | 0.969 |
| observed | 0.017 | 0.046 | 0.089 | 0.159 | 0.220 | 0.314 | 0.472 |
| observed_diverse | 0.018 | 0.047 | 0.089 | 0.160 | 0.221 | 0.315 | 0.472 |
| cost_aware | 0.019 | 0.049 | 0.099 | 0.199 | 0.299 | 0.496 | 0.968 |
| history_ml | 0.019 | 0.049 | 0.099 | 0.199 | 0.299 | 0.497 | 0.968 |
| adaptive_bayes | 0.018 | 0.040 | 0.065 | 0.106 | 0.137 | 0.189 | 0.273 |

![detection vs cost](figures/detection_vs_cost.png)

Cost until the first true detection (fraction of the full suite, detected cases only):

| strategy | cost_to_first_detection |
|---|---|
| full | 0.166 |
| random | 0.140 |
| declared | 0.025 |
| ir_tfidf | 0.026 |
| observed | 0.047 |
| observed_diverse | 0.051 |
| cost_aware | 0.046 |
| history_ml | 0.055 |
| adaptive_bayes | 0.026 |

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
| history_ml | 0.020 | 0.049 | 0.099 | 0.199 | 0.299 | 0.498 | 0.990 |
| adaptive_bayes | 0.013 | 0.033 | 0.066 | 0.112 | 0.145 | 0.212 | 0.338 |

![benign waste](figures/benign_waste.png)

Stop reasons of `adaptive_bayes` (rows: is the change a regression?):

| is_regression | budget | clean | no_components | regression | uninformative |
|---|---|---|---|---|---|
| False | 179 | 90 | 140 | 0 | 11 |
| True | 849 | 320 | 0 | 940 | 61 |

## 4. Prioritization and selection quality

APFD / cost-cognizant APFD of the complete order; selection recall = revealing tests inside the selected subset; selected cost = what that subset costs:

| strategy | apfd | apfdc | selection_recall | selected_cost_fraction |
|---|---|---|---|---|
| full | 0.678 | 0.578 | 1.000 | 1.000 |
| random | 0.491 | 0.500 | 1.000 | 1.000 |
| declared | 0.803 | 0.754 | 0.507 | 0.097 |
| ir_tfidf | 0.801 | 0.821 | 1.000 | 1.000 |
| observed | 0.814 | 0.841 | 1.000 | 0.500 |
| observed_diverse | 0.827 | 0.792 | 1.000 | 0.500 |
| cost_aware | 0.816 | 0.843 | 1.000 | 1.000 |
| history_ml | 0.803 | 0.821 | 1.000 | 1.000 |
| adaptive_bayes | 0.807 | 0.784 | 1.000 | 1.000 |

![apfdc](figures/apfdc.png)

## How to read this

`detected` counts *changes* (one failing revealing test is enough). Compare strategies at equal tokens *spent*, not equal nominal budget: `declared`/`observed` select and run out of tests, `adaptive_bayes` stops when it is confident, the others always spend the whole budget. A good strategy is high in section 2 and low in section 3.
