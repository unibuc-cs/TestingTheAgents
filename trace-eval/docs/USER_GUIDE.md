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
examples are for `code_retry_disabled`, a change that makes the retry helper give up after the first transient
failure:

| factor | what it is | example |
|---|---|---|
| kind ratio | of the tests that earlier changes of this kind touched, the fraction that caught the change, averaged over the other recorded changes | tests that ran a changed line in the 13 earlier code changes caught them 11% of the time. Tests that only called a changed function: 20%, from just four changes, almost all of it from `code_delegation_depth_zero` (the orchestrator can no longer hand work to the specialists), which breaks 106 of the 136 tests |
| test record | the earlier changes of this kind that touched the test and that it caught, over the number an average touched test would have caught, both padded with 2 (`prior_strength`) | DS-INTENTS/i19 was expected to catch 0.78 of them and caught none: (0 + 2) / (0.78 + 2) = 0.72. PUB-12 caught one where the average was 0.23: (1 + 2) / (0.23 + 2) = 1.35 |
| coverage | how often the test ran the changed code in its runs on the original app, from 0 to 1 | PUB-11 runs the changed line of `harness/retry.py` in every run: 1.0 |
| tilt | word overlap between the test and the diff (0.5 to 1.5), plus 0.5 if the test's author declared the dependency | a test whose request mentions publishing gets more weight for a change to the publishing skill |

A test with no known link to the changed part gets a small fixed sensitivity (`indirect`, 0.02).

**Weights.** Each factor has its own knob: `prior_strength` sets how far a short record can move a test (larger
means the record counts less), the tilt has a fixed range, and `indirect` sets the floor. The factors are not
weighted further against each other: with 38 changes, extra weights would mostly fit noise. Measuring what each
factor adds (an ablation) is on the roadmap.

**Where the records come from.** Nothing is stored apart from the recordings. Each time the method runs, it
recomputes the kind ratios and every test's record from the recording it is given (`runs/<name>`, or `--history`
for `traceeval check`), from every recorded change except the one being evaluated. The records therefore grow
when more changes are recorded: `traceeval mutants --workdir runs/<name> --only <change>` adds a change to an
existing recording, and the next run uses it. In a team's pipeline, nightly full-suite runs would play that role:
every change whose full-suite outcome is known becomes one more entry in the record of each test it touched.
`traceeval check` does not add its own runs, because a check runs only a few tests, which is not enough to know
which tests the change breaks. Records match code by line number, so record again after editing the app's code.

## 6. How to extend

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

## 7. Gotchas

- The tests replay Gemma's recorded answers (`tests/cassettes/gemma.jsonl`), each keyed by the exact request. After
  a change to anything a prompt is built from (a skill, an agent, a config value, a tool, a case), the replay
  misses (`CacheMiss`): start Gemma (`scripts/gpu_remote.sh up`), run `TRACEEVAL_BACKEND=vllm pytest -q` to record
  what is missing, and commit the cassette.
- Test texts share vocabulary with skills and config keys, which is why `ir_tfidf` is strong here.
- `history_ml` (needs scikit-learn) and `observed_diverse` are optional. `--strategies all` includes them.
- `runs/` is git-ignored and large (it holds line-level coverage). To keep a run, copy its `results/` into
  `docs/results/`.
