# The replay's stand-ins, checked live

`runs/gemma8_gen` was recorded for the tests each change reaches only. Every other (change, test) pair, 101,534 of
them over the 691 changes, has no run: the test replays to the end on the changed copy, and its replayed run stands
in for it. Under conditions R and D the live outcome is the replay's
([RESEARCH_PLAN.md](../../RESEARCH_PLAN.md) §3.3). This page checks that on a sample, with the model.
[Qwen's page](../qwen8_gen/stand_ins_live.md) does the same for `runs/qwen8_gen`.

`python scripts/analysis/stand_ins_live.py runs/gemma8_gen --backend vllm --workers 32 --changes 100 --tests 30`
draws 100 changes at random and 30 replayed tests of each (27 for nine changes that have no more), makes each
changed copy again from the recording's copy of the original app, and runs the drawn tests on it with Gemma,
served as when the recording was made. It took 15 minutes on one GPU.

- **2,973 pairs run live, and all 2,973 end like their stand-in.** That includes the 146 pairs where the replay
  fails the test: the live run fails it too.
- **2,503 are the same conversation** as the replay: the same tool calls, final answer, final state and tokens.
- **The others differ in wording, not in outcome.** Of the 15,634 requests the cassette knows, 522 are answered
  otherwise, in 521 runs. 268 of those runs then sent a request the cassette lacks, and still ended as the replay
  did.
- No run was broken by the environment.

| group of the change | pairs | the replay fails | end like the stand-in | the same conversation |
|---|---|---|---|---|
| a skill's steps | 807 | 31 | 807 | 679 |
| an agent's tools and skills | 267 | 11 | 267 | 222 |
| code | 567 | 57 | 567 | 475 |
| text the model reads | 705 | 19 | 705 | 622 |
| the configuration | 267 | 10 | 267 | 216 |
| the starting data | 360 | 18 | 360 | 289 |
| all | 2973 | 146 | 2973 | 2503 |

"The replay fails" counts the pairs whose stand-in is a failure, whether the test passes on the original app or
not.
