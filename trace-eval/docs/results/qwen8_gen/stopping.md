# Stopping with a bounded miss rate under Qwen: the full tables

The output of `scripts/analysis/stop_with_guarantee.py runs/qwen8_gen runs/qwen8_exact`, as it prints it. The
method is in [RESEARCH_PLAN.md](../../RESEARCH_PLAN.md) §3.4 and the reading of these tables in its §5.4.
[The same tables for Gemma](../gemma8_gen/stopping.md) explain every column.

- `runs/qwen8_gen` holds the generated changes and `runs/qwen8_exact` the 43 hand-written ones, both recorded with
  Qwen served one test at a time and without the prefix cache, one run per reached test.
- `thresholds` says how the threshold is set: `one` for all changes, `one, sure` lower so that the target holds for
  nine sets of past regressions in ten, `per group` one per group of changes, and `floor last` or `floor first`
  with the change's coverage floor run before a clean verdict or before the plan.
- Tokens are shares of the full suite; `tokens, no test reveals` is what a clean verdict costs.

```text
[loaded runs/qwen8_gen: 180 tests, 691 variants, 3 s]
runs/qwen8_gen: 691 changes; the replay settles 138 (36 as regressions); of the other 553, 321 are regressions

20 splits: a quarter of the changes is what a rule learns from, a quarter sets the threshold (70 to 85 regressions), half measures the rule.
A target under 0.014 leaves no threshold in some split: every diverged test runs there.

the rules on the measured changes: means over the splits, tokens as shares of the full suite
            thresholds                          rule                  target  miss rate  highest splits over target  clean verdicts on a regression  tokens, no test reveals  tokens, regressions  tokens, all  coverage when clean
                   one                        random                   0.000      0.000    0.000              0.000                           0.000                    0.150                0.066        0.101                1.000
                   one                        random                   0.050      0.049    0.150              0.400                           0.061                    0.128                0.065        0.091                0.992
                   one                        random                   0.100      0.096    0.212              0.400                           0.114                    0.107                0.062        0.081                0.985
                   one                        random                   0.200      0.180    0.350              0.350                           0.195                    0.083                0.057        0.068                0.971
                   one                 text (TF-IDF)                   0.000      0.000    0.000              0.000                           0.000                    0.150                0.061        0.099                1.000
                   one                 text (TF-IDF)                   0.050      0.037    0.108              0.350                           0.047                    0.145                0.060        0.096                0.998
                   one                 text (TF-IDF)                   0.100      0.101    0.160              0.500                           0.120                    0.107                0.049        0.074                0.969
                   one                 text (TF-IDF)                   0.200      0.223    0.327              0.800                           0.233                    0.071                0.037        0.051                0.920
                   one                       learned                   0.000      0.000    0.000              0.000                           0.000                    0.150                0.067        0.102                1.000
                   one                       learned                   0.050      0.041    0.144              0.300                           0.052                    0.116                0.061        0.084                0.967
                   one                       learned                   0.100      0.087    0.150              0.250                           0.106                    0.093                0.053        0.070                0.927
                   one                       learned                   0.200      0.201    0.341              0.500                           0.214                    0.057                0.039        0.047                0.832
                   one              learned + replay                   0.000      0.000    0.000              0.000                           0.000                    0.150                0.057        0.096                1.000
                   one              learned + replay                   0.050      0.046    0.110              0.350                           0.058                    0.114                0.054        0.079                0.960
                   one              learned + replay                   0.100      0.090    0.145              0.350                           0.108                    0.086                0.050        0.065                0.914
                   one              learned + replay                   0.200      0.192    0.264              0.500                           0.207                    0.053                0.042        0.047                0.845
                   one                adaptive_bayes                   0.000      0.000    0.000              0.000                           0.000                    0.150                0.051        0.092                1.000
                   one                adaptive_bayes                   0.050      0.040    0.071              0.350                           0.051                    0.148                0.044        0.088                0.977
                   one                adaptive_bayes                   0.100      0.097    0.176              0.400                           0.115                    0.139                0.034        0.078                0.955
                   one                adaptive_bayes                   0.200      0.199    0.311              0.550                           0.211                    0.096                0.017        0.050                0.854
                   one                adaptive_bayes none (eps_clean = 0.05)      0.091    0.133                NaN                           0.110                    0.144                0.034        0.080                0.963
                   one adaptive_bayes, reached tests                   0.000      0.000    0.000              0.000                           0.000                    0.150                0.049        0.091                1.000
                   one adaptive_bayes, reached tests                   0.050      0.040    0.082              0.350                           0.051                    0.147                0.042        0.087                0.977
                   one adaptive_bayes, reached tests                   0.100      0.088    0.151              0.400                           0.106                    0.140                0.036        0.080                0.960
                   one adaptive_bayes, reached tests                   0.200      0.180    0.252              0.400                           0.196                    0.120                0.023        0.064                0.912
             one, sure                        random                   0.050      0.026    0.091              0.200                           0.034                    0.137                0.066        0.096                0.995
             one, sure                        random                   0.100      0.060    0.156              0.100                           0.074                    0.123                0.065        0.089                0.992
             one, sure                        random                   0.200      0.135    0.269              0.100                           0.153                    0.095                0.060        0.075                0.978
             one, sure                 text (TF-IDF)                   0.050      0.005    0.069              0.050                           0.006                    0.149                0.061        0.098                1.000
             one, sure                 text (TF-IDF)                   0.100      0.057    0.127              0.100                           0.071                    0.136                0.058        0.091                0.993
             one, sure                 text (TF-IDF)                   0.200      0.152    0.231              0.100                           0.170                    0.087                0.043        0.061                0.947
             one, sure                       learned                   0.050      0.016    0.063              0.050                           0.021                    0.130                0.065        0.092                0.989
             one, sure                       learned                   0.100      0.052    0.150              0.050                           0.065                    0.110                0.060        0.081                0.960
             one, sure                       learned                   0.200      0.140    0.220              0.150                           0.159                    0.074                0.045        0.057                0.879
             one, sure              learned + replay                   0.050      0.024    0.075              0.150                           0.031                    0.131                0.055        0.087                0.982
             one, sure              learned + replay                   0.100      0.055    0.118              0.100                           0.069                    0.105                0.052        0.075                0.948
             one, sure              learned + replay                   0.200      0.137    0.218              0.100                           0.157                    0.074                0.048        0.059                0.893
             one, sure                adaptive_bayes                   0.050      0.011    0.038              0.000                           0.015                    0.150                0.048        0.091                0.997
             one, sure                adaptive_bayes                   0.100      0.054    0.094              0.000                           0.067                    0.147                0.043        0.087                0.970
             one, sure                adaptive_bayes                   0.200      0.143    0.255              0.100                           0.161                    0.123                0.024        0.066                0.919
             one, sure adaptive_bayes, reached tests                   0.050      0.008    0.038              0.000                           0.011                    0.149                0.047        0.090                0.997
             one, sure adaptive_bayes, reached tests                   0.100      0.050    0.113              0.100                           0.063                    0.147                0.041        0.086                0.971
             one, sure adaptive_bayes, reached tests                   0.200      0.122    0.226              0.100                           0.140                    0.135                0.030        0.074                0.950
             per group                        random                   0.050      0.015    0.064              0.050                           0.019                    0.149                0.066        0.101                0.991
             per group                        random                   0.100      0.075    0.175              0.200                           0.091                    0.128                0.065        0.091                0.980
             per group                        random                   0.200      0.151    0.263              0.150                           0.169                    0.106                0.061        0.080                0.973
             per group                 text (TF-IDF)                   0.050      0.011    0.045              0.000                           0.015                    0.149                0.060        0.098                0.996
             per group                 text (TF-IDF)                   0.100      0.076    0.122              0.300                           0.093                    0.116                0.054        0.080                0.974
             per group                 text (TF-IDF)                   0.200      0.160    0.258              0.100                           0.179                    0.082                0.043        0.059                0.931
             per group                       learned                   0.050      0.005    0.025              0.000                           0.007                    0.149                0.066        0.101                0.997
             per group                       learned                   0.100      0.062    0.122              0.150                           0.077                    0.115                0.064        0.086                0.981
             per group                       learned                   0.200      0.137    0.248              0.150                           0.155                    0.095                0.061        0.075                0.960
             per group              learned + replay                   0.050      0.010    0.038              0.000                           0.013                    0.149                0.056        0.095                0.997
             per group              learned + replay                   0.100      0.060    0.157              0.150                           0.075                    0.127                0.052        0.084                0.969
             per group              learned + replay                   0.200      0.147    0.258              0.150                           0.165                    0.099                0.046        0.068                0.910
             per group                adaptive_bayes                   0.050      0.004    0.032              0.000                           0.005                    0.150                0.050        0.092                0.999
             per group                adaptive_bayes                   0.100      0.044    0.087              0.000                           0.056                    0.116                0.043        0.074                0.982
             per group                adaptive_bayes                   0.200      0.140    0.203              0.050                           0.160                    0.078                0.029        0.049                0.949
             per group adaptive_bayes, reached tests                   0.050      0.001    0.012              0.000                           0.002                    0.150                0.048        0.091                1.000
             per group adaptive_bayes, reached tests                   0.100      0.047    0.082              0.000                           0.059                    0.117                0.041        0.073                0.980
             per group adaptive_bayes, reached tests                   0.200      0.150    0.209              0.150                           0.169                    0.079                0.027        0.049                0.947
per group, floor first                        random                   0.050      0.007    0.032              0.000                           0.009                    0.149                0.056        0.096                1.000
per group, floor first                        random                   0.100      0.055    0.156              0.050                           0.068                    0.128                0.055        0.086                1.000
per group, floor first                        random                   0.200      0.119    0.212              0.050                           0.138                    0.107                0.052        0.075                1.000
per group, floor first                 text (TF-IDF)                   0.050      0.010    0.038              0.000                           0.013                    0.149                0.053        0.093                1.000
per group, floor first                 text (TF-IDF)                   0.100      0.060    0.098              0.000                           0.075                    0.116                0.048        0.077                1.000
per group, floor first                 text (TF-IDF)                   0.200      0.117    0.189              0.000                           0.137                    0.083                0.039        0.058                1.000
per group, floor first                       learned                   0.050      0.003    0.019              0.000                           0.003                    0.149                0.054        0.094                1.000
per group, floor first                       learned                   0.100      0.044    0.091              0.000                           0.057                    0.116                0.052        0.079                1.000
per group, floor first                       learned                   0.200      0.102    0.191              0.000                           0.122                    0.096                0.050        0.069                1.000
per group, floor first              learned + replay                   0.050      0.009    0.038              0.000                           0.013                    0.149                0.047        0.090                1.000
per group, floor first              learned + replay                   0.100      0.053    0.132              0.050                           0.066                    0.128                0.044        0.079                1.000
per group, floor first              learned + replay                   0.200      0.118    0.214              0.050                           0.138                    0.101                0.039        0.065                1.000
per group, floor first                adaptive_bayes                   0.050      0.003    0.026              0.000                           0.004                    0.150                0.041        0.087                1.000
per group, floor first                adaptive_bayes                   0.100      0.036    0.081              0.000                           0.047                    0.116                0.036        0.070                1.000
per group, floor first                adaptive_bayes                   0.200      0.110    0.158              0.000                           0.130                    0.078                0.025        0.048                1.000
per group, floor first adaptive_bayes, reached tests                   0.050      0.001    0.006              0.000                           0.001                    0.150                0.040        0.086                1.000
per group, floor first adaptive_bayes, reached tests                   0.100      0.039    0.073              0.000                           0.050                    0.117                0.035        0.069                1.000
per group, floor first adaptive_bayes, reached tests                   0.200      0.120    0.165              0.000                           0.140                    0.079                0.024        0.047                1.000
 per group, floor last                        random                   0.050      0.007    0.032              0.000                           0.009                    0.149                0.066        0.101                1.000
 per group, floor last                        random                   0.100      0.055    0.156              0.050                           0.068                    0.128                0.065        0.091                1.000
 per group, floor last                        random                   0.200      0.119    0.212              0.050                           0.138                    0.107                0.062        0.081                1.000
 per group, floor last                 text (TF-IDF)                   0.050      0.010    0.038              0.000                           0.013                    0.149                0.060        0.098                1.000
 per group, floor last                 text (TF-IDF)                   0.100      0.060    0.098              0.000                           0.075                    0.116                0.055        0.081                1.000
 per group, floor last                 text (TF-IDF)                   0.200      0.117    0.189              0.000                           0.137                    0.083                0.044        0.061                1.000
 per group, floor last                       learned                   0.050      0.003    0.019              0.000                           0.003                    0.149                0.066        0.101                1.000
 per group, floor last                       learned                   0.100      0.044    0.091              0.000                           0.057                    0.116                0.064        0.086                1.000
 per group, floor last                       learned                   0.200      0.102    0.191              0.000                           0.122                    0.096                0.061        0.076                1.000
 per group, floor last              learned + replay                   0.050      0.009    0.038              0.000                           0.013                    0.149                0.056        0.095                1.000
 per group, floor last              learned + replay                   0.100      0.053    0.132              0.050                           0.066                    0.128                0.053        0.084                1.000
 per group, floor last              learned + replay                   0.200      0.118    0.214              0.050                           0.138                    0.101                0.047        0.070                1.000
 per group, floor last                adaptive_bayes                   0.050      0.003    0.026              0.000                           0.004                    0.150                0.050        0.092                1.000
 per group, floor last                adaptive_bayes                   0.100      0.036    0.081              0.000                           0.047                    0.116                0.043        0.074                1.000
 per group, floor last                adaptive_bayes                   0.200      0.110    0.158              0.000                           0.130                    0.078                0.029        0.050                1.000
 per group, floor last adaptive_bayes, reached tests                   0.050      0.001    0.006              0.000                           0.001                    0.150                0.048        0.091                1.000
 per group, floor last adaptive_bayes, reached tests                   0.100      0.039    0.073              0.000                           0.050                    0.117                0.042        0.074                1.000
 per group, floor last adaptive_bayes, reached tests                   0.200      0.120    0.165              0.000                           0.140                    0.079                0.028        0.050                1.000

the groups of changes, per split: {"a skill's steps": {'changes per split': 85.0, 'regressions': 27.2, 'tokens, every test': 0.12}, "an agent's tools and skills": {'changes per split': 25.0, 'regressions': 22.3, 'tokens, every test': 0.041}, 'code': {'changes per split': 45.0, 'regressions': 44.5, 'tokens, every test': 0.03}, 'text the model reads': {'changes per split': 77.0, 'regressions': 29.35, 'tokens, every test': 0.185}, 'the configuration': {'changes per split': 25.0, 'regressions': 23.0, 'tokens, every test': 0.027}, 'the starting data': {'changes per split': 17.0, 'regressions': 12.05, 'tokens, every test': 0.014}}

miss rate per group, target 0.1, thresholds: one
rule                         random  text (TF-IDF)  learned  learned + replay  adaptive_bayes  adaptive_bayes, reached tests
group                                                                                                                       
a skill's steps               0.134          0.072    0.031             0.213           0.011                          0.013
an agent's tools and skills   0.043          0.000    0.000             0.000           0.020                          0.018
code                          0.053          0.094    0.000             0.001           0.208                          0.210
text the model reads          0.198          0.150    0.440             0.286           0.181                          0.083
the configuration             0.046          0.000    0.000             0.000           0.000                          0.020
the starting data             0.116          0.456    0.000             0.000           0.000                          0.075

tokens per group, target 0.1, thresholds: one
rule                         random  text (TF-IDF)  learned  learned + replay  adaptive_bayes  adaptive_bayes, reached tests
group                                                                                                                       
a skill's steps               0.090          0.090    0.107             0.088           0.109                          0.108
an agent's tools and skills   0.036          0.037    0.054             0.058           0.017                          0.018
code                          0.029          0.023    0.034             0.038           0.004                          0.004
text the model reads          0.151          0.129    0.078             0.079           0.146                          0.154
the configuration             0.025          0.021    0.039             0.035           0.008                          0.004
the starting data             0.012          0.007    0.013             0.015           0.011                          0.010

miss rate per group, target 0.1, thresholds: per group
rule                         random  text (TF-IDF)  learned  learned + replay  adaptive_bayes  adaptive_bayes, reached tests
group                                                                                                                       
a skill's steps               0.090          0.083    0.057             0.053           0.055                          0.061
an agent's tools and skills   0.076          0.056    0.063             0.083           0.034                          0.043
code                          0.097          0.076    0.070             0.072           0.053                          0.042
text the model reads          0.048          0.090    0.061             0.080           0.073                          0.075
the configuration             0.087          0.107    0.085             0.030           0.007                          0.030
the starting data             0.000          0.000    0.000             0.000           0.004                          0.004

tokens per group, target 0.1, thresholds: per group
rule                         random  text (TF-IDF)  learned  learned + replay  adaptive_bayes  adaptive_bayes, reached tests
group                                                                                                                       
a skill's steps               0.101          0.088    0.100             0.113           0.071                          0.071
an agent's tools and skills   0.035          0.020    0.044             0.056           0.014                          0.018
code                          0.026          0.027    0.030             0.026           0.023                          0.026
text the model reads          0.175          0.157    0.148             0.127           0.163                          0.157
the configuration             0.025          0.019    0.037             0.030           0.003                          0.003
the starting data             0.014          0.013    0.013             0.015           0.010                          0.011

each kind of change measured with rules and thresholds from the other kinds (all kinds pooled)
            thresholds                          rule                  target     missed  miss rate  clean verdicts on a regression  tokens, no test reveals  tokens, regressions  tokens, all  coverage when clean
                   one                        random                   0.000   0 of 321      0.000                           0.000                    0.146                0.066        0.100                1.000
                   one                        random                   0.050  18 of 321      0.056                           0.072                    0.124                0.066        0.090                0.993
                   one                        random                   0.100  30 of 321      0.093                           0.115                    0.102                0.063        0.079                0.992
                   one                        random                   0.200  76 of 321      0.237                           0.247                    0.068                0.054        0.060                0.961
                   one                 text (TF-IDF)                   0.000   0 of 321      0.000                           0.000                    0.146                0.061        0.096                1.000
                   one                 text (TF-IDF)                   0.050  14 of 321      0.044                           0.057                    0.141                0.060        0.094                0.999
                   one                 text (TF-IDF)                   0.100  30 of 321      0.093                           0.115                    0.102                0.049        0.071                0.978
                   one                 text (TF-IDF)                   0.200  67 of 321      0.209                           0.224                    0.069                0.037        0.050                0.918
                   one                       learned                   0.000   0 of 321      0.000                           0.000                    0.146                0.074        0.104                1.000
                   one                       learned                   0.050   8 of 321      0.025                           0.033                    0.116                0.069        0.089                0.992
                   one                       learned                   0.100  17 of 321      0.053                           0.068                    0.097                0.065        0.078                0.986
                   one                       learned                   0.200  50 of 321      0.156                           0.177                    0.077                0.043        0.058                0.867
                   one              learned + replay                   0.000   0 of 321      0.000                           0.000                    0.146                0.055        0.093                1.000
                   one              learned + replay                   0.050  38 of 321      0.118                           0.141                    0.106                0.047        0.072                0.949
                   one              learned + replay                   0.100  89 of 321      0.277                           0.277                    0.073                0.037        0.052                0.863
                   one              learned + replay                   0.200 117 of 321      0.364                           0.335                    0.055                0.032        0.041                0.828
                   one                adaptive_bayes                   0.000   0 of 321      0.000                           0.000                    0.146                0.068        0.101                1.000
                   one                adaptive_bayes                   0.050  21 of 321      0.065                           0.083                    0.144                0.059        0.095                0.961
                   one                adaptive_bayes                   0.100  45 of 321      0.140                           0.162                    0.137                0.038        0.080                0.956
                   one                adaptive_bayes                   0.200  65 of 321      0.202                           0.219                    0.118                0.026        0.064                0.830
                   one                adaptive_bayes none (eps_clean = 0.05)  42 of 321      0.131                           0.153                    0.142                0.048        0.087                0.958
                   one adaptive_bayes, reached tests                   0.000   0 of 321      0.000                           0.000                    0.146                0.063        0.098                1.000
                   one adaptive_bayes, reached tests                   0.050  21 of 321      0.065                           0.083                    0.144                0.054        0.092                0.963
                   one adaptive_bayes, reached tests                   0.100  46 of 321      0.143                           0.165                    0.136                0.033        0.077                0.955
                   one adaptive_bayes, reached tests                   0.200  55 of 321      0.171                           0.192                    0.124                0.024        0.066                0.885
             one, sure                        random                   0.050  10 of 321      0.031                           0.041                    0.132                0.066        0.094                0.994
             one, sure                        random                   0.100  22 of 321      0.069                           0.087                    0.117                0.065        0.087                0.993
             one, sure                        random                   0.200  62 of 321      0.193                           0.211                    0.075                0.056        0.064                0.967
             one, sure                 text (TF-IDF)                   0.050  12 of 321      0.037                           0.049                    0.146                0.060        0.096                1.000
             one, sure                 text (TF-IDF)                   0.100  18 of 321      0.056                           0.072                    0.129                0.057        0.087                0.994
             one, sure                 text (TF-IDF)                   0.200  52 of 321      0.162                           0.183                    0.080                0.042        0.058                0.943
             one, sure                       learned                   0.050   5 of 321      0.016                           0.021                    0.122                0.071        0.092                0.993
             one, sure                       learned                   0.100  10 of 321      0.031                           0.041                    0.107                0.066        0.083                0.988
             one, sure                       learned                   0.200  33 of 321      0.103                           0.125                    0.082                0.058        0.068                0.906
             one, sure              learned + replay                   0.050  19 of 321      0.059                           0.076                    0.124                0.051        0.082                0.986
             one, sure              learned + replay                   0.100  65 of 321      0.202                           0.219                    0.081                0.043        0.059                0.912
             one, sure              learned + replay                   0.200 111 of 321      0.346                           0.324                    0.061                0.033        0.045                0.841
             one, sure                adaptive_bayes                   0.050  21 of 321      0.065                           0.083                    0.145                0.059        0.095                0.963
             one, sure                adaptive_bayes                   0.100  37 of 321      0.115                           0.138                    0.143                0.047        0.087                0.955
             one, sure                adaptive_bayes                   0.200  54 of 321      0.168                           0.189                    0.126                0.029        0.070                0.896
             one, sure adaptive_bayes, reached tests                   0.050  21 of 321      0.065                           0.083                    0.145                0.055        0.092                0.963
             one, sure adaptive_bayes, reached tests                   0.100  37 of 321      0.115                           0.138                    0.142                0.041        0.084                0.955
             one, sure adaptive_bayes, reached tests                   0.200  49 of 321      0.153                           0.174                    0.131                0.030        0.072                0.945
             per group                        random                   0.050   6 of 321      0.019                           0.025                    0.137                0.066        0.096                0.999
             per group                        random                   0.100  13 of 321      0.040                           0.053                    0.128                0.066        0.092                0.995
             per group                        random                   0.200  24 of 321      0.075                           0.094                    0.106                0.063        0.081                0.987
             per group                 text (TF-IDF)                   0.050   1 of 321      0.003                           0.004                    0.139                0.060        0.093                0.999
             per group                 text (TF-IDF)                   0.100   9 of 321      0.028                           0.037                    0.114                0.057        0.081                0.990
             per group                 text (TF-IDF)                   0.200  47 of 321      0.146                           0.168                    0.084                0.042        0.059                0.903
             per group                       learned                   0.050   2 of 321      0.006                           0.009                    0.127                0.073        0.096                1.000
             per group                       learned                   0.100   5 of 321      0.016                           0.021                    0.108                0.072        0.087                1.000
             per group                       learned                   0.200  12 of 321      0.037                           0.049                    0.084                0.069        0.075                0.992
             per group              learned + replay                   0.050   6 of 321      0.019                           0.025                    0.128                0.054        0.085                0.991
             per group              learned + replay                   0.100  11 of 321      0.034                           0.045                    0.111                0.052        0.077                0.984
             per group              learned + replay                   0.200  47 of 321      0.146                           0.168                    0.089                0.041        0.061                0.907
             per group                adaptive_bayes                   0.050  14 of 321      0.044                           0.057                    0.133                0.056        0.088                0.983
             per group                adaptive_bayes                   0.100  14 of 321      0.044                           0.057                    0.121                0.054        0.082                0.978
             per group                adaptive_bayes                   0.200  55 of 321      0.171                           0.192                    0.082                0.036        0.055                0.939
             per group adaptive_bayes, reached tests                   0.050  14 of 321      0.044                           0.057                    0.132                0.049        0.084                0.982
             per group adaptive_bayes, reached tests                   0.100  14 of 321      0.044                           0.057                    0.120                0.047        0.078                0.977
             per group adaptive_bayes, reached tests                   0.200  56 of 321      0.174                           0.194                    0.080                0.030        0.051                0.933
per group, floor first                        random                   0.050   6 of 321      0.019                           0.025                    0.138                0.057        0.091                1.000
per group, floor first                        random                   0.100  12 of 321      0.037                           0.049                    0.128                0.056        0.086                1.000
per group, floor first                        random                   0.200  22 of 321      0.069                           0.087                    0.107                0.054        0.076                1.000
per group, floor first                 text (TF-IDF)                   0.050   1 of 321      0.003                           0.004                    0.139                0.052        0.089                1.000
per group, floor first                 text (TF-IDF)                   0.100   7 of 321      0.022                           0.029                    0.115                0.049        0.077                1.000
per group, floor first                 text (TF-IDF)                   0.200  25 of 321      0.078                           0.097                    0.085                0.038        0.058                1.000
per group, floor first                       learned                   0.050   2 of 321      0.006                           0.009                    0.128                0.056        0.086                1.000
per group, floor first                       learned                   0.100   5 of 321      0.016                           0.021                    0.109                0.055        0.078                1.000
per group, floor first                       learned                   0.200  10 of 321      0.031                           0.041                    0.085                0.054        0.067                1.000
per group, floor first              learned + replay                   0.050   6 of 321      0.019                           0.025                    0.129                0.045        0.080                1.000
per group, floor first              learned + replay                   0.100  10 of 321      0.031                           0.041                    0.112                0.044        0.073                1.000
per group, floor first              learned + replay                   0.200  32 of 321      0.100                           0.121                    0.091                0.037        0.060                1.000
per group, floor first                adaptive_bayes                   0.050  13 of 321      0.040                           0.053                    0.134                0.044        0.082                1.000
per group, floor first                adaptive_bayes                   0.100  13 of 321      0.040                           0.053                    0.122                0.043        0.076                1.000
per group, floor first                adaptive_bayes                   0.200  44 of 321      0.137                           0.159                    0.083                0.029        0.052                1.000
per group, floor first adaptive_bayes, reached tests                   0.050  13 of 321      0.040                           0.053                    0.132                0.038        0.077                1.000
per group, floor first adaptive_bayes, reached tests                   0.100  13 of 321      0.040                           0.053                    0.121                0.036        0.072                1.000
per group, floor first adaptive_bayes, reached tests                   0.200  44 of 321      0.137                           0.159                    0.081                0.023        0.047                1.000
 per group, floor last                        random                   0.050   6 of 321      0.019                           0.025                    0.138                0.066        0.096                1.000
 per group, floor last                        random                   0.100  12 of 321      0.037                           0.049                    0.128                0.066        0.092                1.000
 per group, floor last                        random                   0.200  22 of 321      0.069                           0.087                    0.107                0.064        0.082                1.000
 per group, floor last                 text (TF-IDF)                   0.050   1 of 321      0.003                           0.004                    0.139                0.060        0.093                1.000
 per group, floor last                 text (TF-IDF)                   0.100   7 of 321      0.022                           0.029                    0.115                0.057        0.081                1.000
 per group, floor last                 text (TF-IDF)                   0.200  25 of 321      0.078                           0.097                    0.085                0.043        0.060                1.000
 per group, floor last                       learned                   0.050   2 of 321      0.006                           0.009                    0.128                0.073        0.096                1.000
 per group, floor last                       learned                   0.100   5 of 321      0.016                           0.021                    0.109                0.072        0.088                1.000
 per group, floor last                       learned                   0.200  10 of 321      0.031                           0.041                    0.085                0.069        0.076                1.000
 per group, floor last              learned + replay                   0.050   6 of 321      0.019                           0.025                    0.129                0.054        0.085                1.000
 per group, floor last              learned + replay                   0.100  10 of 321      0.031                           0.041                    0.112                0.053        0.078                1.000
 per group, floor last              learned + replay                   0.200  32 of 321      0.100                           0.121                    0.091                0.042        0.063                1.000
 per group, floor last                adaptive_bayes                   0.050  13 of 321      0.040                           0.053                    0.134                0.056        0.089                1.000
 per group, floor last                adaptive_bayes                   0.100  13 of 321      0.040                           0.053                    0.122                0.054        0.083                1.000
 per group, floor last                adaptive_bayes                   0.200  44 of 321      0.137                           0.159                    0.083                0.037        0.056                1.000
 per group, floor last adaptive_bayes, reached tests                   0.050  13 of 321      0.040                           0.053                    0.132                0.049        0.084                1.000
 per group, floor last adaptive_bayes, reached tests                   0.100  13 of 321      0.040                           0.053                    0.121                0.048        0.078                1.000
 per group, floor last adaptive_bayes, reached tests                   0.200  44 of 321      0.137                           0.159                    0.081                0.031        0.052                1.000
[loaded runs/qwen8_exact: 180 tests, 43 variants, 1 s]

runs/qwen8_exact: 43 changes; the replay settles 9 (4 as regressions); of the other 34, 28 are regressions

the rules learnt on 279 changes of runs/qwen8_gen, their thresholds set on the other 274 (164 regressions), run on those changes
            thresholds                          rule                  target   missed  miss rate  clean verdicts on a regression  tokens, no test reveals  tokens, regressions  tokens, all  coverage when clean
                   one                        random                   0.000  0 of 28      0.000                           0.000                    0.110                0.077        0.082                1.000
                   one                        random                   0.050  1 of 28      0.036                           0.143                    0.098                0.074        0.078                1.000
                   one                        random                   0.100  2 of 28      0.071                           0.250                    0.085                0.071        0.073                1.000
                   one                        random                   0.200 11 of 28      0.393                           0.647                    0.059                0.062        0.061                1.000
                   one                 text (TF-IDF)                   0.000  0 of 28      0.000                           0.000                    0.110                0.038        0.051                1.000
                   one                 text (TF-IDF)                   0.050  0 of 28      0.000                           0.000                    0.094                0.038        0.048                1.000
                   one                 text (TF-IDF)                   0.100  2 of 28      0.071                           0.250                    0.038                0.038        0.038                0.893
                   one                 text (TF-IDF)                   0.200  3 of 28      0.107                           0.333                    0.034                0.034        0.034                0.889
                   one                       learned                   0.000  0 of 28      0.000                           0.000                    0.110                0.065        0.073                1.000
                   one                       learned                   0.050  5 of 28      0.179                           0.455                    0.110                0.064        0.072                0.798
                   one                       learned                   0.100  5 of 28      0.179                           0.455                    0.110                0.064        0.072                0.798
                   one                       learned                   0.200 10 of 28      0.357                           0.625                    0.099                0.027        0.040                0.772
                   one              learned + replay                   0.000  0 of 28      0.000                           0.000                    0.110                0.075        0.081                1.000
                   one              learned + replay                   0.050  2 of 28      0.071                           0.250                    0.105                0.062        0.070                0.949
                   one              learned + replay                   0.100  3 of 28      0.107                           0.333                    0.092                0.052        0.059                0.938
                   one              learned + replay                   0.200  4 of 28      0.143                           0.400                    0.090                0.050        0.057                0.916
                   one                adaptive_bayes                   0.000  0 of 28      0.000                           0.000                    0.110                0.049        0.059                1.000
                   one                adaptive_bayes                   0.050  2 of 28      0.071                           0.250                    0.093                0.048        0.056                0.946
                   one                adaptive_bayes                   0.100  3 of 28      0.107                           0.333                    0.065                0.045        0.048                0.952
                   one                adaptive_bayes                   0.200  7 of 28      0.250                           0.538                    0.026                0.029        0.029                0.607
                   one                adaptive_bayes none (eps_clean = 0.05)  2 of 28      0.071                           0.250                    0.074                0.048        0.053                0.946
                   one adaptive_bayes, reached tests                   0.000  0 of 28      0.000                           0.000                    0.110                0.048        0.059                1.000
                   one adaptive_bayes, reached tests                   0.050  2 of 28      0.071                           0.250                    0.057                0.047        0.049                0.946
                   one adaptive_bayes, reached tests                   0.100  3 of 28      0.107                           0.333                    0.030                0.043        0.040                0.937
                   one adaptive_bayes, reached tests                   0.200  7 of 28      0.250                           0.538                    0.021                0.033        0.031                0.758
             one, sure                        random                   0.050  1 of 28      0.036                           0.143                    0.100                0.074        0.079                1.000
             one, sure                        random                   0.100  2 of 28      0.071                           0.250                    0.088                0.072        0.075                1.000
             one, sure                        random                   0.200  8 of 28      0.286                           0.571                    0.067                0.066        0.066                1.000
             one, sure                 text (TF-IDF)                   0.050  0 of 28      0.000                           0.000                    0.110                0.038        0.051                1.000
             one, sure                 text (TF-IDF)                   0.100  1 of 28      0.036                           0.143                    0.088                0.038        0.047                1.000
             one, sure                 text (TF-IDF)                   0.200  3 of 28      0.107                           0.333                    0.034                0.037        0.036                0.905
             one, sure                       learned                   0.050  5 of 28      0.179                           0.455                    0.110                0.064        0.072                0.798
             one, sure                       learned                   0.100  5 of 28      0.179                           0.455                    0.110                0.064        0.072                0.798
             one, sure                       learned                   0.200  8 of 28      0.286                           0.571                    0.102                0.042        0.052                0.841
             one, sure              learned + replay                   0.050  1 of 28      0.036                           0.143                    0.107                0.066        0.074                0.959
             one, sure              learned + replay                   0.100  3 of 28      0.107                           0.333                    0.097                0.056        0.063                0.938
             one, sure              learned + replay                   0.200  4 of 28      0.143                           0.400                    0.092                0.051        0.058                0.916
             one, sure                adaptive_bayes                   0.050  1 of 28      0.036                           0.143                    0.110                0.048        0.059                0.980
             one, sure                adaptive_bayes                   0.100  2 of 28      0.071                           0.250                    0.080                0.048        0.054                0.946
             one, sure                adaptive_bayes                   0.200  5 of 28      0.179                           0.455                    0.051                0.037        0.040                0.883
             one, sure adaptive_bayes, reached tests                   0.050  1 of 28      0.036                           0.143                    0.077                0.047        0.053                0.959
             one, sure adaptive_bayes, reached tests                   0.100  2 of 28      0.071                           0.250                    0.034                0.047        0.045                0.946
             one, sure adaptive_bayes, reached tests                   0.200  5 of 28      0.179                           0.455                    0.027                0.040        0.038                0.844
             per group                        random                   0.050  1 of 28      0.036                           0.143                    0.095                0.075        0.079                1.000
             per group                        random                   0.100  5 of 28      0.179                           0.455                    0.053                0.073        0.070                1.000
             per group                        random                   0.200  7 of 28      0.250                           0.538                    0.028                0.070        0.063                0.949
             per group                 text (TF-IDF)                   0.050  1 of 28      0.036                           0.143                    0.044                0.038        0.039                0.980
             per group                 text (TF-IDF)                   0.100  2 of 28      0.071                           0.250                    0.022                0.038        0.035                0.893
             per group                 text (TF-IDF)                   0.200  2 of 28      0.071                           0.250                    0.022                0.038        0.035                0.893
             per group                       learned                   0.050  5 of 28      0.179                           0.455                    0.064                0.064        0.064                0.798
             per group                       learned                   0.100  6 of 28      0.214                           0.500                    0.045                0.064        0.060                0.787
             per group                       learned                   0.200 10 of 28      0.357                           0.625                    0.030                0.055        0.051                0.840
             per group              learned + replay                   0.050  1 of 28      0.036                           0.143                    0.065                0.073        0.071                0.939
             per group              learned + replay                   0.100  3 of 28      0.107                           0.333                    0.056                0.060        0.059                0.911
             per group              learned + replay                   0.200  4 of 28      0.143                           0.400                    0.018                0.052        0.046                0.791
             per group                adaptive_bayes                   0.050  1 of 28      0.036                           0.143                    0.053                0.040        0.042                0.962
             per group                adaptive_bayes                   0.100  1 of 28      0.036                           0.143                    0.053                0.039        0.042                0.962
             per group                adaptive_bayes                   0.200  5 of 28      0.179                           0.455                    0.041                0.024        0.027                0.937
             per group adaptive_bayes, reached tests                   0.050  1 of 28      0.036                           0.143                    0.057                0.039        0.042                0.962
             per group adaptive_bayes, reached tests                   0.100  2 of 28      0.071                           0.250                    0.054                0.038        0.041                0.949
             per group adaptive_bayes, reached tests                   0.200  7 of 28      0.250                           0.538                    0.026                0.021        0.022                0.880
per group, floor first                        random                   0.050  1 of 28      0.036                           0.143                    0.095                0.065        0.070                1.000
per group, floor first                        random                   0.100  4 of 28      0.143                           0.400                    0.055                0.063        0.061                1.000
per group, floor first                        random                   0.200  5 of 28      0.179                           0.455                    0.030                0.060        0.055                1.000
per group, floor first                 text (TF-IDF)                   0.050  1 of 28      0.036                           0.143                    0.045                0.021        0.025                1.000
per group, floor first                 text (TF-IDF)                   0.100  2 of 28      0.071                           0.250                    0.024                0.021        0.022                1.000
per group, floor first                 text (TF-IDF)                   0.200  2 of 28      0.071                           0.250                    0.023                0.021        0.022                1.000
per group, floor first                       learned                   0.050  3 of 28      0.107                           0.333                    0.064                0.034        0.039                1.000
per group, floor first                       learned                   0.100  3 of 28      0.107                           0.333                    0.045                0.034        0.036                1.000
per group, floor first                       learned                   0.200  7 of 28      0.250                           0.538                    0.030                0.026        0.026                1.000
per group, floor first              learned + replay                   0.050  0 of 28      0.000                           0.000                    0.066                0.054        0.056                1.000
per group, floor first              learned + replay                   0.100  2 of 28      0.071                           0.250                    0.057                0.045        0.047                1.000
per group, floor first              learned + replay                   0.200  3 of 28      0.107                           0.333                    0.020                0.040        0.037                1.000
per group, floor first                adaptive_bayes                   0.050  1 of 28      0.036                           0.143                    0.054                0.030        0.034                1.000
per group, floor first                adaptive_bayes                   0.100  1 of 28      0.036                           0.143                    0.054                0.030        0.034                1.000
per group, floor first                adaptive_bayes                   0.200  4 of 28      0.143                           0.400                    0.042                0.017        0.022                1.000
per group, floor first adaptive_bayes, reached tests                   0.050  1 of 28      0.036                           0.143                    0.058                0.030        0.035                1.000
per group, floor first adaptive_bayes, reached tests                   0.100  2 of 28      0.071                           0.250                    0.055                0.030        0.034                1.000
per group, floor first adaptive_bayes, reached tests                   0.200  6 of 28      0.214                           0.500                    0.027                0.017        0.019                1.000
 per group, floor last                        random                   0.050  1 of 28      0.036                           0.143                    0.095                0.075        0.079                1.000
 per group, floor last                        random                   0.100  4 of 28      0.143                           0.400                    0.055                0.073        0.070                1.000
 per group, floor last                        random                   0.200  5 of 28      0.179                           0.455                    0.030                0.070        0.063                1.000
 per group, floor last                 text (TF-IDF)                   0.050  1 of 28      0.036                           0.143                    0.045                0.038        0.039                1.000
 per group, floor last                 text (TF-IDF)                   0.100  2 of 28      0.071                           0.250                    0.024                0.038        0.035                1.000
 per group, floor last                 text (TF-IDF)                   0.200  2 of 28      0.071                           0.250                    0.023                0.038        0.035                1.000
 per group, floor last                       learned                   0.050  3 of 28      0.107                           0.333                    0.064                0.065        0.065                1.000
 per group, floor last                       learned                   0.100  3 of 28      0.107                           0.333                    0.045                0.065        0.061                1.000
 per group, floor last                       learned                   0.200  7 of 28      0.250                           0.538                    0.030                0.056        0.052                1.000
 per group, floor last              learned + replay                   0.050  0 of 28      0.000                           0.000                    0.066                0.073        0.072                1.000
 per group, floor last              learned + replay                   0.100  2 of 28      0.071                           0.250                    0.057                0.060        0.060                1.000
 per group, floor last              learned + replay                   0.200  3 of 28      0.107                           0.333                    0.020                0.053        0.047                1.000
 per group, floor last                adaptive_bayes                   0.050  1 of 28      0.036                           0.143                    0.054                0.040        0.042                1.000
 per group, floor last                adaptive_bayes                   0.100  1 of 28      0.036                           0.143                    0.054                0.039        0.042                1.000
 per group, floor last                adaptive_bayes                   0.200  4 of 28      0.143                           0.400                    0.042                0.024        0.027                1.000
 per group, floor last adaptive_bayes, reached tests                   0.050  1 of 28      0.036                           0.143                    0.058                0.039        0.042                1.000
 per group, floor last adaptive_bayes, reached tests                   0.100  2 of 28      0.071                           0.250                    0.055                0.038        0.041                1.000
 per group, floor last adaptive_bayes, reached tests                   0.200  6 of 28      0.214                           0.500                    0.027                0.023        0.023                1.000

the fixed minimal set: 16 tests, 13.1% of the suite
                                        selection   missed  miss rate  clean verdicts on a regression  tokens, no test reveals  tokens, regressions  tokens, all  coverage when clean
a fixed minimal set, the tests the change reaches 16 of 28      0.571                           0.727                    0.029                0.034        0.033                1.000
                   a fixed minimal set, run whole 16 of 28      0.571                           0.727                    0.131                0.113        0.116                1.000
                         the coverage floor alone 20 of 28      0.714                           0.769                    0.002                0.005        0.005                1.000
```
