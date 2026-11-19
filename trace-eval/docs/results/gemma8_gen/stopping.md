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
  | `per group, floor last` | per group, with the change's coverage floor run before a clean verdict |
  | `per group, floor first` | per group, with the coverage floor run before the plan |

- `miss rate` is the share of the regressions called clean, `highest` its highest value among the twenty splits,
  and `splits over target` the share of the splits whose miss rate is over the target.
- Tokens are shares of the full suite; `tokens, no test reveals` is what a clean verdict costs.
- `target 0` runs every reached test; `none (eps_clean = 0.05)` is `adaptive_bayes` with its own constant.
- `coverage when clean` is, on a clean verdict, the share of what the tests can cover of the change (the changed
  components and the affected mandatory properties) that the tests run and the replayed ones cover.
- The last table gives two selections that never stop on a value: a fixed minimal set of the whole suite
  (test-suite minimization, chosen once without the change) and the change's coverage floor alone.

```text
[loaded runs/gemma8_gen: 180 tests, 691 variants, 9 s]
runs/gemma8_gen: 691 changes; the replay settles 134 (35 as regressions); of the other 557, 281 are regressions

20 splits: a quarter of the changes is what a rule learns from, a quarter sets the threshold (64 to 75 regressions), half measures the rule.
A target under 0.015 leaves no threshold in some split: every diverged test runs there.

the rules on the measured changes: means over the splits, tokens as shares of the full suite
            thresholds                          rule                  target  miss rate  highest splits over target  clean verdicts on a regression  tokens, no test reveals  tokens, regressions  tokens, all  coverage when clean
                   one                        random                   0.000      0.000    0.000              0.000                           0.000                    0.201                0.047        0.123                1.000
                   one                        random                   0.050      0.038    0.085              0.250                           0.037                    0.172                0.046        0.108                0.995
                   one                        random                   0.100      0.079    0.113              0.300                           0.075                    0.136                0.045        0.090                0.985
                   one                        random                   0.200      0.181    0.273              0.350                           0.157                    0.089                0.040        0.064                0.968
                   one                 text (TF-IDF)                   0.000      0.000    0.000              0.000                           0.000                    0.201                0.037        0.117                1.000
                   one                 text (TF-IDF)                   0.050      0.022    0.112              0.250                           0.021                    0.185                0.035        0.109                0.996
                   one                 text (TF-IDF)                   0.100      0.096    0.167              0.350                           0.088                    0.128                0.029        0.078                0.972
                   one                 text (TF-IDF)                   0.200      0.210    0.350              0.550                           0.177                    0.077                0.019        0.048                0.916
                   one                       learned                   0.000      0.000    0.000              0.000                           0.000                    0.201                0.057        0.128                1.000
                   one                       learned                   0.050      0.043    0.085              0.400                           0.042                    0.124                0.051        0.087                0.925
                   one                       learned                   0.100      0.098    0.208              0.400                           0.092                    0.078                0.041        0.059                0.824
                   one                       learned                   0.200      0.195    0.271              0.400                           0.167                    0.032                0.033        0.032                0.767
                   one              learned + replay                   0.000      0.000    0.000              0.000                           0.000                    0.201                0.049        0.124                1.000
                   one              learned + replay                   0.050      0.044    0.156              0.350                           0.043                    0.116                0.043        0.079                0.935
                   one              learned + replay                   0.100      0.097    0.177              0.450                           0.090                    0.080                0.039        0.059                0.868
                   one              learned + replay                   0.200      0.212    0.322              0.600                           0.179                    0.032                0.028        0.030                0.748
                   one                adaptive_bayes                   0.000      0.000    0.000              0.000                           0.000                    0.201                0.036        0.117                1.000
                   one                adaptive_bayes                   0.050      0.045    0.135              0.400                           0.043                    0.185                0.032        0.107                0.978
                   one                adaptive_bayes                   0.100      0.099    0.220              0.450                           0.092                    0.140                0.025        0.081                0.935
                   one                adaptive_bayes                   0.200      0.189    0.255              0.400                           0.163                    0.079                0.013        0.046                0.842
                   one                adaptive_bayes none (eps_clean = 0.05)      0.074    0.109                NaN                           0.071                    0.156                0.029        0.091                0.960
                   one adaptive_bayes, reached tests                   0.000      0.000    0.000              0.000                           0.000                    0.201                0.036        0.117                1.000
                   one adaptive_bayes, reached tests                   0.050      0.041    0.129              0.350                           0.040                    0.191                0.033        0.111                0.980
                   one adaptive_bayes, reached tests                   0.100      0.092    0.177              0.450                           0.086                    0.168                0.029        0.097                0.961
                   one adaptive_bayes, reached tests                   0.200      0.191    0.308              0.450                           0.163                    0.109                0.018        0.063                0.872
             one, sure                        random                   0.050      0.010    0.044              0.000                           0.010                    0.188                0.047        0.116                0.997
             one, sure                        random                   0.100      0.051    0.102              0.050                           0.050                    0.160                0.046        0.102                0.992
             one, sure                        random                   0.200      0.110    0.156              0.000                           0.102                    0.113                0.043        0.078                0.978
             one, sure                 text (TF-IDF)                   0.050      0.000    0.000              0.000                           0.000                    0.201                0.037        0.117                1.000
             one, sure                 text (TF-IDF)                   0.100      0.039    0.125              0.150                           0.037                    0.177                0.034        0.104                0.993
             one, sure                 text (TF-IDF)                   0.200      0.149    0.246              0.250                           0.131                    0.099                0.023        0.061                0.943
             one, sure                       learned                   0.050      0.011    0.042              0.000                           0.011                    0.170                0.056        0.112                0.987
             one, sure                       learned                   0.100      0.054    0.099              0.000                           0.053                    0.111                0.049        0.079                0.894
             one, sure                       learned                   0.200      0.143    0.250              0.100                           0.128                    0.051                0.037        0.044                0.793
             one, sure              learned + replay                   0.050      0.012    0.064              0.100                           0.012                    0.162                0.047        0.104                0.982
             one, sure              learned + replay                   0.100      0.060    0.170              0.100                           0.058                    0.099                0.041        0.070                0.905
             one, sure              learned + replay                   0.200      0.147    0.266              0.100                           0.131                    0.057                0.034        0.045                0.815
             one, sure                adaptive_bayes                   0.050      0.010    0.049              0.000                           0.010                    0.199                0.035        0.116                0.996
             one, sure                adaptive_bayes                   0.100      0.061    0.135              0.150                           0.058                    0.177                0.030        0.102                0.969
             one, sure                adaptive_bayes                   0.200      0.143    0.255              0.150                           0.127                    0.105                0.018        0.061                0.877
             one, sure adaptive_bayes, reached tests                   0.050      0.009    0.049              0.000                           0.009                    0.199                0.036        0.116                0.997
             one, sure adaptive_bayes, reached tests                   0.100      0.058    0.129              0.100                           0.056                    0.188                0.032        0.109                0.973
             one, sure adaptive_bayes, reached tests                   0.200      0.139    0.234              0.200                           0.123                    0.135                0.024        0.079                0.932
             per group                        random                   0.050      0.009    0.028              0.000                           0.009                    0.200                0.047        0.122                0.995
             per group                        random                   0.100      0.055    0.109              0.050                           0.053                    0.188                0.046        0.116                0.990
             per group                        random                   0.200      0.149    0.248              0.150                           0.132                    0.132                0.044        0.087                0.972
             per group                 text (TF-IDF)                   0.050      0.013    0.051              0.050                           0.014                    0.199                0.035        0.115                0.993
             per group                 text (TF-IDF)                   0.100      0.066    0.169              0.200                           0.063                    0.180                0.031        0.104                0.971
             per group                 text (TF-IDF)                   0.200      0.151    0.221              0.150                           0.134                    0.122                0.026        0.073                0.931
             per group                       learned                   0.050      0.014    0.057              0.050                           0.014                    0.199                0.056        0.126                0.997
             per group                       learned                   0.100      0.052    0.105              0.050                           0.050                    0.181                0.054        0.117                0.992
             per group                       learned                   0.200      0.135    0.230              0.150                           0.120                    0.143                0.050        0.096                0.978
             per group              learned + replay                   0.050      0.019    0.059              0.050                           0.019                    0.197                0.046        0.120                0.989
             per group              learned + replay                   0.100      0.070    0.153              0.250                           0.066                    0.182                0.042        0.111                0.966
             per group              learned + replay                   0.200      0.140    0.197              0.000                           0.126                    0.140                0.037        0.088                0.920
             per group                adaptive_bayes                   0.050      0.010    0.049              0.000                           0.010                    0.199                0.035        0.116                0.996
             per group                adaptive_bayes                   0.100      0.053    0.121              0.050                           0.051                    0.175                0.032        0.102                0.982
             per group                adaptive_bayes                   0.200      0.127    0.245              0.100                           0.114                    0.122                0.026        0.073                0.955
             per group adaptive_bayes, reached tests                   0.050      0.010    0.049              0.000                           0.010                    0.199                0.036        0.116                0.996
             per group adaptive_bayes, reached tests                   0.100      0.057    0.128              0.100                           0.055                    0.176                0.032        0.103                0.976
             per group adaptive_bayes, reached tests                   0.200      0.141    0.241              0.150                           0.125                    0.122                0.026        0.073                0.946
per group, floor first                        random                   0.050      0.002    0.007              0.000                           0.002                    0.200                0.043        0.120                1.000
per group, floor first                        random                   0.100      0.037    0.080              0.000                           0.036                    0.188                0.043        0.114                1.000
per group, floor first                        random                   0.200      0.107    0.182              0.000                           0.098                    0.134                0.041        0.087                1.000
per group, floor first                 text (TF-IDF)                   0.050      0.012    0.043              0.000                           0.012                    0.199                0.033        0.114                1.000
per group, floor first                 text (TF-IDF)                   0.100      0.052    0.132              0.100                           0.050                    0.181                0.030        0.104                1.000
per group, floor first                 text (TF-IDF)                   0.200      0.108    0.156              0.000                           0.099                    0.124                0.025        0.074                1.000
per group, floor first                       learned                   0.050      0.012    0.050              0.000                           0.012                    0.199                0.050        0.123                1.000
per group, floor first                       learned                   0.100      0.041    0.098              0.000                           0.039                    0.182                0.048        0.114                1.000
per group, floor first                       learned                   0.200      0.110    0.200              0.000                           0.100                    0.144                0.045        0.094                1.000
per group, floor first              learned + replay                   0.050      0.016    0.044              0.000                           0.016                    0.197                0.041        0.118                1.000
per group, floor first              learned + replay                   0.100      0.056    0.109              0.100                           0.053                    0.182                0.038        0.109                1.000
per group, floor first              learned + replay                   0.200      0.101    0.156              0.000                           0.094                    0.142                0.033        0.087                1.000
per group, floor first                adaptive_bayes                   0.050      0.009    0.042              0.000                           0.009                    0.199                0.034        0.115                1.000
per group, floor first                adaptive_bayes                   0.100      0.044    0.099              0.000                           0.043                    0.175                0.031        0.102                1.000
per group, floor first                adaptive_bayes                   0.200      0.107    0.203              0.050                           0.098                    0.123                0.026        0.074                1.000
per group, floor first adaptive_bayes, reached tests                   0.050      0.009    0.042              0.000                           0.009                    0.199                0.034        0.115                1.000
per group, floor first adaptive_bayes, reached tests                   0.100      0.048    0.102              0.050                           0.046                    0.176                0.031        0.102                1.000
per group, floor first adaptive_bayes, reached tests                   0.200      0.118    0.196              0.000                           0.107                    0.123                0.026        0.074                1.000
 per group, floor last                        random                   0.050      0.002    0.007              0.000                           0.002                    0.200                0.047        0.122                1.000
 per group, floor last                        random                   0.100      0.037    0.080              0.000                           0.036                    0.188                0.046        0.116                1.000
 per group, floor last                        random                   0.200      0.107    0.182              0.000                           0.098                    0.134                0.044        0.088                1.000
 per group, floor last                 text (TF-IDF)                   0.050      0.012    0.043              0.000                           0.012                    0.199                0.035        0.115                1.000
 per group, floor last                 text (TF-IDF)                   0.100      0.052    0.132              0.100                           0.050                    0.181                0.032        0.105                1.000
 per group, floor last                 text (TF-IDF)                   0.200      0.108    0.156              0.000                           0.099                    0.124                0.027        0.074                1.000
 per group, floor last                       learned                   0.050      0.012    0.050              0.000                           0.012                    0.199                0.056        0.126                1.000
 per group, floor last                       learned                   0.100      0.041    0.098              0.000                           0.039                    0.182                0.054        0.117                1.000
 per group, floor last                       learned                   0.200      0.110    0.200              0.000                           0.100                    0.144                0.051        0.097                1.000
 per group, floor last              learned + replay                   0.050      0.016    0.044              0.000                           0.016                    0.197                0.046        0.121                1.000
 per group, floor last              learned + replay                   0.100      0.056    0.109              0.100                           0.053                    0.182                0.043        0.111                1.000
 per group, floor last              learned + replay                   0.200      0.101    0.156              0.000                           0.094                    0.142                0.039        0.089                1.000
 per group, floor last                adaptive_bayes                   0.050      0.009    0.042              0.000                           0.009                    0.199                0.035        0.116                1.000
 per group, floor last                adaptive_bayes                   0.100      0.044    0.099              0.000                           0.043                    0.175                0.032        0.102                1.000
 per group, floor last                adaptive_bayes                   0.200      0.107    0.203              0.050                           0.098                    0.123                0.027        0.074                1.000
 per group, floor last adaptive_bayes, reached tests                   0.050      0.009    0.042              0.000                           0.009                    0.199                0.036        0.116                1.000
 per group, floor last adaptive_bayes, reached tests                   0.100      0.048    0.102              0.050                           0.046                    0.176                0.033        0.103                1.000
 per group, floor last adaptive_bayes, reached tests                   0.200      0.118    0.196              0.000                           0.107                    0.123                0.027        0.075                1.000

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
            thresholds                          rule                  target     missed  miss rate  clean verdicts on a regression  tokens, no test reveals  tokens, regressions  tokens, all  coverage when clean
                   one                        random                   0.000   0 of 281      0.000                           0.000                    0.199                0.046        0.122                1.000
                   one                        random                   0.050  12 of 281      0.043                           0.042                    0.170                0.045        0.107                0.995
                   one                        random                   0.100  27 of 281      0.096                           0.089                    0.124                0.043        0.083                0.985
                   one                        random                   0.200  53 of 281      0.189                           0.161                    0.086                0.038        0.062                0.965
                   one                 text (TF-IDF)                   0.000   0 of 281      0.000                           0.000                    0.199                0.036        0.117                1.000
                   one                 text (TF-IDF)                   0.050  11 of 281      0.039                           0.038                    0.199                0.035        0.116                1.000
                   one                 text (TF-IDF)                   0.100  25 of 281      0.089                           0.083                    0.126                0.030        0.077                0.984
                   one                 text (TF-IDF)                   0.200  53 of 281      0.189                           0.161                    0.086                0.020        0.053                0.931
                   one                       learned                   0.000   0 of 281      0.000                           0.000                    0.199                0.043        0.120                1.000
                   one                       learned                   0.050  12 of 281      0.043                           0.042                    0.143                0.036        0.089                0.900
                   one                       learned                   0.100  25 of 281      0.089                           0.083                    0.074                0.026        0.050                0.770
                   one                       learned                   0.200  59 of 281      0.210                           0.176                    0.022                0.017        0.020                0.764
                   one              learned + replay                   0.000   0 of 281      0.000                           0.000                    0.199                0.041        0.119                1.000
                   one              learned + replay                   0.050  18 of 281      0.064                           0.061                    0.085                0.032        0.058                0.868
                   one              learned + replay                   0.100  33 of 281      0.117                           0.107                    0.060                0.027        0.043                0.809
                   one              learned + replay                   0.200 112 of 281      0.399                           0.289                    0.015                0.012        0.013                0.684
                   one                adaptive_bayes                   0.000   0 of 281      0.000                           0.000                    0.199                0.035        0.116                1.000
                   one                adaptive_bayes                   0.050  16 of 281      0.057                           0.055                    0.194                0.030        0.112                0.971
                   one                adaptive_bayes                   0.100  28 of 281      0.100                           0.092                    0.137                0.025        0.080                0.956
                   one                adaptive_bayes                   0.200  73 of 281      0.260                           0.209                    0.081                0.013        0.047                0.851
                   one                adaptive_bayes none (eps_clean = 0.05)  21 of 281      0.075                           0.071                    0.153                0.028        0.090                0.966
                   one adaptive_bayes, reached tests                   0.000   0 of 281      0.000                           0.000                    0.199                0.035        0.116                1.000
                   one adaptive_bayes, reached tests                   0.050  16 of 281      0.057                           0.055                    0.194                0.030        0.111                0.972
                   one adaptive_bayes, reached tests                   0.100  24 of 281      0.085                           0.080                    0.146                0.027        0.086                0.963
                   one adaptive_bayes, reached tests                   0.200  41 of 281      0.146                           0.129                    0.113                0.019        0.065                0.845
             one, sure                        random                   0.050   9 of 281      0.032                           0.032                    0.180                0.045        0.112                0.995
             one, sure                        random                   0.100  18 of 281      0.064                           0.061                    0.152                0.044        0.097                0.994
             one, sure                        random                   0.200  41 of 281      0.146                           0.129                    0.094                0.040        0.067                0.967
             one, sure                 text (TF-IDF)                   0.050  10 of 281      0.036                           0.035                    0.199                0.036        0.116                1.000
             one, sure                 text (TF-IDF)                   0.100  11 of 281      0.039                           0.038                    0.181                0.035        0.108                0.998
             one, sure                 text (TF-IDF)                   0.200  41 of 281      0.146                           0.129                    0.097                0.023        0.060                0.944
             one, sure                       learned                   0.050   9 of 281      0.032                           0.032                    0.151                0.037        0.093                0.967
             one, sure                       learned                   0.100  13 of 281      0.046                           0.045                    0.112                0.035        0.073                0.863
             one, sure                       learned                   0.200  41 of 281      0.146                           0.129                    0.038                0.021        0.029                0.777
             one, sure              learned + replay                   0.050   7 of 281      0.025                           0.025                    0.129                0.036        0.082                0.940
             one, sure              learned + replay                   0.100  22 of 281      0.078                           0.074                    0.073                0.029        0.050                0.812
             one, sure              learned + replay                   0.200  86 of 281      0.306                           0.238                    0.028                0.017        0.023                0.753
             one, sure                adaptive_bayes                   0.050  16 of 281      0.057                           0.055                    0.194                0.031        0.112                0.972
             one, sure                adaptive_bayes                   0.100  22 of 281      0.078                           0.074                    0.157                0.029        0.092                0.964
             one, sure                adaptive_bayes                   0.200  49 of 281      0.174                           0.151                    0.101                0.017        0.059                0.845
             one, sure adaptive_bayes, reached tests                   0.050  15 of 281      0.053                           0.052                    0.194                0.031        0.112                0.974
             one, sure adaptive_bayes, reached tests                   0.100  17 of 281      0.060                           0.058                    0.194                0.030        0.111                0.971
             one, sure adaptive_bayes, reached tests                   0.200  30 of 281      0.107                           0.098                    0.131                0.024        0.077                0.929
             per group                        random                   0.050   2 of 281      0.007                           0.007                    0.196                0.046        0.120                1.000
             per group                        random                   0.100  10 of 281      0.036                           0.035                    0.157                0.045        0.100                0.991
             per group                        random                   0.200  13 of 281      0.046                           0.045                    0.123                0.044        0.083                0.982
             per group                 text (TF-IDF)                   0.050   0 of 281      0.000                           0.000                    0.199                0.036        0.117                1.000
             per group                 text (TF-IDF)                   0.100   5 of 281      0.018                           0.018                    0.159                0.034        0.096                0.994
             per group                 text (TF-IDF)                   0.200  43 of 281      0.153                           0.135                    0.104                0.024        0.064                0.909
             per group                       learned                   0.050   1 of 281      0.004                           0.004                    0.188                0.043        0.115                1.000
             per group                       learned                   0.100  13 of 281      0.046                           0.045                    0.171                0.043        0.106                0.986
             per group                       learned                   0.200  18 of 281      0.064                           0.061                    0.138                0.041        0.089                0.958
             per group              learned + replay                   0.050   0 of 281      0.000                           0.000                    0.197                0.041        0.119                1.000
             per group              learned + replay                   0.100   4 of 281      0.014                           0.014                    0.179                0.039        0.108                0.994
             per group              learned + replay                   0.200  49 of 281      0.174                           0.151                    0.131                0.031        0.081                0.919
             per group                adaptive_bayes                   0.050   1 of 281      0.004                           0.004                    0.184                0.035        0.109                1.000
             per group                adaptive_bayes                   0.100   9 of 281      0.032                           0.032                    0.136                0.031        0.083                0.989
             per group                adaptive_bayes                   0.200  31 of 281      0.110                           0.101                    0.096                0.022        0.059                0.927
             per group adaptive_bayes, reached tests                   0.050   1 of 281      0.004                           0.004                    0.184                0.035        0.109                1.000
             per group adaptive_bayes, reached tests                   0.100   9 of 281      0.032                           0.032                    0.138                0.031        0.084                0.989
             per group adaptive_bayes, reached tests                   0.200  31 of 281      0.110                           0.101                    0.095                0.022        0.058                0.927
per group, floor first                        random                   0.050   2 of 281      0.007                           0.007                    0.196                0.042        0.118                1.000
per group, floor first                        random                   0.100   8 of 281      0.028                           0.028                    0.158                0.041        0.099                1.000
per group, floor first                        random                   0.200  10 of 281      0.036                           0.035                    0.125                0.041        0.082                1.000
per group, floor first                 text (TF-IDF)                   0.050   0 of 281      0.000                           0.000                    0.199                0.033        0.115                1.000
per group, floor first                 text (TF-IDF)                   0.100   5 of 281      0.018                           0.018                    0.160                0.032        0.095                1.000
per group, floor first                 text (TF-IDF)                   0.200  23 of 281      0.082                           0.077                    0.106                0.024        0.065                1.000
per group, floor first                       learned                   0.050   1 of 281      0.004                           0.004                    0.188                0.037        0.112                1.000
per group, floor first                       learned                   0.100   6 of 281      0.021                           0.021                    0.172                0.037        0.104                1.000
per group, floor first                       learned                   0.200   9 of 281      0.032                           0.032                    0.140                0.036        0.087                1.000
per group, floor first              learned + replay                   0.050   0 of 281      0.000                           0.000                    0.197                0.037        0.116                1.000
per group, floor first              learned + replay                   0.100   4 of 281      0.014                           0.014                    0.180                0.035        0.107                1.000
per group, floor first              learned + replay                   0.200  27 of 281      0.096                           0.089                    0.134                0.027        0.080                1.000
per group, floor first                adaptive_bayes                   0.050   1 of 281      0.004                           0.004                    0.184                0.034        0.108                1.000
per group, floor first                adaptive_bayes                   0.100   8 of 281      0.028                           0.028                    0.137                0.030        0.083                1.000
per group, floor first                adaptive_bayes                   0.200  25 of 281      0.089                           0.083                    0.098                0.023        0.060                1.000
per group, floor first adaptive_bayes, reached tests                   0.050   1 of 281      0.004                           0.004                    0.184                0.034        0.108                1.000
per group, floor first adaptive_bayes, reached tests                   0.100   8 of 281      0.028                           0.028                    0.138                0.030        0.084                1.000
per group, floor first adaptive_bayes, reached tests                   0.200  25 of 281      0.089                           0.083                    0.097                0.023        0.059                1.000
 per group, floor last                        random                   0.050   2 of 281      0.007                           0.007                    0.196                0.046        0.120                1.000
 per group, floor last                        random                   0.100   8 of 281      0.028                           0.028                    0.158                0.045        0.101                1.000
 per group, floor last                        random                   0.200  10 of 281      0.036                           0.035                    0.125                0.044        0.084                1.000
 per group, floor last                 text (TF-IDF)                   0.050   0 of 281      0.000                           0.000                    0.199                0.036        0.117                1.000
 per group, floor last                 text (TF-IDF)                   0.100   5 of 281      0.018                           0.018                    0.160                0.035        0.097                1.000
 per group, floor last                 text (TF-IDF)                   0.200  23 of 281      0.082                           0.077                    0.106                0.026        0.066                1.000
 per group, floor last                       learned                   0.050   1 of 281      0.004                           0.004                    0.188                0.043        0.115                1.000
 per group, floor last                       learned                   0.100   6 of 281      0.021                           0.021                    0.172                0.043        0.107                1.000
 per group, floor last                       learned                   0.200   9 of 281      0.032                           0.032                    0.140                0.042        0.090                1.000
 per group, floor last              learned + replay                   0.050   0 of 281      0.000                           0.000                    0.197                0.041        0.119                1.000
 per group, floor last              learned + replay                   0.100   4 of 281      0.014                           0.014                    0.180                0.039        0.109                1.000
 per group, floor last              learned + replay                   0.200  27 of 281      0.096                           0.089                    0.134                0.032        0.082                1.000
 per group, floor last                adaptive_bayes                   0.050   1 of 281      0.004                           0.004                    0.184                0.035        0.109                1.000
 per group, floor last                adaptive_bayes                   0.100   8 of 281      0.028                           0.028                    0.137                0.031        0.084                1.000
 per group, floor last                adaptive_bayes                   0.200  25 of 281      0.089                           0.083                    0.098                0.023        0.060                1.000
 per group, floor last adaptive_bayes, reached tests                   0.050   1 of 281      0.004                           0.004                    0.184                0.035        0.109                1.000
 per group, floor last adaptive_bayes, reached tests                   0.100   8 of 281      0.028                           0.028                    0.138                0.031        0.084                1.000
 per group, floor last adaptive_bayes, reached tests                   0.200  25 of 281      0.089                           0.083                    0.097                0.023        0.060                1.000
[loaded runs/gemma8: 180 tests, 43 variants, 1 s]

runs/gemma8: 43 changes; the replay settles 8 (3 as regressions); of the other 35, 25 are regressions

the rules learnt on 281 changes of runs/gemma8_gen, their thresholds set on the other 276 (144 regressions), run on those changes
            thresholds                          rule                  target   missed  miss rate  clean verdicts on a regression  tokens, no test reveals  tokens, regressions  tokens, all  coverage when clean
                   one                        random                   0.000  0 of 25      0.000                           0.000                    0.370                0.022        0.122                1.000
                   one                        random                   0.050  1 of 25      0.040                           0.091                    0.321                0.022        0.108                1.000
                   one                        random                   0.100  5 of 25      0.200                           0.333                    0.232                0.022        0.082                0.990
                   one                        random                   0.200 10 of 25      0.400                           0.500                    0.158                0.015        0.055                0.986
                   one                 text (TF-IDF)                   0.000  0 of 25      0.000                           0.000                    0.370                0.016        0.117                1.000
                   one                 text (TF-IDF)                   0.050  0 of 25      0.000                           0.000                    0.370                0.016        0.117                1.000
                   one                 text (TF-IDF)                   0.100  2 of 25      0.080                           0.167                    0.256                0.014        0.083                1.000
                   one                 text (TF-IDF)                   0.200  4 of 25      0.160                           0.286                    0.173                0.014        0.060                0.939
                   one                       learned                   0.000  0 of 25      0.000                           0.000                    0.370                0.008        0.111                1.000
                   one                       learned                   0.050  3 of 25      0.120                           0.231                    0.277                0.007        0.085                0.829
                   one                       learned                   0.100  4 of 25      0.160                           0.286                    0.055                0.007        0.021                0.589
                   one                       learned                   0.200  4 of 25      0.160                           0.286                    0.041                0.007        0.017                0.517
                   one              learned + replay                   0.000  0 of 25      0.000                           0.000                    0.370                0.022        0.121                1.000
                   one              learned + replay                   0.050  0 of 25      0.000                           0.000                    0.131                0.022        0.053                0.904
                   one              learned + replay                   0.100  1 of 25      0.040                           0.091                    0.063                0.021        0.033                0.654
                   one              learned + replay                   0.200  4 of 25      0.160                           0.286                    0.034                0.017        0.022                0.651
                   one                adaptive_bayes                   0.000  0 of 25      0.000                           0.000                    0.370                0.008        0.112                1.000
                   one                adaptive_bayes                   0.050  0 of 25      0.000                           0.000                    0.370                0.008        0.112                1.000
                   one                adaptive_bayes                   0.100  2 of 25      0.080                           0.167                    0.135                0.007        0.044                0.905
                   one                adaptive_bayes                   0.200  5 of 25      0.200                           0.333                    0.037                0.007        0.015                0.640
                   one                adaptive_bayes none (eps_clean = 0.05)  2 of 25      0.080                           0.167                    0.192                0.007        0.060                0.929
                   one adaptive_bayes, reached tests                   0.000  0 of 25      0.000                           0.000                    0.370                0.008        0.112                1.000
                   one adaptive_bayes, reached tests                   0.050  0 of 25      0.000                           0.000                    0.349                0.008        0.106                0.986
                   one adaptive_bayes, reached tests                   0.100  2 of 25      0.080                           0.167                    0.148                0.007        0.048                0.917
                   one adaptive_bayes, reached tests                   0.200  6 of 25      0.240                           0.375                    0.042                0.007        0.017                0.609
             one, sure                        random                   0.050  1 of 25      0.040                           0.091                    0.340                0.022        0.113                1.000
             one, sure                        random                   0.100  1 of 25      0.040                           0.091                    0.287                0.022        0.098                1.000
             one, sure                        random                   0.200 10 of 25      0.400                           0.500                    0.172                0.018        0.062                0.986
             one, sure                 text (TF-IDF)                   0.050  0 of 25      0.000                           0.000                    0.370                0.016        0.117                1.000
             one, sure                 text (TF-IDF)                   0.100  0 of 25      0.000                           0.000                    0.354                0.016        0.112                1.000
             one, sure                 text (TF-IDF)                   0.200  3 of 25      0.120                           0.231                    0.203                0.014        0.068                0.945
             one, sure                       learned                   0.050  3 of 25      0.120                           0.231                    0.308                0.007        0.093                0.829
             one, sure                       learned                   0.100  3 of 25      0.120                           0.231                    0.164                0.007        0.052                0.829
             one, sure                       learned                   0.200  4 of 25      0.160                           0.286                    0.041                0.007        0.017                0.517
             one, sure              learned + replay                   0.050  0 of 25      0.000                           0.000                    0.231                0.022        0.081                0.971
             one, sure              learned + replay                   0.100  0 of 25      0.000                           0.000                    0.122                0.022        0.050                0.875
             one, sure              learned + replay                   0.200  2 of 25      0.080                           0.167                    0.043                0.020        0.027                0.650
             one, sure                adaptive_bayes                   0.050  0 of 25      0.000                           0.000                    0.370                0.008        0.112                1.000
             one, sure                adaptive_bayes                   0.100  2 of 25      0.080                           0.167                    0.213                0.007        0.066                0.940
             one, sure                adaptive_bayes                   0.200  5 of 25      0.200                           0.333                    0.043                0.007        0.017                0.640
             one, sure adaptive_bayes, reached tests                   0.050  0 of 25      0.000                           0.000                    0.350                0.008        0.106                0.986
             one, sure adaptive_bayes, reached tests                   0.100  2 of 25      0.080                           0.167                    0.341                0.008        0.103                0.964
             one, sure adaptive_bayes, reached tests                   0.200  3 of 25      0.120                           0.231                    0.095                0.007        0.032                0.846
             per group                        random                   0.050  1 of 25      0.040                           0.091                    0.366                0.022        0.121                1.000
             per group                        random                   0.100  5 of 25      0.200                           0.333                    0.250                0.021        0.086                0.990
             per group                        random                   0.200  7 of 25      0.280                           0.412                    0.188                0.018        0.067                0.983
             per group                 text (TF-IDF)                   0.050  0 of 25      0.000                           0.000                    0.342                0.016        0.109                0.986
             per group                 text (TF-IDF)                   0.100  2 of 25      0.080                           0.167                    0.252                0.014        0.082                0.988
             per group                 text (TF-IDF)                   0.200  3 of 25      0.120                           0.231                    0.224                0.014        0.074                0.945
             per group                       learned                   0.050  5 of 25      0.200                           0.333                    0.295                0.007        0.089                0.830
             per group                       learned                   0.100  5 of 25      0.200                           0.333                    0.282                0.007        0.086                0.830
             per group                       learned                   0.200  6 of 25      0.240                           0.375                    0.275                0.007        0.083                0.840
             per group              learned + replay                   0.050  0 of 25      0.000                           0.000                    0.310                0.022        0.104                1.000
             per group              learned + replay                   0.100  1 of 25      0.040                           0.091                    0.286                0.021        0.097                0.987
             per group              learned + replay                   0.200  1 of 25      0.040                           0.091                    0.190                0.020        0.068                0.950
             per group                adaptive_bayes                   0.050  0 of 25      0.000                           0.000                    0.338                0.008        0.102                0.986
             per group                adaptive_bayes                   0.100  0 of 25      0.000                           0.000                    0.153                0.008        0.050                0.957
             per group                adaptive_bayes                   0.200  3 of 25      0.120                           0.231                    0.096                0.006        0.032                0.945
             per group adaptive_bayes, reached tests                   0.050  0 of 25      0.000                           0.000                    0.340                0.008        0.103                0.986
             per group adaptive_bayes, reached tests                   0.100  0 of 25      0.000                           0.000                    0.156                0.008        0.050                0.957
             per group adaptive_bayes, reached tests                   0.200  3 of 25      0.120                           0.231                    0.095                0.006        0.031                0.945
per group, floor first                        random                   0.050  1 of 25      0.040                           0.091                    0.367                0.023        0.121                1.000
per group, floor first                        random                   0.100  4 of 25      0.160                           0.286                    0.254                0.022        0.088                1.000
per group, floor first                        random                   0.200  6 of 25      0.240                           0.375                    0.194                0.019        0.069                1.000
per group, floor first                 text (TF-IDF)                   0.050  0 of 25      0.000                           0.000                    0.343                0.014        0.108                1.000
per group, floor first                 text (TF-IDF)                   0.100  2 of 25      0.080                           0.167                    0.253                0.013        0.081                1.000
per group, floor first                 text (TF-IDF)                   0.200  2 of 25      0.080                           0.167                    0.226                0.013        0.073                1.000
per group, floor first                       learned                   0.050  3 of 25      0.120                           0.231                    0.296                0.008        0.090                1.000
per group, floor first                       learned                   0.100  3 of 25      0.120                           0.231                    0.283                0.008        0.086                1.000
per group, floor first                       learned                   0.200  4 of 25      0.160                           0.286                    0.276                0.007        0.084                1.000
per group, floor first              learned + replay                   0.050  0 of 25      0.000                           0.000                    0.311                0.018        0.102                1.000
per group, floor first              learned + replay                   0.100  1 of 25      0.040                           0.091                    0.288                0.017        0.094                1.000
per group, floor first              learned + replay                   0.200  1 of 25      0.040                           0.091                    0.196                0.016        0.067                1.000
per group, floor first                adaptive_bayes                   0.050  0 of 25      0.000                           0.000                    0.338                0.010        0.104                1.000
per group, floor first                adaptive_bayes                   0.100  0 of 25      0.000                           0.000                    0.157                0.010        0.052                1.000
per group, floor first                adaptive_bayes                   0.200  2 of 25      0.080                           0.167                    0.100                0.008        0.034                1.000
per group, floor first adaptive_bayes, reached tests                   0.050  0 of 25      0.000                           0.000                    0.340                0.010        0.105                1.000
per group, floor first adaptive_bayes, reached tests                   0.100  0 of 25      0.000                           0.000                    0.160                0.010        0.053                1.000
per group, floor first adaptive_bayes, reached tests                   0.200  2 of 25      0.080                           0.167                    0.099                0.008        0.034                1.000
 per group, floor last                        random                   0.050  1 of 25      0.040                           0.091                    0.367                0.022        0.121                1.000
 per group, floor last                        random                   0.100  4 of 25      0.160                           0.286                    0.254                0.021        0.087                1.000
 per group, floor last                        random                   0.200  6 of 25      0.240                           0.375                    0.194                0.018        0.069                1.000
 per group, floor last                 text (TF-IDF)                   0.050  0 of 25      0.000                           0.000                    0.343                0.016        0.109                1.000
 per group, floor last                 text (TF-IDF)                   0.100  2 of 25      0.080                           0.167                    0.253                0.014        0.083                1.000
 per group, floor last                 text (TF-IDF)                   0.200  2 of 25      0.080                           0.167                    0.226                0.015        0.075                1.000
 per group, floor last                       learned                   0.050  3 of 25      0.120                           0.231                    0.296                0.008        0.090                1.000
 per group, floor last                       learned                   0.100  3 of 25      0.120                           0.231                    0.283                0.008        0.086                1.000
 per group, floor last                       learned                   0.200  4 of 25      0.160                           0.286                    0.276                0.007        0.084                1.000
 per group, floor last              learned + replay                   0.050  0 of 25      0.000                           0.000                    0.311                0.022        0.105                1.000
 per group, floor last              learned + replay                   0.100  1 of 25      0.040                           0.091                    0.288                0.021        0.097                1.000
 per group, floor last              learned + replay                   0.200  1 of 25      0.040                           0.091                    0.196                0.020        0.070                1.000
 per group, floor last                adaptive_bayes                   0.050  0 of 25      0.000                           0.000                    0.338                0.008        0.103                1.000
 per group, floor last                adaptive_bayes                   0.100  0 of 25      0.000                           0.000                    0.157                0.008        0.051                1.000
 per group, floor last                adaptive_bayes                   0.200  2 of 25      0.080                           0.167                    0.100                0.006        0.033                1.000
 per group, floor last adaptive_bayes, reached tests                   0.050  0 of 25      0.000                           0.000                    0.340                0.008        0.103                1.000
 per group, floor last adaptive_bayes, reached tests                   0.100  0 of 25      0.000                           0.000                    0.160                0.008        0.052                1.000
 per group, floor last adaptive_bayes, reached tests                   0.200  2 of 25      0.080                           0.167                    0.099                0.006        0.033                1.000

the fixed minimal set: 15 tests, 14.0% of the suite
                                        selection   missed  miss rate  clean verdicts on a regression  tokens, no test reveals  tokens, regressions  tokens, all  coverage when clean
a fixed minimal set, the tests the change reaches 13 of 25      0.520                           0.565                    0.066                0.020        0.033                1.000
                   a fixed minimal set, run whole 13 of 25      0.520                           0.565                    0.140                0.106        0.115                1.000
                         the coverage floor alone 18 of 25      0.720                           0.643                    0.010                0.003        0.005                1.000
```
