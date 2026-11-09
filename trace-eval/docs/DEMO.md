# Demo walkthrough (20 minutes)

The demo for the AEM team on Thursday 12 November 2026. Everything below runs from the repository root in a
terminal, with the documents open next to it. The commands marked *replay* need no model; the ones marked
*live* need Gemma on the GPU server (`scripts/gpu_remote.sh up gemma`, started an hour before). The plan the
demo answers to is [AEM_ALIGNMENT.md](AEM_ALIGNMENT.md) §4.

## Before the demo

```bash
scripts/gpu_remote.sh status            # both fmi0 GPUs free? then:
scripts/gpu_remote.sh up gemma          # a few minutes; "ready" at the end
pytest -q                               # green (the known model mistakes are expected failures inside the tests)
ls runs/gemma5/variants                 # the recording of the current app, for the live check
```

Open in the editor: `docs/CONTENTOPS.md` (the figure), `traceeval/catalog/tests/publishing.yaml` (PUB-01),
`traceeval/catalog/tests/workflows.yaml` (WF3-01), `traceeval/catalog/properties.yaml`,
`docs/results/gemma5/report.md` and its figures, `docs/sdd/report.md`.

If the GPU server is unreachable on the day, every *live* command below runs with `--backend replay` on the
recorded answers, which replay the same runs exactly (task M6 recorded them).

## 1. The question (2 minutes)

Say it in one sentence: after a change to an agent system (a skill, a prompt, harness code, a config key), which
tests should run, in what order, and when can we stop, so that we spend fewer tokens and still catch regressions.
Show the table of what the AEM team asked for in the README ("Features asked for by Adobe's AEM team"): the
catalog of properties, coverage from several angles, per-test metadata, trace assertions, workflows, agents
modelled on AEM's, budgets with early stopping, OpenTelemetry. Everything in the table marked "done" is shown
in the next 18 minutes.

## 2. The application and one test (3 minutes)

The figure in `docs/CONTENTOPS.md`: one request, top to bottom, through the orchestrator, a specialist, its
skill, the dispatcher, the tools and the services. Eleven agents, thirteen skills, 32 tools; three of the agents
(brand, insights, optimizer) are modelled on AEM's.

```bash
traceeval catalog | grep -E "PUB-01|WF"           # id, risk, entry agent, workflow, fault profile, name
traceeval run --test PUB-01 --backend replay       # replay: one case, its record
```

Point at the case in `publishing.yaml`: the request ("Please publish the welcome page"), the properties it checks
(ids from the catalog of properties), the declared dependencies (deliberately incomplete), and the expectations:
final state, required and forbidden tools, audit counts, facts in the answer. In the printed record: `passed`,
`checks`, `tools` (the trace), `tokens` (the cost), `deps` left out of the printout but recorded (the observed
dependencies: agents, skills, tools, config keys, code lines).

## 3. A workflow across several agents (3 minutes)

```bash
traceeval run --test WF3-01 --backend replay --otel runs/otel/wf3-01.json     # replay
```

WF3-01 in `workflows.yaml`: "Legal says the phrase 'guaranteed returns' must not appear on the live site: find
the pages that use it, take the live ones down, and tell me which". The orchestrator writes a plan (`make_plan`),
delegates to brand (search), asks a person (`request_approval`; the answer is fixture data, so the run repeats),
delegates to publishing, which takes two pages down with the approver's token (`unpublish_page` is guarded). The
expectations check the agent order, the tool order, the final state, the audit log and the page ids in the
answer. Mention the variants: a protected page stays up and is reported (WF3-02), a refused approval takes nothing
down (WF3-03). Mention W1 (campaign launch across five agents), W2 (site optimization through insights,
optimizer, seo and publishing, the three AEM-style agents), W4 (a price change translated into each language
and republished after review; a language the platform does not have fails without stopping the others), W5
(a broken release rolled back and republished) and W6 (a privacy request: export, bylines removed, republish).

Open `runs/otel/wf3-01.json`: the run span, the agent spans nested by delegation, the tool and model-call spans,
and on the orchestrator's span the events `consult`, `plan`, `route`, `approval`, `route`: the cognition events.
It is OTLP JSON, what a collector accepts on `/v1/traces`.

Then why the checks look at the final state, not at the answer:

```bash
traceeval run --test WF2-03 --backend replay      # replay: the site optimization with the broken page ranked first
```

Gemma's answer ends: "pages p7 and p17 were successfully republished, but page p16 could not be republished due to
existing broken links". The record's failed checks say otherwise: `audit:publish_page` expected one publication of
p7 and one of p17, and found none. The model sent all three pages to publishing in one step, publishing stopped at
p16, and nothing was published. An LLM judge reading the answer would pass it; only the checks on the final state
catch it. This is the requirements' point that a trace showing a call does not prove the state changed.

## 4. A change, checked live (5 minutes)

```bash
traceeval mutations                                        # the 43 controlled changes, with their category
cat runs/gemma5/variants/skill_routing_drop_approval/diff.patch   # the orchestrator no longer asks a person before publishing
traceeval check skill_routing_drop_approval --history runs/gemma5 --budget 0.2     # live
```

The change removes one rule from the orchestrator's routing skill: ask a person before a step that publishes,
schedules or takes pages down. It is a prose edit in a skill every request reads, so it touches every test, and
nothing in the code changes. What to narrate while it runs: the method reads the change set
(`skill:routing#prose`), weighs every test by its sensitivity to that component (calibrated on the other recorded
changes), runs the most informative test per token first, updates after each outcome, and stops at the first
failure of a test that passed on the original app. The output of the rehearsal on 9 November:

```text
skill_routing_drop_approval: changed skill:routing#prose
  DS-ROUTING/r41         pass                                       3,935 tokens
  MNT-03                 pass                                       6,468 tokens
  WF3-03                 FAIL required:request_approval,response~not approved,tool_error:unpublish_page  14,708 tokens
REGRESSION: WF3-03 failed
3 runs, 25,111 tokens (1% of the suite), 22 s (the whole suite takes about 361 s, one test at a time); P(something broke) = 1.00
```

WF3-03 is the legal takedown in which the person refuses the approval. Without the rule, the orchestrator skips
the approval and sends the takedown to publishing; the dispatcher's token gate refuses it, so the pages stay up,
and the test fails because no one was asked. Three tests and one percent of the suite's tokens.

Then a change that breaks nothing:

```bash
traceeval check benign_skill_prose_reflow --history runs/gemma5 --budget 0.2     # live
```

It ends "no regression: the method is confident nothing broke" after nine tests, 4% of the suite's tokens, with
P(something broke) = 0.04, and before it ends it has run a test of every mandatory property the change may affect
(the catalog's `mandatory` flag as a stopping rule). The coverage lines are the change coverage the requirements
ask for: changed components exercised, affected properties checked, affected workflows run.

If the GPU server is down, run both with `--backend replay`: the answers of the rehearsal are recorded, so the
same tests run with the same outcomes (the seconds read 0). If it stops answering during a check, the check says
so and gives no verdict (the run is `INFRA_INVALID`, the environment's fault, not the change's).

## 5. The evidence over all changes (4 minutes)

`docs/results/gemma5/report.md`, the replay of every strategy on every change, from the recording of the current
app:

- Section 1, the ground truth: each change with the number of tests that reveal it, and the sanity line. Of the 34
  regressions, 29 are revealed; the other five are ones Gemma ignores either way (it does not act on a review flag
  or a length limit it has to work out for itself), and no benign change fails a test.
- Section 2 and `figures/detection_vs_cost.png`: detection against tokens and time actually spent. At a 20%
  budget, hand-written dependencies find 61% of the regressions, traces 86%, TF-IDF 92%, and the adaptive method
  79% for 3% of the tokens: it sits at the left of the figure. Of the changes that break a safety property it
  catches 86%.
- Section 3: tokens spent on benign changes, and the stop reasons: the adaptive method never calls a benign change
  a regression.
- Section 5: the catalog of properties, each with its category, mandatory flag, threshold and pass rate.
- Section 6: coverage of the suite per dimension (agents, skills, tools, configuration, properties, workflows,
  execution paths, risk; declared and observed; what no test covers), and the change coverage per strategy.

One finding to mention: the mandatory-coverage rule is what catches `skill_publish_drop_link_validation`. Without
it the method calls that change clean; with it, it must test the mandatory "no broken publish" property before
stopping, and that test fails.

## 6. The catalog of properties, drafted by a model (1 minute)

`traceeval/catalog/properties.yaml`: categories, how each property is checked, mandatory flags, thresholds, and
the components each property comes from. `traceeval properties draft` has a model write it from the
requirements only (skills, agents, configuration guards, specs), within fixed limits, and tag the tests; a person
edits the draft and applies it. Show `docs/properties/draft_qwen/properties.draft.md`, Qwen's draft from the
requirements alone: fifteen properties, each with the components it comes from, and one requirement no test
checks (the 30-day approval window of spec FS-0101). Say what it shows: the model writes a good catalog, and its
tags of the tests need a person's review (many tests get only the routing property).

## 7. Spec-driven development, the add-on (2 minutes)

`docs/sdd/report.md`: five change requests as machine-checkable specs, 25 pull requests, every verdict as
expected, with the clause that failed and the counterexample. FS-0101's rule is proven for all inputs; a correct
implementation in the wrong layer is caught by placement; a proven function that is never called is caught by a
scenario. `traceeval sdd` replays it in about a minute. [SDD_DEMO.md](SDD_DEMO.md) has the summary.

## Questions to expect

- *The ground truth depends on the model?* Yes: a change a model cannot see (it ignores the guard either way) is
  a fact about the model, and the report says which. Two models, three repetitions, majority vote.
- *Why are some workflow tests red?* They are Gemma's own mistakes on the original app, not the testbed's. In
  WF1-01 it schedules the launch page after requesting a review instead of having the approver approve it (as in
  PUB-10); in WF5-02 it goes on to publishing after the rollback's link check failed, and publishing's own link
  check refuses the page (defence in depth); in WF6-02 it stops the whole plan after a refused export, although
  the byline edits do not depend on it. A test the model already fails cannot reveal a change, which is why the
  method discounts it. Qwen gets WF1-01 and WF6-02 right; in WF5-02 and WF1-02 it re-plans (it has the broken link
  fixed, or rewrites the page that failed the brand check, and goes on), as Adobe's Agent Orchestrator does.
- *Why only Gemma's numbers?* Qwen's recording of the same app is not a clean ground truth: six of its tests answer
  differently when run 64 at a time than one at a time, so even a change that alters nothing "breaks" them. A
  larger model is not automatically a cleaner ground truth: some of Qwen's answers vary from run to run, and
  vLLM's switch for repeatable decoding does not support Qwen3.8. Both models are used as they are served. The
  lesson for Adobe: measure how much the answers vary under the real serving setup first (RESEARCH_PLAN §5.4).
- *How would this run at Adobe?* Nightly full-suite runs are the recordings the method learns from; per change,
  `traceeval check` is the selection, the order and the stop; the traces are OpenTelemetry; the catalog of
  properties maps onto DeepEval's metrics.
- *What is next?* Re-planning after a failed step, and tau2-bench as a second application
  ([AEM_ALIGNMENT.md](AEM_ALIGNMENT.md) §4).
