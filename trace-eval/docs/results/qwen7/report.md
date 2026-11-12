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

Fraction of regression-inducing changes detected, by nominal budget (% of full-suite tokens):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.00 | 0.12 | 0.79 | 0.84 | 0.85 | 0.98 | 1.00 |
| random | 0.13 | 0.28 | 0.45 | 0.64 | 0.80 | 0.93 | 1.00 |
| declared | 0.28 | 0.38 | 0.37 | 0.46 | 0.47 | 0.47 | 0.48 |
| ir_tfidf | 0.37 | 0.53 | 0.67 | 0.75 | 0.82 | 0.93 | 1.00 |
| observed | 0.38 | 0.49 | 0.57 | 0.69 | 0.74 | 0.83 | 0.90 |
| cost_aware | 0.31 | 0.49 | 0.53 | 0.67 | 0.73 | 0.83 | 1.00 |
| casper_slices | 0.16 | 0.19 | 0.80 | 0.90 | 0.99 | 1.00 | 1.00 |
| risk_aware_ts | 0.07 | 0.28 | 0.45 | 0.67 | 0.80 | 0.92 | 1.00 |
| adaptive_bayes | 0.54 | 0.67 | 0.75 | 0.75 | 0.75 | 0.75 | 0.75 |

Tokens actually spent on those changes (fraction of the full suite):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.020 | 0.050 | 0.100 | 0.200 | 0.300 | 0.500 | 0.936 |
| random | 0.020 | 0.050 | 0.100 | 0.200 | 0.300 | 0.500 | 0.933 |
| declared | 0.011 | 0.025 | 0.044 | 0.069 | 0.088 | 0.109 | 0.109 |
| ir_tfidf | 0.020 | 0.050 | 0.100 | 0.200 | 0.300 | 0.499 | 0.936 |
| observed | 0.018 | 0.042 | 0.083 | 0.146 | 0.201 | 0.294 | 0.417 |
| cost_aware | 0.020 | 0.050 | 0.100 | 0.199 | 0.299 | 0.499 | 0.936 |
| casper_slices | 0.020 | 0.050 | 0.100 | 0.200 | 0.300 | 0.500 | 0.937 |
| risk_aware_ts | 0.020 | 0.050 | 0.100 | 0.200 | 0.300 | 0.500 | 0.938 |
| adaptive_bayes | 0.011 | 0.018 | 0.022 | 0.026 | 0.030 | 0.035 | 0.038 |

Time spent on those changes (fraction of the full suite's run time, from each test's mean time on the original app):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.020 | 0.049 | 0.099 | 0.197 | 0.279 | 0.473 | 1.000 |
| random | 0.019 | 0.050 | 0.104 | 0.211 | 0.318 | 0.536 | 1.000 |
| declared | 0.013 | 0.030 | 0.054 | 0.085 | 0.105 | 0.126 | 0.126 |
| ir_tfidf | 0.019 | 0.050 | 0.109 | 0.226 | 0.334 | 0.540 | 1.000 |
| observed | 0.017 | 0.042 | 0.088 | 0.153 | 0.206 | 0.310 | 0.468 |
| cost_aware | 0.020 | 0.050 | 0.109 | 0.214 | 0.314 | 0.507 | 1.000 |
| casper_slices | 0.022 | 0.055 | 0.110 | 0.246 | 0.377 | 0.568 | 1.000 |
| risk_aware_ts | 0.021 | 0.062 | 0.126 | 0.256 | 0.381 | 0.598 | 1.000 |
| adaptive_bayes | 0.012 | 0.019 | 0.023 | 0.028 | 0.031 | 0.035 | 0.038 |

Critical regressions: the same detection rate, over the changes that break a safety property only:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.00 | 0.12 | 0.79 | 0.84 | 0.85 | 0.98 | 1.00 |
| random | 0.13 | 0.28 | 0.45 | 0.64 | 0.80 | 0.93 | 1.00 |
| declared | 0.28 | 0.38 | 0.37 | 0.46 | 0.47 | 0.47 | 0.48 |
| ir_tfidf | 0.37 | 0.53 | 0.67 | 0.75 | 0.82 | 0.93 | 1.00 |
| observed | 0.38 | 0.49 | 0.57 | 0.69 | 0.74 | 0.83 | 0.90 |
| cost_aware | 0.31 | 0.49 | 0.53 | 0.67 | 0.73 | 0.83 | 1.00 |
| casper_slices | 0.16 | 0.19 | 0.80 | 0.90 | 0.99 | 1.00 | 1.00 |
| risk_aware_ts | 0.07 | 0.28 | 0.45 | 0.67 | 0.80 | 0.92 | 1.00 |
| adaptive_bayes | 0.54 | 0.67 | 0.75 | 0.75 | 0.75 | 0.75 | 0.75 |

![detection vs cost](figures/detection_vs_cost.png)

Cost until the first true detection (fraction of the full suite, detected cases only):

| strategy | cost_to_first_detection |
|---|---|
| full | 0.083 |
| random | 0.112 |
| declared | 0.039 |
| ir_tfidf | 0.067 |
| observed | 0.064 |
| cost_aware | 0.084 |
| casper_slices | 0.068 |
| risk_aware_ts | 0.106 |
| adaptive_bayes | 0.016 |

## 3. Changes no test reveals — wasted budget and stopping

| strategy |
|---|

![tokens spent on changes no test reveals](figures/benign_waste.png)

Stop reasons of `adaptive_bayes` (rows: is the change a regression?):

| is_regression | budget | clean | no_components | regression | uninformative |
|---|---|---|---|---|---|
| True | 92 | 278 | 70 | 1049 | 16 |

## 4. Prioritization and selection quality

APFD / cost-cognizant APFD of the complete order; selection recall = revealing tests inside the selected subset; selected cost = what that subset costs:

| strategy | apfd | apfdc | selection_recall | selected_cost_fraction |
|---|---|---|---|---|
| full | 0.619 | 0.494 | 1.000 | 1.000 |
| random | 0.523 | 0.491 | 1.000 | 1.000 |
| declared | 0.675 | 0.575 | 0.246 | 0.121 |
| ir_tfidf | 0.621 | 0.615 | 1.000 | 1.000 |
| observed | 0.634 | 0.606 | 0.705 | 0.461 |
| cost_aware | 0.479 | 0.542 | 1.000 | 1.000 |
| casper_slices | 0.693 | 0.634 | 1.000 | 1.000 |
| risk_aware_ts | 0.527 | 0.585 | 1.000 | 1.000 |
| adaptive_bayes | 0.632 | 0.616 | 1.000 | 1.000 |

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
| full | 0.27 | 0.29 | 0.42 | 0.43 | 0.62 | 1.00 | 1.00 |
| random | 0.32 | 0.50 | 0.71 | 0.85 | 0.92 | 0.97 | 1.00 |
| declared | 0.29 | 0.38 | 0.41 | 0.41 | 0.42 | 0.42 | 0.42 |
| ir_tfidf | 0.32 | 0.46 | 0.66 | 0.79 | 0.82 | 0.95 | 1.00 |
| observed | 0.24 | 0.38 | 0.55 | 0.80 | 0.84 | 0.85 | 0.88 |
| cost_aware | 0.30 | 0.41 | 0.59 | 0.84 | 0.90 | 0.94 | 1.00 |
| casper_slices | 0.26 | 0.61 | 0.68 | 0.85 | 0.91 | 0.99 | 1.00 |
| risk_aware_ts | 0.42 | 0.69 | 0.78 | 0.84 | 0.86 | 0.88 | 1.00 |
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
| full | 0.37 | 0.49 | 0.59 | 0.68 | 0.85 | 0.97 | 0.97 |
| random | 0.62 | 0.75 | 0.87 | 0.94 | 0.96 | 0.97 | 0.97 |
| declared | 0.65 | 0.67 | 0.67 | 0.67 | 0.67 | 0.67 | 0.67 |
| ir_tfidf | 0.92 | 0.97 | 0.94 | 0.97 | 0.97 | 0.97 | 0.97 |
| observed | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 |
| cost_aware | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 |
| casper_slices | 0.61 | 0.78 | 0.87 | 0.97 | 0.97 | 0.97 | 0.97 |
| risk_aware_ts | 0.60 | 0.75 | 0.85 | 0.92 | 0.96 | 0.97 | 0.97 |
| adaptive_bayes | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 |

Affected properties checked:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.29 | 0.40 | 0.51 | 0.55 | 0.68 | 1.00 | 1.00 |
| random | 0.33 | 0.48 | 0.67 | 0.82 | 0.89 | 0.96 | 1.00 |
| declared | 0.25 | 0.34 | 0.37 | 0.39 | 0.42 | 0.43 | 0.43 |
| ir_tfidf | 0.36 | 0.52 | 0.69 | 0.80 | 0.85 | 0.94 | 1.00 |
| observed | 0.34 | 0.51 | 0.67 | 0.87 | 0.92 | 0.95 | 1.00 |
| cost_aware | 0.37 | 0.55 | 0.68 | 0.86 | 0.92 | 0.97 | 1.00 |
| casper_slices | 0.29 | 0.56 | 0.68 | 0.81 | 0.85 | 0.96 | 1.00 |
| risk_aware_ts | 0.40 | 0.59 | 0.70 | 0.79 | 0.83 | 0.90 | 1.00 |
| adaptive_bayes | 0.30 | 0.37 | 0.40 | 0.40 | 0.40 | 0.40 | 0.40 |

Runs that found no regression and tested every affected mandatory property (the method's step 5):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 1.00 | 1.00 |
| random | 0.06 | 0.06 | 0.15 | 0.42 | 0.68 | 0.94 | 1.00 |
| declared | 0.12 | 0.20 | 0.23 | 0.26 | 0.33 | 0.33 | 0.33 |
| ir_tfidf | 0.05 | 0.13 | 0.33 | 0.44 | 0.51 | 0.72 | 1.00 |
| observed | 0.09 | 0.21 | 0.48 | 0.78 | 0.82 | 0.94 | 1.00 |
| cost_aware | 0.16 | 0.21 | 0.54 | 0.77 | 0.82 | 0.93 | 1.00 |
| casper_slices | 0.05 | 0.05 | 0.19 | 1.00 | 1.00 | 1.00 | 1.00 |
| risk_aware_ts | 0.07 | 0.16 | 0.38 | 0.80 | 0.96 | 1.00 | 1.00 |
| adaptive_bayes | 0.21 | 0.63 | 0.95 | 1.00 | 1.00 | 1.00 | 1.00 |

Affected workflows run (the workflows of the tests that exercised a changed component):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.25 | 1.00 |
| random | 0.03 | 0.08 | 0.20 | 0.42 | 0.61 | 0.85 | 1.00 |
| declared | 0.15 | 0.26 | 0.35 | 0.39 | 0.43 | 0.43 | 0.43 |
| ir_tfidf | 0.03 | 0.21 | 0.43 | 0.64 | 0.74 | 0.84 | 1.00 |
| observed | 0.07 | 0.24 | 0.42 | 0.55 | 0.62 | 0.77 | 1.00 |
| cost_aware | 0.15 | 0.27 | 0.49 | 0.61 | 0.70 | 0.81 | 1.00 |
| casper_slices | 0.00 | 0.11 | 0.24 | 0.88 | 0.98 | 1.00 | 1.00 |
| risk_aware_ts | 0.09 | 0.26 | 0.48 | 0.80 | 0.95 | 1.00 | 1.00 |
| adaptive_bayes | 0.03 | 0.09 | 0.10 | 0.10 | 0.10 | 0.10 | 0.10 |

Affected features reached (the features with a tool or a part the change touches), over the changes that affect one:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.13 | 0.29 | 0.41 | 0.52 | 0.79 | 1.00 | 1.00 |
| random | 0.37 | 0.64 | 0.87 | 0.96 | 0.98 | 0.99 | 1.00 |
| declared | 0.61 | 0.63 | 0.66 | 0.67 | 0.70 | 0.70 | 0.70 |
| ir_tfidf | 0.88 | 0.94 | 0.95 | 0.98 | 1.00 | 1.00 | 1.00 |
| observed | 0.73 | 0.76 | 0.87 | 1.00 | 1.00 | 1.00 | 1.00 |
| cost_aware | 0.77 | 0.77 | 0.90 | 1.00 | 1.00 | 1.00 | 1.00 |
| casper_slices | 0.27 | 0.60 | 0.87 | 0.97 | 0.99 | 1.00 | 1.00 |
| risk_aware_ts | 0.36 | 0.70 | 0.85 | 0.93 | 0.99 | 1.00 | 1.00 |
| adaptive_bayes | 0.82 | 0.84 | 0.85 | 0.85 | 0.85 | 0.85 | 0.85 |

## How to read this

`detected` counts *changes* (one failing revealing test is enough). Compare strategies at equal tokens *spent*, not equal nominal budget: `declared`/`observed` select and run out of tests, `adaptive_bayes` stops when it is confident, the others always spend the whole budget. A good strategy is high in section 2 and low in section 3.
