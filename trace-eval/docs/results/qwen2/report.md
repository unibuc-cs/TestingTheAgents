# TRACE-Eval experiment report

`runs/qwen2` · 136 tests · 33 changes · 3 baseline repetitions · full suite = 1,080,378 tokens · tests failing on the original app: 1

## 1. Ground truth — which changes are revealed by how many tests

| change | category | expected | revealing tests |
|---|---|---|---|
| `benign_code_comment_docstring` | benign | benign | 0 |
| `benign_code_rename_locals` | benign | benign | 0 |
| `benign_config_comments_reordered` | benign | benign | 0 |
| `benign_new_unused_tool` | benign | benign | 0 |
| `benign_orchestrator_prompt_wording` | benign | benign | 0 |
| `benign_skill_prose_reflow` | benign | benign | 0 |
| `benign_translation_intents_reordered` | benign | benign | 0 |
| `code_approval_gate_bypass` | code | regression | 1 |
| `code_edit_keeps_review` | code | regression | 1 |
| `code_get_page_review_flag` | code | regression | 15 |
| `code_links_external_lenient` | code | regression | 6 |
| `code_metadata_arg_swap` | code | regression | 5 |
| `code_retry_drop_idempotency` | code | regression | 5 |
| `combined_seo_keyword_limit` | combined | regression | 1 |
| `config_default_agent_publishing` | config | regression | 3 |
| `config_disable_validate_links` | config | regression | 43 |
| `config_max_tool_calls_5` | config | regression | 8 |
| `config_require_review_false` | config | regression | 3 |
| `config_retries_0` | config | regression | 5 |
| `config_seo_title_20` | config | regression | 1 |
| `prompt_governance_consent_tool_removed` | prompt | regression | 4 |
| `prompt_seo_tool_removed` | prompt | regression | 5 |
| `code_delegation_truncates_answer` | runtime | regression | 6 |
| `code_termination_off_by_six` | runtime | regression | 2 |
| `skill_authoring_drop_metadata` | skill | regression | 1 |
| `skill_governance_drop_consent` | skill | regression | 5 |
| `skill_linkval_ignore_assets` | skill | regression | 1 |
| `skill_publish_drop_link_validation` | skill | regression | 1 |
| `skill_publish_drop_permission_check` | skill | regression | 3 |
| `skill_rollback_drop_permission_check` | skill | regression | 1 |
| `skill_rollback_restores_latest` | skill | regression | 2 |
| `skill_seo_drop_length_guard` | skill | regression | 1 |
| `skill_translation_wrong_default` | skill | regression | 2 |

Testbed sanity (every regression revealed by ≥1 test, no benign change revealed): **OK**.

## 2. Detection within a budget

Fraction of regression-inducing changes detected, by nominal budget (% of full-suite tokens):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.00 | 0.08 | 0.19 | 0.50 | 0.54 | 0.77 | 1.00 |
| random | 0.07 | 0.15 | 0.33 | 0.52 | 0.64 | 0.78 | 1.00 |
| declared | 0.45 | 0.58 | 0.65 | 0.65 | 0.65 | 0.65 | 0.65 |
| ir_tfidf | 0.50 | 0.73 | 0.81 | 0.88 | 0.96 | 1.00 | 1.00 |
| observed | 0.42 | 0.54 | 0.65 | 0.85 | 0.92 | 0.96 | 1.00 |
| cost_aware | 0.38 | 0.54 | 0.65 | 0.85 | 0.92 | 0.96 | 1.00 |
| adaptive_bayes | 0.35 | 0.46 | 0.58 | 0.65 | 0.65 | 0.69 | 0.73 |

Tokens actually spent on those changes (fraction of the full suite):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.020 | 0.050 | 0.099 | 0.199 | 0.299 | 0.499 | 0.993 |
| random | 0.019 | 0.049 | 0.099 | 0.199 | 0.299 | 0.499 | 0.991 |
| declared | 0.011 | 0.027 | 0.044 | 0.067 | 0.080 | 0.089 | 0.089 |
| ir_tfidf | 0.019 | 0.049 | 0.099 | 0.199 | 0.299 | 0.499 | 0.990 |
| observed | 0.017 | 0.047 | 0.085 | 0.150 | 0.206 | 0.293 | 0.425 |
| cost_aware | 0.019 | 0.049 | 0.099 | 0.199 | 0.299 | 0.498 | 0.990 |
| adaptive_bayes | 0.016 | 0.031 | 0.047 | 0.061 | 0.069 | 0.081 | 0.082 |

![detection vs cost](figures/detection_vs_cost.png)

Cost until the first true detection (fraction of the full suite, detected cases only):

| strategy | cost_to_first_detection |
|---|---|
| full | 0.193 |
| random | 0.165 |
| declared | 0.018 |
| ir_tfidf | 0.041 |
| observed | 0.059 |
| cost_aware | 0.061 |
| adaptive_bayes | 0.045 |

## 3. Benign changes — wasted budget and stopping

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.020 | 0.050 | 0.099 | 0.199 | 0.299 | 0.499 | 0.999 |
| random | 0.019 | 0.049 | 0.099 | 0.199 | 0.299 | 0.499 | 0.995 |
| declared | 0.008 | 0.021 | 0.042 | 0.072 | 0.089 | 0.108 | 0.108 |
| ir_tfidf | 0.019 | 0.049 | 0.098 | 0.198 | 0.298 | 0.498 | 0.995 |
| observed | 0.011 | 0.033 | 0.056 | 0.090 | 0.120 | 0.154 | 0.196 |
| cost_aware | 0.019 | 0.049 | 0.099 | 0.199 | 0.299 | 0.498 | 0.989 |
| adaptive_bayes | 0.014 | 0.027 | 0.048 | 0.084 | 0.113 | 0.170 | 0.251 |

![benign waste](figures/benign_waste.png)

Stop reasons of `adaptive_bayes` (rows: is the change a regression?):

| is_regression | budget | clean | no_components | regression | uninformative |
|---|---|---|---|---|---|
| False | 75 | 95 | 70 | 0 | 5 |
| True | 190 | 185 | 0 | 535 | 0 |

## 4. Prioritization and selection quality

APFD / cost-cognizant APFD of the complete order; selection recall = revealing tests inside the selected subset; selected cost = what that subset costs:

| strategy | apfd | apfdc | selection_recall | selected_cost_fraction |
|---|---|---|---|---|
| full | 0.689 | 0.583 | 1.000 | 1.000 |
| random | 0.443 | 0.440 | 1.000 | 1.000 |
| declared | 0.846 | 0.801 | 0.520 | 0.093 |
| ir_tfidf | 0.788 | 0.799 | 1.000 | 1.000 |
| observed | 0.814 | 0.834 | 1.000 | 0.430 |
| cost_aware | 0.813 | 0.833 | 1.000 | 1.000 |
| adaptive_bayes | 0.787 | 0.760 | 1.000 | 1.000 |

![apfdc](figures/apfdc.png)

## How to read this

`detected` counts *changes* (one failing revealing test is enough). Compare strategies at equal tokens *spent*, not equal nominal budget: `declared`/`observed` select and run out of tests, `adaptive_bayes` stops when it is confident, the others always spend the whole budget. A good strategy is high in section 2 and low in section 3.
