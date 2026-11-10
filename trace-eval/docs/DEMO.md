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
`traceeval/catalog/features.yaml`,
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
coverage: 100% of the changed components exercised, 27% of the 15 affected properties checked, 17% of the 6 affected workflows run, 100% of the 3 affected features reached
invoked: 3 of 11 agents, 5 of 13 skills, 5 of 32 tools, 5 of 19 features
```

Live, the token counts can differ slightly from these, because decoding on the GPU server is nearly but not exactly
repeatable ([EXPERIMENT.md](EXPERIMENT.md) section 3). The tests and the verdict stay the same.

WF3-03 is the legal takedown in which the person refuses the approval. Without the rule, the orchestrator skips
the approval and sends the takedown to publishing. The dispatcher refuses the call because it carries no approval
token, so the pages stay up, and the test fails because no one was asked. The method needed three tests and one
percent of the suite's tokens.

Then a change that breaks nothing:

```bash
traceeval check benign_skill_prose_reflow --history runs/gemma5 --budget 0.2     # live
```

It ends with "no regression: the method is confident nothing broke" after nine tests and 4% of the suite's tokens,
with P(something broke) = 0.04. Before it ends, it has run a test of every mandatory property the change may
affect, because the catalog's `mandatory` flag acts as a stopping rule. The coverage lines in the output are the
change coverage the requirements ask for: changed components exercised, affected properties checked, affected
workflows run and affected features reached. The features are the unit the AEM team suggested: this change affects
three (publish, schedule, take a page down), and the nine tests reached all three.

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
  are agents, features, skills, tools, tool error paths, configuration, properties, workflows, execution paths
  and risk, each declared and observed, with what no test covers. Every feature has a test, but the tests reach
  only 13 of the 31 places where a tool refuses: a gap no other dimension shows. Below it, each agent, skill,
  tool and feature has the number of tests that declare it and the number that invoke it. The assets agent,
  for instance, is declared by 37 tests and invoked by 17, because the routing datasets stop at the hand-off.
  `traceeval coverage --history runs/gemma5` prints the same in the terminal.

Mention one finding: the mandatory-coverage rule is what catches `skill_publish_drop_link_validation`. Without
the rule, the method calls that change clean. With it, the method must test the mandatory "no broken publish"
property before stopping, and that test fails.

## 6. The catalog of properties, drafted by a model (1 minute)

`traceeval/catalog/properties.yaml` gives each property a category, how it is checked, a mandatory flag, a
threshold, and the components it comes from. The mandatory flag drives the method's last step, the threshold the
report's verdict per property, and the sources the map from a change to the properties it may affect
([AEM_ALIGNMENT.md](AEM_ALIGNMENT.md) §3.4). `traceeval properties draft` has a model write this catalog from the
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
- *Why only Gemma's numbers?* Qwen's recording of the same app is not a clean ground truth. Six of its tests answer
  differently when run 64 at a time than when run one at a time, so even a change that alters nothing appears to
  break them. A larger model does not automatically give a cleaner ground truth: some of Qwen's answers vary from
  run to run, and vLLM, the model server, has a switch for repeatable decoding that does not support Qwen3.8.
  gpt-oss-120b, a third model recorded on the re-planning branch, varies even more. The models are used as they are
  served. The lesson for Adobe is to measure first how much the answers vary under the real serving setup
  (RESEARCH_PLAN §5.4).
- *How would this run at Adobe?* Nightly full-suite runs provide the recordings the method learns from. For each
  change, `traceeval check` selects the tests, orders them and decides when to stop. The traces are
  OpenTelemetry, and the catalog of properties maps onto DeepEval's metrics.
- *What is next?* Re-planning after a failed step is built on a branch and recorded with three models. It waits for
  one decision: whether a single publication with a broken link is repaired or refused
  ([AEM_ALIGNMENT.md](AEM_ALIGNMENT.md) §4.1). Then tau2-bench, a public agent benchmark, as a second application.

## Questions for the AEM team

Their answers decide what comes next ([RESEARCH_PLAN.md](RESEARCH_PLAN.md) §9 keeps the list):

- Should a single publish request for a page with a broken link be repaired or refused? Re-planning waits for this
  answer ([AEM_ALIGNMENT.md](AEM_ALIGNMENT.md) §4.1).
- Is the diff available per pull request or per nightly batch, and are skills, prompts and settings versioned
  together with the harness code? The change sets assume one tree.
- Are the traces of the nightly runs kept: tool calls, skills loaded, settings read? The observed dependencies need
  one traced run per test.
- Which properties block a release, and which are judged by a model?
- Is a budget counted in tokens, in time or both, per change or per night? Is a partial run that ends with "nothing
  broke, with probability p" acceptable?

## The methods, one by one

Each strategy answers the same question, which tests to run on the changed app and in what order, from the same
inputs: the recording of the current app (traces, costs, pass rates) and the change set. None sees the ground
truth. The names are those of the report; the formulas are in [RESEARCH_PLAN.md](RESEARCH_PLAN.md) §3 and the paper
draft in `docs/paper/`.

- `full` runs the suite in catalog order, that is, as the tests are listed in `catalog/tests/*.yaml`, followed
  by the dataset items. It is the reference, not a method.
- `random` runs it in a random order, the baseline every method must beat.
- `declared` runs only the tests whose hand-written metadata names a changed component, riskiest first. This is
  classic regression test selection on what the authors declared, and the metadata is incomplete on purpose, as it
  is in practice.
- `ir_tfidf` ranks every test by how much its text (name, request, expectations) resembles the diff, with words
  weighted by TF-IDF so that a word every test uses counts little. It is information-retrieval prioritization, as
  in REPiR, and uses no traces.
- `observed` runs only the tests whose recorded traces touched a changed component (an agent, a skill, a tool, a
  setting read, a code line executed), ordered by how often they touched it times their risk, divided by cost. This
  is the trace-informed selection the project argues for.
- `cost_aware` ranks the whole suite by risk, closeness to the change, failure history and cost, affected tests
  first and cheap ones before expensive ones. It never stops early, so it always spends the budget.
- `casper_slices` reproduces CASPER. It groups the tests into slices that behave alike on the current app (tool
  calls, hand-offs, skills, size of the run), runs two representatives of every slice on the changed app, and then
  runs first the slices whose representatives failed more than before. It does not read the diff.
- `risk_aware_ts` reproduces Risk-Aware Adaptive Evaluation. It is a bandit: after each test it refits a model of
  which tests fail, draws a failure probability for every test still to run, and runs the one whose draw times its
  risk is highest. It does not read the diff either, and any failure counts as a find.
- `adaptive_bayes` is the proposed method. For every changed component it keeps the probability that the component
  is broken, and for every test the probability that the test fails if it is, calibrated on the other recorded
  changes and on the test's own record. It runs the test with the most information per token, updates after each
  outcome, stops at the first failure of a test that passed on the current app, or when the probability that
  anything is broken is small, and before ending without a regression it runs a test of every mandatory property
  the change may affect. It is the only strategy that stops, and the only one with a verdict.

## What the results say

A test reveals a change when it passes on the current app and fails on the changed copy, by majority over the three
runs of each; the revealing tests of a change are its ground truth, measured after the fact and never shown to a
strategy. The report compares the strategies on Gemma's recording: 29 regressions that at least one test reveals,
14 changes that none does (nine benign, five that Gemma cannot see), seven budgets from 2% to 100% of the suite's
tokens, five replay seeds.

- *Hand-written metadata is not enough.* `declared` tops out at 61% of the regressions however large the budget,
  because shared skills, harness code and most settings are reached without being declared. The traces recover
  that: `observed` reaches 86% at a 20% budget and everything at 100%.
- *The diff is worth a lot.* The two methods that ignore it, CASPER's slices and the bandit, find 50% and 59% at
  20%, close to a random order's 52%; the strategies that read it find 79% to 92%. Their first revealing test comes
  after 12% to 13% of the suite's tokens, against 2% to 6% for the change-aware strategies. The tests were written
  for the app, not for the changes, and the changes were written to resemble real regressions; which test reveals
  which change was measured afterwards, and no strategy is told.
- *Text alone is strong, but spends everything.* TF-IDF over the diff has the best detection at 20% (92%) and the
  best over the changes that break a safety property (98%), and it always spends the whole budget, on benign
  changes too. The adaptive method reaches 79% for 3% of the tokens, and 76% already at a 5% budget, where TF-IDF
  is at 70%.
- *Stopping is what saves tokens, and it has a price.* The adaptive method returns the budget: 3% of the suite
  spent on regressions, a tenth on benign changes at a 20% budget and a fifth at 100%. Its ceiling is 83%, because
  on a change that only one to five tests reveal it can become confident nothing broke before reaching them. The
  mandatory rule lowers that risk for the safety properties: before calling a change clean it tests every mandatory
  property the change may affect, for under one extra test per change, and on this app that is what catches the
  publishing skill without its link check.
- *Red tests on the current app mislead the others.* Six tests fail on the current app, Gemma's own mistakes, and
  fail on every changed copy too. A strategy that runs one sees a failure the change did not cause: on the 14
  changes no test reveals, this happens to `full` in 71% of its replays, to the bandit in 71%, to CASPER's slices
  in 57% and to the adaptive method in none, because it discounts a test by its failures on the current app and
  stops only on a test that used to pass.
- *The order is good, not only the stopping.* Read as a plain order with no stopping, the adaptive method has the
  highest cost-weighted APFD (0.81, against 0.53 for random and 0.76 to 0.79 for the other change-aware strategies)
  and the earliest first detection (1.7% of the suite's tokens).
- *Where the ground truth comes from.* Gemma's three runs agreed on all but five (change, test) pairs over the 43
  changes; Qwen's and gpt-oss's answers vary too much from run to run for the same majority rule, and five
  repetitions instead of three do not settle gpt-oss's vote, which is why only Gemma's numbers are reported.

## Take-aways

What the experiments say, in the order a team would act on them. The numbers are Gemma's, at a budget of 20% of the
suite's tokens unless said otherwise.

1. **Record traces; do not maintain a map.** Hand-written dependency metadata finds 61% of the regressions at any
   budget, because shared skills, harness code and settings are reached without being declared. Dependencies read
   from traces find 86%, and everything at 100%. One instrumentation of the agent runtime (the testbed exports
   OpenTelemetry spans) replaces a test-to-component map that nobody keeps current.
2. **Read the diff.** The strategies that use the change find 79% to 92% of the regressions; the two that do not,
   CASPER's slices and the risk-aware bandit, find 50% and 59%, near a random order's 52%, and their first
   revealing test comes after 12% to 13% of the suite's tokens instead of 2% to 6%.
3. **Stop when confident, with a safety net.** The adaptive method finds 79% for 3% of the tokens and returns the
   rest. Its ceiling is 83%: on a regression that one to five tests reveal it can stop too early. The mandatory
   rule covers the safety properties for under one extra test per change, and on this app catches the publishing
   skill without its link check, which the stopping rule alone misses. The catalog of properties is where that
   policy lives: whoever sets the mandatory flag decides what the pipeline never skips.
4. **Discount the tests the model already fails.** Six tests fail on the current app, and on every changed copy.
   On the 14 changes no test reveals, every other strategy reports a failure the change did not cause in 51% to
   91% of its replays; the adaptive method in none, because it keeps each test's pass rate on the current app and
   acts only on a flip. A pipeline should do the same rather than treat every red test as a regression.
5. **Measure the model's noise before trusting a verdict.** Gemma's three runs agree on every test of the current
   app and disagree on five (change, test) pairs over the 43 changes; Qwen's disagree on 260 and gpt-oss's on 577,
   both "reveal" every benign change, and five repetitions do not settle gpt-oss's vote. The baseline runs one
   test at a time and the changed copies in batches, and that alone flips some tests. An empty change, recorded
   like the others, measures the noise floor; record it per model and per serving setup.
6. **CASPER and the bandit have their place.** CASPER needs no diff: a model or provider update, or a prompt-level
   change in a system the team does not own. For AEM its representatives are the natural first pass after a model
   update, when every test is affected and the question is which behaviours drifted; its slices could also serve
   as the adaptive method's groups of near-duplicate tests. The bandit learns from the outcomes of earlier changes
   and from the tests it has run; with no history it has only the tests' risk to go on. The change-aware
   strategies cover edits to skills, code and settings; the two kinds combine.
7. **Text is a strong, cheap baseline.** TF-IDF similarity between the diff and the tests' text has the best
   detection when the whole budget is spent (92%, and 98% on the changes that break a safety property). It never
   stops, so it spends everything on benign changes too; it is the fallback order to keep in any pipeline.
8. **Not yet covered.** Real version history instead of mutants; a second system under test (tau2-bench); suites
   large enough for slicing to pay; re-planning after a failed step (recorded on a branch, awaiting the AEM team's
   decision); tuning the stopping threshold, the priors and the discount; time rather than tokens as the budget.
