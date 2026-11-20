# TODO: the replay-first plan

**Direction.** The paper is built on replay-first testing: after a change, every test is first re-run with the
model answers recorded on the original app. A test that replays to the end has a known outcome for no tokens; a
test that diverges (it makes a request the original app never made) is where the change reaches the model, and only
those tests need the model. `adaptive_bayes` stays as one of the orders compared on the diverged tests.

This file is the plan: what is next, what is open, and one line per finished part with where its results are. The
results themselves are in the README ("Main results") and in `docs/RESEARCH_PLAN.md` §5, with the take-aways in
its §5.9.

## Next, in this order

| | what | state |
|---|---|---|
| 1 | A day of changelists, the open steps: halving live, the rolling cassette, a live sample to watch R, and the adaptive method for a day's many components | §9 |
| 2 | Exact serving for gpt-oss: the prefix cache off, one test at a time, a baseline and the empty change under two starts of the server | later: it needs both of fmi0's GPUs |
| 3 | A second application, tau2-bench's airline domain | later: waits for the go-ahead to install and run its code (§4) |
| 4 | The paper in the venue's format | later: the venue and its page limit are still to choose (§6) |

## 1. Fair tables (replay only): done

Every strategy runs under the same two rules (`selection/base.py`) and is compared on detection against the tokens
spent, with intervals over the changes, a verdict table and one fault per change in APFD. A batch's members are
held out of what a strategy learns from. Results: `docs/RESEARCH_PLAN.md` §5.6 and §5.5.

## 2. Replay-first in the testbed: done

`traceeval replay-first`, a cassette per recording, the strategies over the diverged tests, a diverged test charged
from its divergence point, and `traceeval check` in two phases. Method and results: `docs/RESEARCH_PLAN.md` §3.3
and §5.2.

## 3. Recording and measurement fixes: done

The recording made after them is `runs/gemma8`. Each fix has a probe in `scripts/analysis/probes/` and a test.

- **The recording:** a manifest of what it was made from and with; the check refuses a recording of another
  version of the app; the empty change; every answer of a changed copy compared with the cassette's; a pair with
  no valid run is missing; the judge's verdict is the first word of its answer.
- **What the model is sent:** the change sets and the dependencies hold it (a skill's text and steps, a tool's
  schema, the agents an orchestrator lists, the tools each agent is offered, the fixture); the cassette counts two
  answers as one when they say the same.
- **The app and the tests:** `_route_only` kept out of the prompt; delegation through the dispatcher's gates; a
  badly typed argument refused instead of a crash; a positive condition for the 22 cases that passed when the
  agent did nothing.

Open:

- [ ] An edited default on a `def` line and an edited continuation line of a statement have no test that executed
      the line, so the change links by function only (`probe_changeset.py`, edits 8 and 9). None of the 43 changes
      is one.
- [ ] A run has no limit on model calls. A change that makes an agent ask again after every answer never ends
      (`g_condnot_llm_openai_9`, the one generated change that is not recorded). A limit changes the app, so it
      goes with the next recording.

## 4. More evidence (GPU)

Done, with the results in `docs/RESEARCH_PLAN.md`:

| what | recording | results |
|---|---|---|
| the generated changes, replayed for no tokens and recorded for the tests they reach | `runs/gemma8_gen` | §5.3 |
| a second recording, under another start of the server | `runs/gemma8_restart` | §5.2 |
| exact serving, no prefix cache and one test at a time, for Gemma and Qwen | `runs/gemma8_exact`, `runs/qwen8_exact` | §5.2 |
| a second model, with its own cassette | `runs/qwen8` | §5.2 |
| the second model's 43 changes with every answer repeating, its generated changes, its stop thresholds and their live checks | `runs/qwen8_exact`, `runs/qwen8_gen` | §5.2, §5.3, §5.4 |
| the batches on the current app: replayed, evaluated, checked live | `runs/gemma8_batches` | §5.5 |
| `traceeval check` live on the 43 changes | `docs/results/gemma8/live_checks.md` | §5.2 |
| the replay's stand-ins checked live: a sample of the pairs a recording took from the replay, run with the model | `docs/results/gemma8_gen/stand_ins_live.md` | §5.3 |

Open:

- [ ] Model updates as changes without a diff: the three baselines already give six (`model_updates.py`).
- [ ] gpt-oss's baseline recorded again, with its cassette, and the exact serving setup for it: its outcomes
      change with a restart of the server.
- [ ] The demo's batch check for the three models, whose cassettes (`tests/cassettes/`) lack the tests the check
      now picks.
- [ ] Real changes beside the generated ones (skill revision histories).
- [ ] A second application not built here: tau2-bench's airline domain (50 tasks, MIT licence). Scoped from its
      source; nothing of it has been run:
      - every model call passes through one function (`tau2.utils.llm_utils._generate_once`), where a recording
        and replaying client goes; the endpoint and the model are set per role, so the local model can play both
        the agent and the user;
      - the policy and the 14 tool schemas are in every agent request. An edit to the policy or to a tool's
        description makes all 50 tasks diverge at their first call; only a change to what a tool does reaches
        some of the tasks, so the replay prunes for that kind alone;
      - its evaluator builds the expected database with the tools of the copy under test, so a changed tool can
        hide itself: the expected state has to come from the original tools;
      - an outcome without a model judge needs its substring check of the answer (`--communicate-scorer
        substring`), which is not the default;
      - 24 of the 50 tasks pass when the agent changes nothing, and how many an open model passes is not known;
      - to check before recording: the ids the server makes up for tool calls (number them, as the `llm` backend
        does), and a report that prefix caching on the server breaks repeatability on these tasks.

## 5. The method: stopping on the diverged tests

Done: a clean verdict with a bounded miss rate (`traceeval check --miss-rate`, a threshold per group of changes set
on past changes), a failure confirmed by running the test again (`--confirm`), and which order of the diverged
tests finds a regression soonest. Method and results: `docs/RESEARCH_PLAN.md` §3.4 and §5.4; live:
`docs/results/gemma8_gen/live_checks_miss_rate.md`.

Tried and not kept:

- the threshold set on the evidence the passing tests have given (the method's odds that something broke, over its
  odds before any test) instead of on its probability. Per group it changes nothing on the generated changes and
  is worse on the hand-written ones (one of 25 missed at a 10% target for 28% of the suite, against none for 15%).
  With one threshold it still misses 21% of the regressions among edits to text;
- replayed outcomes as evidence in `adaptive_bayes`. Teaching it on the tests each past change reaches, instead of
  every test whose traces touch the change, makes its clean verdicts more expensive
  (`docs/RESEARCH_PLAN.md` §5.4). A replayed pass stays out of its posterior: the floor on every test's sensitivity
  would let a hundred free passes call any change clean.

Open:

- [ ] For models whose answers vary more (Qwen in batches, gpt-oss): a sequential test of "this test's pass rate
      dropped" against the noise floor of the empty change.

## 6. The paper and the documents

Done: `docs/paper/main.tex`, `README.md` and `docs/RESEARCH_PLAN.md` are written around replay-first, with the
related work verified at its sources (`docs/related_work.md` §8) and every cost given against the whole suite
re-run through an exact-match cache. The paper has 13 tables and 18 pages of text.

Open:

- [ ] Venue format: the draft is 27 pages: 18 of text, then the references and an appendix of 6 pages with the
      strategies' algorithms and constants. What else to cut depends on the venue.
- [ ] The Adobe Team's agreement to being named; an anonymous version for a double-blind venue.

## 7. With the Adobe Team

- Keep: selection, ordering and stopping under a budget; multi-agent workflows; mandatory properties; batches.
- [ ] Ask: test runs that replay from recorded model and tool answers; a target miss rate for "clean"; model
      updates as a kind of change; a replay of the selection on their nightly history, aggregated if need be; how
      often their changes touch a prompt every test reads.
- Parked, out of the paper: re-planning (branch `replanning`), the eleven-dimension coverage report, the
  OpenTelemetry event detail, the model-drafted catalog of properties.

## 8. Housekeeping

- [ ] A `LICENSE` file (`pyproject.toml` says MIT) and a CI job for `pytest` and `ruff`.
- [ ] The GPU server's address and login out of `docs/EXPERIMENT.md` and `scripts/gpu_remote.sh`.
- [ ] `CLAUDE.md` says every demo PR's verdict is checked by `tests/test_sdd.py`; 14 of 25 are.
- [ ] With the next change to `traceeval/sut` that needs new recordings anyway: "selectors" becomes "strategies" in
      the two comments of `harness/dispatcher.py` (lines 31 and 133). Any edit there, a comment included, makes
      `traceeval check` refuse every recording made before it, so it waits; the rest of the app's comments read
      well. The inline comment `# edits invalidate approvals` in `services/repository.py` stays as it is: it is
      part of the anchor of the change `code_edit_keeps_review`.

## 9. A day of changelists

The Adobe Team submits a set of changelists (CLs) every day. The day's testing must be prioritized, and a minimal
set of tests must reach coverage.

- Already there: per change, the replay, an order of the reached tests and a stop with a bounded miss rate; a batch
  tested as one change, which also catches the failures no member causes alone, with the component blamed most.
- Gaps left: the adaptive method keeps at most eight changed components, too few for a day; the cassette goes
  stale once the day's CLs merge; on a hosted model condition R can only be watched; the stop thresholds need past
  changes in every group.

The daily pipeline:

1. [x] Replay each CL alone and the merged day, without the model: which tests each CL reaches (the CL x test map),
       and the CLs settled for free (`culprits.py::day_map`, printed by `traceeval check <batch>`). Results:
       `docs/RESEARCH_PLAN.md` §5.5.
2. [x] A coverage floor: the cheapest set of reached tests that, with the tests the replay settles, covers every
       changed component and every affected mandatory property; no clean verdict before the floor has run
       (`coverage.py::coverage_floor`, `traceeval check --floor`). Results: `docs/RESEARCH_PLAN.md` §5.4.
3. [x] The floor with the adaptive order, until the calibrated threshold:
       `traceeval check --miss-rate 0.1 --floor`.
4. [x] On a failure of the merged day, the suspects are the CLs whose own replay reaches the failing test or fails
       it (`experiment/culprits.py`, printed by `traceeval check <batch>`). Results: `docs/RESEARCH_PLAN.md` §5.5.
   - [ ] Halving live: run the failing test with half of the suspects at a time until one remains.
5. [ ] Overnight: the reached tests the stop skipped, to refresh the cassette for the next day, and a random sample
       of replayed tests run live, to watch condition R.

- [ ] The adaptive method for a day's many components: one hypothesis per CL, or components taken as independent.

## Parked: the spec-driven development layer

Out of the paper. Its probes (`scripts/analysis/sdd/`) show what a fix would start from: the solver translation is
unsound outside comparisons and `and`, a proven function need not be the one the code calls, placement clauses
accept unused decoys, and trace clauses pass on runs that did not happen.
