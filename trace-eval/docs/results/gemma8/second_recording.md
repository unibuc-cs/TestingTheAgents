# A second recording, under another start of the server

`runs/gemma8` was recorded with Gemma on one GPU of the shared server. `runs/gemma8_restart` records its changed
copies again, from the same baseline and the same cassette, with another start of the same model on two other GPUs
(a cluster job, a copy of the model on each, the requests sent to the two in turn):

- the empty change, the whole suite;
- each of the 43 changes for the tests it reaches only (`traceeval mutants --reached-only`). A test that replays
  to the end is not run: its outcome is the replay's, which no server can move;
- five repetitions, 32 tests at a time: 8,110 runs in 33 minutes, none broken by the environment.

```bash
python scripts/analysis/two_recordings.py runs/gemma8 runs/gemma8_restart
```

## 1. The empty change

| | `runs/gemma8` | `runs/gemma8_restart` |
|---|---|---|
| runs that end as the baseline's majority | 900 of 900 | 900 of 900 |
| tests whose majority flips | 0 | 0 |
| runs that are the replay's conversation (calls, answer, state, tokens) | 818 | 778 |
| requests the baseline had sent | 5,218 | 5,294 |
| of them, answered otherwise than the cassette | 104 (2.0%) | 139 (2.6%) |

## 2. The tests the changes reach

Both recordings ran the same 1,442 (change, test) pairs, five times each.

| | `runs/gemma8` | `runs/gemma8_restart` |
|---|---|---|
| pairs whose five runs disagree | 4 | 13 |
| requests the baseline had sent | 30,738 | 30,183 |
| of them, answered otherwise than the cassette | 564 (1.8%) | 745 (2.5%) |

The majority label differs on 2 of the 1,442 pairs:

| change | test | `runs/gemma8`: passing runs | `runs/gemma8_restart`: passing runs |
|---|---|---|---|
| `skill_publish_drop_permission_check` | WF2-02 | 5 of 5 | 2 of 5 |
| `skill_routing_drop_brand_gate` | WF1-02 | 4 of 5 | 2 of 5 |

Of the 15 pairs whose runs disagree in either recording, 13 are multi-agent workflows (WF1 to WF4), the long
tests in which one answer worded otherwise can change the path.

## 3. Regressions

| | `runs/gemma8` | `runs/gemma8_restart` |
|---|---|---|
| changes with at least one revealing test | 28 | 29, the same 28 and `skill_routing_drop_brand_gate` |
| changes with the same revealing tests in both | 41 of 43 | |

`skill_routing_drop_brand_gate` is the change that rests on one test at the majority line: WF1-02 fails one run of
five in the first recording and three in the second. `skill_publish_drop_permission_check` has three revealing
tests in the first recording and a fourth, WF2-02, in the second.

## 4. What a reached test costs

The runs of this recording count the tokens of the requests the original app made too (`cassette.known_tokens`),
before the divergence point and after it. Tokens are shares of the full suite, means over the 43 changes, with no
budget:

| | a test charged from its divergence point on | charged for its new requests only |
|---|---|---|
| the whole suite through a cache of the original app's answers, no stop at a failure | 0.207 (median 0.083) | 0.135 (median 0.050) |
| a random order of the reached tests, stopped at the first failure | 0.092 | 0.062 |
| `ir_tfidf` | 0.075 | 0.051 |
| `history_ml` | 0.076 | 0.054 |
| `adaptive_bayes`, which stops early | 0.020 | 0.017 |
| every reached test, on the 14 changes no test reveals | 0.197 | 0.131 |

## 5. Reading

- The outcomes hold across a start of the server: the empty change flips no test, and 2 of 1,442 labels on the
  reached tests move. The 6,298 pairs that replay to the end cannot move.
- The answers hold less well than on the first server: 2.6% of the requests sent again are answered otherwise,
  against 2.0%, and thirteen pairs have runs that disagree, against four.
- The labels that move are those of long workflow tests on a changed copy, where the five runs disagree. One run
  of such a test is not its majority: with no budget, the strategies end clean on `skill_routing_drop_brand_gate`
  in the runs that draw one of WF1-02's two passing runs, which is why they find 93% to 99% of the 29 regressions
  and not all of them.
- A third of what follows a divergence point is requests the original app made. Answered from the cassette too,
  as `traceeval check` does, the reached tests cost about a third less than the bound the replay gives.
