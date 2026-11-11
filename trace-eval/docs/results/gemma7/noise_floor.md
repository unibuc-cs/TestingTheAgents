# The noise floor against K

The empty change (`benign_code_comment_docstring`, whose change set is empty) recorded with Gemma fifteen times, 32
tests at a time like every changed copy (`traceeval mutants --only benign_code_comment_docstring --reps 15`, 2,700
runs, none broken by the environment, six minutes, `runs/gemma7_noise`), against the baseline of `runs/gemma7`
(five runs per test, one test at a time). For each K, the first K repetitions, and 50 random subsets of K of the
fifteen repetitions (`random.Random(0)`, one subset of repetitions for every test), averaged. A test's majority
label is pass when at least half its runs pass; a test's runs disagree when they do not all end the same way. The
last two columns count the tests whose K runs are not all identical: the same outcome, the same tokens, the same
final answer and the same final state.

| K | majority differs from the baseline's, first K | the same, 50 subsets (mean) | runs disagree, first K | the same, 50 subsets (mean) | runs not identical, first K | the same, 50 subsets (mean, min–max) |
|---|---|---|---|---|---|---|
| 3 | 0 | 0 | 0 | 0 | 22 | 25.4 (17–31) |
| 5 | 0 | 0 | 0 | 0 | 32 | 33.3 (27–38) |
| 7 | 0 | 0 | 0 | 0 | 33 | 36.4 (32–40) |
| 9 | 0 | 0 | 0 | 0 | 35 | 38.5 (34–42) |
| 11 | 0 | 0 | 0 | 0 | 37 | 41.1 (38–44) |
| 15 | 0 | 0 | 0 | 0 | 44 | 44 |

Under Gemma the noise floor is zero at every K. In 2,700 runs no test changes its majority against the baseline and
no test's runs disagree: the eight tests that fail are Gemma's known mistakes (AUT-04, CFG-01, PUB-10, SEO-02,
WF1-01, WF2-03, WF5-02, WF6-02) and fail in all fifteen runs, and every other test passes in all fifteen. The runs
are not bit-exact: over the fifteen repetitions 136 tests give the same run every time, 25 give two distinct runs,
11 three, and 8 between four and seven, and the count of tests with differing runs grows with K, but no difference
changes an outcome. For Gemma's ground truth under this serving setup three repetitions say what fifteen say. Under
Qwen, the same change recorded in batches flips six tests at five repetitions
(`docs/results/qwen7/one_at_a_time.md`).
