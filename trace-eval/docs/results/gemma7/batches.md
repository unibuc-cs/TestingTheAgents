# Batches of changes

Three batches of catalog changes applied to one copy each (`traceeval mutations` lists them with their members),
recorded with Gemma, five repetitions, into a copy of `runs/gemma7` (`runs/gemma7_batches`), and replayed with
every strategy like the 43 single changes. Tokens are shares of the full suite (2,084,733 tokens).

| batch | members | revealing tests |
|---|---|---|
| `batch_nightly`: a day's merges | `code_metadata_arg_swap`, `code_retry_drop_idempotency`, `code_links_external_lenient`, `skill_governance_drop_consent`, `skill_translation_wrong_default`, `prompt_seo_tool_removed`, and the harmless `benign_code_rename_locals`, `benign_brand_skill_prose_reworded` | 28 |
| `batch_publishing_pr`: one pull request on the publishing path | `skill_publish_drop_link_validation`, `code_links_external_lenient`, `config_unpublish_no_approval` | 9 |
| `batch_benign`: a day of harmless edits | all nine benign changes | 1: PUB-02, in all five runs (below) |

Detection (share of five seeds in which a revealing test ran and failed), the tokens spent, and the tests run, at a
5% and a 20% budget:

| strategy | nightly @5% | nightly @20% | publishing PR @5% | publishing PR @20% | benign batch @5% | benign batch @20% |
|---|---|---|---|---|---|---|
| `full` | 1.0, 5.0%, 11 tests | 1.0, 20%, 36 | 0.0, 4.9%, 11 | 1.0, 20%, 33 | 0.0 | 0.0 |
| `random` | 0.6, 5.0%, 12 | 1.0, 20%, 38 | 0.2, 4.9%, 12 | 1.0, 20%, 39 | 0.0 | 0.0 |
| `declared` | 1.0, 4.9%, 6 | 1.0, 20%, 14 | 1.0, 5.0%, 12 | 1.0, 20%, 20 | 0.0 | 0.0 |
| `ir_tfidf` | 1.0, 5.6%, 8 | 1.0, 20%, 31 | 1.0, 5.0%, 7 | 1.0, 20%, 26 | 0.0 | 0.0 |
| `observed` | 1.0, 5.5%, 11 | 1.0, 20%, 43 | 1.0, 5.0%, 13 | 1.0, 20%, 42 | 0.0 | 0.0 |
| `cost_aware` | 1.0, 4.9%, 8 | 1.0, 20%, 37 | 1.0, 5.0%, 9 | 1.0, 20%, 38 | 0.0 | 0.0 |
| `casper_slices` | 1.0, 5.0%, 18 | 1.0, 20%, 28 | 0.0, 5.0%, 17 | 1.0, 20%, 28 | 0.0 | 0.0 |
| `risk_aware_ts` | 1.0, 5.5%, 5 | 1.0, 21%, 15 | 0.2, 5.0%, 8 | 0.8, 20%, 20 | 0.4 | 0.8 |
| `adaptive_bayes` | 1.0, 0.3%, 1 | 1.0, 0.3%, 1 | 1.0, 1.2%, 2 | 1.0, 1.2%, 2 | 0.0, 5.0%, 14 | 0.0, 20%, 34 |

Live, `traceeval check <batch> --history runs/gemma7 --budget 0.2 --backend vllm`, with the components the
posterior holds responsible (`blamed`):

| batch | live verdict | tests, tokens | blamed |
|---|---|---|---|
| `batch_nightly` | regression: SEO-06 failed | 1 test, 0.3% | `agent:seo.tools` 0.77; the other members stay near their prior (0.50 to 0.55), untested |
| `batch_publishing_pr` | regression: PUB-02 failed | 2 tests, 1.2% | `code:services/links.py::validate_links` 0.68, `skill:publishing-workflow#procedure` 0.59, `config:tools.requires_approval` 0.49 |
| `batch_benign` | no failure within the budget; P(something broke) = 0.32 | 34 tests, 20% | `code:tools/content_tools.py::get_page_stats` 0.21, the tool no agent may use: no test can reach it, so nothing can clear it |

The benign batch is revealed by one test, PUB-02 (publish a page with a broken link: the answer must name the link),
which fails in every one of its five runs under the batch and passes in every run under each member alone. Two of
the members do it together: PUB-02 run live, three times, on every combination of the three prompt edits on its
path gives

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
truth of a batch is not the union of its members'. The adaptive method does not reach PUB-02 within the budget in
any seed; the bandit, which runs the risky tests first, finds it in four of five.
