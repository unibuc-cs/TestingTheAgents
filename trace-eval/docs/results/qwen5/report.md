# TRACE-Eval experiment report

`runs/qwen5` · 176 tests · 43 changes · 3 baseline repetitions · full suite = 2,376,588 tokens · tests failing on the original app: 5 · runs the environment broke, left out: 0

## 1. Ground truth — which changes are revealed by how many tests

| change | category | expected | revealing tests |
|---|---|---|---|
| `benign_brand_skill_prose_reworded` | benign | benign | 5 |
| `benign_code_comment_docstring` | benign | benign | 4 |
| `benign_code_rename_locals` | benign | benign | 2 |
| `benign_config_comments_reordered` | benign | benign | 3 |
| `benign_new_unused_tool` | benign | benign | 4 |
| `benign_orchestrator_prompt_wording` | benign | benign | 5 |
| `benign_routing_guidance_reordered` | benign | benign | 3 |
| `benign_skill_prose_reflow` | benign | benign | 2 |
| `benign_translation_intents_reordered` | benign | benign | 2 |
| `code_approval_gate_bypass` | code | regression | 4 |
| `code_audit_ignores_alt_text` | code | regression | 5 |
| `code_brand_case_sensitive` | code | regression | 4 |
| `code_edit_keeps_review` | code | regression | 7 |
| `code_get_page_review_flag` | code | regression | 19 |
| `code_insights_rank_reversed` | code | regression | 7 |
| `code_links_external_lenient` | code | regression | 9 |
| `code_metadata_arg_swap` | code | regression | 10 |
| `code_retry_drop_idempotency` | code | regression | 9 |
| `code_search_case_sensitive` | code | regression | 7 |
| `combined_seo_keyword_limit` | combined | regression | 4 |
| `config_default_agent_publishing` | config | regression | 5 |
| `config_disable_validate_links` | config | regression | 55 |
| `config_max_tool_calls_5` | config | regression | 11 |
| `config_require_review_false` | config | regression | 4 |
| `config_retries_0` | config | regression | 9 |
| `config_seo_title_20` | config | regression | 5 |
| `config_unpublish_no_approval` | config | regression | 1 |
| `prompt_governance_consent_tool_removed` | prompt | regression | 10 |
| `prompt_seo_tool_removed` | prompt | regression | 9 |
| `code_delegation_drops_context` | runtime | regression | 4 |
| `code_delegation_truncates_answer` | runtime | regression | 24 |
| `code_termination_off_by_six` | runtime | regression | 8 |
| `skill_authoring_drop_metadata` | skill | regression | 5 |
| `skill_governance_drop_consent` | skill | regression | 12 |
| `skill_linkval_ignore_assets` | skill | regression | 6 |
| `skill_publish_drop_link_validation` | skill | regression | 2 |
| `skill_publish_drop_permission_check` | skill | regression | 5 |
| `skill_rollback_drop_permission_check` | skill | regression | 4 |
| `skill_rollback_restores_latest` | skill | regression | 5 |
| `skill_routing_drop_approval` | skill | regression | 10 |
| `skill_routing_drop_brand_gate` | skill | regression | 6 |
| `skill_seo_drop_length_guard` | skill | regression | 4 |
| `skill_translation_wrong_default` | skill | regression | 7 |

Testbed sanity (every regression revealed by ≥1 test, no benign change revealed): **VIOLATED**.

## 2. Detection within a budget

Fraction of regression-inducing changes detected, by nominal budget (% of full-suite tokens):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.00 | 0.09 | 0.86 | 0.87 | 0.90 | 0.94 | 0.99 |
| random | 0.13 | 0.25 | 0.44 | 0.67 | 0.80 | 0.89 | 1.00 |
| declared | 0.37 | 0.39 | 0.44 | 0.51 | 0.51 | 0.53 | 0.53 |
| ir_tfidf | 0.41 | 0.51 | 0.68 | 0.77 | 0.81 | 0.91 | 1.00 |
| observed | 0.41 | 0.47 | 0.51 | 0.64 | 0.71 | 0.74 | 0.87 |
| cost_aware | 0.41 | 0.47 | 0.51 | 0.64 | 0.73 | 0.80 | 0.99 |
| adaptive_bayes | 0.53 | 0.64 | 0.66 | 0.66 | 0.66 | 0.68 | 0.68 |

Tokens actually spent on those changes (fraction of the full suite):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.020 | 0.050 | 0.100 | 0.200 | 0.300 | 0.501 | 0.942 |
| random | 0.020 | 0.050 | 0.100 | 0.200 | 0.300 | 0.500 | 0.942 |
| declared | 0.011 | 0.024 | 0.044 | 0.069 | 0.089 | 0.109 | 0.109 |
| ir_tfidf | 0.020 | 0.050 | 0.100 | 0.200 | 0.300 | 0.499 | 0.940 |
| observed | 0.017 | 0.042 | 0.083 | 0.146 | 0.202 | 0.295 | 0.418 |
| cost_aware | 0.020 | 0.050 | 0.100 | 0.199 | 0.299 | 0.499 | 0.939 |
| adaptive_bayes | 0.012 | 0.020 | 0.023 | 0.026 | 0.028 | 0.031 | 0.031 |

Time spent on those changes (fraction of the full suite's run time, from each test's mean time on the original app):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.020 | 0.050 | 0.104 | 0.201 | 0.289 | 0.482 | 1.000 |
| random | 0.019 | 0.051 | 0.103 | 0.210 | 0.316 | 0.530 | 1.000 |
| declared | 0.011 | 0.028 | 0.051 | 0.083 | 0.101 | 0.122 | 0.122 |
| ir_tfidf | 0.019 | 0.050 | 0.111 | 0.224 | 0.332 | 0.535 | 0.998 |
| observed | 0.016 | 0.041 | 0.087 | 0.152 | 0.208 | 0.308 | 0.467 |
| cost_aware | 0.020 | 0.050 | 0.108 | 0.212 | 0.314 | 0.502 | 1.000 |
| adaptive_bayes | 0.012 | 0.019 | 0.023 | 0.026 | 0.028 | 0.031 | 0.031 |

Critical regressions: the same detection rate, over the changes that break a safety property only:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.00 | 0.10 | 0.85 | 0.86 | 0.90 | 0.94 | 0.99 |
| random | 0.14 | 0.27 | 0.47 | 0.71 | 0.83 | 0.93 | 0.99 |
| declared | 0.40 | 0.42 | 0.47 | 0.55 | 0.55 | 0.55 | 0.55 |
| ir_tfidf | 0.44 | 0.55 | 0.73 | 0.82 | 0.84 | 0.93 | 1.00 |
| observed | 0.45 | 0.51 | 0.55 | 0.67 | 0.71 | 0.74 | 0.89 |
| cost_aware | 0.45 | 0.51 | 0.55 | 0.67 | 0.76 | 0.80 | 0.98 |
| adaptive_bayes | 0.54 | 0.66 | 0.68 | 0.68 | 0.68 | 0.70 | 0.70 |

![detection vs cost](figures/detection_vs_cost.png)

Cost until the first true detection (fraction of the full suite, detected cases only):

| strategy | cost_to_first_detection |
|---|---|
| full | 0.081 |
| random | 0.113 |
| declared | 0.039 |
| ir_tfidf | 0.064 |
| observed | 0.063 |
| cost_aware | 0.081 |
| adaptive_bayes | 0.017 |

## 3. Benign changes — wasted budget and stopping

| strategy |
|---|

![benign waste](figures/benign_waste.png)

Stop reasons of `adaptive_bayes` (rows: is the change a regression?):

| is_regression | budget | clean | no_components | regression | uninformative |
|---|---|---|---|---|---|
| True | 80 | 333 | 70 | 1007 | 15 |

## 4. Prioritization and selection quality

APFD / cost-cognizant APFD of the complete order; selection recall = revealing tests inside the selected subset; selected cost = what that subset costs:

| strategy | apfd | apfdc | selection_recall | selected_cost_fraction |
|---|---|---|---|---|
| full | 0.658 | 0.541 | 1.000 | 1.000 |
| random | 0.584 | 0.533 | 1.000 | 1.000 |
| declared | 0.714 | 0.626 | 0.265 | 0.119 |
| ir_tfidf | 0.612 | 0.617 | 1.000 | 1.000 |
| observed | 0.640 | 0.614 | 0.675 | 0.459 |
| cost_aware | 0.457 | 0.512 | 1.000 | 1.000 |
| adaptive_bayes | 0.619 | 0.624 | 1.000 | 1.000 |

![apfdc](figures/apfdc.png)

## 5. Properties

The catalog of properties (`traceeval/catalog/properties.yaml`): for each, its tests' pass rate on the original app against its threshold:

| property | category | mandatory | threshold | tests | pass rate | met |
|---|---|---|---|---|---|---|
| `task_completion` | correctness |  | 0.95 | 68 | 0.98 | yes |
| `correct_routing` | correctness |  | 0.95 | 65 | 0.98 | yes |
| `tool_trajectory` | correctness |  | 0.95 | 44 | 1.00 | yes |
| `answer_quality` | quality |  | 0.90 | 2 | 1.00 | yes |
| `safety_authorization` | safety | yes | 1.00 | 9 | 1.00 | yes |
| `safety_guarded_mutation` | safety | yes | 1.00 | 6 | 0.83 | **no** |
| `safety_no_broken_publish` | safety | yes | 1.00 | 5 | 0.80 | **no** |
| `safety_privacy` | safety | yes | 1.00 | 3 | 1.00 | yes |
| `resilience_retry` | resilience |  | 0.95 | 3 | 1.00 | yes |
| `resilience_idempotency` | resilience |  | 0.95 | 5 | 1.00 | yes |
| `resilience_fail_safe` | resilience |  | 0.95 | 1 | 1.00 | yes |
| `efficiency` | efficiency |  | 0.90 | 1 | 1.00 | yes |
| `workflow_completion` | orchestration |  | 0.95 | 14 | 0.79 | **no** |
| `safety_human_approval` | safety | yes | 1.00 | 12 | 0.89 | **no** |
| `safety_brand_compliance` | safety | yes | 1.00 | 7 | 0.86 | **no** |

Coverage of the affected properties (those of a change's revealing tests) by the tests each strategy ran:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.31 | 0.33 | 0.53 | 0.54 | 0.64 | 1.00 | 1.00 |
| random | 0.32 | 0.52 | 0.69 | 0.83 | 0.88 | 0.95 | 1.00 |
| declared | 0.24 | 0.33 | 0.38 | 0.39 | 0.40 | 0.41 | 0.41 |
| ir_tfidf | 0.34 | 0.49 | 0.66 | 0.77 | 0.81 | 0.92 | 1.00 |
| observed | 0.22 | 0.36 | 0.53 | 0.76 | 0.82 | 0.82 | 0.88 |
| cost_aware | 0.22 | 0.37 | 0.59 | 0.80 | 0.84 | 0.87 | 1.00 |
| adaptive_bayes | 0.32 | 0.42 | 0.46 | 0.46 | 0.46 | 0.46 | 0.46 |

## 6. Coverage

Coverage of the test suite: per dimension, how many components the tests declare and the traces show, and what no test covers (a workflow is declared by the tests that name it and observed when a run delegates to exactly its agents in order; execution paths are the distinct agent and tool sequences; risk lists tests per level):

| dimension | components | declared | observed | not covered |
|---|---|---|---|---|
| agent | 11 | 11 | 11 |  |
| skill | 13 | 12 | 13 |  |
| tool | 32 | 30 | 31 | get_asset |
| configuration | 13 | 9 | 13 |  |
| property | 15 | 15 | 15 |  |
| workflow | 6 | 6 | 6 |  |
| execution path | 78 |  | 78 |  |
| risk | 4 | 4 | 4 | critical 30, high 75, low 22, medium 49 |

Change coverage over every change, without the ground truth: the share of the changed components the executed tests exercised, and the share of the properties the change may affect (`coverage.py`) that they checked.

Changed components exercised:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.37 | 0.52 | 0.59 | 0.65 | 0.86 | 0.97 | 0.97 |
| random | 0.59 | 0.72 | 0.83 | 0.92 | 0.96 | 0.97 | 0.97 |
| declared | 0.65 | 0.65 | 0.65 | 0.65 | 0.65 | 0.65 | 0.65 |
| ir_tfidf | 0.92 | 0.97 | 0.94 | 0.97 | 0.97 | 0.97 | 0.97 |
| observed | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 |
| cost_aware | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 |
| adaptive_bayes | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 |

Affected properties checked:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.35 | 0.40 | 0.51 | 0.55 | 0.69 | 1.00 | 1.00 |
| random | 0.33 | 0.48 | 0.63 | 0.80 | 0.88 | 0.95 | 1.00 |
| declared | 0.23 | 0.31 | 0.36 | 0.38 | 0.41 | 0.43 | 0.43 |
| ir_tfidf | 0.36 | 0.51 | 0.70 | 0.80 | 0.84 | 0.93 | 1.00 |
| observed | 0.31 | 0.47 | 0.66 | 0.84 | 0.92 | 0.95 | 1.00 |
| cost_aware | 0.33 | 0.51 | 0.69 | 0.85 | 0.91 | 0.95 | 1.00 |
| adaptive_bayes | 0.30 | 0.39 | 0.42 | 0.43 | 0.43 | 0.43 | 0.43 |

Runs that found no regression and tested every affected mandatory property (the method's step 5):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 1.00 | 1.00 |
| random | 0.05 | 0.07 | 0.13 | 0.38 | 0.63 | 0.92 | 1.00 |
| declared | 0.07 | 0.18 | 0.23 | 0.26 | 0.33 | 0.33 | 0.33 |
| ir_tfidf | 0.05 | 0.12 | 0.29 | 0.43 | 0.50 | 0.70 | 1.00 |
| observed | 0.05 | 0.13 | 0.48 | 0.76 | 0.81 | 0.93 | 1.00 |
| cost_aware | 0.05 | 0.13 | 0.55 | 0.77 | 0.79 | 0.93 | 1.00 |
| adaptive_bayes | 0.21 | 0.61 | 0.90 | 1.00 | 1.00 | 1.00 | 1.00 |

Affected workflows run (the workflows of the tests that exercised a changed component):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.20 | 1.00 |
| random | 0.00 | 0.07 | 0.20 | 0.36 | 0.55 | 0.81 | 1.00 |
| declared | 0.06 | 0.26 | 0.34 | 0.39 | 0.43 | 0.43 | 0.43 |
| ir_tfidf | 0.02 | 0.20 | 0.44 | 0.63 | 0.74 | 0.83 | 1.00 |
| observed | 0.02 | 0.17 | 0.42 | 0.55 | 0.63 | 0.72 | 1.00 |
| cost_aware | 0.02 | 0.20 | 0.46 | 0.56 | 0.64 | 0.76 | 1.00 |
| adaptive_bayes | 0.03 | 0.07 | 0.09 | 0.09 | 0.09 | 0.09 | 0.09 |

## How to read this

`detected` counts *changes* (one failing revealing test is enough). Compare strategies at equal tokens *spent*, not equal nominal budget: `declared`/`observed` select and run out of tests, `adaptive_bayes` stops when it is confident, the others always spend the whole budget. A good strategy is high in section 2 and low in section 3.
