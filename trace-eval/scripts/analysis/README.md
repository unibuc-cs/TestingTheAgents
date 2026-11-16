# Analysis scripts

Offline checks of the results, behind the plan in [`TODO.md`](../../TODO.md). Run them from the repository root
with the project's Python. They read a recording (`runs/<name>`, `runs/gemma7` unless another is given) and the
test suite's recorded answers, call no model and change nothing in a recording (`stale_line_ids.py --fix` is the
exception); what they write goes under `runs/analysis/`, which git ignores.

```
python scripts/analysis/<script>.py [recording]
```

## Replay-first

Replay-first itself is part of the testbed: `traceeval replay-first`, the report's section 7, and
`docs/RESEARCH_PLAN.md` §5.7. One script goes beyond it:

| script | what it shows | on `runs/gemma7` |
|---|---|---|
| `prompt_only_edits.py` | edits that reach the model only through its prompt: tests the traces link against tests whose requests diverge | 6, 0, 0 and 0 linked; 46, 153, 46 and 46 diverge; two of the four give an empty change set |

## The comparison in the report

The report itself (`traceeval report`, `docs/results/gemma7/report.md`) runs every strategy under the same two
rules and gives the intervals and the verdicts. These scripts go further into one question each. Tokens are a mean
over all changes, as in the report.

| script | what it shows | on `runs/gemma7` |
|---|---|---|
| `stop_rule_frontier.py` | the strategies' orders on a finer grid of budgets, with three two-line orders that combine the traces and the text | `adaptive_bayes` 0.75 for 2.7% and 0.78 for 5.1%; the traced tests ordered by text 0.72 for 1.7%, 0.97 for 6.0%, every regression for 10.5% |
| `method_ablations.py` | the stopping threshold swept, each ingredient removed, less history, the regressions behind the differences | at a 20% budget: shipped 0.78, no history 0.81, no per-test record 0.85, TF-IDF text 0.83, no text 0.68, no mandatory rule 0.74 |
| `test_text.py` | `ir_tfidf` and the method with the declared block out of the test's text | `ir_tfidf` at 20%: 0.93, 0.79 without the block, 0.77 with name and request only |
| `batch_calibration.py` | batches replayed with their members held out (the evaluator's rule), with the single changes, and with every other variant; then whom the method blames | detection 0.94 at a 5% budget all three ways, after 4.1, 3.4 and 2.2 tests; the blame on a member that is a regression alone in 79 of 80 runs |
| `benchmark_structure.py` | the suite by kind, revealing tests per regression, hypotheses per change, how selective the traces are | 8 of 29 regressions rest on one test; 35 of 43 changes have one hypothesis; 94 of 180 tests reveal nothing |
| `other_models_stable_tests.py` | a second model with its unstable tests left out (default `runs/qwen7`) | indicative: the same ranking as under Gemma |
| `model_updates.py` | tests that flip between the models' baselines: changes without a diff | six ordered pairs, 3 to 23 tests regress |
| `stale_line_ids.py` | change sets that are not those of the recording's own tree; `--fix` rewrites them and keeps the old ones | none in the three Gemma recordings |
| `paper_counts.py` | the draft's floats, words and citation keys | 24 tables; every key resolves |

`replaylib.py` holds what they share: loading a recording, the evaluator's replay loop, and variants of the method.

## Probes of the measurement chain (`probes/`)

Each takes the folders it needs as arguments; a scratch folder can be `runs/analysis/scratch`.

| script | what it shows |
|---|---|
| `probe_changeset.py <scratch> <recording>` | edits that change the prompt and leave the change set empty, or link to no test |
| `probe_drift.py <scratch> <recording> [others]` | change sets computed today against the line ids a recording holds |
| `probe_cov.py` | the modules imported inside the first test's coverage |
| `probe_harness.py` | `_route_only` in the prompt, delegation past the dispatcher, the judge's parsing, badly typed arguments |
| `probe_oracles.py` | cases a specialist that does nothing would pass; assertions true before the run |
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
