# The members' own replays: the day's map and the culprits of a failure

Each member of a batch can be replayed alone against the cassette, in a few seconds and with no model
(`traceeval/experiment/culprits.py`; `traceeval check <batch>` prints both parts below). The rows come from
`python scripts/analysis/culprits_by_replay.py runs/gemma8_batches runs/live_check8_batches --md`, on the batches
of [batches.md](batches.md).

## The day's map

Before any model call: which tests each member reaches, the members that reach none, and how many members reach
each test the batch reaches.

- **The batch reaches what its members reach:** 2,766 tests over the 23 batches, the same tests as its members
  alone, none more and none fewer.
- **Members settled with no model:** 18 of 117 reach no test and fail none (5 distinct changes). A test reveals
  none of them. Four are benign; the fifth, `code_edit_keeps_review`, is a regression no test of the suite
  reveals, so the map points at the gap in the suite before anything runs.
- **A culprit known before any run:** in 2 batches a member fails a test in its own replay, both times
  `code_termination_off_by_six` (WF4-01, WF4-02 and WF6-01).
- **One owner:** 1,505 of the 2,766 reached tests are reached by one member, so a failure there names its member
  with no further run; 1,261 by several.
- **Checked once for the day:** the reached tests are 2,766 runs for the batches, 4,309 if each member were
  checked alone, and 55% of the tokens (whole tests, before the replay's savings and any stop).

| batch | members | settled with no model | tests reached | by one member | by several | by no member alone | tokens of the reached tests: batch, each member (% of the suite) |
|---|---|---|---|---|---|---|---|
| `batch_benign` | 9 | 4 | 165 | 12 | 153 | 0 | 95%, 255% |
| `batch_nightly` | 8 | 1 | 67 | 54 | 13 | 0 | 56%, 75% |
| `batch_publishing_pr` | 3 | 0 | 49 | 44 | 5 | 0 | 50%, 54% |
| `batch_sweep_2_1` | 2 | 0 | 10 | 10 | 0 | 0 | 12%, 12% |
| `batch_sweep_2_2` | 2 | 1 | 14 | 14 | 0 | 0 | 14%, 14% |
| `batch_sweep_2_3` | 2 | 0 | 92 | 58 | 34 | 0 | 71%, 112% |
| `batch_sweep_3_1` | 3 | 0 | 153 | 133 | 20 | 0 | 90%, 122% |
| `batch_sweep_3_2` | 3 | 1 | 156 | 145 | 11 | 0 | 91%, 104% |
| `batch_sweep_3_3` | 3 | 0 | 162 | 123 | 39 | 0 | 94%, 165% |
| `batch_sweep_4_1` | 4 | 1 | 153 | 0 | 153 | 0 | 90%, 189% |
| `batch_sweep_4_2` | 4 | 1 | 30 | 29 | 1 | 0 | 37%, 39% |
| `batch_sweep_4_3` | 4 | 1 | 47 | 2 | 45 | 0 | 49%, 96% |
| `batch_sweep_5_1` | 5 | 1 | 162 | 9 | 153 | 0 | 94%, 229% |
| `batch_sweep_5_2` | 5 | 0 | 100 | 47 | 53 | 0 | 81%, 155% |
| `batch_sweep_5_3` | 5 | 0 | 162 | 113 | 49 | 0 | 94%, 161% |
| `batch_sweep_6_1` | 6 | 2 | 156 | 3 | 153 | 0 | 91%, 206% |
| `batch_sweep_6_2` | 6 | 2 | 165 | 112 | 53 | 0 | 95%, 165% |
| `batch_sweep_6_3` | 6 | 0 | 93 | 70 | 23 | 0 | 77%, 110% |
| `batch_sweep_7_1` | 7 | 1 | 157 | 124 | 33 | 0 | 91%, 151% |
| `batch_sweep_7_2` | 7 | 1 | 166 | 110 | 56 | 0 | 95%, 183% |
| `batch_sweep_7_3` | 7 | 1 | 166 | 113 | 53 | 0 | 95%, 155% |
| `batch_sweep_8_1` | 8 | 0 | 169 | 82 | 87 | 0 | 95%, 242% |
| `batch_sweep_8_2` | 8 | 0 | 172 | 98 | 74 | 0 | 98%, 205% |

## The culprits of a failure

When a test fails on a batch, the members to suspect are those whose own replay reaches that test or fails it. A
member whose own replay runs the test to the end and passes cannot make it fail on its own. A *culprit* is a member
that the test reveals in the member's own recording; a pair with none is one only the members together fail.

- **278 pairs** of a batch and a test that reveals it, over the 20 batches with a revealing test: 273 with a
  culprit alone, 5 that only the members together fail.
- **Every culprit is a suspect:** 273 of 273. The suspects are 1.94 members on average, of 5.67, and the one
  suspect is the culprit in 85 of the 273.
- **Fewer runs to find the culprit:** halving the suspects finds one in 0.92 runs of the failing test on average,
  halving all the members in 2.53.
- **Only together:** each of the 5 such pairs has suspects, members that reach the test alone without failing it;
  halving them ends with no single culprit, which is how the batch's interaction shows.
- **Live:** of the 18 batches whose live check failed on a test with a culprit alone, the suspects hold every
  culprit in all 18 and are that culprit alone in 9. The component the check blamed most belongs to a culprit in
  13.

"Runs to find it" is the mean number of runs of the failing test that find one culprit by halving, among the
suspects and among all the members.

| batch | members | revealing tests | with a culprit alone | culprit among the suspects | one suspect, the culprit | runs to find it: suspects, all members |
|---|---|---|---|---|---|---|
| `batch_benign` | 9 | 1 | 0 | 0 | 0 |  |
| `batch_nightly` | 8 | 30 | 28 | 28 | 19 | 0.3, 3.0 |
| `batch_publishing_pr` | 3 | 9 | 9 | 9 | 5 | 0.4, 2.0 |
| `batch_sweep_2_1` | 2 | 9 | 9 | 9 | 9 | 0.0, 1.0 |
| `batch_sweep_2_3` | 2 | 26 | 26 | 26 | 17 | 0.3, 1.0 |
| `batch_sweep_3_1` | 3 | 12 | 12 | 12 | 0 | 1.0, 2.0 |
| `batch_sweep_3_3` | 3 | 7 | 7 | 7 | 0 | 1.3, 2.0 |
| `batch_sweep_4_1` | 4 | 9 | 8 | 8 | 0 | 1.6, 2.0 |
| `batch_sweep_4_2` | 4 | 17 | 17 | 17 | 17 | 0.0, 2.0 |
| `batch_sweep_4_3` | 4 | 4 | 4 | 4 | 1 | 0.8, 2.0 |
| `batch_sweep_5_1` | 5 | 4 | 4 | 4 | 0 | 1.2, 3.0 |
| `batch_sweep_5_2` | 5 | 14 | 14 | 14 | 0 | 1.6, 3.0 |
| `batch_sweep_5_3` | 5 | 2 | 2 | 2 | 0 | 1.0, 3.0 |
| `batch_sweep_6_1` | 6 | 1 | 0 | 0 | 0 |  |
| `batch_sweep_6_3` | 6 | 23 | 23 | 23 | 9 | 0.7, 3.0 |
| `batch_sweep_7_1` | 7 | 20 | 20 | 20 | 1 | 1.1, 3.0 |
| `batch_sweep_7_2` | 7 | 23 | 23 | 23 | 2 | 1.2, 3.0 |
| `batch_sweep_7_3` | 7 | 20 | 20 | 20 | 2 | 1.1, 3.0 |
| `batch_sweep_8_1` | 8 | 35 | 35 | 35 | 3 | 1.6, 3.0 |
| `batch_sweep_8_2` | 8 | 12 | 12 | 12 | 0 | 1.5, 3.0 |
