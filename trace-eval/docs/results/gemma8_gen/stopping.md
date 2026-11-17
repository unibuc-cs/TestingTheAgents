# Stopping with a bounded miss rate: the full tables

The output of `scripts/analysis/stop_with_guarantee.py runs/gemma8_gen runs/gemma8`, as it prints it. The method is
in [RESEARCH_PLAN.md](../../RESEARCH_PLAN.md) §3.4 and the reading of these tables in its §5.9.

- A rule orders the tests a change reaches and gives each a value; the run stops with a clean verdict at the first
  value under a threshold, set on past regressions for a target miss rate.
- `thresholds` says how the threshold is set:

  | | |
  |---|---|
  | `one` | one threshold for all changes |
  | `one, sure` | one for all changes, lower, so that the target holds for nine sets of past regressions in ten |
  | `per group` | one per group of changes, a group being what the change edits; a group with too few past regressions has none, and every reached test runs |

- `miss rate` is the share of the regressions called clean, `highest` its highest value among the twenty splits,
  and `splits over target` the share of the splits whose miss rate is over the target.
- Tokens are shares of the full suite; `tokens, no test reveals` is what a clean verdict costs.
- `target 0` runs every reached test; `none (eps_clean = 0.05)` is `adaptive_bayes` with its own constant.

```text
[loaded runs/gemma8_gen: 180 tests, 691 variants, 8 s]
runs/gemma8_gen: 691 changes; the replay settles 134 (35 as regressions); of the other 557, 281 are regressions

20 splits: a quarter of the changes is what a rule learns from, a quarter sets the threshold (64 to 75 regressions), half measures the rule.
A target under 0.015 leaves no threshold in some split: every diverged test runs there.

the rules on the measured changes: means over the splits, tokens as shares of the full suite
thresholds                          rule                  target  miss rate  highest splits over target  clean verdicts on a regression  tokens, no test reveals  tokens, regressions  tokens, all
       one                        random                   0.000      0.000    0.000              0.000                           0.000                    0.201                0.047        0.123
       one                        random                   0.050      0.038    0.085              0.250                           0.037                    0.172                0.046        0.108
       one                        random                   0.100      0.079    0.113              0.300                           0.075                    0.136                0.045        0.090
       one                        random                   0.200      0.181    0.273              0.350                           0.157                    0.089                0.040        0.064
       one                 text (TF-IDF)                   0.000      0.000    0.000              0.000                           0.000                    0.201                0.037        0.117
       one                 text (TF-IDF)                   0.050      0.022    0.112              0.250                           0.021                    0.185                0.035        0.109
       one                 text (TF-IDF)                   0.100      0.096    0.167              0.350                           0.088                    0.128                0.029        0.078
       one                 text (TF-IDF)                   0.200      0.210    0.350              0.550                           0.177                    0.077                0.019        0.048
       one                       learned                   0.000      0.000    0.000              0.000                           0.000                    0.201                0.057        0.128
       one                       learned                   0.050      0.043    0.085              0.400                           0.042                    0.124                0.051        0.087
       one                       learned                   0.100      0.098    0.208              0.400                           0.092                    0.078                0.041        0.059
       one                       learned                   0.200      0.195    0.271              0.400                           0.167                    0.032                0.033        0.032
       one              learned + replay                   0.000      0.000    0.000              0.000                           0.000                    0.201                0.049        0.124
       one              learned + replay                   0.050      0.044    0.156              0.350                           0.043                    0.116                0.043        0.079
       one              learned + replay                   0.100      0.097    0.177              0.450                           0.090                    0.080                0.039        0.059
       one              learned + replay                   0.200      0.212    0.322              0.600                           0.179                    0.032                0.028        0.030
       one                adaptive_bayes                   0.000      0.000    0.000              0.000                           0.000                    0.201                0.036        0.117
       one                adaptive_bayes                   0.050      0.045    0.135              0.400                           0.043                    0.185                0.032        0.107
       one                adaptive_bayes                   0.100      0.099    0.220              0.450                           0.092                    0.140                0.025        0.081
       one                adaptive_bayes                   0.200      0.189    0.255              0.400                           0.163                    0.079                0.013        0.046
       one                adaptive_bayes none (eps_clean = 0.05)      0.074    0.109                NaN                           0.071                    0.156                0.029        0.091
       one adaptive_bayes, reached tests                   0.000      0.000    0.000              0.000                           0.000                    0.201                0.036        0.117
       one adaptive_bayes, reached tests                   0.050      0.041    0.129              0.350                           0.040                    0.191                0.033        0.111
       one adaptive_bayes, reached tests                   0.100      0.092    0.177              0.450                           0.086                    0.168                0.029        0.097
       one adaptive_bayes, reached tests                   0.200      0.191    0.308              0.450                           0.163                    0.109                0.018        0.063
 one, sure                        random                   0.050      0.010    0.044              0.000                           0.010                    0.188                0.047        0.116
 one, sure                        random                   0.100      0.051    0.102              0.050                           0.050                    0.160                0.046        0.102
 one, sure                        random                   0.200      0.110    0.156              0.000                           0.102                    0.113                0.043        0.078
 one, sure                 text (TF-IDF)                   0.050      0.000    0.000              0.000                           0.000                    0.201                0.037        0.117
 one, sure                 text (TF-IDF)                   0.100      0.039    0.125              0.150                           0.037                    0.177                0.034        0.104
 one, sure                 text (TF-IDF)                   0.200      0.149    0.246              0.250                           0.131                    0.099                0.023        0.061
 one, sure                       learned                   0.050      0.011    0.042              0.000                           0.011                    0.170                0.056        0.112
 one, sure                       learned                   0.100      0.054    0.099              0.000                           0.053                    0.111                0.049        0.079
 one, sure                       learned                   0.200      0.143    0.250              0.100                           0.128                    0.051                0.037        0.044
 one, sure              learned + replay                   0.050      0.012    0.064              0.100                           0.012                    0.162                0.047        0.104
 one, sure              learned + replay                   0.100      0.060    0.170              0.100                           0.058                    0.099                0.041        0.070
 one, sure              learned + replay                   0.200      0.147    0.266              0.100                           0.131                    0.057                0.034        0.045
 one, sure                adaptive_bayes                   0.050      0.010    0.049              0.000                           0.010                    0.199                0.035        0.116
 one, sure                adaptive_bayes                   0.100      0.061    0.135              0.150                           0.058                    0.177                0.030        0.102
 one, sure                adaptive_bayes                   0.200      0.143    0.255              0.150                           0.127                    0.105                0.018        0.061
 one, sure adaptive_bayes, reached tests                   0.050      0.009    0.049              0.000                           0.009                    0.199                0.036        0.116
 one, sure adaptive_bayes, reached tests                   0.100      0.058    0.129              0.100                           0.056                    0.188                0.032        0.109
 one, sure adaptive_bayes, reached tests                   0.200      0.139    0.234              0.200                           0.123                    0.135                0.024        0.079
 per group                        random                   0.050      0.009    0.028              0.000                           0.009                    0.200                0.047        0.122
 per group                        random                   0.100      0.055    0.109              0.050                           0.053                    0.188                0.046        0.116
 per group                        random                   0.200      0.149    0.248              0.150                           0.132                    0.132                0.044        0.087
 per group                 text (TF-IDF)                   0.050      0.013    0.051              0.050                           0.014                    0.199                0.035        0.115
 per group                 text (TF-IDF)                   0.100      0.066    0.169              0.200                           0.063                    0.180                0.031        0.104
 per group                 text (TF-IDF)                   0.200      0.151    0.221              0.150                           0.134                    0.122                0.026        0.073
 per group                       learned                   0.050      0.014    0.057              0.050                           0.014                    0.199                0.056        0.126
 per group                       learned                   0.100      0.052    0.105              0.050                           0.050                    0.181                0.054        0.117
 per group                       learned                   0.200      0.135    0.230              0.150                           0.120                    0.143                0.050        0.096
 per group              learned + replay                   0.050      0.019    0.059              0.050                           0.019                    0.197                0.046        0.120
 per group              learned + replay                   0.100      0.070    0.153              0.250                           0.066                    0.182                0.042        0.111
 per group              learned + replay                   0.200      0.140    0.197              0.000                           0.126                    0.140                0.037        0.088
 per group                adaptive_bayes                   0.050      0.010    0.049              0.000                           0.010                    0.199                0.035        0.116
 per group                adaptive_bayes                   0.100      0.053    0.121              0.050                           0.051                    0.175                0.032        0.102
 per group                adaptive_bayes                   0.200      0.127    0.245              0.100                           0.114                    0.122                0.026        0.073
 per group adaptive_bayes, reached tests                   0.050      0.010    0.049              0.000                           0.010                    0.199                0.036        0.116
 per group adaptive_bayes, reached tests                   0.100      0.057    0.128              0.100                           0.055                    0.176                0.032        0.103
 per group adaptive_bayes, reached tests                   0.200      0.141    0.241              0.150                           0.125                    0.122                0.026        0.073

the groups of changes, per split: {"a skill's steps": {'changes per split': 85.0, 'regressions': 23.45, 'tokens, every test': 0.127}, "an agent's tools and skills": {'changes per split': 25.0, 'regressions': 22.8, 'tokens, every test': 0.028}, 'code': {'changes per split': 45.0, 'regressions': 43.4, 'tokens, every test': 0.036}, 'text the model reads': {'changes per split': 77.0, 'regressions': 13.3, 'tokens, every test': 0.252}, 'the configuration': {'changes per split': 26.0, 'regressions': 23.95, 'tokens, every test': 0.043}, 'the starting data': {'changes per split': 18.0, 'regressions': 13.45, 'tokens, every test': 0.014}}

miss rate per group, target 0.1, thresholds: one
rule                         random  text (TF-IDF)  learned  learned + replay  adaptive_bayes  adaptive_bayes, reached tests
group                                                                                                                       
a skill's steps               0.243          0.117    0.100             0.228           0.032                          0.017
an agent's tools and skills   0.031          0.000    0.000             0.000           0.013                          0.004
code                          0.046          0.063    0.000             0.007           0.199                          0.181
text the model reads          0.026          0.158    0.865             0.594           0.312                          0.132
the configuration             0.031          0.019    0.000             0.002           0.000                          0.065
the starting data             0.115          0.401    0.000             0.000           0.007                          0.097

tokens per group, target 0.1, thresholds: one
rule                         random  text (TF-IDF)  learned  learned + replay  adaptive_bayes  adaptive_bayes, reached tests
group                                                                                                                       
a skill's steps               0.089          0.087    0.097             0.092           0.098                          0.107
an agent's tools and skills   0.023          0.029    0.039             0.036           0.010                          0.014
code                          0.030          0.020    0.043             0.047           0.003                          0.003
text the model reads          0.181          0.150    0.037             0.052           0.174                          0.222
the configuration             0.040          0.026    0.083             0.047           0.009                          0.004
the starting data             0.013          0.009    0.012             0.016           0.009                          0.008

miss rate per group, target 0.1, thresholds: per group
rule                         random  text (TF-IDF)  learned  learned + replay  adaptive_bayes  adaptive_bayes, reached tests
group                                                                                                                       
a skill's steps               0.060          0.060    0.045             0.060           0.064                          0.068
an agent's tools and skills   0.072          0.057    0.064             0.064           0.024                          0.031
code                          0.055          0.091    0.068             0.108           0.094                          0.085
text the model reads          0.004          0.034    0.015             0.030           0.011                          0.011
the configuration             0.079          0.092    0.058             0.073           0.042                          0.071
the starting data             0.026          0.000    0.015             0.011           0.004                          0.007

tokens per group, target 0.1, thresholds: per group
rule                         random  text (TF-IDF)  learned  learned + replay  adaptive_bayes  adaptive_bayes, reached tests
group                                                                                                                       
a skill's steps               0.118          0.105    0.101             0.110           0.085                          0.085
an agent's tools and skills   0.022          0.016    0.028             0.034           0.005                          0.006
code                          0.029          0.015    0.031             0.017           0.014                          0.016
text the model reads          0.244          0.232    0.250             0.236           0.259                          0.258
the configuration             0.039          0.023    0.080             0.042           0.003                          0.006
the starting data             0.014          0.016    0.012             0.016           0.009                          0.009

each kind of change measured with rules and thresholds from the other kinds (all kinds pooled)
thresholds                          rule                  target     missed  miss rate  clean verdicts on a regression  tokens, no test reveals  tokens, regressions  tokens, all
       one                        random                   0.000   0 of 281      0.000                           0.000                    0.199                0.046        0.122
       one                        random                   0.050  12 of 281      0.043                           0.042                    0.170                0.045        0.107
       one                        random                   0.100  27 of 281      0.096                           0.089                    0.124                0.043        0.083
       one                        random                   0.200  53 of 281      0.189                           0.161                    0.086                0.038        0.062
       one                 text (TF-IDF)                   0.000   0 of 281      0.000                           0.000                    0.199                0.036        0.117
       one                 text (TF-IDF)                   0.050  11 of 281      0.039                           0.038                    0.199                0.035        0.116
       one                 text (TF-IDF)                   0.100  25 of 281      0.089                           0.083                    0.126                0.030        0.077
       one                 text (TF-IDF)                   0.200  53 of 281      0.189                           0.161                    0.086                0.020        0.053
       one                       learned                   0.000   0 of 281      0.000                           0.000                    0.199                0.043        0.120
       one                       learned                   0.050  12 of 281      0.043                           0.042                    0.143                0.036        0.089
       one                       learned                   0.100  25 of 281      0.089                           0.083                    0.074                0.026        0.050
       one                       learned                   0.200  59 of 281      0.210                           0.176                    0.022                0.017        0.020
       one              learned + replay                   0.000   0 of 281      0.000                           0.000                    0.199                0.041        0.119
       one              learned + replay                   0.050  18 of 281      0.064                           0.061                    0.085                0.032        0.058
       one              learned + replay                   0.100  33 of 281      0.117                           0.107                    0.060                0.027        0.043
       one              learned + replay                   0.200 112 of 281      0.399                           0.289                    0.015                0.012        0.013
       one                adaptive_bayes                   0.000   0 of 281      0.000                           0.000                    0.199                0.035        0.116
       one                adaptive_bayes                   0.050  16 of 281      0.057                           0.055                    0.194                0.030        0.112
       one                adaptive_bayes                   0.100  28 of 281      0.100                           0.092                    0.137                0.025        0.080
       one                adaptive_bayes                   0.200  73 of 281      0.260                           0.209                    0.081                0.013        0.047
       one                adaptive_bayes none (eps_clean = 0.05)  21 of 281      0.075                           0.071                    0.153                0.028        0.090
       one adaptive_bayes, reached tests                   0.000   0 of 281      0.000                           0.000                    0.199                0.035        0.116
       one adaptive_bayes, reached tests                   0.050  16 of 281      0.057                           0.055                    0.194                0.030        0.111
       one adaptive_bayes, reached tests                   0.100  24 of 281      0.085                           0.080                    0.146                0.027        0.086
       one adaptive_bayes, reached tests                   0.200  41 of 281      0.146                           0.129                    0.113                0.019        0.065
 one, sure                        random                   0.050   9 of 281      0.032                           0.032                    0.180                0.045        0.112
 one, sure                        random                   0.100  18 of 281      0.064                           0.061                    0.152                0.044        0.097
 one, sure                        random                   0.200  41 of 281      0.146                           0.129                    0.094                0.040        0.067
 one, sure                 text (TF-IDF)                   0.050  10 of 281      0.036                           0.035                    0.199                0.036        0.116
 one, sure                 text (TF-IDF)                   0.100  11 of 281      0.039                           0.038                    0.181                0.035        0.108
 one, sure                 text (TF-IDF)                   0.200  41 of 281      0.146                           0.129                    0.097                0.023        0.060
 one, sure                       learned                   0.050   9 of 281      0.032                           0.032                    0.151                0.037        0.093
 one, sure                       learned                   0.100  13 of 281      0.046                           0.045                    0.112                0.035        0.073
 one, sure                       learned                   0.200  41 of 281      0.146                           0.129                    0.038                0.021        0.029
 one, sure              learned + replay                   0.050   7 of 281      0.025                           0.025                    0.129                0.036        0.082
 one, sure              learned + replay                   0.100  22 of 281      0.078                           0.074                    0.073                0.029        0.050
 one, sure              learned + replay                   0.200  86 of 281      0.306                           0.238                    0.028                0.017        0.023
 one, sure                adaptive_bayes                   0.050  16 of 281      0.057                           0.055                    0.194                0.031        0.112
 one, sure                adaptive_bayes                   0.100  22 of 281      0.078                           0.074                    0.157                0.029        0.092
 one, sure                adaptive_bayes                   0.200  49 of 281      0.174                           0.151                    0.101                0.017        0.059
 one, sure adaptive_bayes, reached tests                   0.050  15 of 281      0.053                           0.052                    0.194                0.031        0.112
 one, sure adaptive_bayes, reached tests                   0.100  17 of 281      0.060                           0.058                    0.194                0.030        0.111
 one, sure adaptive_bayes, reached tests                   0.200  30 of 281      0.107                           0.098                    0.131                0.024        0.077
 per group                        random                   0.050   2 of 281      0.007                           0.007                    0.196                0.046        0.120
 per group                        random                   0.100  10 of 281      0.036                           0.035                    0.157                0.045        0.100
 per group                        random                   0.200  13 of 281      0.046                           0.045                    0.123                0.044        0.083
 per group                 text (TF-IDF)                   0.050   0 of 281      0.000                           0.000                    0.199                0.036        0.117
 per group                 text (TF-IDF)                   0.100   5 of 281      0.018                           0.018                    0.159                0.034        0.096
 per group                 text (TF-IDF)                   0.200  43 of 281      0.153                           0.135                    0.104                0.024        0.064
 per group                       learned                   0.050   1 of 281      0.004                           0.004                    0.188                0.043        0.115
 per group                       learned                   0.100  13 of 281      0.046                           0.045                    0.171                0.043        0.106
 per group                       learned                   0.200  18 of 281      0.064                           0.061                    0.138                0.041        0.089
 per group              learned + replay                   0.050   0 of 281      0.000                           0.000                    0.197                0.041        0.119
 per group              learned + replay                   0.100   4 of 281      0.014                           0.014                    0.179                0.039        0.108
 per group              learned + replay                   0.200  49 of 281      0.174                           0.151                    0.131                0.031        0.081
 per group                adaptive_bayes                   0.050   1 of 281      0.004                           0.004                    0.184                0.035        0.109
 per group                adaptive_bayes                   0.100   9 of 281      0.032                           0.032                    0.136                0.031        0.083
 per group                adaptive_bayes                   0.200  31 of 281      0.110                           0.101                    0.096                0.022        0.059
 per group adaptive_bayes, reached tests                   0.050   1 of 281      0.004                           0.004                    0.184                0.035        0.109
 per group adaptive_bayes, reached tests                   0.100   9 of 281      0.032                           0.032                    0.138                0.031        0.084
 per group adaptive_bayes, reached tests                   0.200  31 of 281      0.110                           0.101                    0.095                0.022        0.058
[loaded runs/gemma8: 180 tests, 43 variants, 1 s]

runs/gemma8: 43 changes; the replay settles 8 (3 as regressions); of the other 35, 25 are regressions

the rules learnt on 281 changes of runs/gemma8_gen, their thresholds set on the other 276 (144 regressions), run on those changes
thresholds                          rule                  target   missed  miss rate  clean verdicts on a regression  tokens, no test reveals  tokens, regressions  tokens, all
       one                        random                   0.000  0 of 25      0.000                           0.000                    0.370                0.022        0.122
       one                        random                   0.050  1 of 25      0.040                           0.091                    0.321                0.022        0.108
       one                        random                   0.100  5 of 25      0.200                           0.333                    0.232                0.022        0.082
       one                        random                   0.200 10 of 25      0.400                           0.500                    0.158                0.015        0.055
       one                 text (TF-IDF)                   0.000  0 of 25      0.000                           0.000                    0.370                0.016        0.117
       one                 text (TF-IDF)                   0.050  0 of 25      0.000                           0.000                    0.370                0.016        0.117
       one                 text (TF-IDF)                   0.100  2 of 25      0.080                           0.167                    0.256                0.014        0.083
       one                 text (TF-IDF)                   0.200  4 of 25      0.160                           0.286                    0.173                0.014        0.060
       one                       learned                   0.000  0 of 25      0.000                           0.000                    0.370                0.008        0.111
       one                       learned                   0.050  3 of 25      0.120                           0.231                    0.277                0.007        0.085
       one                       learned                   0.100  4 of 25      0.160                           0.286                    0.055                0.007        0.021
       one                       learned                   0.200  4 of 25      0.160                           0.286                    0.041                0.007        0.017
       one              learned + replay                   0.000  0 of 25      0.000                           0.000                    0.370                0.022        0.121
       one              learned + replay                   0.050  0 of 25      0.000                           0.000                    0.131                0.022        0.053
       one              learned + replay                   0.100  1 of 25      0.040                           0.091                    0.063                0.021        0.033
       one              learned + replay                   0.200  4 of 25      0.160                           0.286                    0.034                0.017        0.022
       one                adaptive_bayes                   0.000  0 of 25      0.000                           0.000                    0.370                0.008        0.112
       one                adaptive_bayes                   0.050  0 of 25      0.000                           0.000                    0.370                0.008        0.112
       one                adaptive_bayes                   0.100  2 of 25      0.080                           0.167                    0.135                0.007        0.044
       one                adaptive_bayes                   0.200  5 of 25      0.200                           0.333                    0.037                0.007        0.015
       one                adaptive_bayes none (eps_clean = 0.05)  2 of 25      0.080                           0.167                    0.192                0.007        0.060
       one adaptive_bayes, reached tests                   0.000  0 of 25      0.000                           0.000                    0.370                0.008        0.112
       one adaptive_bayes, reached tests                   0.050  0 of 25      0.000                           0.000                    0.349                0.008        0.106
       one adaptive_bayes, reached tests                   0.100  2 of 25      0.080                           0.167                    0.148                0.007        0.048
       one adaptive_bayes, reached tests                   0.200  6 of 25      0.240                           0.375                    0.042                0.007        0.017
 one, sure                        random                   0.050  1 of 25      0.040                           0.091                    0.340                0.022        0.113
 one, sure                        random                   0.100  1 of 25      0.040                           0.091                    0.287                0.022        0.098
 one, sure                        random                   0.200 10 of 25      0.400                           0.500                    0.172                0.018        0.062
 one, sure                 text (TF-IDF)                   0.050  0 of 25      0.000                           0.000                    0.370                0.016        0.117
 one, sure                 text (TF-IDF)                   0.100  0 of 25      0.000                           0.000                    0.354                0.016        0.112
 one, sure                 text (TF-IDF)                   0.200  3 of 25      0.120                           0.231                    0.203                0.014        0.068
 one, sure                       learned                   0.050  3 of 25      0.120                           0.231                    0.308                0.007        0.093
 one, sure                       learned                   0.100  3 of 25      0.120                           0.231                    0.164                0.007        0.052
 one, sure                       learned                   0.200  4 of 25      0.160                           0.286                    0.041                0.007        0.017
 one, sure              learned + replay                   0.050  0 of 25      0.000                           0.000                    0.231                0.022        0.081
 one, sure              learned + replay                   0.100  0 of 25      0.000                           0.000                    0.122                0.022        0.050
 one, sure              learned + replay                   0.200  2 of 25      0.080                           0.167                    0.043                0.020        0.027
 one, sure                adaptive_bayes                   0.050  0 of 25      0.000                           0.000                    0.370                0.008        0.112
 one, sure                adaptive_bayes                   0.100  2 of 25      0.080                           0.167                    0.213                0.007        0.066
 one, sure                adaptive_bayes                   0.200  5 of 25      0.200                           0.333                    0.043                0.007        0.017
 one, sure adaptive_bayes, reached tests                   0.050  0 of 25      0.000                           0.000                    0.350                0.008        0.106
 one, sure adaptive_bayes, reached tests                   0.100  2 of 25      0.080                           0.167                    0.341                0.008        0.103
 one, sure adaptive_bayes, reached tests                   0.200  3 of 25      0.120                           0.231                    0.095                0.007        0.032
 per group                        random                   0.050  1 of 25      0.040                           0.091                    0.366                0.022        0.121
 per group                        random                   0.100  5 of 25      0.200                           0.333                    0.250                0.021        0.086
 per group                        random                   0.200  7 of 25      0.280                           0.412                    0.188                0.018        0.067
 per group                 text (TF-IDF)                   0.050  0 of 25      0.000                           0.000                    0.342                0.016        0.109
 per group                 text (TF-IDF)                   0.100  2 of 25      0.080                           0.167                    0.252                0.014        0.082
 per group                 text (TF-IDF)                   0.200  3 of 25      0.120                           0.231                    0.224                0.014        0.074
 per group                       learned                   0.050  5 of 25      0.200                           0.333                    0.295                0.007        0.089
 per group                       learned                   0.100  5 of 25      0.200                           0.333                    0.282                0.007        0.086
 per group                       learned                   0.200  6 of 25      0.240                           0.375                    0.275                0.007        0.083
 per group              learned + replay                   0.050  0 of 25      0.000                           0.000                    0.310                0.022        0.104
 per group              learned + replay                   0.100  1 of 25      0.040                           0.091                    0.286                0.021        0.097
 per group              learned + replay                   0.200  1 of 25      0.040                           0.091                    0.190                0.020        0.068
 per group                adaptive_bayes                   0.050  0 of 25      0.000                           0.000                    0.338                0.008        0.102
 per group                adaptive_bayes                   0.100  0 of 25      0.000                           0.000                    0.153                0.008        0.050
 per group                adaptive_bayes                   0.200  3 of 25      0.120                           0.231                    0.096                0.006        0.032
 per group adaptive_bayes, reached tests                   0.050  0 of 25      0.000                           0.000                    0.340                0.008        0.103
 per group adaptive_bayes, reached tests                   0.100  0 of 25      0.000                           0.000                    0.156                0.008        0.050
 per group adaptive_bayes, reached tests                   0.200  3 of 25      0.120                           0.231                    0.095                0.006        0.031
```
