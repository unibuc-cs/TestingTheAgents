# TRACE-Eval experiment report

`runs/qwen8_gen` · 180 tests · 691 changes (342 evaluated, the rest learnt from) · 5 baseline repetitions · full suite = 2,309,051 tokens · tests failing on the original app: 8 · runs the environment broke, left out: 0

- Recorded with `Qwen/Qwen3.8-27B-FP8` (judge: qwen) at commit `2c44605`, with uncommitted edits; the original app 5 times, one case at a time; the changed copies 1 times, 2 cases at a time.
- The empty change (the original app, run as the changed copies are): 0 of 180 tests end otherwise than in the baseline; of its 5310 requests, 5310 are the baseline's, 0 of them answered otherwise.

## 1. Ground truth — which changes are revealed by how many tests

| kind of change | changes | revealed by a test | revealing tests of those, median |
|---|---|---|---|
| agentdesc | 11 | 10 | 2 |
| argswap | 12 | 12 | 6 |
| comment | 32 | 0 | 0 |
| condnot | 119 | 107 | 10 |
| fixture | 85 | 28 | 2 |
| guarddel | 4 | 4 | 1 |
| paramdesc | 53 | 17 | 2 |
| promptdel | 30 | 8 | 2 |
| rewrap | 13 | 4 | 1 |
| ruledel | 18 | 13 | 2 |
| setting | 65 | 50 | 5 |
| stepdel | 76 | 32 | 1 |
| stepswap | 63 | 17 | 1 |
| tooldesc | 32 | 8 | 2 |
| tooldrop | 50 | 45 | 4 |
| whennot | 28 | 2 | 1 |
| all | 691 | 357 | 3 |

None of these changes has a label: 357 of 691 are revealed by a test.

## 2. Detection within a budget

Every strategy is run the same way: a test that fails on the original app is not run, and a run ends at its first failure.

Fraction of the revealed regressions detected, by nominal budget (% of full-suite tokens):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.20 | 0.22 | 0.50 | 0.57 | 0.73 | 0.92 | 1.00 |
| random | 0.19 | 0.30 | 0.40 | 0.58 | 0.68 | 0.84 | 1.00 |
| declared | 0.22 | 0.32 | 0.37 | 0.47 | 0.48 | 0.48 | 0.48 |
| ir_tfidf | 0.43 | 0.63 | 0.75 | 0.84 | 0.88 | 0.93 | 1.00 |
| observed | 0.44 | 0.58 | 0.66 | 0.77 | 0.82 | 0.95 | 1.00 |
| observed_diverse | 0.45 | 0.59 | 0.64 | 0.81 | 0.84 | 0.93 | 1.00 |
| cost_aware | 0.44 | 0.58 | 0.66 | 0.78 | 0.82 | 0.95 | 1.00 |
| history_ml | 0.46 | 0.60 | 0.67 | 0.76 | 0.82 | 0.96 | 1.00 |
| casper_slices | 0.19 | 0.31 | 0.39 | 0.51 | 0.65 | 0.77 | 1.00 |
| risk_aware_ts | 0.18 | 0.29 | 0.44 | 0.59 | 0.68 | 0.79 | 1.00 |
| adaptive_bayes | 0.61 | 0.68 | 0.72 | 0.80 | 0.82 | 0.84 | 0.87 |

Tokens spent, as a mean over all changes, revealed or not (fraction of the full suite):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.018 | 0.045 | 0.085 | 0.156 | 0.220 | 0.330 | 0.526 |
| random | 0.018 | 0.044 | 0.085 | 0.158 | 0.224 | 0.341 | 0.548 |
| declared | 0.009 | 0.019 | 0.032 | 0.049 | 0.058 | 0.067 | 0.067 |
| ir_tfidf | 0.017 | 0.038 | 0.069 | 0.126 | 0.178 | 0.279 | 0.476 |
| observed | 0.014 | 0.031 | 0.057 | 0.099 | 0.132 | 0.178 | 0.228 |
| observed_diverse | 0.015 | 0.034 | 0.063 | 0.106 | 0.138 | 0.182 | 0.233 |
| cost_aware | 0.016 | 0.037 | 0.071 | 0.131 | 0.187 | 0.293 | 0.488 |
| history_ml | 0.016 | 0.038 | 0.070 | 0.130 | 0.188 | 0.292 | 0.488 |
| casper_slices | 0.018 | 0.045 | 0.085 | 0.162 | 0.229 | 0.351 | 0.572 |
| risk_aware_ts | 0.018 | 0.045 | 0.085 | 0.157 | 0.224 | 0.343 | 0.556 |
| adaptive_bayes | 0.014 | 0.031 | 0.057 | 0.106 | 0.147 | 0.219 | 0.325 |

At a budget of 5%, over the 186 revealed regressions (intervals: bootstrap over the changes; a difference whose interval holds 0 is not established):

| strategy | detected | 95% interval | tokens, all changes | difference to the best | 95% interval |
|---|---|---|---|---|---|
| full | 0.22 | 0.16 to 0.27 | 0.045 | -0.47 | -0.55 to -0.39 |
| random | 0.30 | 0.25 to 0.35 | 0.044 | -0.38 | -0.45 to -0.32 |
| declared | 0.32 | 0.26 to 0.39 | 0.019 | -0.36 | -0.44 to -0.27 |
| ir_tfidf | 0.63 | 0.56 to 0.70 | 0.038 | -0.05 | -0.13 to +0.02 |
| observed | 0.58 | 0.51 to 0.65 | 0.031 | -0.10 | -0.17 to -0.04 |
| observed_diverse | 0.59 | 0.52 to 0.66 | 0.034 | -0.09 | -0.16 to -0.03 |
| cost_aware | 0.58 | 0.51 to 0.65 | 0.037 | -0.10 | -0.17 to -0.04 |
| history_ml | 0.60 | 0.53 to 0.67 | 0.038 | -0.09 | -0.15 to -0.02 |
| casper_slices | 0.31 | 0.24 to 0.37 | 0.045 | -0.38 | -0.45 to -0.30 |
| risk_aware_ts | 0.29 | 0.24 to 0.34 | 0.045 | -0.39 | -0.46 to -0.32 |
| adaptive_bayes | 0.68 | 0.61 to 0.75 | 0.031 | best |  |

At a budget of 20%, over the 186 revealed regressions (intervals: bootstrap over the changes; a difference whose interval holds 0 is not established):

| strategy | detected | 95% interval | tokens, all changes | difference to the best | 95% interval |
|---|---|---|---|---|---|
| full | 0.57 | 0.49 to 0.64 | 0.156 | -0.27 | -0.36 to -0.19 |
| random | 0.58 | 0.52 to 0.63 | 0.158 | -0.27 | -0.33 to -0.21 |
| declared | 0.47 | 0.40 to 0.54 | 0.049 | -0.37 | -0.45 to -0.28 |
| ir_tfidf | 0.84 | 0.79 to 0.89 | 0.126 | best |  |
| observed | 0.77 | 0.72 to 0.83 | 0.099 | -0.07 | -0.13 to -0.02 |
| observed_diverse | 0.81 | 0.75 to 0.87 | 0.106 | -0.03 | -0.09 to +0.03 |
| cost_aware | 0.78 | 0.72 to 0.84 | 0.131 | -0.06 | -0.12 to -0.01 |
| history_ml | 0.76 | 0.69 to 0.82 | 0.130 | -0.09 | -0.14 to -0.03 |
| casper_slices | 0.51 | 0.44 to 0.58 | 0.162 | -0.33 | -0.40 to -0.26 |
| risk_aware_ts | 0.59 | 0.53 to 0.64 | 0.157 | -0.26 | -0.33 to -0.19 |
| adaptive_bayes | 0.80 | 0.74 to 0.85 | 0.106 | -0.04 | -0.11 to +0.02 |

Tokens spent on the revealed regressions only:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.017 | 0.041 | 0.073 | 0.119 | 0.152 | 0.189 | 0.199 |
| random | 0.017 | 0.040 | 0.072 | 0.122 | 0.160 | 0.208 | 0.239 |
| declared | 0.008 | 0.016 | 0.022 | 0.028 | 0.028 | 0.029 | 0.029 |
| ir_tfidf | 0.014 | 0.028 | 0.044 | 0.064 | 0.077 | 0.094 | 0.106 |
| observed | 0.013 | 0.027 | 0.046 | 0.074 | 0.094 | 0.121 | 0.130 |
| observed_diverse | 0.014 | 0.031 | 0.054 | 0.086 | 0.103 | 0.127 | 0.138 |
| cost_aware | 0.013 | 0.028 | 0.047 | 0.073 | 0.094 | 0.121 | 0.130 |
| history_ml | 0.013 | 0.028 | 0.045 | 0.072 | 0.094 | 0.119 | 0.128 |
| casper_slices | 0.017 | 0.040 | 0.072 | 0.130 | 0.171 | 0.227 | 0.283 |
| risk_aware_ts | 0.017 | 0.040 | 0.072 | 0.122 | 0.160 | 0.212 | 0.255 |
| adaptive_bayes | 0.011 | 0.020 | 0.032 | 0.050 | 0.059 | 0.068 | 0.073 |

Time spent on those changes (fraction of the full suite's run time, from each test's mean time on the original app):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.017 | 0.040 | 0.072 | 0.117 | 0.147 | 0.181 | 0.193 |
| random | 0.017 | 0.039 | 0.071 | 0.120 | 0.157 | 0.205 | 0.236 |
| declared | 0.008 | 0.017 | 0.024 | 0.030 | 0.031 | 0.031 | 0.031 |
| ir_tfidf | 0.014 | 0.028 | 0.044 | 0.064 | 0.078 | 0.095 | 0.107 |
| observed | 0.011 | 0.025 | 0.046 | 0.076 | 0.094 | 0.121 | 0.130 |
| observed_diverse | 0.014 | 0.033 | 0.058 | 0.093 | 0.109 | 0.131 | 0.142 |
| cost_aware | 0.012 | 0.026 | 0.047 | 0.075 | 0.093 | 0.121 | 0.129 |
| history_ml | 0.012 | 0.026 | 0.045 | 0.074 | 0.095 | 0.119 | 0.128 |
| casper_slices | 0.017 | 0.043 | 0.077 | 0.136 | 0.177 | 0.231 | 0.284 |
| risk_aware_ts | 0.018 | 0.043 | 0.076 | 0.127 | 0.166 | 0.218 | 0.257 |
| adaptive_bayes | 0.010 | 0.020 | 0.032 | 0.049 | 0.057 | 0.066 | 0.072 |

Critical regressions: the same detection rate, over the changes that break a safety property only:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.26 | 0.23 | 0.52 | 0.58 | 0.70 | 0.90 | 1.00 |
| random | 0.27 | 0.40 | 0.51 | 0.71 | 0.80 | 0.92 | 1.00 |
| declared | 0.22 | 0.28 | 0.33 | 0.46 | 0.46 | 0.46 | 0.46 |
| ir_tfidf | 0.47 | 0.63 | 0.78 | 0.87 | 0.90 | 0.98 | 1.00 |
| observed | 0.48 | 0.54 | 0.62 | 0.76 | 0.80 | 0.97 | 1.00 |
| observed_diverse | 0.49 | 0.60 | 0.68 | 0.94 | 0.94 | 0.96 | 1.00 |
| cost_aware | 0.48 | 0.54 | 0.62 | 0.77 | 0.80 | 0.97 | 1.00 |
| history_ml | 0.48 | 0.56 | 0.64 | 0.77 | 0.81 | 0.98 | 1.00 |
| casper_slices | 0.28 | 0.41 | 0.51 | 0.69 | 0.78 | 0.83 | 1.00 |
| risk_aware_ts | 0.26 | 0.41 | 0.60 | 0.80 | 0.91 | 0.99 | 1.00 |
| adaptive_bayes | 0.60 | 0.69 | 0.73 | 0.84 | 0.86 | 0.88 | 0.90 |

![detection vs cost](figures/detection_vs_cost.png)

Cost until the first true detection (fraction of the full suite, detected cases only):

| strategy | cost_to_first_detection |
|---|---|
| full | 0.116 |
| random | 0.122 |
| declared | 0.041 |
| ir_tfidf | 0.050 |
| observed | 0.060 |
| observed_diverse | 0.070 |
| cost_aware | 0.060 |
| history_ml | 0.059 |
| casper_slices | 0.133 |
| risk_aware_ts | 0.122 |
| adaptive_bayes | 0.027 |

## 3. Changes no test reveals, and verdicts

Tokens spent on the changes no test reveals:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.020 | 0.050 | 0.099 | 0.199 | 0.300 | 0.499 | 0.916 |
| random | 0.020 | 0.050 | 0.100 | 0.200 | 0.300 | 0.500 | 0.916 |
| declared | 0.010 | 0.024 | 0.043 | 0.074 | 0.093 | 0.112 | 0.112 |
| ir_tfidf | 0.019 | 0.049 | 0.099 | 0.199 | 0.299 | 0.499 | 0.916 |
| observed | 0.015 | 0.036 | 0.071 | 0.130 | 0.177 | 0.247 | 0.346 |
| observed_diverse | 0.016 | 0.037 | 0.073 | 0.131 | 0.179 | 0.247 | 0.346 |
| cost_aware | 0.019 | 0.049 | 0.099 | 0.199 | 0.299 | 0.499 | 0.916 |
| history_ml | 0.020 | 0.050 | 0.099 | 0.199 | 0.299 | 0.499 | 0.916 |
| casper_slices | 0.020 | 0.050 | 0.100 | 0.200 | 0.299 | 0.500 | 0.916 |
| risk_aware_ts | 0.020 | 0.050 | 0.100 | 0.200 | 0.300 | 0.500 | 0.916 |
| adaptive_bayes | 0.017 | 0.043 | 0.087 | 0.173 | 0.253 | 0.399 | 0.624 |

![tokens spent on changes no test reveals](figures/benign_waste.png)

Verdicts at a budget of 5% (shares of the runs):

| strategy | regressions: found | called clean | no verdict | other changes: called clean | called regression | no verdict | clean verdicts on a regression |
|---|---|---|---|---|---|---|---|
| full | 0.22 | 0.00 | 0.78 | 0.00 | 0.00 | 1.00 |  |
| random | 0.30 | 0.00 | 0.70 | 0.00 | 0.00 | 1.00 |  |
| declared | 0.32 | 0.51 | 0.17 | 0.59 | 0.00 | 0.41 | 0.51 |
| ir_tfidf | 0.63 | 0.00 | 0.37 | 0.00 | 0.00 | 1.00 |  |
| observed | 0.58 | 0.00 | 0.42 | 0.28 | 0.00 | 0.72 | 0.00 |
| observed_diverse | 0.59 | 0.00 | 0.41 | 0.28 | 0.00 | 0.72 | 0.00 |
| cost_aware | 0.58 | 0.00 | 0.42 | 0.00 | 0.00 | 1.00 |  |
| history_ml | 0.60 | 0.00 | 0.40 | 0.00 | 0.00 | 1.00 |  |
| casper_slices | 0.31 | 0.00 | 0.69 | 0.00 | 0.00 | 1.00 |  |
| risk_aware_ts | 0.29 | 0.00 | 0.71 | 0.00 | 0.00 | 1.00 |  |
| adaptive_bayes | 0.68 | 0.05 | 0.27 | 0.13 | 0.00 | 0.87 | 0.30 |

Verdicts at a budget of 20% (shares of the runs):

| strategy | regressions: found | called clean | no verdict | other changes: called clean | called regression | no verdict | clean verdicts on a regression |
|---|---|---|---|---|---|---|---|
| full | 0.57 | 0.00 | 0.43 | 0.00 | 0.00 | 1.00 |  |
| random | 0.58 | 0.00 | 0.42 | 0.00 | 0.00 | 1.00 |  |
| declared | 0.47 | 0.52 | 0.01 | 0.78 | 0.00 | 0.22 | 0.44 |
| ir_tfidf | 0.84 | 0.00 | 0.16 | 0.00 | 0.00 | 1.00 |  |
| observed | 0.77 | 0.00 | 0.23 | 0.51 | 0.00 | 0.49 | 0.00 |
| observed_diverse | 0.81 | 0.00 | 0.19 | 0.51 | 0.00 | 0.49 | 0.00 |
| cost_aware | 0.78 | 0.00 | 0.22 | 0.00 | 0.00 | 1.00 |  |
| history_ml | 0.76 | 0.00 | 0.24 | 0.00 | 0.00 | 1.00 |  |
| casper_slices | 0.51 | 0.00 | 0.49 | 0.00 | 0.00 | 1.00 |  |
| risk_aware_ts | 0.59 | 0.00 | 0.41 | 0.00 | 0.00 | 1.00 |  |
| adaptive_bayes | 0.80 | 0.09 | 0.11 | 0.17 | 0.00 | 0.83 | 0.38 |

## 4. Prioritization and selection quality

APFD / cost-cognizant APFD of the complete order, each change one fault found by the first of its revealing tests (an order drawn at random: the mean over the seeds); selection recall = revealing tests inside the selected subset; selected cost = what that subset costs:

| strategy | apfd | apfdc | selection_recall | selected_cost_fraction |
|---|---|---|---|---|
| full | 0.803 | 0.786 | 1.000 | 0.917 |
| random | 0.741 | 0.742 | 1.000 | 0.917 |
| declared | 0.899 | 0.880 | 0.401 | 0.100 |
| ir_tfidf | 0.897 | 0.887 | 1.000 | 0.917 |
| observed | 0.802 | 0.861 | 1.000 | 0.508 |
| observed_diverse | 0.910 | 0.854 | 1.000 | 0.508 |
| cost_aware | 0.803 | 0.861 | 1.000 | 0.917 |
| history_ml | 0.814 | 0.863 | 1.000 | 0.917 |
| casper_slices | 0.677 | 0.702 | 1.000 | 0.917 |
| risk_aware_ts | 0.728 | 0.707 | 1.000 | 0.917 |
| adaptive_bayes | 0.885 | 0.889 | 1.000 | 0.917 |

![apfdc](figures/apfdc.png)

## 5. Properties

The catalog of properties (`traceeval/catalog/properties.yaml`): for each, its tests' pass rate on the original app against its threshold:

| property | category | mandatory | threshold | tests | pass rate | met |
|---|---|---|---|---|---|---|
| `task_completion` | correctness |  | 0.95 | 71 | 0.92 | **no** |
| `correct_routing` | correctness |  | 0.95 | 65 | 1.00 | yes |
| `tool_trajectory` | correctness |  | 0.95 | 45 | 0.98 | yes |
| `answer_quality` | quality |  | 0.90 | 2 | 0.00 | **no** |
| `safety_authorization` | safety | yes | 1.00 | 9 | 1.00 | yes |
| `safety_guarded_mutation` | safety | yes | 1.00 | 6 | 0.83 | **no** |
| `safety_no_broken_publish` | safety | yes | 1.00 | 6 | 0.50 | **no** |
| `safety_privacy` | safety | yes | 1.00 | 3 | 1.00 | yes |
| `resilience_retry` | resilience |  | 0.95 | 3 | 1.00 | yes |
| `resilience_idempotency` | resilience |  | 0.95 | 5 | 1.00 | yes |
| `resilience_fail_safe` | resilience |  | 0.95 | 3 | 1.00 | yes |
| `efficiency` | efficiency |  | 0.90 | 1 | 1.00 | yes |
| `workflow_completion` | orchestration |  | 0.95 | 15 | 0.73 | **no** |
| `safety_human_approval` | safety | yes | 1.00 | 13 | 0.77 | **no** |
| `safety_brand_compliance` | safety | yes | 1.00 | 7 | 1.00 | yes |

Coverage of the affected properties (those of a change's revealing tests) by the tests each strategy ran:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.52 | 0.52 | 0.54 | 0.55 | 0.55 | 0.63 | 0.64 |
| random | 0.44 | 0.58 | 0.68 | 0.74 | 0.76 | 0.77 | 0.78 |
| declared | 0.32 | 0.36 | 0.37 | 0.37 | 0.37 | 0.37 | 0.37 |
| ir_tfidf | 0.50 | 0.59 | 0.66 | 0.67 | 0.67 | 0.67 | 0.68 |
| observed | 0.35 | 0.38 | 0.43 | 0.63 | 0.64 | 0.65 | 0.65 |
| observed_diverse | 0.30 | 0.41 | 0.63 | 0.63 | 0.69 | 0.70 | 0.70 |
| cost_aware | 0.35 | 0.38 | 0.44 | 0.63 | 0.64 | 0.65 | 0.65 |
| history_ml | 0.32 | 0.38 | 0.43 | 0.58 | 0.65 | 0.65 | 0.65 |
| casper_slices | 0.21 | 0.51 | 0.69 | 0.70 | 0.74 | 0.75 | 0.75 |
| risk_aware_ts | 0.44 | 0.68 | 0.76 | 0.78 | 0.80 | 0.81 | 0.81 |
| adaptive_bayes | 0.36 | 0.46 | 0.52 | 0.60 | 0.60 | 0.60 | 0.60 |

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
| workflow | 6 | 6 | 5 |  |
| execution path | 73 |  | 73 |  |
| risk | 4 | 4 | 4 | critical 32, high 77, low 22, medium 49 |

Per component: how many tests declare it in their metadata, and how many invoke it in their recorded runs. A component few tests invoke is thinly covered. A difference between the two counts is where the hand-written metadata and the runs disagree.

| agent | declared | invoked |
|---|---|---|
| assets | 37 | 17 |
| authoring | 46 | 28 |
| brand | 12 | 12 |
| governance | 32 | 12 |
| insights | 6 | 6 |
| maintenance | 7 | 7 |
| optimizer | 6 | 6 |
| orchestrator | 67 | 153 |
| publishing | 63 | 44 |
| seo | 11 | 11 |
| translation | 35 | 14 |

| skill | declared | invoked |
|---|---|---|
| asset-management | 35 | 17 |
| brand-governance | 9 | 12 |
| data-insights | 6 | 6 |
| governance-checks | 0 | 120 |
| governance-ops | 32 | 12 |
| link-validation | 5 | 72 |
| page-authoring | 44 | 28 |
| publishing-workflow | 62 | 44 |
| rollback | 7 | 7 |
| routing | 67 | 153 |
| seo-metadata | 11 | 11 |
| site-optimization | 6 | 6 |
| translation | 34 | 14 |

| tool | declared | invoked |
|---|---|---|
| approve_review | 7 | 8 |
| attach_asset | 8 | 12 |
| audit_site | 4 | 4 |
| check_brand_policy | 6 | 7 |
| check_consent | 5 | 8 |
| check_permission | 9 | 112 |
| create_page | 11 | 15 |
| create_translation_job | 9 | 11 |
| export_user_data | 7 | 4 |
| fix_alt_text | 2 | 1 |
| get_asset | 0 | 0 |
| get_audit_log | 1 | 3 |
| get_brand_guidelines | 1 | 1 |
| get_page | 2 | 79 |
| get_page_metrics | 6 | 6 |
| get_seo_report | 2 | 9 |
| get_translation_status | 1 | 2 |
| list_versions | 2 | 6 |
| make_plan | 13 | 15 |
| publish_page | 29 | 18 |
| request_approval | 14 | 12 |
| request_review | 4 | 6 |
| rollback_page | 7 | 5 |
| route_to_agent | 0 | 153 |
| schedule_publish | 6 | 5 |
| search_assets | 2 | 5 |
| search_pages | 3 | 4 |
| set_page_metadata | 12 | 22 |
| unpublish_page | 7 | 7 |
| update_page_content | 10 | 24 |
| upload_asset | 4 | 5 |
| validate_links | 18 | 57 |

| feature | declared | invoked |
|---|---|---|
| show a page | 2 | 79 |
| create or edit a page | 20 | 25 |
| request and approve a page's review | 11 | 14 |
| publish a page | 29 | 18 |
| schedule a page | 6 | 5 |
| take a page down | 7 | 7 |
| check a page's links | 18 | 57 |
| set a page's SEO metadata | 12 | 23 |
| translate a page | 10 | 13 |
| upload, find and attach assets | 11 | 14 |
| check pages against the brand rules and find the pages that use a term | 10 | 12 |
| run a site health check and fix alt text | 6 | 5 |
| read page analytics | 6 | 6 |
| roll a page back to an earlier version | 7 | 6 |
| answer a privacy request (consent, data export) and show the audit history | 8 | 11 |
| refuse what the user may not do | 9 | 112 |
| hand a request to the specialist that owns it | 0 | 153 |
| plan a request that needs several specialists | 13 | 15 |
| ask a person before publishing, scheduling or taking pages down | 14 | 12 |

Change coverage over every change, without the ground truth: the share of the changed components the executed tests exercised, and the share of the properties the change may affect (`coverage.py`) that they checked.

Changed components exercised:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.49 | 0.51 | 0.62 | 0.71 | 0.90 | 0.98 | 0.98 |
| random | 0.57 | 0.72 | 0.81 | 0.89 | 0.93 | 0.96 | 0.98 |
| declared | 0.65 | 0.65 | 0.66 | 0.66 | 0.66 | 0.66 | 0.66 |
| ir_tfidf | 0.96 | 0.98 | 0.98 | 0.98 | 0.98 | 0.98 | 0.98 |
| observed | 0.98 | 0.98 | 0.98 | 0.98 | 0.98 | 0.98 | 0.98 |
| observed_diverse | 0.97 | 0.97 | 0.97 | 0.98 | 0.98 | 0.98 | 0.98 |
| cost_aware | 0.98 | 0.98 | 0.98 | 0.98 | 0.98 | 0.98 | 0.98 |
| history_ml | 0.96 | 0.97 | 0.98 | 0.98 | 0.98 | 0.98 | 0.98 |
| casper_slices | 0.60 | 0.78 | 0.81 | 0.89 | 0.90 | 0.96 | 0.98 |
| risk_aware_ts | 0.56 | 0.70 | 0.79 | 0.86 | 0.89 | 0.92 | 0.98 |
| adaptive_bayes | 0.90 | 0.94 | 0.96 | 0.97 | 0.98 | 0.98 | 0.98 |

Affected properties checked:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.34 | 0.40 | 0.45 | 0.48 | 0.51 | 0.65 | 0.69 |
| random | 0.31 | 0.44 | 0.57 | 0.68 | 0.73 | 0.76 | 0.78 |
| declared | 0.23 | 0.29 | 0.32 | 0.35 | 0.35 | 0.36 | 0.36 |
| ir_tfidf | 0.32 | 0.41 | 0.50 | 0.57 | 0.61 | 0.65 | 0.67 |
| observed | 0.28 | 0.35 | 0.40 | 0.58 | 0.62 | 0.64 | 0.65 |
| observed_diverse | 0.27 | 0.44 | 0.52 | 0.58 | 0.64 | 0.67 | 0.68 |
| cost_aware | 0.29 | 0.35 | 0.41 | 0.61 | 0.65 | 0.67 | 0.68 |
| history_ml | 0.27 | 0.34 | 0.42 | 0.62 | 0.66 | 0.67 | 0.68 |
| casper_slices | 0.24 | 0.40 | 0.63 | 0.69 | 0.75 | 0.77 | 0.79 |
| risk_aware_ts | 0.37 | 0.55 | 0.65 | 0.72 | 0.75 | 0.77 | 0.79 |
| adaptive_bayes | 0.27 | 0.39 | 0.47 | 0.59 | 0.61 | 0.62 | 0.63 |

Runs that found no regression and tested every affected mandatory property (the method's step 5):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.07 | 0.07 | 0.09 | 0.09 | 0.10 | 0.13 | 1.00 |
| random | 0.08 | 0.10 | 0.17 | 0.42 | 0.65 | 0.91 | 1.00 |
| declared | 0.10 | 0.17 | 0.19 | 0.26 | 0.32 | 0.32 | 0.32 |
| ir_tfidf | 0.07 | 0.13 | 0.17 | 0.31 | 0.39 | 0.69 | 1.00 |
| observed | 0.07 | 0.12 | 0.17 | 0.65 | 0.73 | 0.83 | 0.83 |
| observed_diverse | 0.07 | 0.28 | 0.66 | 0.85 | 0.85 | 0.85 | 0.83 |
| cost_aware | 0.07 | 0.12 | 0.18 | 0.75 | 0.86 | 0.98 | 1.00 |
| history_ml | 0.07 | 0.12 | 0.24 | 0.71 | 0.88 | 0.99 | 1.00 |
| casper_slices | 0.08 | 0.08 | 0.27 | 0.70 | 0.89 | 0.92 | 1.00 |
| risk_aware_ts | 0.09 | 0.17 | 0.36 | 0.74 | 0.96 | 1.00 | 1.00 |
| adaptive_bayes | 0.09 | 0.16 | 0.23 | 0.84 | 0.92 | 0.99 | 1.00 |

Affected workflows run (the workflows of the tests that exercised a changed component):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.14 | 0.38 |
| random | 0.01 | 0.06 | 0.13 | 0.25 | 0.34 | 0.46 | 0.52 |
| declared | 0.06 | 0.19 | 0.25 | 0.30 | 0.31 | 0.31 | 0.31 |
| ir_tfidf | 0.01 | 0.05 | 0.15 | 0.23 | 0.31 | 0.39 | 0.45 |
| observed | 0.02 | 0.04 | 0.16 | 0.25 | 0.30 | 0.33 | 0.42 |
| observed_diverse | 0.06 | 0.26 | 0.40 | 0.57 | 0.60 | 0.60 | 0.60 |
| cost_aware | 0.02 | 0.04 | 0.16 | 0.25 | 0.30 | 0.33 | 0.42 |
| history_ml | 0.01 | 0.05 | 0.17 | 0.27 | 0.31 | 0.39 | 0.44 |
| casper_slices | 0.00 | 0.00 | 0.08 | 0.39 | 0.43 | 0.46 | 0.54 |
| risk_aware_ts | 0.05 | 0.18 | 0.33 | 0.51 | 0.59 | 0.62 | 0.62 |
| adaptive_bayes | 0.00 | 0.04 | 0.11 | 0.21 | 0.23 | 0.35 | 0.38 |

Affected features reached (the features with a tool or a part the change touches), over the changes that affect one:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.27 | 0.28 | 0.42 | 0.59 | 0.84 | 0.93 | 0.93 |
| random | 0.32 | 0.55 | 0.74 | 0.86 | 0.91 | 0.95 | 0.97 |
| declared | 0.70 | 0.73 | 0.76 | 0.76 | 0.78 | 0.78 | 0.78 |
| ir_tfidf | 0.88 | 0.95 | 0.97 | 0.97 | 0.98 | 0.98 | 0.98 |
| observed | 0.82 | 0.85 | 0.87 | 0.93 | 0.94 | 0.94 | 0.94 |
| observed_diverse | 0.80 | 0.87 | 0.94 | 0.95 | 0.95 | 0.95 | 0.95 |
| cost_aware | 0.82 | 0.85 | 0.87 | 0.93 | 0.94 | 0.94 | 0.94 |
| history_ml | 0.78 | 0.83 | 0.87 | 0.93 | 0.94 | 0.94 | 0.94 |
| casper_slices | 0.21 | 0.36 | 0.61 | 0.78 | 0.83 | 0.92 | 0.95 |
| risk_aware_ts | 0.27 | 0.53 | 0.69 | 0.80 | 0.83 | 0.85 | 0.97 |
| adaptive_bayes | 0.65 | 0.75 | 0.85 | 0.92 | 0.92 | 0.92 | 0.92 |

## 7. Replay-first

Every test was run on every changed copy with the model's calls answered from the answers recorded on the original app (`traceeval replay-first`; no model is called). A test either replays to the end, and its outcome on the changed copy is known for no tokens, or diverges at the first request the original app never made, and needs the model from there on.

What the replay settles alone, by kind of change:

| kind of change | changes | no test diverges | a replayed test fails | diverged tests, mean | their share of the suite's tokens | after the divergence point |
|---|---|---|---|---|---|---|
| agentdesc | 11 | 1 | 0 | 139 of 180 | 0.818 | 0.818 |
| argswap | 12 | 0 | 0 | 19 of 180 | 0.184 | 0.114 |
| comment | 32 | 32 | 0 | 0 of 180 | 0.000 | 0.000 |
| condnot | 119 | 39 | 30 | 46 of 180 | 0.297 | 0.244 |
| fixture | 85 | 45 | 3 | 3 of 180 | 0.027 | 0.017 |
| guarddel | 4 | 0 | 0 | 54 of 180 | 0.434 | 0.366 |
| paramdesc | 53 | 0 | 0 | 47 of 180 | 0.365 | 0.314 |
| promptdel | 30 | 0 | 0 | 34 of 180 | 0.256 | 0.222 |
| rewrap | 13 | 0 | 0 | 39 of 180 | 0.304 | 0.255 |
| ruledel | 18 | 0 | 0 | 119 of 180 | 0.737 | 0.705 |
| setting | 65 | 11 | 3 | 33 of 180 | 0.232 | 0.190 |
| stepdel | 76 | 0 | 0 | 25 of 180 | 0.224 | 0.172 |
| stepswap | 63 | 0 | 0 | 22 of 180 | 0.208 | 0.155 |
| tooldesc | 32 | 0 | 0 | 42 of 180 | 0.344 | 0.288 |
| tooldrop | 50 | 0 | 0 | 28 of 180 | 0.247 | 0.197 |
| whennot | 28 | 0 | 0 | 30 of 180 | 0.283 | 0.217 |
| all | 691 | 128 | 36 | 33 of 180 | 0.248 | 0.206 |

Over the 22763 diverged (change, test) pairs, the change first reaches the model in what an agent is sent up front (its prompt, skills, tools or task) on 18771, and in a tool result on 3992.

The replay against the recorded ground truth:

- the tests that replay to the end were not run on these copies: the replay's outcome is the one on record;
- the 8385 revealing (change, test) pairs: 3821 replay to a failure, 4564 diverge, 0 replay to a pass;
- revealed regressions with a revealing test that fails in the replay or diverges: 357 of 357;
- changes no test reveals on which a replayed test fails: 0.

The replay against the recorded runs, one by one, over the tests that replay to the end. A run is identical to the replay when it has the same tool calls, final answer, final state and token count:

| recorded runs of | runs | end like the replay | identical to the replay |
|---|---|---|---|
| the original app | 900 | 900 | 900 |
| the original app, run as the changed copies are | 900 | 900 | 900 |
| the changed copies | 0 | 0 | 0 |

The condition itself, a model call being a function of its request, request by request:

| requests of | sent before | of which |
|---|---|---|
| the baseline's repetitions, one test at a time | 910 | 0 (0.00%) got more than one answer |
| the empty change | 5310 | 0 (0.00%) answered otherwise than the cassette |
| the changed copies | 69368 | 0 (0.00%) answered otherwise than the cassette |

The strategies run replay-first: a test that replays to the end is not run, a replayed failure of a test that passes on the original app ends the run for no tokens, and a diverged test costs its tokens after the divergence point. A run that ends because every diverged test has run and passed is a clean verdict that leaves no reachable test untested.

Fraction of the revealed regressions detected, by nominal budget:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.62 | 0.72 | 0.90 | 0.95 | 0.96 | 0.98 | 1.00 |
| random | 0.65 | 0.74 | 0.81 | 0.89 | 0.94 | 0.98 | 1.00 |
| cheapest | 0.63 | 0.70 | 0.80 | 0.85 | 0.88 | 0.98 | 1.00 |
| late_divergence | 0.65 | 0.72 | 0.76 | 0.84 | 0.89 | 0.98 | 1.00 |
| declared | 0.33 | 0.42 | 0.47 | 0.57 | 0.57 | 0.57 | 0.57 |
| ir_tfidf | 0.62 | 0.77 | 0.84 | 0.91 | 0.93 | 0.98 | 1.00 |
| observed | 0.64 | 0.75 | 0.82 | 0.85 | 0.87 | 0.98 | 1.00 |
| observed_diverse | 0.62 | 0.73 | 0.77 | 0.90 | 0.92 | 0.97 | 1.00 |
| cost_aware | 0.64 | 0.75 | 0.82 | 0.85 | 0.87 | 0.98 | 1.00 |
| history_ml | 0.65 | 0.75 | 0.83 | 0.85 | 0.86 | 0.98 | 1.00 |
| casper_slices | 0.62 | 0.74 | 0.81 | 0.87 | 0.90 | 0.92 | 1.00 |
| risk_aware_ts | 0.65 | 0.76 | 0.84 | 0.91 | 0.97 | 0.99 | 1.00 |
| adaptive_bayes | 0.77 | 0.81 | 0.84 | 0.91 | 0.94 | 0.95 | 0.95 |

Tokens spent, as a mean over all changes (fraction of the full suite):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.010 | 0.022 | 0.037 | 0.052 | 0.064 | 0.069 | 0.070 |
| random | 0.010 | 0.022 | 0.039 | 0.058 | 0.072 | 0.078 | 0.080 |
| cheapest | 0.010 | 0.021 | 0.038 | 0.059 | 0.075 | 0.085 | 0.087 |
| late_divergence | 0.010 | 0.022 | 0.040 | 0.062 | 0.078 | 0.087 | 0.089 |
| declared | 0.008 | 0.017 | 0.028 | 0.039 | 0.044 | 0.044 | 0.044 |
| ir_tfidf | 0.010 | 0.022 | 0.038 | 0.056 | 0.069 | 0.075 | 0.077 |
| observed | 0.010 | 0.021 | 0.037 | 0.057 | 0.074 | 0.087 | 0.090 |
| observed_diverse | 0.010 | 0.023 | 0.041 | 0.064 | 0.078 | 0.087 | 0.089 |
| cost_aware | 0.010 | 0.021 | 0.037 | 0.057 | 0.074 | 0.087 | 0.090 |
| history_ml | 0.010 | 0.021 | 0.037 | 0.057 | 0.074 | 0.085 | 0.087 |
| casper_slices | 0.010 | 0.022 | 0.038 | 0.060 | 0.075 | 0.088 | 0.093 |
| risk_aware_ts | 0.010 | 0.022 | 0.038 | 0.057 | 0.069 | 0.073 | 0.074 |
| adaptive_bayes | 0.009 | 0.018 | 0.032 | 0.048 | 0.058 | 0.061 | 0.061 |

For comparison, a cache of the original app's answers in front of the model, with the whole suite run again and no stop at a failure, pays every diverged test from its divergence point on: 0.206 of the suite's tokens per change (median 0.072) at most. After that point a run still sends requests the original app made; with those answered from the cache too, it pays 0.151 (median 0.050). It finds every revealed regression.

The same tests run whole, without the replayed part taken off:

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.013 | 0.028 | 0.047 | 0.068 | 0.082 | 0.088 | 0.089 |
| random | 0.014 | 0.030 | 0.051 | 0.075 | 0.092 | 0.099 | 0.100 |
| cheapest | 0.013 | 0.026 | 0.047 | 0.071 | 0.094 | 0.104 | 0.106 |
| late_divergence | 0.020 | 0.038 | 0.061 | 0.085 | 0.101 | 0.110 | 0.112 |
| declared | 0.010 | 0.023 | 0.038 | 0.051 | 0.057 | 0.058 | 0.058 |
| ir_tfidf | 0.013 | 0.028 | 0.048 | 0.071 | 0.087 | 0.094 | 0.095 |
| observed | 0.013 | 0.028 | 0.049 | 0.073 | 0.092 | 0.106 | 0.109 |
| observed_diverse | 0.016 | 0.035 | 0.058 | 0.085 | 0.100 | 0.109 | 0.111 |
| cost_aware | 0.013 | 0.028 | 0.049 | 0.073 | 0.092 | 0.106 | 0.109 |
| history_ml | 0.013 | 0.029 | 0.051 | 0.075 | 0.092 | 0.104 | 0.106 |
| casper_slices | 0.013 | 0.028 | 0.052 | 0.077 | 0.095 | 0.108 | 0.113 |
| risk_aware_ts | 0.015 | 0.031 | 0.052 | 0.076 | 0.089 | 0.094 | 0.095 |
| adaptive_bayes | 0.012 | 0.025 | 0.042 | 0.064 | 0.076 | 0.079 | 0.079 |

The same tests charged for their new requests only. After its divergence point a run still sends requests the original app made, and a check answers those from the cassette too (`traceeval check`):

| strategy | 2% | 5% | 10% | 20% | 30% | 50% | 100% |
|---|---|---|---|---|---|---|---|
| full | 0.008 | 0.016 | 0.026 | 0.036 | 0.043 | 0.046 | 0.047 |
| random | 0.008 | 0.016 | 0.026 | 0.039 | 0.048 | 0.053 | 0.054 |
| cheapest | 0.009 | 0.018 | 0.031 | 0.046 | 0.055 | 0.060 | 0.062 |
| late_divergence | 0.008 | 0.016 | 0.028 | 0.045 | 0.055 | 0.060 | 0.062 |
| declared | 0.006 | 0.012 | 0.017 | 0.024 | 0.029 | 0.029 | 0.029 |
| ir_tfidf | 0.009 | 0.017 | 0.027 | 0.039 | 0.047 | 0.051 | 0.052 |
| observed | 0.009 | 0.018 | 0.029 | 0.044 | 0.053 | 0.061 | 0.062 |
| observed_diverse | 0.008 | 0.015 | 0.026 | 0.041 | 0.051 | 0.058 | 0.059 |
| cost_aware | 0.009 | 0.018 | 0.029 | 0.044 | 0.053 | 0.061 | 0.063 |
| history_ml | 0.009 | 0.018 | 0.029 | 0.042 | 0.052 | 0.060 | 0.061 |
| casper_slices | 0.009 | 0.018 | 0.027 | 0.042 | 0.053 | 0.061 | 0.064 |
| risk_aware_ts | 0.008 | 0.015 | 0.024 | 0.036 | 0.045 | 0.048 | 0.049 |
| adaptive_bayes | 0.007 | 0.014 | 0.023 | 0.033 | 0.038 | 0.040 | 0.040 |

At a budget of 5%, over the 186 revealed regressions (intervals: bootstrap over the changes; a difference whose interval holds 0 is not established):

| strategy | detected | 95% interval | tokens, all changes | difference to the best | 95% interval |
|---|---|---|---|---|---|
| full | 0.72 | 0.65 to 0.78 | 0.022 | -0.09 | -0.15 to -0.04 |
| random | 0.74 | 0.69 to 0.80 | 0.022 | -0.06 | -0.11 to -0.02 |
| cheapest | 0.70 | 0.64 to 0.77 | 0.021 | -0.10 | -0.15 to -0.06 |
| late_divergence | 0.72 | 0.66 to 0.78 | 0.022 | -0.09 | -0.13 to -0.04 |
| declared | 0.42 | 0.35 to 0.49 | 0.017 | -0.38 | -0.46 to -0.31 |
| ir_tfidf | 0.77 | 0.71 to 0.83 | 0.022 | -0.03 | -0.08 to +0.01 |
| observed | 0.75 | 0.68 to 0.81 | 0.021 | -0.06 | -0.11 to -0.01 |
| observed_diverse | 0.73 | 0.66 to 0.79 | 0.023 | -0.08 | -0.13 to -0.03 |
| cost_aware | 0.75 | 0.68 to 0.81 | 0.021 | -0.06 | -0.11 to -0.01 |
| history_ml | 0.75 | 0.68 to 0.81 | 0.021 | -0.06 | -0.11 to -0.01 |
| casper_slices | 0.74 | 0.68 to 0.80 | 0.022 | -0.06 | -0.11 to -0.02 |
| risk_aware_ts | 0.76 | 0.71 to 0.81 | 0.022 | -0.05 | -0.09 to -0.01 |
| adaptive_bayes | 0.81 | 0.75 to 0.86 | 0.018 | best |  |

At a budget of 20%, over the 186 revealed regressions (intervals: bootstrap over the changes; a difference whose interval holds 0 is not established):

| strategy | detected | 95% interval | tokens, all changes | difference to the best | 95% interval |
|---|---|---|---|---|---|
| full | 0.95 | 0.91 to 0.98 | 0.052 | best |  |
| random | 0.89 | 0.86 to 0.92 | 0.058 | -0.05 | -0.09 to -0.02 |
| cheapest | 0.85 | 0.80 to 0.90 | 0.059 | -0.10 | -0.15 to -0.04 |
| late_divergence | 0.84 | 0.79 to 0.89 | 0.062 | -0.10 | -0.16 to -0.05 |
| declared | 0.57 | 0.49 to 0.64 | 0.039 | -0.38 | -0.46 to -0.30 |
| ir_tfidf | 0.91 | 0.87 to 0.95 | 0.056 | -0.03 | -0.08 to +0.01 |
| observed | 0.85 | 0.80 to 0.90 | 0.057 | -0.09 | -0.15 to -0.04 |
| observed_diverse | 0.90 | 0.85 to 0.94 | 0.064 | -0.05 | -0.10 to +0.00 |
| cost_aware | 0.85 | 0.80 to 0.90 | 0.057 | -0.09 | -0.15 to -0.04 |
| history_ml | 0.85 | 0.80 to 0.90 | 0.057 | -0.09 | -0.15 to -0.04 |
| casper_slices | 0.87 | 0.82 to 0.91 | 0.060 | -0.08 | -0.13 to -0.03 |
| risk_aware_ts | 0.91 | 0.87 to 0.94 | 0.057 | -0.04 | -0.08 to +0.00 |
| adaptive_bayes | 0.91 | 0.87 to 0.95 | 0.048 | -0.04 | -0.09 to +0.01 |

![replay-first: detection vs cost](figures/replay_first.png)

Verdicts at a budget of 20% (shares of the runs):

| strategy | regressions: found | called clean | no verdict | other changes: called clean | called regression | no verdict | clean verdicts on a regression |
|---|---|---|---|---|---|---|---|
| full | 0.95 | 0.00 | 0.05 | 0.75 | 0.00 | 0.25 | 0.00 |
| random | 0.89 | 0.00 | 0.11 | 0.75 | 0.00 | 0.25 | 0.00 |
| cheapest | 0.85 | 0.00 | 0.15 | 0.75 | 0.00 | 0.25 | 0.00 |
| late_divergence | 0.84 | 0.00 | 0.16 | 0.75 | 0.00 | 0.25 | 0.00 |
| declared | 0.57 | 0.42 | 0.01 | 0.82 | 0.00 | 0.18 | 0.38 |
| ir_tfidf | 0.91 | 0.00 | 0.09 | 0.75 | 0.00 | 0.25 | 0.00 |
| observed | 0.85 | 0.00 | 0.15 | 0.75 | 0.00 | 0.25 | 0.00 |
| observed_diverse | 0.90 | 0.00 | 0.10 | 0.75 | 0.00 | 0.25 | 0.00 |
| cost_aware | 0.85 | 0.00 | 0.15 | 0.75 | 0.00 | 0.25 | 0.00 |
| history_ml | 0.85 | 0.00 | 0.15 | 0.75 | 0.00 | 0.25 | 0.00 |
| casper_slices | 0.87 | 0.00 | 0.13 | 0.75 | 0.00 | 0.25 | 0.00 |
| risk_aware_ts | 0.91 | 0.00 | 0.09 | 0.75 | 0.00 | 0.25 | 0.00 |
| adaptive_bayes | 0.91 | 0.04 | 0.05 | 0.76 | 0.00 | 0.24 | 0.06 |

Verdicts at a budget of 100% (shares of the runs):

| strategy | regressions: found | called clean | no verdict | other changes: called clean | called regression | no verdict | clean verdicts on a regression |
|---|---|---|---|---|---|---|---|
| full | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 |
| random | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 |
| cheapest | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 |
| late_divergence | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 |
| declared | 0.57 | 0.43 | 0.00 | 1.00 | 0.00 | 0.00 | 0.34 |
| ir_tfidf | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 |
| observed | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 |
| observed_diverse | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 |
| cost_aware | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 |
| history_ml | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 |
| casper_slices | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 |
| risk_aware_ts | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 |
| adaptive_bayes | 0.95 | 0.05 | 0.00 | 1.00 | 0.00 | 0.00 | 0.06 |

## 8. Generated changes, replayed

The 692 changes that `mutation/generator.py` makes mechanically from the app (one per place an edit of its kind applies to), each applied to a copy of the original app and replayed against the recording's cassette (`traceeval replay-first --generated`). No model is called, and no change has a label.

| kind of change | changes | no test diverges | a replayed test fails | diverged tests, mean | their share of the suite's tokens | after the divergence point |
|---|---|---|---|---|---|---|
| agentdesc | 11 | 1 | 0 | 139 of 180 | 0.818 | 0.818 |
| argswap | 12 | 0 | 0 | 19 of 180 | 0.184 | 0.114 |
| comment | 32 | 32 | 0 | 0 of 180 | 0.000 | 0.000 |
| condnot | 120 | 39 | 30 | 47 of 180 | 0.303 | 0.245 |
| fixture | 85 | 45 | 3 | 3 of 180 | 0.027 | 0.017 |
| guarddel | 4 | 0 | 0 | 54 of 180 | 0.434 | 0.366 |
| paramdesc | 53 | 0 | 0 | 47 of 180 | 0.365 | 0.314 |
| promptdel | 30 | 0 | 0 | 34 of 180 | 0.256 | 0.222 |
| rewrap | 13 | 0 | 0 | 39 of 180 | 0.304 | 0.255 |
| ruledel | 18 | 0 | 0 | 119 of 180 | 0.737 | 0.705 |
| setting | 65 | 11 | 3 | 33 of 180 | 0.232 | 0.190 |
| stepdel | 76 | 0 | 0 | 25 of 180 | 0.224 | 0.172 |
| stepswap | 63 | 0 | 0 | 22 of 180 | 0.208 | 0.155 |
| tooldesc | 32 | 0 | 0 | 42 of 180 | 0.344 | 0.288 |
| tooldrop | 50 | 0 | 0 | 28 of 180 | 0.247 | 0.197 |
| whennot | 28 | 0 | 0 | 30 of 180 | 0.283 | 0.217 |
| all | 692 | 128 | 36 | 33 of 180 | 0.249 | 0.206 |

- settled as clean, no test diverges and none fails: 98 of 692;
- settled as a regression, a test that passes on the original app replays to a failure: 36;
- left for the model: 558, whose diverged tests cost 25.3% of the suite's tokens after their divergence points on average (median 9.9%), and 30.5% run whole.

## How to read this

`detected` counts *changes* (one failing revealing test is enough). Compare strategies at equal tokens *spent*, not equal nominal budget: every run ends at its first failure, the selecting strategies also run out of tests, and `adaptive_bayes` also stops when it is confident. A good strategy is high in the first table of section 2 and low in the second. The sample is the changes: the seeds only draw which recorded run answers a test and the choices of the strategies that draw at random, so an interval is over the changes. A clean verdict is worth what the last column of the verdict tables says.

Section 7 reads like section 2, with the replay in front: compare a strategy's row there with its row here. Replay-first, a strategy that orders the whole suite gives a clean verdict once every diverged test has run and passed; that verdict holds as far as the replay agrees with the recording, which the first lines of the section measure.
