# The replay's stand-ins, checked live (Qwen)

`runs/qwen8_gen` was recorded for the tests each change reaches only. Every other (change, test) pair, 101,617 of
them over the 691 changes, has no run: the test replays to the end on the changed copy, and its replayed run stands
in for it. Under conditions R and D the live outcome is the replay's
([RESEARCH_PLAN.md](../../RESEARCH_PLAN.md) §3.3). This page checks that on a sample, with the model.
[Gemma's page](../gemma8_gen/stand_ins_live.md) does the same for `runs/gemma8_gen`.

`python scripts/analysis/stand_ins_live.py runs/qwen8_gen --backend llm --workers 2 --changes 100 --tests 10`
draws 100 changes at random and 10 replayed tests of each, makes each changed copy again from the recording's copy
of the original app, and runs the drawn tests on it with Qwen. Qwen is served as when the recording was made:
without the prefix cache, one test at a time on each of two GPUs (`TRACEEVAL_LLM_BASE_URL` lists both servers). It
took 52 minutes.

- **1,000 pairs run live, and all 1,000 end like their stand-in.** That includes the 83 pairs where the replay
  fails the test: the live run fails it too.
- **All 1,000 are the same conversation** as the replay: the same tool calls, final answer, final state and tokens.
- **No answer differs.** The 1,000 runs sent 4,846 requests; the cassette knows every one, and none is answered
  otherwise. Served this way, condition R holds exactly, and so does the claim.
- No run was broken by the environment.

| group of the change | pairs | the replay fails | end like the stand-in | the same conversation |
|---|---|---|---|---|
| a skill's steps | 270 | 12 | 270 | 270 |
| an agent's tools and skills | 90 | 4 | 90 | 90 |
| code | 200 | 43 | 200 | 200 |
| text the model reads | 250 | 10 | 250 | 250 |
| the configuration | 80 | 13 | 80 | 80 |
| the starting data | 110 | 1 | 110 | 110 |
| all | 1000 | 83 | 1000 | 1000 |

"The replay fails" counts the pairs whose stand-in is a failure, whether the test passes on the original app or
not.
