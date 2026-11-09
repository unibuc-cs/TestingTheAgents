# Demo walkthrough (20 minutes)

This is the walkthrough for the demo to the AEM team on Thursday 12 November 2026. Every command runs from the
repository root in a terminal, with the documents open next to it. Commands marked *replay* need no model.
Commands marked *live* need Gemma on the GPU server, started an hour before with `scripts/gpu_remote.sh up gemma`.
Section 4 says what to do if the server is down. The limits worth mentioning, and what comes after the demo, are
in [AEM_ALIGNMENT.md](AEM_ALIGNMENT.md) §4.

## Before the demo

```bash
scripts/gpu_remote.sh status            # both fmi0 GPUs free? then:
scripts/gpu_remote.sh up gemma          # a few minutes; "ready" at the end
pytest -q                               # green (the known model mistakes are expected failures inside the tests)
ls runs/gemma5/variants                 # the recording of the current app, for the live check
```

Open these in the editor: `docs/CONTENTOPS.md` (the figure), `traceeval/catalog/tests/publishing.yaml` (PUB-01),
`traceeval/catalog/tests/workflows.yaml` (WF3-01), `traceeval/catalog/properties.yaml`,
`docs/results/gemma5/report.md` and its figures, and `docs/sdd/report.md`.

## 1. The question (2 minutes)

Say it in one sentence: after a change to an agent system (a skill, a prompt, harness code, a config key), which
tests should run, in what order, and when can we stop, so that we spend fewer tokens and still catch regressions.

Then show the README's table "Features asked for by Adobe's AEM team": the catalog of properties, coverage from
several angles, per-test metadata, trace assertions, workflows, agents modelled on AEM's, budgets with early
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
live site: find the pages that use it, take the live ones down, and tell me which". The orchestrator writes a plan
(`make_plan`) and delegates the search to brand. It then asks a person (`request_approval`), whose answer is
fixture data, so the run is repeatable. Finally, it delegates to publishing, which takes two pages down with the
approver's token, since `unpublish_page` is a guarded tool. The expectations check the agent order, the tool
order, the final state, the audit log and the page ids in the answer.

Mention the variants: in WF3-02 a protected page stays up and is reported, and in WF3-03 a refused approval takes
nothing down. Then mention the other workflows:

- W1, a campaign launch across five agents.
- W2, site optimization through insights, optimizer, seo and publishing, two of them modelled on AEM's agents.
- W4, a price change translated into each language and republished after review. A language the platform does
  not have fails without stopping the others.
- W5, a broken release rolled back and republished.
- W6, a privacy request: the data exported, the bylines removed, the pages republished.

Open `runs/otel/wf3-01.json`. It holds the run span, the agent spans nested by delegation, and the tool and
model-call spans. The orchestrator's span carries its decisions as span events, called cognition events:
`consult`, `plan`, `route`, `approval`, `route`. The file is OTLP JSON, the OpenTelemetry format a collector
accepts on `/v1/traces`.

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
cat runs/gemma5/variants/skill_routing_drop_approval/diff.patch   # the orchestrator no longer asks a person before publishing
traceeval check skill_routing_drop_approval --history runs/gemma5 --budget 0.2     # live
```

The change removes one rule from the orchestrator's routing skill: ask a person before a step that publishes,
schedules or takes pages down. It edits the prose of a skill that every request reads, so it touches every test,
and nothing in the code changes.

While it runs, narrate what the method does. It reads the change set (`skill:routing#prose`) and weighs every
test by its sensitivity to that component, calibrated on the other recorded changes. It runs the most informative
test per token first, updates after each outcome, and stops at the first failure of a test that passed on the
original app. The output of a rehearsal:

```text
skill_routing_drop_approval: changed skill:routing#prose
  DS-ROUTING/r41         pass                                       3,935 tokens
  MNT-03                 pass                                       6,468 tokens
  WF3-03                 FAIL required:request_approval,response~not approved,tool_error:unpublish_page  14,708 tokens
REGRESSION: WF3-03 failed
3 runs, 25,111 tokens (1% of the suite), 22 s (the whole suite takes about 361 s, one test at a time); P(something broke) = 1.00
```

WF3-03 is the legal takedown in which the person refuses the approval. Without the rule, the orchestrator skips
the approval and sends the takedown to publishing. The dispatcher refuses the call because it carries no approval
token, so the pages stay up, and the test fails because no one was asked. The method needed three tests and one
percent of the suite's tokens.

Then a change that breaks nothing:

```bash
traceeval check benign_skill_prose_reflow --history runs/gemma5 --budget 0.2     # live
```

It ends with "no regression: the method is confident nothing broke" after nine tests and 4% of the suite's
tokens, with P(something broke) = 0.04. Before it ends, it has run a test of every mandatory property the change
may affect, because the catalog's `mandatory` flag acts as a stopping rule. The coverage lines in the output are
the change coverage the requirements ask for: changed components exercised, affected properties checked and
affected workflows run.

If the GPU server is down, run both checks with `--backend replay`. The rehearsal's answers are recorded, so the
same tests run with the same outcomes, and the timings read 0 seconds. If the server stops answering during a
check, the check says so and gives no verdict. The run is marked `INFRA_INVALID`, the environment's fault rather
than the change's.

## 5. The evidence over all changes (4 minutes)

Open `docs/results/gemma5/report.md`, the replay of every strategy on every change, from the recording of the
current app:

- Section 1 is the ground truth: each change with the number of tests that reveal it, and the testbed sanity
  line. Of the 34 regressions, 29 are revealed. Gemma ignores the other five either way: it does not act on a
  review flag, or on a length limit it has to work out for itself. No benign change fails a test.
- Section 2 and `figures/detection_vs_cost.png` show detection against the tokens and time actually spent. At a
  20% budget, hand-written dependencies find 61% of the regressions, traces 86%, TF-IDF 92%, and the adaptive
  method 79% for 3% of the tokens, which puts it at the left of the figure. It catches 86% of the changes that
  break a safety property.
- Section 3 gives the tokens spent on benign changes and the reasons each strategy stopped. The adaptive method
  never calls a benign change a regression.
- Section 5 lists the catalog of properties, each with its category, mandatory flag, threshold and pass rate.
- Section 6 gives the coverage of the suite per dimension and the change coverage per strategy. The dimensions
  are agents, skills, tools, configuration, properties, workflows, execution paths and risk, each declared and
  observed, with what no test covers.

Mention one finding: the mandatory-coverage rule is what catches `skill_publish_drop_link_validation`. Without
the rule, the method calls that change clean. With it, the method must test the mandatory "no broken publish"
property before stopping, and that test fails.

## 6. The catalog of properties, drafted by a model (1 minute)

`traceeval/catalog/properties.yaml` gives each property a category, how it is checked, a mandatory flag, a
threshold, and the components it comes from. `traceeval properties draft` has a model write this catalog from the
requirements only (skills, agents, configuration guards, specs), within fixed limits, and tag the tests. A person
then edits the draft and applies it.

Show `docs/properties/draft_qwen/properties.draft.md`, Qwen's draft from the requirements alone. It has fifteen
properties, each with the components it comes from, and one requirement that no test checks: the 30-day approval
window of spec FS-0101. The point to make is that the model writes a good catalog, but its tags of the tests need
a person's review, since many tests get only the routing property.

## 7. Spec-driven development, the add-on (2 minutes)

Open `docs/sdd/report.md`: five change requests written as machine-checkable specs, and 25 pull requests checked
against them. Every verdict is as expected, with the clause that failed and the counterexample. Point at these
cases:

- FS-0101's rule is proven for all inputs.
- A correct implementation in the wrong layer is caught by the placement check.
- A proven function that is never called is caught by a scenario.

`traceeval sdd` replays it in about a minute. [SDD_DEMO.md](SDD_DEMO.md) has the summary.

## Questions to expect

- *Does the ground truth depend on the model?* Yes. A change a model cannot see, because it ignores the guard
  with or without the change, is a fact about the model, and the report says which changes these are. The
  ground truth is Gemma's: three repetitions per test and a majority vote.
- *Why are some workflow tests red?* They are Gemma's own mistakes on the original app, not faults of the
  testbed. In WF1-01 it schedules the launch page after requesting a review, instead of having the approver
  approve it as in PUB-10. In WF5-02 it goes on to publishing after the rollback's link check failed, and
  publishing's own link check refuses the page: defence in depth. In WF6-02 it stops the whole plan after a
  refused export, although the byline edits do not depend on it. A test the model already fails cannot reveal a
  change, which is why the method discounts it. Qwen gets WF1-01 and WF6-02 right. In WF5-02 and WF1-02 it
  re-plans, as Adobe's Agent Orchestrator does: it has the broken link fixed, or rewrites the page that failed
  the brand check, and goes on.
- *Why only Gemma's numbers?* Qwen's recording of the same app is not a clean ground truth. Six of its tests
  answer differently when run 64 at a time than when run one at a time, so even a change that alters nothing
  appears to break them. A larger model does not automatically give a cleaner ground truth: some of Qwen's
  answers vary from run to run, and vLLM, the model server, has a switch for repeatable decoding that does not
  support Qwen3.8. Both models are used as they are served. The lesson for Adobe is to measure first how much the
  answers vary under the real serving setup (RESEARCH_PLAN §5.4).
- *How would this run at Adobe?* Nightly full-suite runs provide the recordings the method learns from. For each
  change, `traceeval check` selects the tests, orders them and decides when to stop. The traces are
  OpenTelemetry, and the catalog of properties maps onto DeepEval's metrics.
- *What is next?* Re-planning after a failed step, and tau2-bench, a public agent benchmark, as a second
  application ([AEM_ALIGNMENT.md](AEM_ALIGNMENT.md) §4).
