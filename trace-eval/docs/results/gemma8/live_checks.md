# The live checks against the offline evaluation

`traceeval check <change> --history runs/gemma8 --budget 0.2 --backend vllm`, run on each of the 43 changes, one
check at a time, with Gemma started anew on two cluster GPUs (not the server the recording was made on). A check
replays the changed copy against the recording's cassette, then runs the adaptive method live over the tests that
diverge, with the cassette in front of the model. Offline, the evaluator ran the same method replay-first on the
recorded runs, five seeds per change (`runs/gemma8/results/replay_first.csv`). Tokens are shares of the full suite
(2,083,624 tokens).

```bash
python scripts/analysis/live_checks.py runs/gemma8 runs/live_check8
```

The 43 checks took 16 minutes in all: 148 seconds of replay, 222 seconds of model time for 168 tests, and 70% of
one suite's tokens for the 43 verdicts together.

- checks: 43 of 43
- the live verdict is one the evaluator gave in some seed on 41, and its majority verdict on 41;
- regressions (28): the live check found 27, the evaluator's majority 27;
- changes no test reveals (15): regression verdicts live 1, offline 0;
- tokens per check: live 1.6% of the suite; offline, charged from the divergence point on, 2.1%.

| change | regression | revealing tests | tests that diverge | live verdict | live tests | live tokens | failed live | offline verdicts | offline tests | offline tokens |
|---|---|---|---|---|---|---|---|---|---|---|
| `benign_brand_skill_prose_reworded` | no | 0 | 12 | clean | 7 | 1.4% |  | clean (5 of 5) | 7 | 3.1% |
| `benign_code_comment_docstring` | no | 0 | 0 | clean | 0 | 0.0% |  | clean (5 of 5) | 0 | 0.0% |
| `benign_code_rename_locals` | no | 0 | 0 | clean | 0 | 0.0% |  | clean (5 of 5) | 0 | 0.0% |
| `benign_config_comments_reordered` | no | 0 | 0 | clean | 0 | 0.0% |  | clean (5 of 5) | 0 | 0.0% |
| `benign_new_unused_tool` | no | 0 | 0 | clean | 0 | 0.0% |  | clean (5 of 5) | 0 | 0.0% |
| `benign_orchestrator_prompt_wording` | no | 0 | 153 | regression | 2 | 1.3% | WF3-03 | clean (5 of 5) | 21 | 8.8% |
| `benign_routing_guidance_reordered` | no | 0 | 153 | clean | 10 | 2.9% |  | clean (5 of 5) | 10 | 4.0% |
| `benign_skill_prose_reflow` | no | 0 | 46 | clean | 5 | 2.6% |  | clean (5 of 5) | 5 | 3.1% |
| `benign_translation_intents_reordered` | no | 0 | 14 | clean | 4 | 0.7% |  | clean (5 of 5) | 4 | 1.0% |
| `code_approval_gate_bypass` | yes | 1 | 2 | regression | 2 | 0.4% | PUB-07 | regression (5 of 5) | 2 | 0.4% |
| `code_audit_ignores_alt_text` | yes | 1 | 4 | regression | 1 | 0.2% | OPT-01 | regression (5 of 5) | 1 | 0.2% |
| `code_brand_case_sensitive` | yes | 1 | 1 | regression | 1 | 0.1% | BRD-02 | regression (5 of 5) | 1 | 0.1% |
| `code_delegation_drops_context` | yes | 4 | 12 | regression | 1 | 2.8% | WF1-02 | regression (5 of 5) | 1 | 0.4% to 2.9% |
| `code_delegation_truncates_answer` | yes | 25 | 80 | regression | 8 | 0.8% | WF1-02 | regression (5 of 5) | 8 | 0.8% |
| `code_edit_keeps_review` | no | 0 | 0 | clean | 0 | 0.0% |  | clean (5 of 5) | 0 | 0.0% |
| `code_get_page_review_flag` | yes | 4 | 65 | regression | 12 | 2.9% | PUB-01 | regression (5 of 5) | 12 | 4.0% |
| `code_insights_rank_reversed` | yes | 4 | 5 | regression | 1 | 0.2% | INS-01 | regression (5 of 5) | 1 | 0.2% |
| `code_links_external_lenient` | yes | 6 | 7 | regression | 1 | 0.3% | AUT-02 | regression (5 of 5) | 1 | 0.3% |
| `code_metadata_arg_swap` | yes | 5 | 21 | regression | 2 | 0.4% | AUT-02 | regression (5 of 5) | 2 | 0.6% |
| `code_retry_drop_idempotency` | yes | 5 | 5 | regression | 1 | 0.2% | TRN-06 | regression (5 of 5) | 1 | 0.2% |
| `code_search_case_sensitive` | yes | 3 | 4 | regression | 1 | 0.2% | BRD-05 | regression (5 of 5) | 1 | 0.2% |
| `code_termination_off_by_six` | yes | 5 | 3 | regression | 0 | 0.0% | WF4-01, WF4-02, WF6-01 | regression (5 of 5) | 0 | 0.0% |
| `combined_seo_keyword_limit` | yes | 1 | 2 | regression | 2 | 0.4% | SEO-07 | regression (5 of 5) | 2 | 0.4% |
| `config_default_agent_publishing` | yes | 3 | 153 | regression | 1 | 0.2% | DS-ROUTING/r39 | regression (5 of 5) | 1 | 0.2% |
| `config_disable_validate_links` | yes | 49 | 48 | regression | 0 | 0.0% | PUB-01, PUB-11, PUB-12, PUB-13, PUB-16, PUB-18, DS-INTENTS/i01 | regression (5 of 5) | 0 | 0.0% |
| `config_max_tool_calls_5` | yes | 11 | 14 | regression | 0 | 0.0% | WF4-01, WF4-02, WF6-01 | regression (5 of 5) | 0 | 0.0% |
| `config_require_review_false` | no | 0 | 45 | clean | 34 | 18.7% |  | budget (5 of 5) | 30 | 19.7% |
| `config_retries_0` | yes | 8 | 8 | regression | 1 | 0.2% | PUB-11 | regression (5 of 5) | 1 | 0.2% |
| `config_seo_title_20` | no | 0 | 11 | clean | 9 | 4.3% |  | clean (5 of 5) | 9 | 8.0% |
| `config_unpublish_no_approval` | yes | 1 | 1 | regression | 1 | 0.2% | PUB-07 | regression (5 of 5) | 1 | 0.2% |
| `prompt_governance_consent_tool_removed` | yes | 7 | 12 | regression | 1 | 0.3% | GOV-02 | regression (5 of 5) | 1 | 0.3% |
| `prompt_seo_tool_removed` | yes | 8 | 11 | regression | 1 | 0.4% | SEO-01 | regression (5 of 5) | 1 | 0.4% |
| `skill_authoring_drop_metadata` | yes | 1 | 27 | clean | 8 | 2.8% |  | clean (5 of 5) | 8 | 3.2% |
| `skill_governance_drop_consent` | yes | 5 | 12 | regression | 3 | 0.5% | GOV-02 | regression (5 of 5) | 3 | 0.6% |
| `skill_linkval_ignore_assets` | no | 0 | 74 | clean | 13 | 5.9% |  | clean (5 of 5) | 13 | 6.6% |
| `skill_publish_drop_link_validation` | yes | 4 | 46 | regression | 8 | 4.1% | PUB-03 | regression (5 of 5) | 8 | 4.4% |
| `skill_publish_drop_permission_check` | yes | 3 | 46 | regression | 1 | 0.4% | PUB-08 | regression (5 of 5) | 1 | 0.4% |
| `skill_rollback_drop_permission_check` | yes | 1 | 7 | regression | 1 | 0.3% | MNT-03 | regression (5 of 5) | 1 | 0.3% |
| `skill_rollback_restores_latest` | yes | 3 | 7 | regression | 2 | 0.6% | MNT-02 | regression (5 of 5) | 2 | 0.7% |
| `skill_routing_drop_approval` | yes | 11 | 153 | regression | 2 | 0.9% | WF3-03 | regression (5 of 5) | 2 | 0.9% |
| `skill_routing_drop_brand_gate` | no | 0 | 153 | clean | 9 | 4.6% |  | clean (5 of 5) | 9 | 4.6% to 5.0% |
| `skill_seo_drop_length_guard` | no | 0 | 11 | clean | 9 | 7.3% |  | clean (5 of 5) | 9 | 8.4% |
| `skill_translation_wrong_default` | yes | 3 | 14 | regression | 3 | 0.5% | TRN-02 | regression (5 of 5) | 3 | 0.6% |

## Reading

- The live verdict is the evaluator's on 41 of the 43 changes, after as many tests.
- Eight checks call no model: on five no test diverges, and three regressions are found by a test that replays to
  a failure (`code_termination_off_by_six`, `config_disable_validate_links`, `config_max_tool_calls_5`).
- 27 of the 28 regressions are found, live and offline. The one missed is `skill_authoring_drop_metadata`: the
  method calls it clean after eight tests, with 17 reached tests not run.
- The one false alarm is `benign_orchestrator_prompt_wording`: live, WF3-03 fails its one run (the orchestrator
  skips the approval). No test reveals this change in the recording, where WF3-03 passes its five runs; in the
  second recording it passes four of five (`second_recording.md`). A check reads one run of a test and the ground
  truth reads five, so on a test whose runs disagree one run can be the minority. `traceeval check --confirm`
  runs a failing test again before its failure counts ([RESEARCH_PLAN.md](../../RESEARCH_PLAN.md) §5.4).
- On `config_require_review_false` the live check ends clean after 34 tests where the evaluator's budget ends
  the run after 30. The evaluator charges a test everything after its divergence point; the live check pays for
  the requests the cassette lacks, wherever they come in the run, so the same budget buys more tests: 1.6% of
  the suite per check live, 2.1% offline.
