# Qwen without batching

The empty change (`benign_code_comment_docstring`, whose change set is empty) recorded with Qwen3.8-27B one test at a
time (`traceeval mutants --only benign_code_comment_docstring --reps 5 --workers 1 --backend llm`: two repetitions on
fmi0's GPU1, three on the cluster's job, 900 runs in all), against Qwen's baseline of `runs/qwen7`, also one test at a
time, and against the same change as `runs/qwen7` recorded it, 64 tests at a time. A test's majority label is the
majority of its runs; a test "disagrees with itself" when its runs do not all end the same way.

| recording | runs per test | tests failing by majority | tests whose runs disagree |
|---|---|---|---|
| baseline, one test at a time | 4–5 | 7 | 1: WF5-02 |
| empty change, one test at a time | 5 | 8 | 1: WF5-02 |
| empty change, 64 tests at a time (`runs/qwen7`) | 5 | 7 | 9: CFG-03, INS-03, PUB-07, WF1-01, WF1-02, WF2-01, WF4-01, WF4-02, WF5-02 |

| comparison | tests whose majority flips |
|---|---|
| baseline against the empty change, both one test at a time: run-to-run variation alone | 1: WF5-02 |
| baseline against the empty change in batches: what the recording measures | 6: DS-ROUTING/r40, PUB-20, SEO-05, WF1-02, WF4-01, WF4-02 |
| the empty change one at a time against in batches: batching alone | 7: DS-ROUTING/r40, PUB-20, SEO-05, WF1-02, WF4-01, WF4-02, WF5-02 |

Pooled over the baseline and the one-at-a-time recording, nine or ten runs per test, WF5-02 is still the only test
whose runs disagree: it sits at the majority line, passing about half the time under identical conditions. Every
other test gives the same outcome on every one of its one-at-a-time runs. The six tests that appear to flip under
the empty change in `runs/qwen7` are batching.
