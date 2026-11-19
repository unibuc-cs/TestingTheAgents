# Analysis scripts

Offline checks of the results, behind the plan in [`TODO.md`](../../TODO.md). Run them from the repository root
with the project's Python. They read a recording (`runs/<name>`, `runs/gemma8` unless another is given) and the
test suite's recorded answers, call no model and change nothing in a recording; what they write goes under
`runs/analysis/`, which git ignores.

```
python scripts/analysis/<script>.py [recording]
```

## Replay-first

Replay-first itself is part of the testbed: `traceeval replay-first`, the report's section 7, and
`docs/RESEARCH_PLAN.md` §5.7. These scripts go beyond it:

| script | what it shows | on `runs/gemma8` |
|---|---|---|
| `prompt_only_edits.py` | edits that reach the model only through its prompt: tests the traces link against tests whose requests diverge | 46, 153, 46 and 46 linked, the very tests that diverge; each of the four has a component |
| `two_recordings.py <recording> <the same changes recorded again>` | the empty change, the labels, the revealing tests and the requests answered otherwise, side by side | against `runs/gemma8_restart`: no test flips under either empty change; 2 of 1,442 labels differ; 28 and 29 regressions. Against `runs/gemma8_exact`: 3 labels differ; 28 and 30 regressions |
| `answered_otherwise.py <recording> ...` | the empty change of each recording: the requests answered otherwise than the cassette, and whether a test has them in every run or in some | with the cassette of `runs/gemma8`: 1.9% to 3.9% of the requests under four settings of the server, the tests' runs one and the same when they run one at a time; in `runs/gemma8_exact` (no prefix cache, one test at a time) none of 5,505, under two starts of the server |
| `live_checks.py <recording> <folder of check logs>` | `traceeval check` run live on every change, against the evaluator's runs of the method: verdict, tests and tokens per change | with `runs/live_check8`: the same verdict on 41 of 43, after as many tests; 1.6% of the suite per check live, 2.1% as the evaluator charges. With the logs of checks made with `--miss-rate 0.1 --confirm` and a budget of 1.0 as the third argument: all 28 regressions found, no false alarm, 2.8% per check |
| `stop_with_guarantee.py [recording [second recording]]` | a clean verdict before every reached test has run, with a threshold set on past changes for a target miss rate: six rules, one threshold, one per group of changes or one that holds for nine sets of past regressions in ten, the per-group ones also with the coverage floor, measured within the changes, with one kind left out, and on a second recording's changes, beside a fixed minimal set and the floor alone; with the coverage of each clean verdict | on `runs/gemma8_gen` and `runs/gemma8`: every rule at its target on average; a clean verdict for 7.8% of the suite instead of 20.1% at a 10% target with one threshold, which misses 87% of the regressions among edits to text; `adaptive_bayes` with a threshold per group misses none of 25 hand-written regressions at 5% and 10%; with the coverage floor every clean verdict covers what the change touches, for a few tenths of a point, and a fixed minimal set of 15 tests misses 13 of the 25 (`docs/RESEARCH_PLAN.md` §5.9) |
| `confirm_failures.py [recording ...]` | a failure confirmed by running the test again before it ends a run: false regression verdicts, regressions called clean and tokens, under three rules | on `runs/gemma8_restart`: regression verdicts on changes no test reveals from 6% to 8% of the runs to under 2%, for a point and a half of the suite's tokens; on `runs/gemma8` from under 2% to none |

## The comparison in the report

The report itself (`traceeval report`, `docs/results/gemma8/report.md`) runs every strategy under the same two
rules and gives the intervals and the verdicts. These scripts go further into one question each. Tokens are a mean
over all changes, as in the report.

| script | what it shows | on `runs/gemma8`, unless another recording is named |
|---|---|---|
| `stop_rule_frontier.py` | the strategies' orders on a finer grid of budgets, with three two-line orders that combine the traces and the text | `adaptive_bayes` 0.78 for 2.7% and 0.81 for 5.1%; the traced tests ordered by text 0.75 for 1.7%, 0.96 for 6.0%, every regression for 11.4% |
| `method_ablations.py` | the stopping threshold swept, each ingredient removed, less history, the regressions behind the differences | at a 20% budget: shipped 0.81, no history 0.85, no per-test record 0.89, TF-IDF text 0.86, no text 0.71, no mandatory rule 0.78 |
| `test_text.py` | `ir_tfidf` and the method with the declared block out of the test's text | `ir_tfidf` at 20%: 0.93, 0.78 without the block, 0.74 with name and request only |
| `batch_calibration.py` | batches replayed with their members held out (the evaluator's rule), with the single changes, and with every other variant; then whom the method blames | on `runs/gemma8_batches`: at a 5% budget detection 0.88 with the members held out after 4.0 tests, 0.90 calibrated on the single changes, 0.95 on every other change after 2.4; the blame on a member that is a regression alone in 88 of 95 runs |
| `culprits_by_replay.py <recording of batches> [live checks] [--md out.md]` | the day's map of each batch: the members that reach no test, those that fail one in their own replay, the tests the batch reaches against those its members reach alone, by how many members each is reached, and its tokens checked once against once per member; then for each pair of a batch and a test that reveals it, the members whose own replay reaches the test or fails it (the suspects) against those the test reveals alone (the culprits), and the runs of the failing test that find a culprit by halving, among the suspects and among all the members; the same for the test each live check failed on | on `runs/gemma8_batches`: a batch reaches exactly what its members reach (2,766 tests); 18 of 117 members reach none; 1,505 tests have one owner; 55% of the tokens; every culprit a suspect (273 of 273), 1.9 suspects of 5.7 members, the culprit alone in 85; 0.9 runs instead of 2.5 (`docs/results/gemma8_batches/culprits.md`) |
| `benchmark_structure.py` | the suite by kind, revealing tests per regression, hypotheses per change, how selective the traces are | 7 of 28 regressions rest on one test; 34 of 43 changes have one hypothesis; 94 of 180 tests reveal nothing |
| `other_models_stable_tests.py` | a second model with its unstable tests left out (default `runs/qwen7`) | on `runs/qwen7` and `runs/gptoss7`, indicative: the same ranking as under Gemma |
| `model_updates.py` | tests that flip between the models' baselines: changes without a diff | on the three recordings of the earlier app: six ordered pairs, 3 to 23 tests regress |
| `paper_counts.py` | the draft's floats, words and citation keys | 24 tables; every key resolves |

`replaylib.py` holds what they share: loading a recording, the evaluator's replay loop, and variants of the method.

## Probes of the measurement chain (`probes/`)

Each takes the folders it needs as arguments; a scratch folder can be `runs/analysis/scratch`.

| script | what it shows |
|---|---|
| `probe_changeset.py <scratch> <recording>` | eleven edits that reach the model through its prompt or through code that runs at import: the components of each, and the tests the recording's dependencies link them to. Each has a component; two still link by function only, an edited default on a `def` line and an edited continuation line of a statement, since no test's coverage holds those lines |
| `probe_drift.py <scratch> <recording> [others]` | change sets computed today against the line ids a recording holds (`traceeval check` refuses such a recording, `manifest.py::drift`) |
| `probe_cov.py` | that no module is imported inside a test's coverage: every module of a copy is imported when it is loaded |
| `probe_harness.py` | what the model is sent for a route-only item, a delegation by an agent that is not offered it, a delegation that passes another user and a token, the judge's parsing, badly typed arguments |
| `probe_oracles.py` | cases a specialist that does nothing would pass (one, `ORC-01`, where doing nothing is the right answer); assertions true before the run |
| `probe_prompts.py [agent ...]` | the prompts each agent is sent, built without a model |
| `probe_history.py <recording>`, `probe_matrix.py <recording>` | a recording's classifications, repetitions, fault matrix |
| `probe_models.py <recording ...>`, `probe_reps.py <recording ...>` | judge verdicts and errors per model; how alike the repetitions are |
| `probe_details.py <gemma recording> <qwen recording>` | what differs between repetitions; a judged case that flips on a no-op change |

## Probes of the spec-driven development layer (`sdd/`)

| script | what it shows |
|---|---|
| `probe_contracts.py` (with `probe_fns.py`) | functions the solver "proves" wrongly, and correct ones it rejects |
| `probe_pbt.py` | why the property test misses a defect a domain-shaped strategy finds at once |
| `probe_prs.py <scratch>` | pull requests with the defect a spec excludes that are accepted |
| `probe_ablation.py <scratch>` | which kind of clause tells each wrong pull request from the correct one (after `probe_prs.py`) |
| `probe_baseline_monitors.py <scratch>` | trace rules on the unchanged app's own runs |
| `probe_cfg01.py <scratch>` | a reference pull request against an existing feature its regression line leaves out |
