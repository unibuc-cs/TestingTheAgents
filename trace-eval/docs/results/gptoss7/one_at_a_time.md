# gpt-oss without batching

The empty change (`benign_code_comment_docstring`, whose change set is empty) recorded with gpt-oss-120b one test
at a time (`traceeval mutants --only benign_code_comment_docstring --reps 3 --workers 1 --backend llm`, the model
split over both of fmi0's GPUs, 540 runs, none broken by the environment, 27 minutes), against gpt-oss's baseline
of `runs/gptoss7`, also one test at a time, and against the same change as `runs/gptoss7` recorded it, 32 tests at
a time. A test's majority label is the majority of its runs; a test's runs disagree when they do not all end the
same way. The three recordings run the same application, catalog and scorers (since `runs/gptoss7` they have
changed in comments only) with the same server settings; the baseline and the batched recording come from one start
of the server, the one-at-a-time recording from another.

| recording | runs per test | tests failing by majority | tests whose runs disagree |
|---|---|---|---|
| baseline, one test at a time | 4–5 | 27 | 6: AUT-06, DS-INTENTS/i22, MNT-05, WF1-01, WF3-01, WF5-02 |
| empty change, one test at a time | 3 | 25 | 5: PUB-02, PUB-14, PUB-22, WF3-01, WF6-01 |
| empty change, 32 tests at a time (`runs/gptoss7`) | 5 | 27 | 11: AUT-06, DS-INTENTS/i22, MNT-05, PUB-07, PUB-12, PUB-14, PUB-22, PUB-23, WF3-01, WF3-02, WF5-01 |

| comparison | tests whose majority flips |
|---|---|
| baseline against the empty change, both one test at a time, two starts of the server | 10: AST-08, DS-INTENTS/i01, MNT-05, PUB-15, PUB-16, PUB-19, PUB-22, WF1-01, WF1-03, WF5-02 |
| baseline against the empty change in batches, one start of the server: what the recording measures | 8: AST-10, PUB-15, PUB-22, PUB-23, WF1-01, WF1-03, WF5-01, WF5-02 |
| the empty change one test at a time against in batches | 8: AST-08, AST-10, DS-INTENTS/i01, MNT-05, PUB-16, PUB-19, PUB-23, WF5-01 |

Without batching gpt-oss is not repeatable either. Within one recording one test at a time, five or six tests have
runs that disagree, against eleven in batches; pooled over the baseline and the one-at-a-time recording, eight runs
per test, sixteen tests disagree. Between the two one-at-a-time recordings the majority flips on ten tests, more
than batching flips within one start of the server, and six of the ten flip with every run agreeing on each side:
AST-08, DS-INTENTS/i01, PUB-15, PUB-16 and PUB-19 fail in every baseline run and pass in every run of the new
recording, WF1-03 the other way round. A test's outcome can hold for the life of one server and change with the
next start. Batching has an effect of its own: AST-10 fails in all eight runs one test at a time, over both starts,
and passes in all five batched runs; PUB-23 fails in all eight and passes in four of five batched.

Under the same comparison Qwen flips one test (WF5-02, `docs/results/qwen7/one_at_a_time.md`), and Gemma none,
across starts of the server and in batches (`docs/results/gemma7/false_alarm_one_at_a_time.md`,
`docs/results/gemma7/noise_floor.md`). For gpt-oss, recording the changed copies one test at a time is not enough
for a clean ground truth: the baseline and the changes would also have to come from one start of the server, and
even then five or six tests disagree with themselves within a recording.
