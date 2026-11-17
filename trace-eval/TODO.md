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
  regressions for 9% to 10% of the suite's tokens, with no wrong clean verdict (the report, section 7);
- without the replay, and with every strategy run under the same two rules, `adaptive_bayes` leads only below
  about 4% of the suite, by a margin the 28 regressions do not establish (the report, section 2), and its
  calibration from history adds nothing measurable (`method_ablations.py`);
- 27% of its clean verdicts are then given on revealed regressions (the report, section 3); replay-first, 6%.

Order of work: sections 1 to 3 are done; 4 needs recordings; 5 is the method; 6 follows the results.

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

The app and the tests:

- [x] `_route_only` kept out of the prompt (`harness/backends/llm_openai.py`).
- [x] Delegation through the dispatcher's gates; the user, the approval token and the harness's switches not
      writable by a delegation; a badly typed argument refused instead of a crash (`probe_harness.py`).
- [x] A positive condition for the 22 cases that passed when the agent did nothing (`tools_required` or the new
      `tools_attempted`; `probe_oracles.py`).

## 4. More evidence (GPU)

- [x] A generator of changes (`mutation/generator.py`): 598 on the current app, in thirteen kinds, without
      labels. All of them replayed for no tokens (`docs/RESEARCH_PLAN.md` §5.8): 97 settled as clean, 36 as
      regressions, 465 left for the model.
- [ ] The generated changes recorded for the tests they reach only (`runs/gemma8_gen`, five repetitions), and the
      strategies evaluated on the half held out of what they learn from (`traceeval evaluate --held-out`). The
      recording's manifest holds a digest of `traceeval/selection`: leave that folder as it is until the results
      are in.
- [ ] The batches and the second recording again on the current app: those of `docs/results/gemma7/` were recorded
      before the fixes of section 3.
- [ ] Model updates as changes without a diff: the three baselines already give six (`model_updates.py`).
- [ ] A second model with its own cassette, baseline and changed copies recorded the same way. Indicative today:
      with the unstable tests left out, Qwen and gpt-oss show the same ranking (`other_models_stable_tests.py`).
      Qwen's and gpt-oss's recordings predate the cassette and cannot be replayed: their baselines are to be
      recorded again, the changed copies one test at a time.
- [x] The condition of replay-first on Gemma's serving setup (`runs/gemma8`; `docs/RESEARCH_PLAN.md` §5.7): the
      empty change flips no test, every recorded run of a pair that replays ends like the replay, and about 2%
      of the requests sent again are answered otherwise, one test at a time and in batches alike.
- [x] A cassette built from the baseline's own five repetitions, the answer given most often: the one outcome
      the replay got wrong on `runs/gemma7` (WF3-01, whose runs take two paths) is right on `runs/gemma8`.
- [ ] The same condition for a second model and its serving setup (with its recording, above).
- [ ] `traceeval check` live with its replay phase: the 43 changes, and the demo's batch check for the three
      models, whose cassettes (`tests/cassettes/`) lack the tests the check now picks.
- [ ] A second application not built here (tau2-bench, as planned).
- [ ] Real changes beside the generated ones (skill revision histories).
- [ ] The live checks of the 23 batches again: those of `docs/results/gemma7/batches.md` and `batch_sweep.md` were
      run with each batch's members among the changes the check learned from, which `traceeval check` now holds
      out, and without the replay phase.

## 5. The method: stopping on the diverged tests

- [ ] A "clean" verdict with a bounded miss rate, before every diverged test has run: the stop threshold
      calibrated on past changes with known outcomes (conformal risk control or Learn-then-Test), the miss rate
      reported against the target. The case that pays is the change that reaches most tests and breaks none: a
      sound clean verdict costs 20% of the suite on the changes no test reveals, about 80% on an edit to a prompt
      every request reads.
- [ ] Repetitions after the divergence point for models whose answers vary: a sequential test of "this test's
      pass rate dropped" against the noise floor of the empty change.
- [ ] Which order of the diverged tests finds a regression soonest. Today: on a revealed regression `history_ml`
      spends 1.3% of the suite and `ir_tfidf` 1.7%, a random order 4.2%; cost and divergence depth add nothing.
- [ ] Replayed outcomes as evidence in `adaptive_bayes`: today a replayed pass is left out of its posterior,
      because the floor on every test's sensitivity would let a hundred free passes call any change clean.

## 6. The paper and the documents

- [ ] `docs/paper/main.tex` still has the tables of the comparison before section 1 and calls the two adapted
      methods reproduced. `README.md` and `docs/RESEARCH_PLAN.md` have the new numbers and still present
      `adaptive_bayes` as the contribution. Rewrite the three around replay-first once section 2 has numbers.
- [ ] A related-work section. Verify each at its source before citing: test-result caching as selection (Ekstazi,
      Bazel; Poirot's memoized re-execution), diagnostic test prioritization (Sequoia, Barinel; Mirarab and
      Tahvildari), selection for non-code changes (uRTS), mutation testing of agent workflows (Kahani and
      Bagherzadeh; AgentAssay; AdaT2), batch-dependent greedy decoding (Yuan et al.), stopping with guarantees.
- [ ] Secondary numbers to correct: Qwen's flips one test at a time (1, not 0); "five or six tests flip" (four to
      six); gpt-oss's "thirteen tests" (not reproducible); "the same tokens to within a few hundred" (two checks
      differ by more); "never before every mandatory property has had a test" (while the budget allows); "nobody
      declares the shared skill" (five tests declare `link-validation`); "each property has its sources" (3 of 15).
- [ ] Threats to add: constants set on the evaluated changes, the changes kept or relabelled after measuring, the
      declared metadata incomplete by design, 8 of the 29 regressions revealed by a single test each.
- [ ] Venue format (the draft is 25 pages with 24 tables); the feature list of section 1 out.
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
- [ ] The `ml` extra of `pyproject.toml` (scikit-learn) is no longer imported: `history_ml` fits its model with
      numpy. Drop it, with the install lines of `CLAUDE.md`.

## Parked: the spec-driven development layer

Out of the paper. Its probes (`scripts/analysis/sdd/`) show what a fix would start from: the solver translation is
unsound outside comparisons and `and`, a proven function need not be the one the code calls, placement clauses
accept unused decoys, and trace clauses pass on runs that did not happen.
