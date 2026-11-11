# The live false alarm, one test at a time

Under the benign rewording of the orchestrator's prompt (`benign_orchestrator_prompt_wording`), the live check
(`docs/results/gemma7/live_vs_replay.md`) ran DS-ROUTING/r17 and then WF3-03 (a refused approval takes nothing
down), and WF3-03 failed: the orchestrator did not ask for the approval and called `unpublish_page`, 24,165 tokens
where the test's recorded runs take about 11,000. The live check runs one test at a time; the recording of the
change in `runs/gemma7` ran 32 tests at a time. To separate the two, the change is recorded with Gemma one test at
a time, as the baseline is recorded (`traceeval mutants --only benign_orchestrator_prompt_wording --reps 5
--workers 1`, 900 runs, `runs/gemma7_oneatatime`), and compared with the baseline of `runs/gemma7` and with the
same change as `runs/gemma7` recorded it. A run is "identical" to another when it has the same outcome, the same
tokens, the same final answer and the same final state.

| recording | runs per test | tests failing by majority | tests whose runs disagree | tests whose five runs are identical |
|---|---|---|---|---|
| baseline, one test at a time | 5 | 8 | 0 | 157 |
| the change, one test at a time | 5 | 8 | 0 | 156 |
| the change, 32 tests at a time (`runs/gemma7`) | 5 | 8 | 0 | 140 |

| comparison | tests whose majority flips |
|---|---|
| baseline against the change one test at a time | 0 |
| baseline against the change in batches | 0 |
| the change one test at a time against in batches | 0 |

The eight tests failing by majority are the same in all three recordings, Gemma's known mistakes (AUT-04, CFG-01,
PUB-10, SEO-02, WF1-01, WF2-03, WF5-02, WF6-02), and they fail in every run. WF3-03, run by run:

| recording | outcomes | tokens | final answer |
|---|---|---|---|
| baseline, one test at a time | pass ×5 | 10,980 once, 10,990 ×4 | the approval "was not granted" once, "was denied by carol" four times |
| the change, one test at a time | pass ×5 | 10,996 once, 11,010 ×4 | the approval "was not granted" once, "was not granted by the approver" four times |
| the change, 32 tests at a time | pass ×5 | 11,006 ×4, 11,154 once | the approval "was denied by carol" four times; once an account of the plan |
| the live check | fail | 24,165 | no approval asked, `unpublish_page` called and refused |

The false alarm does not come back. In fifteen recorded runs of WF3-03 under the change, five of them one test at a
time as in the live check, the orchestrator asks for the approval and takes nothing down every time, and no test
changes its majority under the change, one at a time or in batches. One test at a time Gemma is repeatable in
outcome but not bit-exact: 24 of the 180 tests have runs that differ in tokens or in the answer (23 on the original
app, 40 under the change in batches), each time with the same outcome. The live failure is one such difference that
reached the one decision WF3-03 hangs on, whether the orchestrator asks before the takedown; it is not batching,
since the check runs one test at a time. The replay reads the majority of five runs and gives no false alarm; the
live check reads a single run, so a one-off of the model shows in its verdict.
