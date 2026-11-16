# Batches of changes

Three batches of catalog changes applied to one copy each (`traceeval mutations` lists them with their members),
recorded with Gemma, five repetitions, into a copy of `runs/gemma7` (`runs/gemma7_batches`), and replayed with
every strategy like the 43 single changes. Tokens are shares of the full suite (2,084,733 tokens).

| batch | members | revealing tests |
|---|---|---|
| `batch_nightly`: a day's merges | `code_metadata_arg_swap`, `code_retry_drop_idempotency`, `code_links_external_lenient`, `skill_governance_drop_consent`, `skill_translation_wrong_default`, `prompt_seo_tool_removed`, and the harmless `benign_code_rename_locals`, `benign_brand_skill_prose_reworded` | 28 |
| `batch_publishing_pr`: one pull request on the publishing path | `skill_publish_drop_link_validation`, `code_links_external_lenient`, `config_unpublish_no_approval` | 9 |
| `batch_benign`: a day of harmless edits | all nine benign changes | 1: PUB-02, in all five runs (below) |

## The replay

A strategy that learns from the other recorded changes does not learn from a batch's members
(`History.training_variants`), and every run ends at its first failure. Per cell: detection (the share of the five
seeds in which a revealing test ran and failed), the tokens spent, the tests run. A budget of 20% is given only
where it differs from 5%.

| strategy | nightly @5% | nightly @20% | publishing PR @5% | publishing PR @20% | benign batch @5% | benign batch @20% |
|---|---|---|---|---|---|---|
| `full` | 1.0, 2.8%, 6 tests | | 0.0, 4.9%, 11 | 1.0, 10.4%, 19 | 0.0, 5.0%, 11 | 0.0, 20%, 36 |
| `random` | 0.6, 3.1%, 8 | 1.0, 3.4%, 8 | 0.2, 4.6%, 11 | 1.0, 8.4%, 16 | 0.0, 4.9%, 11 | 0.0, 20%, 40 |
| `declared` | 1.0, 1.0%, 3 | | 1.0, 0.6%, 1 | | 0.0, 4.9%, 4 | 0.0, 20%, 12 |
| `ir_tfidf` | 1.0, 0.5%, 1 | | 1.0, 2.2%, 4 | | 0.0, 5.0%, 10 | 0.0, 20%, 23 |
| `observed` | 0.6, 0.9%, 6 | | 1.0, 0.7%, 1 | | 0.0, 4.9%, 23 | 0.0, 20%, 75 |
| `observed_diverse` | 1.0, 4.8%, 11 | | 1.0, 3.1%, 7 | | 0.0, 4.9%, 11 | 0.0, 20%, 22 |
| `cost_aware` | 0.6, 0.9%, 6 | | 1.0, 0.7%, 1 | | 0.0, 4.9%, 23 | 0.0, 20%, 73 |
| `history_ml` | 1.0, 3.5%, 2 | | 1.0, 4.6%, 16 | | 0.0, 5.0%, 4 | 0.0, 20%, 11 |
| `casper_slices` | 1.0, 0.5%, 3 | | 0.0, 5.0%, 17 | 0.4, 19%, 30 | 0.0, 4.9%, 17 | 0.0, 20%, 31 |
| `risk_aware_ts` | 0.8, 1.0%, 2 | | 1.0, 2.2%, 2 | 1.0, 3.0%, 4 | 0.0, 5.0%, 8 | 0.8, 14%, 17 |
| `adaptive_bayes` | 1.0, 0.3%, 1 | | 1.0, 1.9%, 4 | | 0.0, 4.9%, 11 | 0.0, 20%, 37 |

- On the nightly batch every run of `observed`, `cost_aware` and the bandit ends at a failure. Where their
  detection is below 1.0, the test that failed passes in most of its five runs under the batch, so it is not a
  revealing test.
- The adaptive method blames `agent:seo.tools` on the nightly batch and `code:services/links.py::validate_links` on
  the publishing pull request, in every seed. Both belong to a member that is a regression on its own, and the test
  that failed reveals that member alone (`scripts/analysis/batch_calibration.py`).
- The benign batch is found by the bandit only, which runs the risky tests first, in four seeds of five at 20%. The
  adaptive method does not reach PUB-02 within the budget in any seed and ends without a verdict.

## The live check

`traceeval check <batch> --history runs/gemma7 --budget 0.2 --backend vllm`, with the components the posterior
holds responsible (`blamed`). These checks were run with the batch's members still among the changes the check
learned from, so they needed fewer tests than the replay above on the publishing pull request; with the members
held out, the nightly check runs the same test and blames `agent:seo.tools` at 0.75.

| batch | live verdict | tests, tokens | blamed |
|---|---|---|---|
| `batch_nightly` | regression: SEO-06 failed | 1 test, 0.3% | `agent:seo.tools` 0.77; the other members stay near their prior (0.50 to 0.55), untested |
| `batch_publishing_pr` | regression: PUB-02 failed | 2 tests, 1.2% | `code:services/links.py::validate_links` 0.68, `skill:publishing-workflow#procedure` 0.59, `config:tools.requires_approval` 0.49 |
| `batch_benign` | no failure within the budget; $P(\text{something broke}) = 0.32$ | 34 tests, 20% | `code:tools/content_tools.py::get_page_stats` 0.21, the tool no agent may use: no test can reach it, so nothing can clear it |

## The benign batch

It is revealed by one test, PUB-02 (publish a page with a broken link: the answer must name the link), which fails
in every one of its five runs under the batch and passes in every run under each member alone. Two of the members
do it together: PUB-02 run live, three times, on every combination of the three prompt edits on its path gives

| prompt edits applied | PUB-02 |
|---|---|
| the publishing skill's prose reflowed | pass, pass, pass |
| the orchestrator's prompt reworded | pass, pass, pass |
| the routing skill's guidance reordered | fail, pass, pass |
| prose reflowed + prompt reworded | pass, pass, pass |
| prose reflowed + guidance reordered | pass, pass, pass |
| prompt reworded + guidance reordered | fail, fail, fail |
| all three | fail, fail, fail |

so the orchestrator's prompt reworded and its routing guidance reordered, harmless alone, make the orchestrator
drop the broken link from the answer it relays. The nine harmless edits are not harmless together, and the ground
truth of a batch is not the union of its members'.

## Replay-first

The same batches with the replay in front (`traceeval replay-first`; `docs/RESEARCH_PLAN.md` §5.7): the tests
that diverge on the batch's copy, what is left of them after their divergence points as a share of the suite's
tokens, and the adaptive method over those tests at a 5% and a 20% budget (detection as the share of the five
seeds, tests run, tokens; how the run ended when not at a failure; one cell where the two budgets agree).

| batch | diverged tests | their tokens after the divergence | adaptive, 5% | adaptive, 20% |
|---|---|---|---|---|
| `batch_benign` | 165 | 0.949 | 0.0, 11 tests, 4.9%: budget | 0.0, 29 tests, 19.9%: budget/uninformative |
| `batch_nightly` | 67 | 0.388 | 1.0, 1 test, 0.4% |  |
| `batch_publishing_pr` | 49 | 0.311 | 1.0, 2 tests, 0.7% |  |

- The replay is exact on the batches: 0 of its 259 replayed outcomes differ from the recorded majority, and 0
  replayed tests fail.
- With no budget, every strategy ends at a failure on all three batches, `batch_benign` included: PUB-02 is
  reached after 18 tests (the bandit) to 131 (cheapest first), for 15% to 71% of the suite's tokens; the adaptive
  method reaches it after 39 tests, for 26%. Within a 20% budget only the bandit, in four seeds of five, and the
  random order, in one, reach it.
