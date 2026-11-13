# A second recording with Gemma

`runs/gemma7` recorded a second time from scratch with the same command (`traceeval experiment --backend vllm
--reps 5 --workers 64`: Gemma 4 E4B, 180 tests, 43 changes, five repetitions, the model judge), into
`runs/gemma7_second`. `runs/gemma7` was recorded on fmi0's GPU0; the second recording on a cluster job with a copy
of the model on each of its two GPUs, the requests sent to the two in turn. It took two hours: 33 minutes for the
baseline, one test at a time, and 1.7 to 2.4 minutes per change. None of its 39,600 runs was broken by the
environment. A test's majority label is pass when at least three of its five runs pass; a test reveals a change
when its majority is pass on the original app and fail on the changed copy.

## 1. The original app

| | `runs/gemma7` | `runs/gemma7_second` |
|---|---|---|
| runs that pass | 860 of 900 | 860 of 900 |
| tests failing by majority | 8 | the same 8 |
| tests whose five runs disagree | 0 | 0 |
| full suite, tokens | 2,084,733 | 2,085,239 |

The majority label differs on none of the 180 tests, and every one of the 900 runs ends the same way in both
recordings, repetition by repetition. The answers are not identical token for token: 103 runs, of 40 tests, differ
in their token count, and one test, WF2-03 (which fails on the original app), takes a different course of steps and
tool calls in its five runs.

## 2. The changed copies, test by test

Of the 7,740 (change, test) pairs, 4 have a different majority label. Of the 38,700 runs on the changed copies, 23
end differently (same change, test and repetition) and 5,482 differ in their token count.

| change | test | `runs/gemma7`: passing runs | `runs/gemma7_second`: passing runs |
|---|---|---|---|
| `benign_routing_guidance_reordered` | PUB-02 | 4 of 5 | 2 of 5 |
| `code_search_case_sensitive` | WF3-03 | 5 of 5 | 2 of 5 |
| `config_max_tool_calls_5` | WF3-02 | 5 of 5 | 0 of 5 |
| `skill_routing_drop_brand_gate` | WF1-02 | 0 of 5 | 3 of 5 |

The four tests pass all five runs on the original app in both recordings. On three of the four pairs, one
recording's five runs all agree and the other recording gives the opposite label; under `config_max_tool_calls_5`,
WF3-02 passes every run in one recording and fails every run in the other. Five runs that agree with each other do
not fix the label of the next recording.

## 3. Revealing tests and regressions

| | `runs/gemma7` | `runs/gemma7_second` |
|---|---|---|
| changes counted as regressions (at least one revealing test) | 29 | 29, of which 28 are the same |
| the 34 changes expected to be regressions, revealed | 29 | 28 |
| the 9 benign changes, "revealed" | 0 | 1 |

The other 39 changes have the same revealing tests in both recordings (the counts of `report.md` §1). The four that
differ:

| change | expected | revealing tests, `runs/gemma7` | revealing tests, `runs/gemma7_second` | a regression in |
|---|---|---|---|---|
| `skill_routing_drop_brand_gate` | regression | 1: WF1-02 | 0 | `runs/gemma7` only |
| `benign_routing_guidance_reordered` | benign | 0 | 1: PUB-02 | `runs/gemma7_second` only |
| `code_search_case_sensitive` | regression | 3 | 4: WF3-03 added | both |
| `config_max_tool_calls_5` | regression | 10 | 11: WF3-02 added | both |

The verdict moves for the regression revealed by a single test and for a benign change that one test near the
majority line "reveals"; PUB-02 is also the test the nine benign changes break together (`batches.md`). The second
recording's sanity line is VIOLATED by seven changes instead of five: the five regressions no test reveals under
Gemma (`docs/EXPERIMENT.md` §7), `skill_routing_drop_brand_gate` and `benign_routing_guidance_reordered`.

## 4. Pairs whose own runs disagree

Passing runs of five, for every (change, test) pair whose runs disagree in at least one recording:

| change | test | `runs/gemma7` | `runs/gemma7_second` |
|---|---|---|---|
| `benign_routing_guidance_reordered` | PUB-02 | 4 | 2 |
| `code_search_case_sensitive` | WF3-03 | 5 | 2 |
| `config_max_tool_calls_5` | WF3-01 | 1 | 0 |
| `config_seo_title_20` | WF2-02 | 5 | 4 |
| `skill_governance_drop_consent` | DS-INTENTS/i20 | 3 | 3 |
| `skill_publish_drop_permission_check` | WF2-02 | 5 | 3 |
| `skill_routing_drop_brand_gate` | WF1-02 | 0 | 3 |
| `skill_translation_wrong_default` | WF4-01 | 2 | 2 |

Four pairs disagree in `runs/gemma7`, seven in the second recording, three in both; no test on the original app
disagrees in either. DS-INTENTS/i20 and WF4-01, the two pairs at the majority line in `runs/gemma7`
(`docs/RESEARCH_PLAN.md` §5.4), sit at it again, with other runs passing.

## 5. Detection at a 20% budget

From each recording's `results/report.md` §2: the share of the changes counted as regressions that a strategy
detects (29 in each, 28 of them shared, §3), over five replay seeds, and the tokens it spends on them, as a share
of the full suite.

| strategy | detection, `runs/gemma7` | detection, `runs/gemma7_second` | tokens, `runs/gemma7` | tokens, `runs/gemma7_second` |
|---|---|---|---|---|
| full | 0.34 | 0.34 | 0.200 | 0.200 |
| random | 0.56 | 0.56 | 0.200 | 0.200 |
| declared | 0.62 | 0.59 | 0.068 | 0.068 |
| ir_tfidf | 0.93 | 0.90 | 0.200 | 0.200 |
| observed | 0.86 | 0.86 | 0.154 | 0.153 |
| cost_aware | 0.86 | 0.86 | 0.199 | 0.199 |
| casper_slices | 0.59 | 0.48 | 0.200 | 0.200 |
| risk_aware_ts | 0.57 | 0.59 | 0.200 | 0.200 |
| adaptive_bayes | 0.78 | 0.78 | 0.029 | 0.028 |

- `declared` and `ir_tfidf` lose one change each: both detect `skill_routing_drop_brand_gate`, a regression in
  `runs/gemma7` only, and neither detects `benign_routing_guidance_reordered`, a regression in the second recording
  only. `observed` and `adaptive_bayes` detect neither, so their rates do not move.
- `risk_aware_ts` moves by one or two seeds of five on six of the shared regressions, in both directions.
- `casper_slices` falls from 0.59 to 0.48: of the shared regressions it loses four and gains two. Its slices come
  from behavioural signals averaged over the baseline runs, the runs' size in tokens among them, and those of 37
  tests differ slightly between the recordings; k-means then draws other slices, and 3 of the 12 slices and 15 of
  the 24 representatives are the same in both. Its $\mathrm{APFD}_c$ falls from 0.525 to 0.482.

Gemma's ground truth holds up to a second recording: the original app is the same run for run, 4 of 7,740 labels
move, and the set of changes counted as regressions trades one change for another. What moves rests on one test: a
regression revealed by a single test, and a benign change that one test near the majority line "reveals". The
strategies that read the diff keep their detection to within one change; CASPER's slices, drawn from the baseline's
traces, do not.
