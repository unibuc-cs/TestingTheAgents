# Demo walkthrough (20 minutes)

Every command runs from the repository root in a terminal, with the documents open next to it. Commands marked
*replay* need no model. Commands marked *live* need Gemma on the GPU server, started well before the demo with
`scripts/gpu_remote.sh up gemma` (it takes a few minutes, and the GPUs may be busy). Section 4 says what to do if
the server is down. What comes after the demo is in [AEM_ALIGNMENT.md](AEM_ALIGNMENT.md) §4.

## Before the demo

```bash
scripts/gpu_remote.sh status            # GPU0 of the GPU server (fmi0) free? then:
scripts/gpu_remote.sh up gemma          # a few minutes; "ready" at the end
pytest -q                               # green (the known model mistakes are expected failures inside the tests)
ls runs/gemma8/history runs/gemma8/variants   # the recording and the changed copies the live check needs
```

The recording must be of the app as it is now: the check refuses any other ([USER_GUIDE.md](USER_GUIDE.md) §8).

Open these in the editor: `docs/CONTENTOPS.md` (the figure), `traceeval/catalog/tests/publishing.yaml` (PUB-01),
`traceeval/catalog/tests/workflows.yaml` (WF3-01), `traceeval/catalog/properties.yaml`,
`traceeval/catalog/features.yaml`,
`docs/results/gemma8/report.md` and its figures, and `docs/sdd/report.md`.

## The terms used below

Test, property, change, change set, "reveals", strategy and budget are the README's terms
([USER_GUIDE.md](USER_GUIDE.md) §2 lists them). [RESEARCH_PLAN.md](RESEARCH_PLAN.md) §3 has the strategies, §5 the
results.

## 1. The question (2 minutes)

Say it in one sentence: after a change to an agent system (a skill, a prompt, harness code, a config key), which
tests should run, in what order, and when can we stop, so that we spend fewer tokens and still catch regressions.

Then show the table of requirements in [AEM_ALIGNMENT.md](AEM_ALIGNMENT.md) §2: the catalog of properties, coverage
from several angles, per-test metadata, trace assertions, workflows, agents modelled on AEM's, budgets with early
stopping, and OpenTelemetry. The next 18 minutes show everything the table marks as done.

## 2. The application and one test (3 minutes)

Show the figure in `docs/CONTENTOPS.md`. It follows one request from top to bottom: the orchestrator, a
specialist, its skill, the dispatcher, the tools and the services. The app has eleven agents, thirteen skills and
32 tools. Three of the agents (brand, insights, optimizer) are modelled on AEM's.

```bash
traceeval catalog | grep -E "PUB-01|WF"           # id, risk, entry agent, workflow, fault profile, name
traceeval run --test PUB-01 --backend replay       # replay: one case, its record
```

Point at the case in `publishing.yaml`:

- the request, "Please publish the welcome page";
- the properties it checks, as ids from the catalog of properties;
- the declared dependencies, which are deliberately incomplete;
- the expectations: final state, required and forbidden tools, audit counts, facts in the answer.

In the printed record, point at `passed`, `checks`, `tools` (the trace) and `tokens` (the cost). The record also
holds `deps`, the observed dependencies (agents, skills, tools, config keys, code lines), which the printout
leaves out.

## 3. A workflow across several agents (3 minutes)

```bash
traceeval run --test WF3-01 --backend replay --otel runs/otel/wf3-01.json     # replay
```

Open WF3-01 in `workflows.yaml`. The request is "Legal says the phrase 'guaranteed returns' must not appear on the
live site. Find the pages that use it, take the live ones down, and tell me which pages you took down". The run:

1. the orchestrator writes a plan (`make_plan`) and delegates the search to brand;
2. it asks a person (`request_approval`), whose answer is in the starting data (the fixture), so the run is
   repeatable;
3. it delegates to publishing, which takes two pages down with the approver's token, since `unpublish_page` is a
   guarded tool.

The expectations check the agent order, the tool order, the final state, the audit log and the page ids in the
answer.

Mention the variants: in WF3-02 a protected page stays up and is reported, and in WF3-03 a refused approval takes
nothing down. The other five workflows are in
[AEM_ALIGNMENT.md](AEM_ALIGNMENT.md) §3.3's table; name W1 (five agents) and W2 (two agents modelled on AEM's).

Open `runs/otel/wf3-01.json`. It holds the run span, the agent spans nested by delegation, and the tool and
model-call spans. The orchestrator's span carries its decisions as span events, called cognition events:
`consult`, `plan`, `route`, `approval`, `route`. The file is OTLP JSON ([AEM_ALIGNMENT.md](AEM_ALIGNMENT.md)
§3.6).

Then show why the checks look at the final state rather than at the answer:

```bash
traceeval run --test WF2-03 --backend replay      # replay: the site optimization with the broken page ranked first
```

Gemma's answer ends: "pages p7 and p17 were successfully republished, but page p16 could not be republished due to
existing broken links". The failed checks in the record say otherwise. `audit:publish_page` expected one
publication of p7 and one of p17, and found none. The model sent all three pages to publishing in one step,
publishing stopped at p16, and nothing was published. An LLM judge reading the answer would pass it. Only the
checks on the final state catch it. This is the point the requirements make: a trace that shows a call does not
prove that the state changed.

## 4. A change, checked live (5 minutes)

```bash
traceeval mutations                                        # the 43 controlled changes, with their category
# the orchestrator no longer asks a person before publishing:
cat runs/gemma8/variants/skill_routing_drop_approval/diff.patch
traceeval check skill_routing_drop_approval --history runs/gemma8 --budget 0.2     # live
```

The change removes one rule from the orchestrator's routing skill: ask a person before a step that publishes,
schedules or takes pages down. It edits the prose of a skill that every request reads, so it touches every test,
and nothing in the code changes.

While it runs, narrate the two phases ([RESEARCH_PLAN.md](RESEARCH_PLAN.md) §3.3 pictures the first,
[USER_GUIDE.md](USER_GUIDE.md) §5 the second):

- the replay: every test runs on the changed app with the answers the model gave the original app. The 27 tests
  that never read the routing skill replay to the end, and need no model. The other 153 send the model a prompt
  it has not seen;
- the method reads the change set (`skill:routing#prose`) and weighs those 153 tests by their sensitivity to that
  component, calibrated on the other recorded changes;
- it runs the most informative test per token first and updates after each outcome;
- it stops at the first failure of a test that passed on the original app.

What the check prints:

```text
skill_routing_drop_approval: changed skill:routing#prose
replay: 27 of 180 tests replay to the end, for no tokens, in 2 s; 153 diverge and need the model
  DS-ROUTING/r41         pass                                       3,923 tokens
  WF3-03                 FAIL required:request_approval,response~not approved,tool_error:unpublish_page  14,708 tokens
REGRESSION: WF3-03 failed
2 tests run with the model, 18,631 tokens (1% of the suite), ...; P(something broke) = 1.00
blamed: skill:routing#prose 0.63
coverage: 100% of the changed components exercised, 33% of the 15 affected properties checked, 17% of the 6 affected workflows run, 100% of the 3 affected features reached
... then what the tests invoked, the properties left unchecked and the workflows not run
```

Live, the token counts can differ from these, because decoding on the GPU server is nearly but not exactly
repeatable ([EXPERIMENT.md](EXPERIMENT.md) §3). The tests and the verdict stay the same. The coverage counts the
tests whose outcome is now known, replayed or run.

WF3-03 is the legal takedown in which the person refuses the approval. Without the rule, the orchestrator skips
the approval and sends the takedown to publishing. The dispatcher refuses the call because it carries no approval
token, so the pages stay up, and the test fails because no one was asked. The method needed two tests and one
percent of the suite's tokens.

Then a change that breaks nothing:

```bash
traceeval check benign_skill_prose_reflow --history runs/gemma8 --budget 0.2     # live
```

```text
benign_skill_prose_reflow: changed skill:publishing-workflow#prose
replay: 134 of 180 tests replay to the end, for no tokens, in 3 s; 46 diverge and need the model
  PUB-08                 pass                                       6,184 tokens (10,256 with its replayed part)
  PUB-01                 pass                                      10,512 tokens (14,556 with its replayed part)
  PUB-02                 pass                                      10,610 tokens (14,688 with its replayed part)
  WF4-01                 pass                                      10,697 tokens (55,968 with its replayed part)
  WF3-01                 pass                                      15,635 tokens (29,231 with its replayed part)
no regression: the method is confident nothing broke (36 tests the change reaches were not run)
5 tests run with the model, 53,638 tokens (3% of the suite), ...; P(something broke) = 0.05
```

Points to make:

- Only the 46 tests in which the publishing agent runs can be affected, and the replay finds them without a model.
- Each of the five tests is paid from its divergence point on: the multi-agent workflow WF4-01 costs 10,697 tokens
  instead of 55,968, because everything before the publishing step is replayed.
- The verdict says what it rests on: the method's confidence, with 36 reachable tests not run. Running those as
  well would give a verdict that leaves nothing untested, for 27% of the suite's tokens in all, more than this
  check's budget.
- Before it ends, every mandatory property the change may affect has a test whose outcome is known, replayed or
  run: the catalog's `mandatory` flag acts as a stopping rule. The coverage lines are the change coverage of
  [AEM_ALIGNMENT.md](AEM_ALIGNMENT.md) §3.5; the features are the unit the Adobe Team suggested.

If the GPU server is down, run these two checks with `--backend replay`: their answers are recorded in
`tests/cassettes/gemma.jsonl` ([EXPERIMENT.md](EXPERIMENT.md) §5), so the same tests run with the same outcomes,
and the timings read 0 seconds. If the server stops answering during a check, the check says so and gives no
verdict. The run is marked `INFRA_INVALID`, the environment's fault rather than the change's.

If there is time, a day's merges at once, which is how the Adobe Team runs their tests. `batch_nightly` bundles six
regressions and two harmless edits (`traceeval mutations` lists its members); the check stops at the first failure
and names the member it blames. This one needs the server: the tests it picks are not in the cassette.

```bash
traceeval check batch_nightly --history runs/gemma8 --budget 0.2     # live
```

```text
replay: 113 of 180 tests replay to the end, for no tokens, in 2 s; 67 diverge and need the model
```

Live, the check finds it with the first test it runs, for 0.4% of the suite's tokens, and blames the SEO agent's
lost tool; the other members stay near their prior of one half, untested
([results/gemma8_batches/batches.md](results/gemma8_batches/batches.md)). [RESEARCH_PLAN.md](RESEARCH_PLAN.md) §5.6
has the 23 batches, including the harmless edits that break a test together: the size makes no difference, and the
blame falls on a member that is a regression on its own in most runs.

"What about a bigger model?" The same two checks were run with Qwen and with gpt-oss, each against its own
recording and without a replay phase, since those recordings keep no answers of their original app:

| check | Qwen | gpt-oss |
|---|---|---|
| the routing skill without its approval rule | regression: WF3-03, after 2 tests, 1% of the suite | regression: WF3-03, after 3 tests, 2% |
| the publishing skill's prose reflowed (harmless) | clean after 7 tests, 3% | a false alarm: PUB-22 fails after 6 tests; its runs disagree under gpt-oss ([RESEARCH_PLAN.md](RESEARCH_PLAN.md) §5.4) |

Each model runs the tests its own recording ranks first; the verdicts agree with Gemma's except on the harmless
change under gpt-oss, where a single live run of an unstable test is a false alarm that the recording's majority
would absorb. These two recordings (`runs/qwen7`, `runs/gptoss7`) are of the app as it was before the harness
fixes of [TODO.md](../TODO.md) §3, so `traceeval check` now refuses them; a recording of the current app with
each model is TODO §4.

## 5. The evidence over all changes (4 minutes)

Open `docs/results/gemma8/report.md`, every strategy evaluated on every change from the recording of the current
app ([USER_GUIDE.md](USER_GUIDE.md) §4 says how to read it):

- Section 1, the ground truth: 28 of the 34 regressions are revealed and no benign change fails a test; the six
  no test reveals under Gemma are in [EXPERIMENT.md](EXPERIMENT.md) §7. Under the header, the empty change:
  the original app run as the changed copies are flips no test.
- Section 2 and `figures/detection_vs_cost.png`: detection against the tokens actually spent, every strategy run
  under the same two rules ([USER_GUIDE.md](USER_GUIDE.md) §2). At a 20% budget, hand-written dependencies find
  61% of the regressions, traces 86%, TF-IDF 93% and the adaptive method 81%, for 3.8%, 8.6%, 10% and 5.1% of
  the suite's tokens. The adaptive method is the line at the top left of the figure, up to about 4% of the
  tokens; it catches 89% of the changes that break a safety property.
- Section 3: the tokens spent on the changes no test reveals, and the verdict each strategy's runs end with. The
  adaptive method never calls one of those changes a regression; 27% of its clean verdicts are given on a
  regression some test reveals.
- Section 5: the catalog of properties, with each property's pass rate against its threshold.
- Section 6: the coverage of [AEM_ALIGNMENT.md](AEM_ALIGNMENT.md) §3.5. Point at the `not covered` column (the
  tests reach 15 of the 32 places where a tool refuses) and at one declared-against-invoked gap.
  `traceeval coverage --history runs/gemma8` prints the same in the terminal.
- Section 7 and `figures/replay_first.png`: the same strategies with the replay in front. Eight of the 43 changes
  need no model at all, the replayed outcome is the recorded one on all 6,298 (change, test) pairs that replay,
  and with no budget an order of the diverged tests finds 98% to 100% of the regressions for 9% to 10% of the
  suite's tokens. Put the two figures side by side: every line moves up and to the left. Then the table of the
  condition: about 2% of the model's calls are answered otherwise when made again, and no outcome moves.

Mention the finding of [RESEARCH_PLAN.md](RESEARCH_PLAN.md) §5.3: the mandatory rule is what catches the publishing
skill without its link check. Its §5.1 goes through the results by research question, §5.7 has replay-first, and
§5.5 the take-aways.

## 6. The catalog of properties, drafted by a model (1 minute)

[AEM_ALIGNMENT.md](AEM_ALIGNMENT.md) §3.4 has the table of `traceeval/catalog/properties.yaml`'s fields and what
uses them; open the file and point at `mandatory` and `sources`. `traceeval properties draft` has a model write
this catalog from the requirements only, within fixed limits, and tag the tests; a person then edits the draft and
applies it.

Show `docs/properties/draft_qwen/properties.draft.md`, Qwen's draft from the requirements alone. It has fifteen
properties, each with the components it comes from, and one requirement that no test checks: the 30-day approval
window of spec FS-0101. The point to make is that the model writes a good catalog, but someone has to check how it
tagged the tests, since many get only the routing property.

## 7. Spec-driven development, the add-on (2 minutes)

Open `docs/sdd/report.md`: five change requests written as machine-checkable specs, and 25 pull requests checked
against them. Every verdict is as expected, with the clause that failed and the counterexample. Point at these
cases:

- FS-0101's rule is proven for all inputs.
- A correct implementation in the wrong layer is caught by the placement check, the clause that says which layer
  must hold a rule.
- A proven function that is never called is caught by a scenario, a test the spec adds.

`traceeval sdd` replays it in about a minute. [SDD_DEMO.md](SDD_DEMO.md) has the summary.

## Questions to expect

- *Does the ground truth depend on the model?* Yes. A change a model cannot see, because it ignores the guard with
  or without the change, is a fact about the model, and the report says which changes these are. The ground truth
  is Gemma's: five repetitions per test and a majority vote, which absorbs the four (change, test) pairs its runs
  disagree on.
- *Why are some workflow tests red?* They are Gemma's own mistakes on the original app, not faults of the testbed:
  it schedules the launch page right after requesting a review (WF1-01), goes on to publishing after the rollback's
  link check failed (WF5-02), stops a whole plan after a refused export (WF6-02) and misreports the site
  optimization of section 3 (WF2-03); [EXPERIMENT.md](EXPERIMENT.md) §6 lists them. A test the model already fails
  cannot reveal a change, which is why no strategy runs it.
- *Why only Gemma's numbers?* Qwen's and gpt-oss's recordings of the same app are not clean ground truths
  ([RESEARCH_PLAN.md](RESEARCH_PLAN.md) §5.4): recorded many tests at once, a change that alters nothing appears to
  break a few tests. One test at a time Qwen is as repeatable as Gemma, and its recording made that way gives
  the same picture ([RESEARCH_PLAN.md](RESEARCH_PLAN.md) §5.7); gpt-oss is not, and its outcomes change
  with a restart of the server. A larger model does not give a cleaner ground truth by itself, so the lesson for
  Adobe is to measure first how much the answers vary under the real serving setup. The harmless change of section
  4, checked with gpt-oss from its cassette, is a false alarm on PUB-22, a test whose runs disagree under that
  model.
- *How would this run at Adobe?* Nightly full-suite runs provide the recordings: the answers the model gave, which
  the replay answers from, and the outcomes the method learns from. For each change, `traceeval check` replays
  it, selects among the tests that diverge, orders them and decides when to stop. The traces are OpenTelemetry,
  and the catalog of properties maps onto the metrics of DeepEval, the evaluation library the Adobe Team uses.
- *Can recorded answers stand in for the model?* As far as a model call is a function of its request. Under
  Gemma as served here, all 31,490 recorded runs of the tests that replay to the end finish like their replay
  ([RESEARCH_PLAN.md](RESEARCH_PLAN.md) §5.7). Under a serving setup where answers vary with the batch
  (Qwen's, gpt-oss's), that has to be measured first.
- *Does the offline evaluation predict the live run?* Yes: the check, run live on all 43 changes, gave the
  evaluator's verdict on 41, after as many tests. One exception is a live false alarm on a benign change, on a
  test that passes its five recorded runs: the live check reads one run where the evaluator reads five. The other
  is a check that fits more tests in its budget than the evaluator allows it ([EXPERIMENT.md](EXPERIMENT.md) §5).
- *How sure is "no regression"?* By default the method stops on its own probability, which promises nothing.
  With `--miss-rate 0.1` the stop threshold is set on recorded changes that edit the same kind of thing, so that
  at most one regression in ten is called clean, and the check says what the threshold rests on. Run that way on
  the 43 changes, it found all 28 regressions with no false alarm, for 2.8% of the suite's tokens per check
  ([RESEARCH_PLAN.md](RESEARCH_PLAN.md) §5.9).
- *What is next?* Re-planning after a failed step is built on a branch and recorded with three models. It waits for
  one decision: whether a single publication with a broken link is repaired or refused
  ([AEM_ALIGNMENT.md](AEM_ALIGNMENT.md) §4.1). Then tau2-bench, a public agent benchmark, as a second application.

## Questions for the Adobe Team

Close with the questions for the Adobe Team, the re-planning decision first: should a single publish request for a
page with a broken link be repaired or refused? [RESEARCH_PLAN.md](RESEARCH_PLAN.md) §8 keeps the list, with what
each answer decides.
