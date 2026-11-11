# Qwen's noise floor against the number of runs

The empty change (`benign_code_comment_docstring`, whose change set is empty) recorded with Qwen3.8-27B fifteen
times, 64 tests at a time, the way the changed copies are recorded (`traceeval mutants --only
benign_code_comment_docstring --reps 15 --workers 64 --backend llm`: one cluster job with a copy of the model on
each of its two GPUs, 2,700 runs, none broken by the environment, 17 minutes), against Qwen's baseline of
`runs/qwen7`, recorded one test at a time (four or five valid runs per test). The change touches no code, so a test
whose majority differs from the baseline's is noise, and a test that passes on the baseline and fails here is a
false revealing test that every change inherits.

For each number of runs K, the majority label is taken over the first K runs, and over 50 random subsets of K of
the 15 runs (one `random.Random(0)` drawing the subsets for each K in turn); a majority is pass when at least half
the runs pass. "Flips" counts the tests whose majority differs from the baseline's, "pass → fail" the flips that
pass on the baseline, and "disagree" the tests whose K runs do not all end the same way. At K = 15 every subset is
all the runs.

| K | flips, first K | pass → fail, first K | disagree, first K | flips, 50 subsets: mean (range) | pass → fail, 50 subsets: mean | disagree, 50 subsets: mean |
|---|---|---|---|---|---|---|
| 3 | 6 | 3 | 5 | 5.3 (3–8) | 3.0 | 5.0 |
| 5 | 6 | 3 | 7 | 5.1 (3–7) | 2.8 | 6.5 |
| 7 | 4 | 2 | 8 | 5.1 (3–7) | 2.9 | 7.8 |
| 9 | 5 | 3 | 8 | 5.3 (4–7) | 3.2 | 8.4 |
| 11 | 5 | 3 | 8 | 5.4 (4–7) | 3.3 | 8.6 |
| 15 | 5 | 3 | 9 | 5 | 3 | 9 |

More runs do not lower the floor. Five or six tests flip at every K, three of them from pass to fail, and the mean
over the subsets stays between 5.0 and 5.4; only its spread narrows. The tests whose runs disagree grow from five
to nine, because more runs reach the rarer outcomes.

The five tests that still flip at K = 15, and the other tests whose fifteen runs disagree (passing runs of the
valid runs):

| test | baseline, one at a time | empty change, 15 runs in batches | majority at K = 15 |
|---|---|---|---|
| SEO-05 | 5/5 | 0/15 | flips, pass → fail |
| WF4-02 | 4/4 | 6/15 | flips, pass → fail |
| WF5-02 | 2/4 | 5/15 | flips, pass → fail |
| DS-ROUTING/r40 | 0/5 | 15/15 | flips, fail → pass |
| WF1-02 | 0/4 | 11/15 | flips, fail → pass |
| AUT-13 | 5/5 | 13/15 | same |
| CFG-03 | 4/4 | 12/15 | same |
| PUB-07 | 0/4 | 6/15 | same |
| PUB-20 | 4/4 | 8/15 | same, one run above the line; flips over the first three runs |
| WF2-02 | 4/4 | 14/15 | same |
| WF4-01 | 0/4 | 2/15 | same |

Two of the five flips are a shift, not noise: SEO-05 fails all fifteen runs in batches and passes all five one at a
time, and DS-ROUTING/r40 does the reverse. No number of runs in batches gives them the baseline's label. WF1-02,
WF4-02 and WF5-02 vary in batches (11, 6 and 5 passes of 15); WF5-02 sits on the majority line in the baseline
too (two passes of four, which counts as pass).

The earlier recording of the same change, five runs, also 64 tests at a time (`runs/qwen7`), flips six tests:
DS-ROUTING/r40, PUB-20, SEO-05, WF1-02, WF4-01 and WF4-02. Four of them flip here too; PUB-20 and WF4-01 do not,
and WF5-02 flips here only. Two batched recordings of the same empty change disagree on which tests flip, so a
noise floor measured once in batches does not carry over to the next recording.

Under batching, a larger K converges to the batched label, not to the baseline's: about five tests flip and three
appear to reveal a change that touches nothing, from three runs to fifteen. One test at a time, five runs already
agree with the baseline on every test but WF5-02 (`one_at_a_time.md`).
