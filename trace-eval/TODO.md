# TODO: the replay-first plan

**Direction.** The paper is built on replay-first testing: after a change, every test is first re-run with the
model answers recorded on the original app. A test that replays to the end has a known outcome for no tokens; a
test that diverges (it makes a request the original app never made) is where the change reaches the model, and only
those tests need the model. `adaptive_bayes` stays as one of the orders compared on the diverged tests.

**Why**, on `runs/gemma8` (each line names what reproduces it: the report, `docs/results/gemma8/report.md`, or a
script in [`scripts/analysis/`](scripts/analysis/README.md)):

- replay costs seconds of CPU and agrees with the recording on all of about 6,300 outcomes (the report, section
  7);
- what replays exactly is the outcome of a test, not every model call: about 2% of the requests are answered
  otherwise when they are sent again, and no outcome moves (the report, section 7);
- replay, then the diverged tests in any order, stopped at the first failure, finds 98% to 100% of the revealed
  regressions for 9% to 10% of the suite's tokens, with no wrong clean verdict (the report, section 7); charged
  for its new requests only, 5% to 7%, where the whole suite through a cache costs 13.5%
  (`docs/results/gemma8/second_recording.md`);
- the same holds on 342 generated changes the strategies never learned from (`docs/results/gemma8_gen/`);
- without the replay, and with every strategy run under the same two rules, `adaptive_bayes` leads only below
  about 4% of the suite, by a margin the 28 regressions do not establish (the report, section 2), and its
  calibration from history adds nothing measurable (`method_ablations.py`);
- 27% of its clean verdicts are then given on revealed regressions (the report, section 3); replay-first, 6%.

Order of work: sections 1 to 3 are done; 4 and 5 are done for Gemma, with what is open marked; 6 is the paper.

## Next, in this order

| | what | where it is | state |
|---|---|---|---|
| 1 | Exact serving for the other models: Qwen with the prefix cache off, one test at a time, a baseline and the empty change under two starts of the server (gpt-oss needs both GPUs and comes later) | §4 | done for Qwen (`runs/qwen8_exact`): no request of 5,310 answered otherwise, under either start; gpt-oss open |
| 2 | The batches on the current app: the 23 batches recorded again beside `runs/gemma8`, evaluated, and checked live | §4 | done |
| 3 | The paper: fewer tables and a shorter text, keeping what the argument needs; then the venue's format | §6 | cut to 13 tables and 18 pages of text; the venue and its page limit are still to choose |
| 4 | A second application, tau2-bench's airline domain | §4 | waits for the go-ahead to install and run its code |
| 5 | Stop thresholds for Qwen, set on generated changes recorded with Qwen | §4 | can start from `runs/qwen8_exact`: Qwen repeats exactly, so one run per reached test is enough, about 23,000 runs or 40 hours of one GPU |

## 1. Fair tables (replay only): done

The numbers and their reading are in `docs/RESEARCH_PLAN.md` §5.1 and §5.6.

- [x] The same two rules for every strategy (`selection/base.py`): a test the model already fails on the original
      app is not run, and a run ends at its first failure.
- [x] `history_ml` and `observed_diverse` in the default comparison (`selection/strategies.py::CORE`).
- [x] Detection against tokens spent over all changes, with a bootstrap interval over the changes and paired
      differences to the best strategy; the seeds are no longer read as a sample.
- [x] Verdict tables for every strategy: runs that end with a regression verdict, a clean one or none, and the
      clean verdicts given on a regression.
- [x] "False alarm" is a failure of a test that passes on the original app and does not reveal the change.
- [x] APFD: one fault per change, over the tests that pass on the original app; an order drawn at random is the
      mean over the seeds.
- [x] Batches: the batch's members, and the batches that share one, held out of what a strategy learns from
      (`History.training_variants`, also in `traceeval check`); the sweep's change sets recomputed on the
      recording's own tree (`stale_line_ids.py`).
- [x] "The text of a test" said to include the declared block (`docs/RESEARCH_PLAN.md` §3; `test_text.py` measures
      what it is worth).
- [x] CASPER and the bandit called adaptations (`selection/adapted.py`). CASPER's slices are ranked by the shift of
      its representatives' runs on the changed copy. The bandit's per-token variant, `risk_aware_ts_per_token`,
      does worse than the bandit and stays out of the default comparison.

## 2. Replay-first in the testbed: done

The numbers and their reading are in `docs/RESEARCH_PLAN.md` §3.3 and §5.7.

- [x] `traceeval/experiment/replay_first.py` and `traceeval replay-first`: per change and test, replayed or
      diverged, the outcome, and the divergence point (the requests and tokens replayed before it, and whether the
      change first reaches the model in a prompt or in a tool result).
- [x] A cassette per recording (`history/cassette.jsonl`), written by `traceeval baseline`. When the repetitions
      answer a request in more than one way, the answer given most often is the reference, the first seen among
      equals. A Gemma recording without one gets it from the test suite's cassette.
- [x] Strategies over the diverged tests in the evaluator (`evaluate(..., replay_first=True)`,
      `results/replay_first.csv`): a replayed test is not run, a replayed failure ends the run for no tokens. The
      eleven strategies, and two orders by cost and by divergence depth, which do about as well as a random one.
- [x] Reuse of the replayed prefix: a diverged test is charged its tokens after the divergence point; the report
      gives the same tests run whole beside it.
- [x] `traceeval check` replays first and runs only the diverged tests live, behind the cassette.
- [x] The condition under which replay equals re-execution, stated (`docs/RESEARCH_PLAN.md` §3.3) and measured on a
      recording: the recorded runs of the pairs that replay to the end, against the replay (the report, section 7).
      Per model and serving setup it needs recordings: section 4.
- [x] The diverged share of the suite per kind of change in the report.

## 3. Recording and measurement fixes: done

Each has a probe in `scripts/analysis/probes/` that shows the state of today, and a test. The recording made
after them is `runs/gemma8`.

The recording:

- [x] A manifest per recording (`history/manifest.json`, `experiment/manifest.py`): the model, the judge, the
      server's version, the commit, digests of the app and of the catalog, how each part was run. The changed
      copies are made from the recording's own copy of the original app.
- [x] `traceeval check` refuses a recording whose app is not `traceeval/sut` as it is now, a comment included;
      the commands that only read a recording say what differs (`probe_drift.py`).
- [x] The empty change in every recording (`history/unchanged.jsonl`): the original app run as the changed copies
      are. A test that fails under it reveals no change.
- [x] Every answer the changed copies get compared with the cassette's answer to the same request
      (`llm/cache.py::Compare`); the report gives the counts.
- [x] A pair with no valid run is missing: not run, not revealing, counted in the report.
- [x] The judge: the verdict is the first word of its answer, no verdict is an invalid run, and its token limit
      is that of the model that judges (`probe_harness.py`, `probe_models.py`).

What the model is sent:

- [x] Change sets: a skill's front matter and prose as text, its procedure as the steps in their order, a tool's
      description and parameters (`tool:<name>#schema`), the agents an orchestrator lists
      (`agent:<name>.specialists`) (`probe_changeset.py`).
- [x] Dependencies: the tools each agent is offered, the fixture; every module imported before coverage starts,
      and a package's `__init__` touching every test that ran code of the package (`probe_cov.py`).
- [ ] Open: an edited default on a `def` line and an edited continuation line of a statement have no test that
      executed the line, so the change links by function only (`probe_changeset.py`, edits 8 and 9). None of the
      43 changes is one.
- [x] The cassette counts two answers as one when they say the same, whatever ids the server made up for the
      tool calls (`llm/cache.py::Tee`): with the `llm` backend every answer with a tool call used to count as
      another one, so the answer kept was the first seen, not the one given most often.

The app and the tests:

- [x] `_route_only` kept out of the prompt (`harness/backends/llm_openai.py`).
- [x] Delegation through the dispatcher's gates; the user, the approval token and the harness's switches not
      writable by a delegation; a badly typed argument refused instead of a crash (`probe_harness.py`).
- [x] A positive condition for the 22 cases that passed when the agent did nothing (`tools_required` or the new
      `tools_attempted`; `probe_oracles.py`).
- [ ] Open: a run has no limit on model calls. A change that makes an agent ask again after every answer never
      ends (`g_condnot_llm_openai_9`, the one generated change that is not recorded). A limit changes the app,
      so it goes with the next recording.

## 4. More evidence (GPU)

- [x] A generator of changes (`mutation/generator.py`): 692 on the current app, in sixteen kinds, without
      labels. All of them replayed for no tokens (`docs/RESEARCH_PLAN.md` §5.8): 98 settled as clean, 36 as
      regressions, 558 left for the model.
- [x] The generated changes recorded for the tests they reach only (`runs/gemma8_gen`, five repetitions, 114,230
      runs): 691 of the 692, of which a test reveals 316. The strategies evaluated on the half held out of what
      they learn from (`traceeval evaluate --held-out`, `docs/results/gemma8_gen/report.md`): the picture of the
      43 holds, and `adaptive_bayes`'s lead at a 5% budget without the replay is established there
      (`docs/RESEARCH_PLAN.md` §5.8). The recording's manifest holds the digest of `traceeval/selection` as it
      was when the first of these changes was recorded.
- [x] A second recording on the current app, under another start of the server (`runs/gemma8_restart`,
      `docs/results/gemma8/second_recording.md`): the empty change flips no test, 2 of 1,442 labels on the reached
      tests move, 29 regressions instead of 28.
- [x] What a reached test costs when the cassette answers every request it knows, counted while a copy is
      recorded (`cassette.known_tokens`): about a third less than the tokens after the divergence point.
      `runs/gemma8` and `runs/gemma8_gen` were recorded before the count and keep the bound.
- [x] The batches again on the current app (`runs/gemma8_batches`, `docs/results/gemma8_batches/batches.md`):
      the replay stays exact on all 1,374 replayed outcomes, and every revealed batch is found offline with no
      budget.
- [ ] Model updates as changes without a diff: the three baselines already give six (`model_updates.py`).
- [x] A second model with its own cassette, baseline and changed copies recorded the same way (`runs/qwen8`,
      one test at a time; `docs/results/qwen8/`, `docs/RESEARCH_PLAN.md` §5.7): the empty change flips no test,
      the five runs disagree on 2 of 1,448 reached pairs, the replay settles 8 of the 43 changes, and every
      order of the reached tests finds all 32 of Qwen's regressions for 3.6% to 5.4% of the suite, where the
      cache pays 14.2%. Three changes meant as harmless are regressions under Qwen.
- [ ] gpt-oss's baseline recorded again, with its cassette.
- [ ] Generated changes and stop thresholds for Qwen: `adaptive_bayes` with its own constant gives 31% of its
      clean verdicts on a regression there.
- [x] The condition of replay-first on Gemma's serving setup (`runs/gemma8`; `docs/RESEARCH_PLAN.md` §5.7): the
      empty change flips no test, every recorded run of a pair that replays ends like the replay, and about 2%
      of the requests sent again are answered otherwise.
- [x] Where the requests answered otherwise come from (`docs/RESEARCH_PLAN.md` §5.7): many tests at a time
      makes a test's runs differ from each other, and the server's prefix cache makes an answer depend on what
      the server was sent before. With neither (`runs/gemma8_exact`: `--workers 1`, and
      `--no-enable-prefix-caching` through `TRACEEVAL_VLLM_ARGS`), no request of 11,010 is answered otherwise,
      under the baseline's start of the server and under another.
- [x] The 43 changes recorded under that setup (`runs/gemma8_exact`, `docs/results/gemma8_exact/`): none of
      the 31,840 requests the baseline had sent is answered otherwise, and the five runs of each of the 1,442
      reached pairs are one and the same run. 3 labels differ from `runs/gemma8` and 30 changes have a revealing
      test. Every order of the reached tests finds all 30, for 4.8% to 6.1% of the suite, where the cache pays
      12.8%.
- [x] The same setup for Qwen (`runs/qwen8_exact`: a baseline and cassette of its own, and the empty change
      under two starts of the server): none of 5,310 requests is answered otherwise, against 20 of 5,580 with
      the cache on (`runs/qwen8`), and five passes take 100 minutes instead of 78. Five tests pass or fail on the
      original app otherwise than in `runs/qwen8`.
- [ ] The same setup for gpt-oss, whose outcomes change with a restart of the server; it needs both of fmi0's
      GPUs.
- [x] A cassette built from the baseline's own five repetitions, the answer given most often: the one outcome
      the replay got wrong on `runs/gemma7` (WF3-01, whose runs take two paths) is right on `runs/gemma8`.
- [x] The same condition for a second model and its serving setup (`runs/qwen8`): 0.4% of the empty change's
      requests and 2.3% of the reached tests' are answered otherwise, and no outcome moves.
- [x] `traceeval check` live with its replay phase on the 43 changes (`docs/results/gemma8/live_checks.md`): the
      evaluator's verdict on 41; one false alarm from a single run of a test whose runs disagree, and one check
      that fits more tests in its budget than the evaluator charges it for.
- [ ] The demo's batch check for the three models, whose cassettes (`tests/cassettes/`) lack the tests the check
      now picks.
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
- [ ] Real changes beside the generated ones (skill revision histories).
- [x] The live checks of the 23 batches again, with their members held out and the replay phase: 19 of the 20
      revealed batches found, no false alarm, the blame on a member that is a regression alone in 17 of 18.

## 5. The method: stopping on the diverged tests

- [x] A "clean" verdict with a bounded miss rate, before every diverged test has run: a stop threshold set on
      past changes by split conformal prediction, measured on the generated changes
      (`scripts/analysis/stop_with_guarantee.py`; `docs/RESEARCH_PLAN.md` §3.4 and §5.9):
      - the miss rate is at its target on average, for every rule; a learned score makes a clean verdict cost
        7.8% of the suite at a 10% target instead of 20.1%;
      - with one threshold the misses pile up in one group of changes (with the learned score, 87% of the
        regressions among edits to the text the model reads); a threshold per group brings each group to its
        target, and a clean verdict then costs 17.5% at a 10% target;
      - on changes unlike those the threshold was set on (a kind never seen, the hand-written changes) the
        learned scores miss their target, and `adaptive_bayes`'s probability with a threshold per group keeps it:
        none of 25 regressions missed at a 5% and a 10% target, three at 20%, for 34%, 15% and 10% of the suite
        instead of 37%;
      - a threshold that holds for nine sets of past regressions in ten, not only on average, is over its target
        in at most three of twenty splits instead of up to half of them, and stops later (11.1% instead of 7.8%
        with the learned score at a 10% target).
- [x] The same inside the testbed: `traceeval check --miss-rate` (`traceeval/experiment/stopping.py`), the
      threshold of the change's group set on half of the recording's changes, in place of `adaptive_bayes`'s
      constant; a group with too few recorded regressions has no threshold, and every reached test runs. Live on
      the 43 changes at a 10% target: all 28 regressions found, no false alarm, 2.8% of the suite per check
      (`docs/results/gemma8_gen/live_checks_miss_rate.md`).
- [x] Enough recorded regressions among edits to the text the model reads (a skill's prose, an agent's prompt, a
      tool's description). Such edits reach the most tests and seldom break one: with 6 regressions among the
      first 63 of them the group had no threshold under a 20% target, and a clean verdict took every reached
      test. Three more kinds of such edit (a sentence of an agent's prompt deleted, an agent's description cut
      short, a parameter's description emptied: 94 changes, 20 regressions) give the group its threshold at a
      10% target.
- [x] Tried and not kept: the threshold set on the evidence the passing tests have given (the method's odds that
      something broke, over its odds before any test) instead of on its probability. Per group it changes
      nothing on the generated changes and is worse on the hand-written ones (one of 25 missed at a 10% target
      for 28% of the suite, against none for 15%). With one threshold it still misses 21% of the regressions
      among edits to text.
- [x] A failure confirmed by running the test again, two failures of three (`traceeval check --confirm`,
      `scripts/analysis/confirm_failures.py`): regression verdicts on changes no test reveals go from 6% to 8%
      of the runs to under 2% on `runs/gemma8_restart`, for a point and a half of the suite's tokens.
- [ ] For models whose answers vary more (Qwen in batches, gpt-oss): a sequential test of "this test's pass rate
      dropped" against the noise floor of the empty change.
- [x] Which order of the diverged tests finds a regression soonest: on a revealed regression `history_ml` spends
      0.9% of the suite and `ir_tfidf` 1.4%, a random order 2.6% (the 43); on the held-out generated changes
      `adaptive_bayes` 2.6%, `ir_tfidf` 3.5%, a random order 4.7%. Cost and divergence depth add nothing.
- [x] Replayed outcomes as evidence in `adaptive_bayes`: teaching it on the tests each past change reaches,
      instead of every test whose traces touch the change, makes its clean verdicts more expensive (§5.9). A
      replayed pass stays out of its posterior: the floor on every test's sensitivity would let a hundred free
      passes call any change clean.

## 6. The paper and the documents

- [x] `docs/paper/main.tex`, `README.md` and `docs/RESEARCH_PLAN.md` rewritten around replay-first: the
      mechanism and its condition, ordering and stopping over the reached tests, five questions answered from the
      recordings, the cache as the baseline; the strategies' algorithms in an appendix, the two published methods
      called adapted.
- [x] The related work verified at its sources (`docs/related_work.md` §8, with the corrections to §3 and to the
      gap analysis): the replay mechanism is test factoring's (ASE 2005), Chronicle replays model answers into
      changed agent code, and an exact-match cache already pays only for changed requests.
- [x] The paper's related work written from it (its section 1.3 and table): what is not new is said first, and
      every cost is given against the whole suite re-run through an exact-match cache.
- [x] The secondary numbers corrected or gone, and the threats added: constants set on the hand-written changes,
      changes kept or relabelled after measuring, declared metadata incomplete by design, regressions that rest
      on one test, the bound of the stopping rule being marginal.
- [x] The two results the paper waited for are in it: Qwen's recording (recording Q, in its tables of the
      recordings and of the condition) and the serving experiment (its RQ2, with recording X).
- [x] The paper cut to what the argument needs: 13 tables instead of 27 (the others are a sentence or merged), and
      18 pages of text instead of 23.
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

## Parked: the spec-driven development layer

Out of the paper. Its probes (`scripts/analysis/sdd/`) show what a fix would start from: the solver translation is
unsound outside comparisons and `and`, a proven function need not be the one the code calls, placement clauses
accept unused decoys, and trace clauses pass on runs that did not happen.
