# Batches of changes on the current app

`runs/gemma8_batches` is a copy of `runs/gemma8` (its baseline, its cassette and the 43 single changes) with 23
batches recorded beside them: the three of the catalog and the twenty of `scripts/batch_sweep.py`, drawn at random,
of two to eight changes whose edits touch different files. Each batch was recorded like a single change, the whole
suite five times, 32 tests at a time, with Gemma on another start of the server than the recording's. The
strategies never learn from a batch's members, nor from the batches that share one (`History.training_variants`).

- **Live:** `traceeval check <batch> --history runs/gemma8_batches --budget 0.2 --backend vllm`, one check at a
  time (`python scripts/batch_sweep.py check ...` for the twenty, which are not in the catalog).
- **Offline:** `traceeval evaluate` and the report beside this page; `scripts/analysis/batch_calibration.py` for
  the three ways of calibrating and the blame.

A member is a regression alone when a test reveals it in its own recording. "Revealing tests" counts those of the
batch, with in brackets the union of its members' own where the two differ. Tokens are shares of the full suite.

| batch | members | regressions alone | revealing tests (the members' alone) | tests that diverge | `adaptive_bayes` at 5%: found, tests, tokens | at 20% | live: verdict, tests, tokens | test that failed live | blamed most | its member a regression alone |
|---|---|---|---|---|---|---|---|---|---|---|
| `batch_sweep_2_1` | 2 | 2 | 9 | 10 | 1.00, 1.0 tests, 0.2% | 1.00, 1.0 tests, 0.2% | regression, 1, 0.2% | INS-01 | `code:harness/retry.py::with_retry` | yes |
| `batch_sweep_2_2` | 2 | 0 | 0 | 14 | 0.00, 11.0 tests, 4.7% | 0.00, 13.0 tests, 7.0% | clean, 13, 3.6% |  |  |  |
| `batch_sweep_2_3` | 2 | 2 | 26 | 92 | 1.00, 2.0 tests, 0.2% | 1.00, 2.0 tests, 0.2% | regression, 2, 0.2% | MNT-05 | `code:harness/runtime.py::Runtime._delegate` | yes |
| `batch_publishing_pr` | 3 | 3 | 9 | 49 | 1.00, 3.0 tests, 1.3% | 1.00, 3.0 tests, 1.3% | regression, 3, 1.1% | AUT-02 | `code:services/links.py::validate_links` | yes |
| `batch_sweep_3_1` | 3 | 2 | 12 | 153 | 1.00, 3.0 tests, 1.5% | 1.00, 3.0 tests, 1.5% | regression, 3, 0.7% | TRN-06 | `code:harness/runtime.py::Runtime._delegate` | yes |
| `batch_sweep_3_2` | 3 | 0 | 0 | 156 | 0.00, 14.0 tests, 4.9% | 0.00, 44.0 tests, 19.9% | budget, 69, 19.9% |  |  |  |
| `batch_sweep_3_3` | 3 | 2 | 7 | 162 | 1.00, 6.0 tests, 3.3% | 1.00, 6.0 tests, 3.3% | regression, 6, 3.0% | PUB-02 | `code:harness/runtime.py::Runtime._delegate` | yes |
| `batch_sweep_4_1` | 4 | 2 | 9 (8) | 153 | 0.60, 7.6 tests, 3.8% | 1.00, 6.8 tests, 4.2% | regression, 8, 2.3% | WF2-02 | `code:services/workflow.py::publish_page` | no |
| `batch_sweep_4_2` | 4 | 3 | 17 | 30 | 1.00, 1.0 tests, 0.3% | 1.00, 1.0 tests, 0.3% | regression, 1, 0.3% | GOV-02 | `agent:governance.tools` | yes |
| `batch_sweep_4_3` | 4 | 2 | 4 | 47 | 1.00, 1.0 tests, 0.1% | 1.00, 1.0 tests, 0.1% | regression, 1, 0.1% | BRD-02 | `code:services/brand.py::check_page` | yes |
| `batch_sweep_5_1` | 5 | 2 | 4 | 162 | 1.00, 2.0 tests, 1.0% | 1.00, 2.0 tests, 1.0% | regression, 2, 0.9% | BRD-02 | `code:services/brand.py::check_page` | yes |
| `batch_sweep_5_2` | 5 | 3 | 14 | 100 | 1.00, 3.0 tests, 0.7% | 1.00, 3.0 tests, 0.7% | regression, 3, 0.6% | TRN-06 | `code:tools/content_tools.py::get_page` | yes |
| `batch_sweep_5_3` | 5 | 2 | 2 | 162 | 1.00, 1.0 tests, 0.3% | 1.00, 1.0 tests, 0.3% | regression, 1, 0.3% | OPT-01 | `code:services/site.py::audit_site` | yes |
| `batch_sweep_6_1` | 6 | 0 | 1 (0) | 156 | 0.00, 12.0 tests, 4.8% | 0.00, 32.2 tests, 20.0% | budget, 57, 20.0% |  |  |  |
| `batch_sweep_6_2` | 6 | 0 | 0 | 165 | 0.00, 12.0 tests, 4.9% | 0.00, 32.0 tests, 20.0% | budget, 41, 19.8% |  |  |  |
| `batch_sweep_6_3` | 6 | 5 | 23 | 93 | 1.00, 1.0 tests, 0.4% | 1.00, 1.0 tests, 0.4% | regression, 1, 0.4% | SEO-01 | `agent:seo.tools` | yes |
| `batch_sweep_7_1` | 7 | 4 | 20 | 157 | 1.00, 6.0 tests, 1.5% | 1.00, 6.0 tests, 1.5% | regression, 6, 1.3% | INS-01 | `code:services/site.py::page_metrics` | yes |
| `batch_sweep_7_2` | 7 | 5 | 23 | 166 | 1.00, 1.0 tests, 0.2% | 1.00, 1.0 tests, 0.2% | regression, 1, 0.2% | DS-INTENTS/i20 | `agent:governance.tools` | yes |
| `batch_sweep_7_3` | 7 | 5 | 20 | 166 | 1.00, 1.0 tests, 0.2% | 1.00, 1.0 tests, 0.2% | regression, 1, 0.2% | DS-INTENTS/i20 | `agent:governance.tools` | yes |
| `batch_nightly` | 8 | 6 | 30 (28) | 67 | 1.00, 1.0 tests, 0.4% | 1.00, 1.0 tests, 0.4% | regression, 1, 0.4% | SEO-01 | `agent:seo.tools` | yes |
| `batch_sweep_8_1` | 8 | 6 | 35 | 169 | 1.00, 1.0 tests, 0.2% | 1.00, 1.0 tests, 0.2% | regression, 1, 0.2% | DS-INTENTS/i20 | `agent:governance.tools` | yes |
| `batch_sweep_8_2` | 8 | 5 | 12 | 172 | 1.00, 5.0 tests, 1.7% | 1.00, 5.0 tests, 1.7% | regression, 5, 1.6% | MNT-03 | `skill:rollback#procedure` | yes |
| `batch_benign` | 9 | 0 | 1 (0) | 165 | 0.00, 12.0 tests, 4.9% | 1.00, 17.0 tests, 9.8% | regression, 17, 8.3% | PUB-02 | `code:tools/content_tools.py::get_page_stats` | no |

## Reading

- **The replay prunes less, and stays exact.** 10 to 172 of the 180 tests diverge, 120 on average, against 34 for a
  single change. None of the 1,374 outcomes that replay to the end differs from the recorded majority.
- **A batch is not the union of its members.** Four batches gain a revealing test that none of their members has
  alone: PUB-02 under three batches that hold the reordered routing guidance (two of them, `batch_benign` and
  `batch_sweep_6_1`, are harmless edits only), and DS-INTENTS/i20 and WF4-01 under `batch_nightly`. No batch loses
  a revealing test of its members.
- **Every revealed batch is found offline with no budget,** by every order of the reached tests, apart from
  `batch_sweep_6_1`, whose one revealing test fails four runs of five, in three runs of four.
- **The adaptive method, members held out,** finds 88% of the 20 revealed batches at a 5% budget and 95% at 20%,
  after 4.0 and 5.5 tests on average, for 1.7% and 2.7% of the suite. Calibrated on every other change, the
  members included, it finds 95% at both budgets after 2.4 and 3.6 tests: what it has seen of a member is worth a
  few tests, and at a 5% budget some detection.
- **The blame is right in most runs:** of the 95 offline runs at a 20% budget that end at a failure, the component
  blamed most belongs to a member that is a regression alone in 88, and the failed test reveals that very member
  in 65.
- **Live, 19 of the 20 revealed batches are found,** after one to seventeen tests, and none of the three batches no
  test reveals gets a regression verdict. `batch_benign` is found by PUB-02 after 17 tests, for 8.3% of the suite.
  The one missed is `batch_sweep_6_1`, where the check runs out of its 20% budget after 57 tests. In 17 of the 18
  batches with a regression member, the component blamed most belongs to such a member.
