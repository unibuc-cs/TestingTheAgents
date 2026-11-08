# User guide

Read the README first. This guide adds what you need to work inside the repository.

## 1. Data flow

```
 test catalog ────────┐                                 ┌─ strategy picks tests from: the change set +
                      ▼                                 │  baseline traces + costs + pass rates
 baseline app ──► run all tests K× ──► traces, costs ───┤
                                                        ├─► "execute" = look up the recorded outcome
 changes ────► edited copies ──────► diff ─► change set ┤   of that test under that change
       │                                                │
       └─────► run all tests K× ──► which tests fail ───┘─► metrics ─► report
```

The runs are recorded once (with the model on the GPU server) and replayed thousands of times. `runs/<name>/`
holds the edited copies (`variants/`), the recordings (`history/*.jsonl`) and the results (`results/`).
`traceeval check` is the same loop for one change, live: "execute" runs the test with the model
(`experiment/check.py`), and a recording supplies only the baseline traces and costs and the other changes.

## 2. Vocabulary

- **Case / test**: one entry of the catalog. Scenario tests in `catalog/tests/*.yaml`; dataset items in
  `catalog/datasets/*.yaml` (ids `DS-ROUTING/r01` etc.).
- **Declared dependencies**: the `declared:` block a test author writes. It is deliberately incomplete.
- **Observed dependencies**: the components the trace shows the run touched (`agent:x`, `skill:x`, `tool:x`,
  `config:key`, `code:file::function`, `line:file:n`).
- **Change set**: the diff turned into components with the same identifiers (`traceeval/mutation/changeset.py`).
  Comments, docstrings, blank lines and formatting are left out: they add no component and no diff line.
- **Revealing test**: passes on the baseline, fails on the changed copy (majority over K repetitions).
- **Budget**: tokens, shown as a fraction of the full-suite cost.
- **Stop reason** (`adaptive_bayes` only): `clean`, `regression` (a test that passed on the original app failed), `budget`, `uninformative`
  (no test left that could change the verdict), `no_components` (the change set is empty, e.g. after a comment-only edit, so there is nothing
  to test).

## 3. Where to look in the code (in this order)

| Want to understand… | Read |
|---|---|
| what the agents do | `sut/skills/publishing-workflow/SKILL.md`, `sut/agents/publishing.yaml`, `sut/config/runtime.yaml` |
| how a request becomes tool calls | `sut/harness/runtime.py` (`_run_agent`), `dispatcher.py`, `backends/llm_openai.py` |
| how a test is run and scored | `experiment/executor.py` (`run_case`), `scoring/scorers.py` |
| how a change becomes components | `mutation/catalog.py` (data), `mutation/changeset.py` |
| the baselines | `selection/strategies.py` (about 140 lines) |
| the proposed method | `selection/adaptive_bayes.py` (its docstring explains the four ideas) |
| the metrics | `experiment/metrics.py`, `experiment/evaluate.py` |
| the prototype (one change, live) | `experiment/check.py` |

Everything else is plumbing (loaders, tracing, report).

## 4. How to read the report

- **Section 1** must say sanity OK. If it does not, the testbed is broken, not the strategies.
- **Section 2**: `detected` is the fraction of changes where at least one revealing test was run and failed.
  Compare strategies by the second table (tokens actually spent), not by the nominal budget. Selecting
  strategies run out of tests, the adaptive one stops early, and the rest always spend the whole budget.
- **Section 3**: tokens spent on changes that break nothing. The stop-reason table shows whether the
  adaptive strategy said `clean` on benign changes and `regression` on regressions.
- **Section 4**: APFD / APFD_c of the complete order (prioritization quality) and selection recall.
- `replay.csv` has one row per (change, strategy, budget, seed) if you want to slice it yourself.

## 5. How the adaptive method weighs a test

For every changed part of the app (a function, a skill's procedure, a config key) and every test, the method
estimates a **sensitivity**: the probability that the test fails if that part is broken. It runs the test that
tells it the most per token (high sensitivity, low cost), and a passing sensitive test is strong evidence that
nothing broke. The sensitivity is the product of four factors (`selection/adaptive_bayes.py::sensitivity`). The
examples are for `code_retry_drop_idempotency` (retried writes lose their idempotency key, §6), with the numbers
of `runs/gemma3`:

| factor | what it is | example |
|---|---|---|
| kind ratio | of the tests that earlier changes of this kind touched, the fraction that caught the change, averaged over the other recorded changes | for a code change, tests that ran a changed line caught it 12% of the time on average: 6 of the 10 tests that ran the changed line of the link check caught `code_links_external_lenient`, but only 2 of the 136 that ran the changed line of the agent loop caught `code_termination_off_by_six`. Tests that only called a changed function, without running the changed line, caught nothing (the 1% floor) |
| test record | the earlier changes of this kind that touched the test and that it caught, over the number an average touched test would have caught, both padded with 2 (`prior_strength`) | AUT-02 caught 3 where an average test would have caught 1.02: (3 + 2) / (1.02 + 2) = 1.66. AUT-13 caught none of an expected 1.02: (0 + 2) / (1.02 + 2) = 0.66 |
| coverage | how often the test ran the changed code in its runs on the original app, from 0 to 1 | PUB-12 runs the changed line of `harness/retry.py` in every run: 1.0 |
| tilt | text similarity between the test and the diff (0.5 to 1.5), plus 0.5 if the test's author declared the dependency. The similarity is word overlap by default; `adaptive_bayes_tfidf` uses TF-IDF instead and `adaptive_bayes_notext` no text at all (`--strategies adaptive_bayes adaptive_bayes_tfidf adaptive_bayes_notext` compares them; RESEARCH_PLAN §5.2) | a test whose request mentions publishing gets more weight for a change to the publishing skill |

A test with no known link to the changed part gets a small fixed sensitivity (`indirect`, 0.02).

**Weights.** Each factor has its own knob: `prior_strength` sets how far a short record can move a test (larger
means the record counts less), the tilt has a fixed range, and `indirect` sets the floor. The factors are not
weighted further against each other: with 33 changes, extra weights would mostly fit noise. Measuring what each
factor adds (an ablation) is on the roadmap.

**Where the records come from.** Nothing is stored apart from the recordings. Each time the method runs, it
recomputes the kind ratios and every test's record from the recording it is given (`runs/<name>`, or `--history`
for `traceeval check`), from every recorded change except the one being evaluated. The records therefore grow
when more changes are recorded: `traceeval mutants --workdir runs/<name> --only <change>` adds a change to an
existing recording, and the next run uses it. In a team's pipeline, nightly full-suite runs would play that role:
every change whose full-suite outcome is known becomes one more entry in the record of each test it touched.
`traceeval check` does not add its own runs, because a check runs only a few tests, which is not enough to know
which tests the change breaks. Records match code by line number, so record again after editing the app's code.

## 6. The controlled changes

The experiment plants 33 known changes in copies of the app (`mutation/catalog.py`) and measures how well each
strategy finds them: 26 regressions, which at least one test should reveal, and 7 benign changes, which no test
should. Each one is in the set for a reason: a kind of change (code, skill, prompt, config), a reach (one test or
dozens), or a trap for selection. "Revealing tests" counts the tests that pass on the original app and fail on the
changed copy, in the recordings `runs/gemma2` / `runs/qwen2`.

| change | what it does | why it is in the set | revealing tests (Gemma / Qwen) |
|---|---|---|---|
| **Code: tools, services, harness** | | | |
| `code_metadata_arg_swap` | the SEO tool writes the title into the description field | a classic bug in a tool adapter; only tests that check the stored metadata see it | 5 / 5 |
| `code_retry_drop_idempotency` | retried writes lose their idempotency key, so a write retried after a lost acknowledgement happens twice | a harness bug that shows only under one kind of fault; reused by the SDD demo (FS-0105) | 5 / 5 |
| `code_approval_gate_bypass` | the dispatcher stops asking for approval tokens on guarded tools | a narrow safety guard that a single test depends on; reused by the SDD demo (FS-0102) | 1 / 1 |
| `code_links_external_lenient` | link validation treats every external URL as reachable | a bug in a service that several skills share; reused by the SDD demo (FS-0103) | 6 / 6 |
| `code_get_page_review_flag` | the shared `get_page` tool reports a requested review as approved | a shared tool with a wide reach, and the clearest case of model dependence | 1 / 15 |
| `code_edit_keeps_review` | editing a page no longer cancels its approved review | a service bug a model can hide: Gemma requests a review after every edit anyway | 0 / 1 |
| **Code: agent loop** | | | |
| `code_termination_off_by_six` | the agent loop stops six tool calls before the configured budget | every test runs the changed line, but only long tasks fail: covering code is not catching the bug | 2 / 2 |
| `code_delegation_truncates_answer` | the orchestrator receives only the first 40 characters of the specialist's answer | a delegation bug that shows only when the answer must carry a fact past 40 characters | 8 / 6 |
| **Skills** | | | |
| `skill_publish_drop_link_validation` | publishing no longer validates links | a change to a skill's procedure, not to code; the link check is a skill no test declares | 6 / 1 |
| `skill_publish_drop_permission_check` | publishing no longer checks the user's permission | a safety rule enforced only in a skill: nothing below it stops the write | 3 / 3 |
| `skill_authoring_drop_metadata` | new pages no longer get SEO metadata | a removed step that one test notices | 1 / 1 |
| `skill_translation_wrong_default` | translation uses en-US instead of the configured languages | a skill that ignores a configuration value | 2 / 2 |
| `skill_rollback_drop_permission_check` | rollback no longer checks the permission; the service still refuses | defence in depth: the data stays safe and only the behaviour shows the mistake | 1 / 1 |
| `skill_rollback_restores_latest` | rollback restores the latest version instead of the requested one | a wrong argument in a procedure step | 3 / 2 |
| `skill_linkval_ignore_assets` | the shared link-validation skill lets broken asset references through | a change to a skill included by others, reaching tests that never name it | 0 / 1 |
| `skill_governance_drop_consent` | user data is exported without checking consent | a privacy rule enforced in a skill | 5 / 5 |
| `skill_seo_drop_length_guard` | SEO no longer refuses over-long titles; reused by the SDD demo (FS-0104) | a guard the model must apply itself; Gemma ignores the limit anyway | 0 / 1 |
| **Agent definitions** | | | |
| `prompt_governance_consent_tool_removed` | the governance agent loses the `check_consent` tool | a change to an agent's tool list | 6 / 4 |
| `prompt_seo_tool_removed` | the SEO agent loses `set_page_metadata` | the same for a tool that writes | 6 / 5 |
| **Configuration** | | | |
| `config_disable_validate_links` | a feature flag turns link validation off everywhere | one key with a wide reach: the broad change in the set | 40 / 43 |
| `config_require_review_false` | pages no longer need an approved review before publishing | a policy switch in configuration; Gemma's own mistake hides it | 0 / 3 |
| `config_max_tool_calls_5` | the step budget drops from 12 to 5 tool calls | a value that limits every agent; long tasks fail | 8 / 8 |
| `config_retries_0` | temporary tool failures are no longer retried; reused by the SDD demo (FS-0105) | a change only the tests with an injected fault notice | 8 / 5 |
| `config_seo_title_20` | the maximum SEO title length drops from 60 to 20 | a boundary value; Gemma ignores the limit anyway | 0 / 1 |
| `config_default_agent_publishing` | requests no specialist owns go to publishing instead of authoring | a routing setting the orchestrator reads | 3 / 3 |
| **Code and configuration together** | | | |
| `combined_seo_keyword_limit` | a keyword-count rule in code plus a very low limit in config | a regression that needs both edits; each alone is harmless | 1 / 1 |
| **Benign: no test should fail** | | | |
| `benign_skill_prose_reflow` | the publishing skill's prose is reworded, its procedure untouched | a wording change: a strategy should spend little on it | 0 / 0 |
| `benign_code_comment_docstring` | comments and docstrings change in the links service | leaves an empty change set (code only), so there is nothing to test | 0 / 0 |
| `benign_code_rename_locals` | local variables are renamed in the workflow service | a real code edit, in a widely used function, that changes nothing | 0 / 0 |
| `benign_config_comments_reordered` | config comments are rewritten and sections reordered | an empty change set for configuration | 0 / 0 |
| `benign_new_unused_tool` | a new tool is registered that no agent may use | added code that nothing reaches | 0 / 0 |
| `benign_orchestrator_prompt_wording` | the orchestrator's prompt is reworded | a prompt edit on the agent every request passes through | 0 / 0 |
| `benign_translation_intents_reordered` | the translation agent's intents are reordered | an order a model ignores | 0 / 0 |

A change that no test reveals under a model (a 0 above) is a fact about that model, not a bug in the testbed:
the report's sanity line lists them. Five earlier changes were dropped from the set: two exact twins of other
changes (retries disabled in code, approval removed in config), two crashes that only checked the crash
classification (unit tests cover it), and one that broke four tests in five and so told nothing about selection.

## 7. How to extend

- **Test**: add a YAML entry. `expect` supports `route_to`, `state` (`[path, op, value]` with `==`, `!=`, `len`,
  `contains`, `in`, `>=`, `<=`, `absent`, `exists`), `tools_required`, `tools_forbidden`, `tools_not_attempted`,
  `tool_attempts`, `tool_results`, `audit`, `response_contains`, `response_excludes`, `max_steps`, `termination` and
  `tool_errors`. `tool_results` checks the last successful result of a tool like the state (`[tool, path, op, value]`).
  `response_contains` is for facts the answer must report (a job id, a path, which link is broken), not for
  wording; an item that is a list is a set of alternatives. A run that ends with an answer must not end with an
  empty one (check `answered`). A test can also set `fixture_patch`
  and `fault_profile` (`transient_once:<tool>`, `ack_timeout_once:<tool>`, `permanent_down:<tool>`). `pytest`
  checks that the whole catalog passes on the baseline, apart from Gemma's known mistakes, on Gemma's recorded
  answers: record the new case's answers with `TRACEEVAL_BACKEND=vllm pytest -q` (see the gotchas).
- **Tool errors**: a tool error the test intends (a refusal, a missing page, an injected outage) must be listed,
  e.g. `tool_errors: {unpublish_page: approval_required}`. Any other error fails the test as `tool_error:<tool>`,
  unless a later call of the same tool succeeded. A crash in tool or service code (any exception other than a
  `ToolError`) always fails it as `crash:<tool>`. Both are classified `TOOL_ERROR`. `tool_errors: "*"` allows
  any error. A spec scenario (`traceeval/specs/`) that writes its own `expect` gets that by default.
- **Change**: add a `Mutation(...)` to the table in `mutation/catalog.py` with `replace`, `delete_line`,
  `delete_block` or `append` edits. Anchors are literal text, so reformatting `sut/` breaks them, and the
  operators then raise an error. A regression must be revealed by ≥1 test, a benign change by none.
- **Strategy**: in `selection/strategies.py`, subclass `Strategy` (from `selection/base.py`), implement `order(ctx)`, which returns a
  prioritized list (tests left out are not selected), and decorate the class with `@register`. Adaptive
  strategies implement `run(ctx, oracle)`. Use only `ctx.change`, `ctx.catalog`, the baseline facts in
  `ctx.history` and the other changes' outcomes (`ctx.train_variants`). Add the name to `CORE` to include it
  in the default comparison.
- **Model backends**: two models play the agents, Gemma 4 E4B and Qwen3.8-27B (see [EXPERIMENT.md](EXPERIMENT.md)).
  - **Gemma.** `--backend hf` (the default; `pip install -e ".[hf]"`) runs it on the local GPU. `--backend vllm`
    sends it to a vLLM server: `scripts/gpu_remote.sh setup` once, then `scripts/gpu_remote.sh up` starts it on
    the GPU server and opens an SSH tunnel; cases then run 32 at a time (`--workers`). Both build the same
    prompts and parse answers the same way (`traceeval/llm/chat.py`).
  - **Qwen.** `scripts/gpu_remote.sh up qwen` serves it on the other GPU, and `--backend llm` reaches it there
    (`pip install -e ".[llm]"`). The `llm` backend takes any other OpenAI-compatible endpoint through
    `TRACEEVAL_LLM_BASE_URL`, `TRACEEVAL_LLM_API_KEY` and `TRACEEVAL_LLM_MODEL`.
  - **Recorded answers.** `--backend replay` plays Gemma from its recorded answers, with no model
    (`traceeval/llm/cache.py`). With `TRACEEVAL_CACHE=<file>`, `hf` and `vllm` answer from that file what they
    can and add every new answer to it.
  - **Debugging.** `TRACEEVAL_MODEL_LOG=<file>` logs every model call.
- **Judge**: a case with a `judge: {rubric: ...}` block has its answer read by a model once its deterministic
  checks pass (`scoring/scorers.py::judge_answer`). `TRACEEVAL_JUDGE=gemma` or `qwen` picks the model; by default
  it is the one playing the agents. Gemma's verdicts are recorded and replayed with its other answers.

## 8. Gotchas

- The tests replay Gemma's recorded answers (`tests/cassettes/gemma.jsonl`), each keyed by the exact request. After
  a change to anything a prompt is built from (a skill, an agent, a config value, a tool, a case), the replay
  misses (`CacheMiss`): start Gemma (`scripts/gpu_remote.sh up`), run `TRACEEVAL_BACKEND=vllm pytest -q` to record
  what is missing, and commit the cassette.
- Test texts share vocabulary with skills and config keys, which is why `ir_tfidf` is strong here.
- `history_ml` (needs scikit-learn) and `observed_diverse` are optional. `--strategies all` includes them.
- `runs/` is git-ignored and large (it holds line-level coverage). To keep a run, copy its `results/` into
  `docs/results/`.
