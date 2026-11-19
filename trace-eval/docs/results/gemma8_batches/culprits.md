# Culprits of the batches, from the members' own replays

When a test fails on a batch, the members to suspect are those whose own replay reaches that test or fails it
(`traceeval/experiment/culprits.py`). A member whose own replay runs the test to the end and passes cannot make it
fail on its own, and the replays need no model. A *culprit* is a member that the test reveals in the member's own
recording; a pair with none is one only the members together fail. The rows come from
`python scripts/analysis/culprits_by_replay.py runs/gemma8_batches runs/live_check8_batches --md`, on the batches
of [batches.md](batches.md).

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
