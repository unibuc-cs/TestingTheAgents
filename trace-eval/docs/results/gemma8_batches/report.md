# TRACE-Eval experiment report

`runs/gemma8_batches` · 180 tests · 66 changes · 5 baseline repetitions · full suite = 2,083,624 tokens · tests failing on the original app: 8 · runs the environment broke, left out: 0

- Recorded with `google/gemma-4-E4B-it` (judge: gemma) at commit `4f780e3`, with uncommitted edits; the original app 5 times, one case at a time; the changed copies 5 times, 32 cases at a time.
- The empty change (the original app, run as the changed copies are): 0 of 180 tests end otherwise than in the baseline; of its 5486 requests, 5218 are the baseline's, 104 of them answered otherwise.

## 1. Ground truth — which changes are revealed by how many tests

| kind of change | changes | revealed by a test | revealing tests of those, median |
|---|---|---|---|
| batch | 23 | 20 | 12 |
| benign | 9 | 0 | 0 |
| code | 10 | 9 | 4 |
| combined | 1 | 1 | 1 |
| config | 7 | 5 | 8 |
| prompt | 2 | 2 | 8 |
| runtime | 3 | 3 | 5 |
| skill | 11 | 8 | 3 |
| all | 66 | 48 | 5 |

Testbed sanity (every change labelled a regression revealed by at least one test, none labelled benign revealed): **VIOLATED**.

## 2. Detection within a budget

Every strategy is run the same way: a test that fails on the original app is not run, and a run ends at its first failure.

Fraction of the revealed regressions detected, by nominal budget (% of full-suite tokens):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.00 | 0.27 | 0.40 | 0.58 | 0.82 | 0.97 | 0.99 |
| random | 0.12 | 0.34 | 0.52 | 0.71 | 0.78 | 0.91 | 1.00 |
| declared | 0.46 | 0.58 | 0.62 | 0.67 | 0.69 | 0.71 | 0.73 |
| ir_tfidf | 0.60 | 0.73 | 0.83 | 0.92 | 0.94 | 0.96 | 1.00 |
| observed | 0.52 | 0.71 | 0.79 | 0.88 | 0.93 | 0.93 | 0.99 |
| observed_diverse | 0.23 | 0.46 | 0.77 | 0.88 | 0.92 | 0.96 | 1.00 |
| cost_aware | 0.50 | 0.71 | 0.81 | 0.88 | 0.92 | 0.93 | 1.00 |
| history_ml | 0.44 | 0.65 | 0.81 | 0.90 | 0.92 | 0.97 | 0.99 |
| casper_slices | 0.31 | 0.46 | 0.57 | 0.75 | 0.80 | 0.84 | 0.99 |
| risk_aware_ts | 0.20 | 0.46 | 0.62 | 0.72 | 0.82 | 0.91 | 1.00 |
| adaptive_bayes | 0.70 | 0.78 | 0.83 | 0.83 | 0.83 | 0.83 | 0.85 |

Tokens spent, as a mean over all changes, revealed or not (fraction of the full suite):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.020 | 0.045 | 0.084 | 0.147 | 0.193 | 0.267 | 0.379 |
| random | 0.019 | 0.043 | 0.078 | 0.134 | 0.179 | 0.254 | 0.372 |
| declared | 0.011 | 0.022 | 0.036 | 0.054 | 0.069 | 0.085 | 0.088 |
| ir_tfidf | 0.015 | 0.031 | 0.054 | 0.088 | 0.119 | 0.179 | 0.290 |
| observed | 0.014 | 0.029 | 0.051 | 0.081 | 0.103 | 0.135 | 0.165 |
| observed_diverse | 0.016 | 0.041 | 0.068 | 0.098 | 0.122 | 0.151 | 0.182 |
| cost_aware | 0.015 | 0.032 | 0.055 | 0.094 | 0.129 | 0.193 | 0.306 |
| history_ml | 0.016 | 0.035 | 0.057 | 0.094 | 0.128 | 0.189 | 0.301 |
| casper_slices | 0.018 | 0.039 | 0.071 | 0.125 | 0.170 | 0.249 | 0.385 |
| risk_aware_ts | 0.018 | 0.042 | 0.073 | 0.125 | 0.169 | 0.244 | 0.364 |
| adaptive_bayes | 0.013 | 0.024 | 0.032 | 0.042 | 0.049 | 0.064 | 0.087 |

At a budget of 5%, over the 48 revealed regressions (intervals: bootstrap over the changes; a difference whose interval holds 0 is not established):

| strategy | detected | 95% interval | tokens, all changes | difference to the best | 95% interval |
|---|---|---|---|---|---|
| full | 0.27 | 0.15 to 0.40 | 0.045 | -0.51 | -0.65 to -0.37 |
| random | 0.34 | 0.25 to 0.43 | 0.043 | -0.44 | -0.55 to -0.33 |
| declared | 0.58 | 0.44 to 0.73 | 0.022 | -0.20 | -0.37 to -0.02 |
| ir_tfidf | 0.73 | 0.60 to 0.85 | 0.031 | -0.05 | -0.19 to +0.09 |
| observed | 0.71 | 0.58 to 0.83 | 0.029 | -0.07 | -0.19 to +0.04 |
| observed_diverse | 0.46 | 0.31 to 0.60 | 0.041 | -0.32 | -0.49 to -0.15 |
| cost_aware | 0.71 | 0.58 to 0.83 | 0.032 | -0.07 | -0.19 to +0.04 |
| history_ml | 0.65 | 0.50 to 0.77 | 0.035 | -0.13 | -0.27 to +0.01 |
| casper_slices | 0.46 | 0.31 to 0.60 | 0.039 | -0.32 | -0.47 to -0.17 |
| risk_aware_ts | 0.46 | 0.35 to 0.57 | 0.042 | -0.32 | -0.46 to -0.18 |
| adaptive_bayes | 0.78 | 0.66 to 0.89 | 0.024 | best |  |

At a budget of 20%, over the 48 revealed regressions (intervals: bootstrap over the changes; a difference whose interval holds 0 is not established):

| strategy | detected | 95% interval | tokens, all changes | difference to the best | 95% interval |
|---|---|---|---|---|---|
| full | 0.58 | 0.44 to 0.71 | 0.147 | -0.33 | -0.48 to -0.19 |
| random | 0.71 | 0.61 to 0.80 | 0.134 | -0.21 | -0.31 to -0.11 |
| declared | 0.67 | 0.52 to 0.79 | 0.054 | -0.25 | -0.38 to -0.12 |
| ir_tfidf | 0.92 | 0.83 to 0.98 | 0.088 | best |  |
| observed | 0.88 | 0.77 to 0.96 | 0.081 | -0.04 | -0.15 to +0.06 |
| observed_diverse | 0.88 | 0.78 to 0.96 | 0.098 | -0.04 | -0.13 to +0.04 |
| cost_aware | 0.88 | 0.77 to 0.96 | 0.094 | -0.04 | -0.15 to +0.06 |
| history_ml | 0.90 | 0.79 to 0.98 | 0.094 | -0.02 | -0.10 to +0.06 |
| casper_slices | 0.75 | 0.63 to 0.86 | 0.125 | -0.17 | -0.27 to -0.07 |
| risk_aware_ts | 0.72 | 0.62 to 0.82 | 0.125 | -0.20 | -0.31 to -0.08 |
| adaptive_bayes | 0.83 | 0.72 to 0.93 | 0.042 | -0.09 | -0.22 to +0.04 |

Tokens spent on the revealed regressions only:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.020 | 0.044 | 0.078 | 0.128 | 0.153 | 0.180 | 0.186 |
| random | 0.018 | 0.041 | 0.069 | 0.109 | 0.134 | 0.163 | 0.177 |
| declared | 0.010 | 0.019 | 0.028 | 0.037 | 0.045 | 0.053 | 0.055 |
| ir_tfidf | 0.013 | 0.024 | 0.036 | 0.047 | 0.054 | 0.064 | 0.071 |
| observed | 0.013 | 0.025 | 0.039 | 0.057 | 0.066 | 0.080 | 0.089 |
| observed_diverse | 0.016 | 0.040 | 0.062 | 0.080 | 0.093 | 0.105 | 0.113 |
| cost_aware | 0.013 | 0.025 | 0.039 | 0.055 | 0.065 | 0.079 | 0.086 |
| history_ml | 0.014 | 0.029 | 0.041 | 0.055 | 0.064 | 0.075 | 0.083 |
| casper_slices | 0.017 | 0.035 | 0.060 | 0.097 | 0.121 | 0.156 | 0.192 |
| risk_aware_ts | 0.018 | 0.039 | 0.062 | 0.097 | 0.120 | 0.148 | 0.164 |
| adaptive_bayes | 0.011 | 0.018 | 0.021 | 0.023 | 0.026 | 0.030 | 0.035 |

Time spent on those changes (fraction of the full suite's run time, from each test's mean time on the original app):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.020 | 0.045 | 0.081 | 0.132 | 0.160 | 0.184 | 0.191 |
| random | 0.018 | 0.042 | 0.071 | 0.111 | 0.136 | 0.165 | 0.179 |
| declared | 0.010 | 0.021 | 0.032 | 0.042 | 0.049 | 0.058 | 0.059 |
| ir_tfidf | 0.014 | 0.025 | 0.038 | 0.051 | 0.058 | 0.067 | 0.073 |
| observed | 0.013 | 0.025 | 0.040 | 0.058 | 0.066 | 0.080 | 0.089 |
| observed_diverse | 0.016 | 0.039 | 0.064 | 0.086 | 0.097 | 0.110 | 0.118 |
| cost_aware | 0.013 | 0.026 | 0.040 | 0.056 | 0.065 | 0.078 | 0.086 |
| history_ml | 0.015 | 0.029 | 0.041 | 0.055 | 0.063 | 0.075 | 0.082 |
| casper_slices | 0.025 | 0.042 | 0.070 | 0.112 | 0.137 | 0.172 | 0.205 |
| risk_aware_ts | 0.018 | 0.043 | 0.067 | 0.103 | 0.127 | 0.155 | 0.170 |
| adaptive_bayes | 0.011 | 0.018 | 0.022 | 0.024 | 0.026 | 0.030 | 0.035 |

Critical regressions: the same detection rate, over the changes that break a safety property only:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.00 | 0.26 | 0.36 | 0.56 | 0.83 | 0.96 | 0.98 |
| random | 0.13 | 0.38 | 0.57 | 0.76 | 0.83 | 0.93 | 1.00 |
| declared | 0.46 | 0.56 | 0.62 | 0.67 | 0.69 | 0.72 | 0.72 |
| ir_tfidf | 0.64 | 0.77 | 0.90 | 0.95 | 0.95 | 0.95 | 1.00 |
| observed | 0.54 | 0.69 | 0.74 | 0.85 | 0.91 | 0.91 | 0.99 |
| observed_diverse | 0.23 | 0.46 | 0.82 | 0.92 | 0.95 | 0.95 | 0.99 |
| cost_aware | 0.51 | 0.69 | 0.77 | 0.85 | 0.90 | 0.92 | 0.99 |
| history_ml | 0.44 | 0.64 | 0.79 | 0.87 | 0.90 | 0.96 | 0.99 |
| casper_slices | 0.36 | 0.54 | 0.64 | 0.83 | 0.83 | 0.85 | 0.98 |
| risk_aware_ts | 0.24 | 0.55 | 0.72 | 0.83 | 0.93 | 0.98 | 0.99 |
| adaptive_bayes | 0.66 | 0.75 | 0.82 | 0.82 | 0.82 | 0.82 | 0.84 |

![detection vs cost](figures/detection_vs_cost.png)

Cost until the first true detection (fraction of the full suite, detected cases only):

| strategy | cost_to_first_detection |
|---|---|
| full | 0.126 |
| random | 0.102 |
| declared | 0.035 |
| ir_tfidf | 0.036 |
| observed | 0.041 |
| observed_diverse | 0.071 |
| cost_aware | 0.041 |
| history_ml | 0.043 |
| casper_slices | 0.084 |
| risk_aware_ts | 0.088 |
| adaptive_bayes | 0.015 |

## 3. Changes no test reveals, and verdicts

Tokens spent on the changes no test reveals:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.020 | 0.049 | 0.100 | 0.199 | 0.300 | 0.500 | 0.894 |
| random | 0.019 | 0.050 | 0.100 | 0.199 | 0.298 | 0.496 | 0.890 |
| declared | 0.012 | 0.029 | 0.056 | 0.100 | 0.133 | 0.169 | 0.176 |
| ir_tfidf | 0.020 | 0.050 | 0.100 | 0.197 | 0.293 | 0.487 | 0.872 |
| observed | 0.017 | 0.040 | 0.082 | 0.145 | 0.201 | 0.279 | 0.366 |
| observed_diverse | 0.016 | 0.043 | 0.084 | 0.145 | 0.199 | 0.275 | 0.363 |
| cost_aware | 0.019 | 0.050 | 0.100 | 0.199 | 0.299 | 0.499 | 0.891 |
| history_ml | 0.020 | 0.050 | 0.100 | 0.200 | 0.298 | 0.493 | 0.883 |
| casper_slices | 0.020 | 0.049 | 0.100 | 0.200 | 0.299 | 0.499 | 0.898 |
| risk_aware_ts | 0.020 | 0.049 | 0.100 | 0.200 | 0.300 | 0.500 | 0.898 |
| adaptive_bayes | 0.017 | 0.038 | 0.061 | 0.090 | 0.112 | 0.157 | 0.226 |

![tokens spent on changes no test reveals](figures/benign_waste.png)

Verdicts at a budget of 5% (shares of the runs):

| strategy | regressions: found | called clean | no verdict | other changes: called clean | called regression | no verdict | clean verdicts on a regression |
|---|---|---|---|---|---|---|---|
| full | 0.27 | 0.00 | 0.73 | 0.00 | 0.00 | 1.00 |  |
| random | 0.34 | 0.00 | 0.66 | 0.00 | 0.00 | 1.00 |  |
| declared | 0.58 | 0.25 | 0.17 | 0.44 | 0.00 | 0.56 | 0.60 |
| ir_tfidf | 0.73 | 0.00 | 0.27 | 0.00 | 0.00 | 1.00 |  |
| observed | 0.71 | 0.00 | 0.29 | 0.17 | 0.00 | 0.83 | 0.00 |
| observed_diverse | 0.46 | 0.00 | 0.54 | 0.17 | 0.00 | 0.83 | 0.00 |
| cost_aware | 0.71 | 0.00 | 0.29 | 0.00 | 0.00 | 1.00 |  |
| history_ml | 0.65 | 0.00 | 0.35 | 0.00 | 0.00 | 1.00 |  |
| casper_slices | 0.46 | 0.00 | 0.54 | 0.00 | 0.00 | 1.00 |  |
| risk_aware_ts | 0.46 | 0.00 | 0.54 | 0.00 | 0.00 | 1.00 |  |
| adaptive_bayes | 0.78 | 0.12 | 0.09 | 0.56 | 0.00 | 0.44 | 0.38 |

Verdicts at a budget of 20% (shares of the runs):

| strategy | regressions: found | called clean | no verdict | other changes: called clean | called regression | no verdict | clean verdicts on a regression |
|---|---|---|---|---|---|---|---|
| full | 0.58 | 0.00 | 0.42 | 0.00 | 0.00 | 1.00 |  |
| random | 0.71 | 0.00 | 0.29 | 0.00 | 0.01 | 0.99 |  |
| declared | 0.67 | 0.25 | 0.08 | 0.67 | 0.00 | 0.33 | 0.50 |
| ir_tfidf | 0.92 | 0.00 | 0.08 | 0.00 | 0.03 | 0.97 |  |
| observed | 0.88 | 0.00 | 0.12 | 0.39 | 0.00 | 0.61 | 0.00 |
| observed_diverse | 0.88 | 0.00 | 0.12 | 0.39 | 0.01 | 0.60 | 0.00 |
| cost_aware | 0.88 | 0.00 | 0.12 | 0.00 | 0.00 | 1.00 |  |
| history_ml | 0.90 | 0.00 | 0.10 | 0.00 | 0.00 | 1.00 |  |
| casper_slices | 0.75 | 0.00 | 0.25 | 0.00 | 0.00 | 1.00 |  |
| risk_aware_ts | 0.72 | 0.00 | 0.28 | 0.00 | 0.00 | 1.00 |  |
| adaptive_bayes | 0.83 | 0.15 | 0.02 | 0.78 | 0.00 | 0.22 | 0.33 |

## 4. Prioritization and selection quality

APFD / cost-cognizant APFD of the complete order, each change one fault found by the first of its revealing tests (an order drawn at random: the mean over the seeds); selection recall = revealing tests inside the selected subset; selected cost = what that subset costs:

| strategy | apfd | apfdc | selection_recall | selected_cost_fraction |
|---|---|---|---|---|
| full | 0.813 | 0.805 | 1.000 | 0.899 |
| random | 0.803 | 0.806 | 1.000 | 0.899 |
| declared | 0.899 | 0.880 | 0.558 | 0.245 |
| ir_tfidf | 0.938 | 0.923 | 1.000 | 0.899 |
| observed | 0.857 | 0.909 | 1.000 | 0.602 |
| observed_diverse | 0.915 | 0.880 | 1.000 | 0.602 |
| cost_aware | 0.861 | 0.910 | 1.000 | 0.899 |
| history_ml | 0.879 | 0.916 | 1.000 | 0.899 |
| casper_slices | 0.778 | 0.803 | 1.000 | 0.899 |
| risk_aware_ts | 0.812 | 0.800 | 1.000 | 0.899 |
| adaptive_bayes | 0.955 | 0.950 | 1.000 | 0.899 |

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
| full | 0.41 | 0.50 | 0.56 | 0.56 | 0.66 | 0.67 | 0.67 |
| random | 0.39 | 0.51 | 0.61 | 0.68 | 0.71 | 0.72 | 0.73 |
| declared | 0.31 | 0.34 | 0.35 | 0.37 | 0.40 | 0.41 | 0.41 |
| ir_tfidf | 0.41 | 0.47 | 0.48 | 0.50 | 0.52 | 0.54 | 0.54 |
| observed | 0.33 | 0.43 | 0.48 | 0.55 | 0.59 | 0.59 | 0.59 |
| observed_diverse | 0.23 | 0.36 | 0.48 | 0.55 | 0.60 | 0.60 | 0.60 |
| cost_aware | 0.33 | 0.44 | 0.49 | 0.56 | 0.59 | 0.59 | 0.59 |
| history_ml | 0.30 | 0.41 | 0.53 | 0.56 | 0.58 | 0.59 | 0.59 |
| casper_slices | 0.41 | 0.41 | 0.47 | 0.52 | 0.58 | 0.59 | 0.61 |
| risk_aware_ts | 0.40 | 0.57 | 0.66 | 0.69 | 0.71 | 0.71 | 0.72 |
| adaptive_bayes | 0.45 | 0.53 | 0.56 | 0.56 | 0.56 | 0.56 | 0.56 |

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
| full | 0.41 | 0.48 | 0.55 | 0.60 | 0.75 | 0.81 | 0.81 |
| random | 0.57 | 0.72 | 0.79 | 0.87 | 0.88 | 0.89 | 0.89 |
| declared | 0.66 | 0.68 | 0.69 | 0.70 | 0.70 | 0.70 | 0.70 |
| ir_tfidf | 0.83 | 0.88 | 0.89 | 0.89 | 0.89 | 0.89 | 0.89 |
| observed | 0.86 | 0.88 | 0.88 | 0.88 | 0.88 | 0.88 | 0.88 |
| observed_diverse | 0.84 | 0.85 | 0.87 | 0.90 | 0.90 | 0.90 | 0.90 |
| cost_aware | 0.85 | 0.88 | 0.88 | 0.88 | 0.88 | 0.88 | 0.88 |
| history_ml | 0.82 | 0.84 | 0.84 | 0.85 | 0.85 | 0.85 | 0.85 |
| casper_slices | 0.43 | 0.78 | 0.82 | 0.82 | 0.82 | 0.84 | 0.86 |
| risk_aware_ts | 0.56 | 0.70 | 0.77 | 0.86 | 0.89 | 0.89 | 0.89 |
| adaptive_bayes | 0.86 | 0.86 | 0.86 | 0.86 | 0.86 | 0.86 | 0.86 |

Affected properties checked:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.26 | 0.38 | 0.46 | 0.49 | 0.55 | 0.62 | 0.64 |
| random | 0.29 | 0.41 | 0.53 | 0.62 | 0.66 | 0.69 | 0.70 |
| declared | 0.21 | 0.25 | 0.27 | 0.29 | 0.31 | 0.31 | 0.32 |
| ir_tfidf | 0.28 | 0.35 | 0.41 | 0.44 | 0.47 | 0.50 | 0.52 |
| observed | 0.23 | 0.31 | 0.37 | 0.49 | 0.52 | 0.53 | 0.54 |
| observed_diverse | 0.21 | 0.39 | 0.50 | 0.57 | 0.60 | 0.61 | 0.62 |
| cost_aware | 0.23 | 0.31 | 0.38 | 0.49 | 0.52 | 0.54 | 0.55 |
| history_ml | 0.26 | 0.37 | 0.45 | 0.52 | 0.53 | 0.55 | 0.56 |
| casper_slices | 0.28 | 0.29 | 0.42 | 0.50 | 0.55 | 0.59 | 0.62 |
| risk_aware_ts | 0.33 | 0.51 | 0.58 | 0.63 | 0.65 | 0.66 | 0.69 |
| adaptive_bayes | 0.29 | 0.41 | 0.44 | 0.45 | 0.46 | 0.46 | 0.47 |

Runs that found no regression and tested every affected mandatory property (the method's step 5):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.03 | 0.04 | 0.04 | 0.05 | 0.08 | 0.23 | 1.00 |
| random | 0.03 | 0.05 | 0.11 | 0.36 | 0.55 | 0.89 | 1.00 |
| declared | 0.07 | 0.11 | 0.11 | 0.12 | 0.27 | 0.25 | 0.23 |
| ir_tfidf | 0.05 | 0.13 | 0.19 | 0.37 | 0.44 | 0.84 | 1.00 |
| observed | 0.05 | 0.09 | 0.18 | 0.25 | 0.72 | 0.72 | 0.72 |
| observed_diverse | 0.04 | 0.11 | 0.17 | 0.75 | 0.77 | 0.75 | 0.72 |
| cost_aware | 0.05 | 0.09 | 0.19 | 0.29 | 0.82 | 0.86 | 1.00 |
| history_ml | 0.04 | 0.09 | 0.19 | 0.52 | 0.72 | 1.00 | 1.00 |
| casper_slices | 0.04 | 0.05 | 0.05 | 0.28 | 0.73 | 0.79 | 1.00 |
| risk_aware_ts | 0.05 | 0.16 | 0.35 | 0.66 | 0.89 | 1.00 | 1.00 |
| adaptive_bayes | 0.09 | 0.53 | 0.77 | 0.88 | 0.96 | 0.96 | 1.00 |

Affected workflows run (the workflows of the tests that exercised a changed component):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.06 | 0.26 |
| random | 0.01 | 0.05 | 0.12 | 0.23 | 0.30 | 0.38 | 0.46 |
| declared | 0.07 | 0.19 | 0.25 | 0.30 | 0.33 | 0.33 | 0.33 |
| ir_tfidf | 0.04 | 0.09 | 0.18 | 0.25 | 0.29 | 0.33 | 0.36 |
| observed | 0.02 | 0.04 | 0.12 | 0.18 | 0.21 | 0.24 | 0.31 |
| observed_diverse | 0.09 | 0.24 | 0.37 | 0.52 | 0.58 | 0.58 | 0.58 |
| cost_aware | 0.02 | 0.04 | 0.12 | 0.18 | 0.21 | 0.24 | 0.32 |
| history_ml | 0.03 | 0.05 | 0.15 | 0.20 | 0.24 | 0.28 | 0.33 |
| casper_slices | 0.00 | 0.00 | 0.12 | 0.27 | 0.34 | 0.40 | 0.48 |
| risk_aware_ts | 0.05 | 0.18 | 0.30 | 0.47 | 0.57 | 0.61 | 0.61 |
| adaptive_bayes | 0.02 | 0.10 | 0.13 | 0.14 | 0.14 | 0.15 | 0.16 |

Affected features reached (the features with a tool or a part the change touches), over the changes that affect one:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.21 | 0.28 | 0.37 | 0.42 | 0.56 | 0.68 | 0.68 |
| random | 0.33 | 0.59 | 0.73 | 0.83 | 0.85 | 0.86 | 0.86 |
| declared | 0.56 | 0.60 | 0.62 | 0.62 | 0.63 | 0.63 | 0.63 |
| ir_tfidf | 0.73 | 0.79 | 0.81 | 0.83 | 0.83 | 0.83 | 0.83 |
| observed | 0.58 | 0.59 | 0.66 | 0.74 | 0.74 | 0.74 | 0.74 |
| observed_diverse | 0.54 | 0.61 | 0.75 | 0.79 | 0.79 | 0.80 | 0.80 |
| cost_aware | 0.56 | 0.59 | 0.67 | 0.74 | 0.74 | 0.74 | 0.74 |
| history_ml | 0.59 | 0.65 | 0.70 | 0.74 | 0.74 | 0.74 | 0.74 |
| casper_slices | 0.19 | 0.55 | 0.70 | 0.76 | 0.77 | 0.81 | 0.82 |
| risk_aware_ts | 0.34 | 0.60 | 0.71 | 0.81 | 0.84 | 0.85 | 0.85 |
| adaptive_bayes | 0.64 | 0.69 | 0.71 | 0.72 | 0.72 | 0.72 | 0.72 |

## 7. Replay-first

Every test was run on every changed copy with the model's calls answered from the answers recorded on the original app (`traceeval replay-first`; no model is called). A test either replays to the end, and its outcome on the changed copy is known for no tokens, or diverges at the first request the original app never made, and needs the model from there on.

What the replay settles alone, by kind of change:

| kind of change | changes | no test diverges | a replayed test fails | diverged tests, mean | their share of the suite's tokens | after the divergence point |
|---|---|---|---|---|---|---|
| batch | 23 | 0 | 0 | 120 of 180 | 0.764 | 0.708 |
| benign | 9 | 4 | 0 | 42 of 180 | 0.283 | 0.250 |
| code | 10 | 1 | 0 | 11 of 180 | 0.109 | 0.069 |
| combined | 1 | 0 | 0 | 2 of 180 | 0.012 | 0.004 |
| config | 7 | 0 | 2 | 40 of 180 | 0.335 | 0.246 |
| prompt | 2 | 0 | 0 | 12 of 180 | 0.098 | 0.079 |
| runtime | 3 | 0 | 1 | 32 of 180 | 0.331 | 0.167 |
| skill | 11 | 0 | 0 | 50 of 180 | 0.382 | 0.325 |
| all | 66 | 5 | 3 | 64 of 180 | 0.439 | 0.382 |

Over the 4208 diverged (change, test) pairs, the change first reaches the model in what an agent is sent up front (its prompt, skills, tools or task) on 3817, and in a tool result on 391.

The replay against the recorded ground truth:

- replayed outcomes that differ from the recorded majority: 0 of 7672;
- the 461 revealing (change, test) pairs: 13 replay to a failure, 448 diverge, 0 replay to a pass;
- revealed regressions with a revealing test that fails in the replay or diverges: 48 of 48;
- changes no test reveals on which a replayed test fails: 0.

The replay against the recorded runs, one by one, over the tests that replay to the end. A run is identical to the replay when it has the same tool calls, final answer, final state and token count:

| recorded runs of | runs | end like the replay | identical to the replay |
|---|---|---|---|
| the original app | 900 | 900 | 887 |
| the original app, run as the changed copies are | 900 | 900 | 818 |
| the changed copies | 38360 | 38360 | 35076 |

The condition itself, a model call being a function of its request, request by request:

| requests of | sent before | of which |
|---|---|---|
| the baseline's repetitions, one test at a time | 914 | 15 (1.64%) got more than one answer |
| the empty change | 5218 | 104 (1.99%) answered otherwise than the cassette |
| the changed copies | 259670 | 5241 (2.02%) answered otherwise than the cassette |

The strategies run replay-first: a test that replays to the end is not run, a replayed failure of a test that passes on the original app ends the run for no tokens, and a diverged test costs its tokens after the divergence point. A run that ends because every diverged test has run and passed is a clean verdict that leaves no reachable test untested.

Fraction of the revealed regressions detected, by nominal budget:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.69 | 0.81 | 0.85 | 0.88 | 0.97 | 1.00 | 1.00 |
| random | 0.62 | 0.76 | 0.85 | 0.92 | 0.93 | 0.97 | 1.00 |
| cheapest | 0.68 | 0.76 | 0.78 | 0.88 | 0.93 | 0.98 | 0.98 |
| late_divergence | 0.67 | 0.81 | 0.85 | 0.90 | 0.94 | 1.00 | 1.00 |
| declared | 0.50 | 0.65 | 0.67 | 0.71 | 0.73 | 0.75 | 0.77 |
| ir_tfidf | 0.81 | 0.85 | 0.94 | 0.96 | 0.96 | 0.96 | 1.00 |
| observed | 0.75 | 0.88 | 0.90 | 0.96 | 0.99 | 0.99 | 0.99 |
| observed_diverse | 0.56 | 0.75 | 0.88 | 0.90 | 0.92 | 0.96 | 1.00 |
| cost_aware | 0.75 | 0.88 | 0.92 | 0.96 | 0.98 | 0.99 | 0.99 |
| history_ml | 0.73 | 0.88 | 0.90 | 0.96 | 0.98 | 0.99 | 0.99 |
| casper_slices | 0.77 | 0.77 | 0.85 | 0.95 | 0.97 | 0.99 | 0.99 |
| risk_aware_ts | 0.67 | 0.81 | 0.88 | 0.94 | 0.95 | 0.98 | 1.00 |
| adaptive_bayes | 0.83 | 0.89 | 0.92 | 0.92 | 0.92 | 0.92 | 0.93 |

Tokens spent, as a mean over all changes (fraction of the full suite):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.010 | 0.021 | 0.035 | 0.057 | 0.072 | 0.093 | 0.115 |
| random | 0.012 | 0.025 | 0.039 | 0.059 | 0.075 | 0.101 | 0.127 |
| cheapest | 0.010 | 0.022 | 0.038 | 0.060 | 0.076 | 0.101 | 0.125 |
| late_divergence | 0.011 | 0.023 | 0.037 | 0.059 | 0.075 | 0.100 | 0.124 |
| declared | 0.010 | 0.019 | 0.031 | 0.046 | 0.061 | 0.072 | 0.075 |
| ir_tfidf | 0.010 | 0.021 | 0.033 | 0.047 | 0.060 | 0.083 | 0.108 |
| observed | 0.010 | 0.020 | 0.033 | 0.051 | 0.064 | 0.083 | 0.107 |
| observed_diverse | 0.012 | 0.028 | 0.043 | 0.063 | 0.081 | 0.108 | 0.136 |
| cost_aware | 0.010 | 0.019 | 0.032 | 0.049 | 0.062 | 0.082 | 0.106 |
| history_ml | 0.010 | 0.020 | 0.033 | 0.050 | 0.062 | 0.081 | 0.105 |
| casper_slices | 0.009 | 0.020 | 0.035 | 0.055 | 0.068 | 0.088 | 0.112 |
| risk_aware_ts | 0.012 | 0.024 | 0.037 | 0.054 | 0.070 | 0.093 | 0.117 |
| adaptive_bayes | 0.008 | 0.014 | 0.019 | 0.024 | 0.029 | 0.038 | 0.048 |

For comparison, a cache of the original app's answers in front of the model, with the whole suite run again and no stop at a failure, pays every diverged test from its divergence point on: 0.382 of the suite's tokens per change (median 0.268), less the requests after that point that the cache also knows. It finds every revealed regression.

The same tests run whole, without the replayed part taken off:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.013 | 0.025 | 0.041 | 0.065 | 0.081 | 0.103 | 0.126 |
| random | 0.015 | 0.031 | 0.047 | 0.069 | 0.087 | 0.113 | 0.139 |
| cheapest | 0.014 | 0.027 | 0.045 | 0.069 | 0.087 | 0.113 | 0.138 |
| late_divergence | 0.020 | 0.037 | 0.053 | 0.075 | 0.091 | 0.117 | 0.141 |
| declared | 0.012 | 0.023 | 0.036 | 0.052 | 0.067 | 0.078 | 0.080 |
| ir_tfidf | 0.012 | 0.025 | 0.039 | 0.057 | 0.070 | 0.093 | 0.118 |
| observed | 0.014 | 0.026 | 0.041 | 0.060 | 0.075 | 0.095 | 0.119 |
| observed_diverse | 0.017 | 0.036 | 0.054 | 0.075 | 0.094 | 0.121 | 0.149 |
| cost_aware | 0.014 | 0.025 | 0.041 | 0.058 | 0.074 | 0.094 | 0.118 |
| history_ml | 0.015 | 0.026 | 0.042 | 0.061 | 0.074 | 0.093 | 0.117 |
| casper_slices | 0.012 | 0.026 | 0.044 | 0.066 | 0.080 | 0.101 | 0.125 |
| risk_aware_ts | 0.016 | 0.031 | 0.046 | 0.066 | 0.082 | 0.105 | 0.130 |
| adaptive_bayes | 0.012 | 0.019 | 0.025 | 0.030 | 0.035 | 0.044 | 0.054 |

At a budget of 5%, over the 48 revealed regressions (intervals: bootstrap over the changes; a difference whose interval holds 0 is not established):

| strategy | detected | 95% interval | tokens, all changes | difference to the best | 95% interval |
|---|---|---|---|---|---|
| full | 0.81 | 0.71 to 0.92 | 0.021 | -0.07 | -0.20 to +0.04 |
| random | 0.76 | 0.66 to 0.86 | 0.025 | -0.12 | -0.22 to -0.04 |
| cheapest | 0.76 | 0.63 to 0.88 | 0.022 | -0.13 | -0.25 to -0.02 |
| late_divergence | 0.81 | 0.69 to 0.92 | 0.023 | -0.07 | -0.19 to +0.04 |
| declared | 0.65 | 0.50 to 0.77 | 0.019 | -0.24 | -0.40 to -0.08 |
| ir_tfidf | 0.85 | 0.75 to 0.94 | 0.021 | -0.03 | -0.13 to +0.06 |
| observed | 0.88 | 0.77 to 0.96 | 0.020 | -0.01 | -0.10 to +0.08 |
| observed_diverse | 0.75 | 0.62 to 0.88 | 0.028 | -0.14 | -0.27 to +0.00 |
| cost_aware | 0.88 | 0.77 to 0.96 | 0.019 | -0.01 | -0.10 to +0.08 |
| history_ml | 0.88 | 0.77 to 0.96 | 0.020 | -0.01 | -0.10 to +0.08 |
| casper_slices | 0.77 | 0.65 to 0.88 | 0.020 | -0.12 | -0.23 to -0.01 |
| risk_aware_ts | 0.81 | 0.70 to 0.90 | 0.024 | -0.08 | -0.18 to +0.01 |
| adaptive_bayes | 0.89 | 0.79 to 0.96 | 0.014 | best |  |

At a budget of 20%, over the 48 revealed regressions (intervals: bootstrap over the changes; a difference whose interval holds 0 is not established):

| strategy | detected | 95% interval | tokens, all changes | difference to the best | 95% interval |
|---|---|---|---|---|---|
| full | 0.88 | 0.77 to 0.96 | 0.057 | -0.08 | -0.17 to -0.02 |
| random | 0.92 | 0.85 to 0.97 | 0.059 | -0.04 | -0.09 to -0.00 |
| cheapest | 0.88 | 0.79 to 0.97 | 0.060 | -0.07 | -0.15 to -0.01 |
| late_divergence | 0.90 | 0.79 to 0.98 | 0.059 | -0.06 | -0.15 to +0.00 |
| declared | 0.71 | 0.58 to 0.83 | 0.046 | -0.25 | -0.38 to -0.12 |
| ir_tfidf | 0.96 | 0.90 to 1.00 | 0.047 | best |  |
| observed | 0.96 | 0.90 to 1.00 | 0.051 | +0.00 | +0.00 to +0.00 |
| observed_diverse | 0.90 | 0.81 to 0.98 | 0.063 | -0.06 | -0.15 to +0.00 |
| cost_aware | 0.96 | 0.90 to 1.00 | 0.049 | +0.00 | +0.00 to +0.00 |
| history_ml | 0.96 | 0.90 to 1.00 | 0.050 | +0.00 | +0.00 to +0.00 |
| casper_slices | 0.95 | 0.90 to 0.99 | 0.055 | -0.00 | -0.05 to +0.05 |
| risk_aware_ts | 0.94 | 0.87 to 0.99 | 0.054 | -0.02 | -0.10 to +0.05 |
| adaptive_bayes | 0.92 | 0.83 to 0.98 | 0.024 | -0.04 | -0.12 to +0.04 |

![replay-first: detection vs cost](figures/replay_first.png)

Verdicts at a budget of 20% (shares of the runs):

| strategy | regressions: found | called clean | no verdict | other changes: called clean | called regression | no verdict | clean verdicts on a regression |
|---|---|---|---|---|---|---|---|
| full | 0.88 | 0.00 | 0.12 | 0.56 | 0.00 | 0.44 | 0.00 |
| random | 0.92 | 0.00 | 0.08 | 0.56 | 0.00 | 0.44 | 0.00 |
| cheapest | 0.90 | 0.00 | 0.10 | 0.56 | 0.00 | 0.44 | 0.00 |
| late_divergence | 0.90 | 0.00 | 0.10 | 0.56 | 0.00 | 0.44 | 0.00 |
| declared | 0.71 | 0.21 | 0.08 | 0.67 | 0.00 | 0.33 | 0.45 |
| ir_tfidf | 0.96 | 0.00 | 0.04 | 0.56 | 0.03 | 0.41 | 0.00 |
| observed | 0.96 | 0.00 | 0.04 | 0.56 | 0.00 | 0.44 | 0.00 |
| observed_diverse | 0.90 | 0.00 | 0.10 | 0.56 | 0.01 | 0.43 | 0.00 |
| cost_aware | 0.96 | 0.00 | 0.04 | 0.56 | 0.00 | 0.44 | 0.00 |
| history_ml | 0.96 | 0.00 | 0.04 | 0.56 | 0.00 | 0.44 | 0.00 |
| casper_slices | 0.96 | 0.00 | 0.04 | 0.56 | 0.00 | 0.44 | 0.00 |
| risk_aware_ts | 0.94 | 0.00 | 0.06 | 0.56 | 0.01 | 0.43 | 0.00 |
| adaptive_bayes | 0.92 | 0.06 | 0.02 | 0.89 | 0.00 | 0.11 | 0.16 |

Verdicts at a budget of 100% (shares of the runs):

| strategy | regressions: found | called clean | no verdict | other changes: called clean | called regression | no verdict | clean verdicts on a regression |
|---|---|---|---|---|---|---|---|
| full | 1.00 | 0.00 | 0.00 | 0.98 | 0.02 | 0.00 | 0.01 |
| random | 1.00 | 0.00 | 0.00 | 0.99 | 0.01 | 0.00 | 0.00 |
| cheapest | 1.00 | 0.00 | 0.00 | 0.98 | 0.02 | 0.00 | 0.01 |
| late_divergence | 1.00 | 0.00 | 0.00 | 0.98 | 0.02 | 0.00 | 0.01 |
| declared | 0.77 | 0.23 | 0.00 | 1.00 | 0.00 | 0.00 | 0.38 |
| ir_tfidf | 1.00 | 0.00 | 0.00 | 0.97 | 0.03 | 0.00 | 0.01 |
| observed | 0.99 | 0.01 | 0.00 | 0.98 | 0.02 | 0.00 | 0.02 |
| observed_diverse | 1.00 | 0.00 | 0.00 | 0.99 | 0.01 | 0.00 | 0.01 |
| cost_aware | 0.99 | 0.01 | 0.00 | 0.98 | 0.02 | 0.00 | 0.02 |
| history_ml | 0.99 | 0.01 | 0.00 | 0.98 | 0.02 | 0.00 | 0.02 |
| casper_slices | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0.01 |
| risk_aware_ts | 1.00 | 0.00 | 0.00 | 0.99 | 0.01 | 0.00 | 0.00 |
| adaptive_bayes | 0.93 | 0.06 | 0.01 | 0.89 | 0.00 | 0.11 | 0.16 |

## How to read this

`detected` counts *changes* (one failing revealing test is enough). Compare strategies at equal tokens *spent*, not equal nominal budget: every run ends at its first failure, the selecting strategies also run out of tests, and `adaptive_bayes` also stops when it is confident. A good strategy is high in the first table of section 2 and low in the second. The sample is the changes: the seeds only draw which recorded run answers a test and the choices of the strategies that draw at random, so an interval is over the changes. A clean verdict is worth what the last column of the verdict tables says.

Section 7 reads like section 2, with the replay in front: compare a strategy's row there with its row here. Replay-first, a strategy that orders the whole suite gives a clean verdict once every diverged test has run and passed; that verdict holds as far as the replay agrees with the recording, which the first lines of the section measure.
