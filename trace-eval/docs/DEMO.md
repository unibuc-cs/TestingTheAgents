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
ls runs/gemma7/history runs/gemma7/variants   # the recording and the changed copies the live check needs
```

Open these in the editor: `docs/CONTENTOPS.md` (the figure), `traceeval/catalog/tests/publishing.yaml` (PUB-01),
`traceeval/catalog/tests/workflows.yaml` (WF3-01), `traceeval/catalog/properties.yaml`,
`traceeval/catalog/features.yaml`,
`docs/results/gemma7/report.md` and its figures, and `docs/sdd/report.md`.

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
cat runs/gemma7/variants/skill_routing_drop_approval/diff.patch
traceeval check skill_routing_drop_approval --history runs/gemma7 --budget 0.2     # live
```

The change removes one rule from the orchestrator's routing skill: ask a person before a step that publishes,
schedules or takes pages down. It edits the prose of a skill that every request reads, so it touches every test,
and nothing in the code changes.

While it runs, narrate what the method does:

- it reads the change set (`skill:routing#prose`) and weighs every test by its sensitivity to that component,
  calibrated on the other recorded changes;
- it runs the most informative test per token first and updates after each outcome;
- it stops at the first failure of a test that passed on the original app.

The loop is pictured in [USER_GUIDE.md](USER_GUIDE.md) §5, which can stay open on screen.

What the check prints:

```text
skill_routing_drop_approval: changed skill:routing#prose
  DS-ROUTING/r41         pass                                       3,935 tokens
  WF3-03                 FAIL required:request_approval,response~not approved,tool_error:unpublish_page  19,161 tokens
REGRESSION: WF3-03 failed
2 runs, 23,096 tokens (1% of the suite), 16 s (the whole suite takes about 375 s, one test at a time); P(something broke) = 1.00
coverage: 100% of the changed components exercised, 20% of the 15 affected properties checked, 17% of the 6 affected workflows run, 100% of the 3 affected features reached
... then what the tests invoked, the properties left unchecked and the workflows not run
```

Live, the token counts can differ slightly from these, because decoding on the GPU server is nearly but not exactly
repeatable ([EXPERIMENT.md](EXPERIMENT.md) §3). The tests and the verdict stay the same.

WF3-03 is the legal takedown in which the person refuses the approval. Without the rule, the orchestrator skips
the approval and sends the takedown to publishing. The dispatcher refuses the call because it carries no approval
token, so the pages stay up, and the test fails because no one was asked. The method needed two tests and one
percent of the suite's tokens.

Then a change that breaks nothing:

```bash
traceeval check benign_skill_prose_reflow --history runs/gemma7 --budget 0.2     # live
```

It ends with "no regression: the method is confident nothing broke" after nine tests and 4% of the suite's tokens,
with P(something broke) = 0.05. Before it ends, it has run a test of every mandatory property the change may
affect, because the catalog's `mandatory` flag acts as a stopping rule. The coverage lines are the change coverage
of [AEM_ALIGNMENT.md](AEM_ALIGNMENT.md) §3.5. The features are the unit the AEM team suggested: this change affects
three (publish, schedule, take a page down), and the nine tests reached all three.

If the GPU server is down, run both checks with `--backend replay`: both are recorded in
`tests/cassettes/gemma.jsonl` ([EXPERIMENT.md](EXPERIMENT.md) §5), so the same tests run with the same outcomes,
and the timings read 0 seconds. If the server stops answering during a check, the check says so and gives no
verdict. The run is marked `INFRA_INVALID`, the environment's fault rather than the change's.

If there is time, a day's merges at once, which is how the AEM team runs their tests. `batch_nightly` bundles six
regressions and two harmless edits (`traceeval mutations` lists its members); the check stops at the first failure
and names the member it blames:

```bash
traceeval check batch_nightly --history runs/gemma7 --budget 0.2     # live only: not in the cassette
```

```text
  SEO-06                 FAIL ...                                    6,136 tokens
REGRESSION: SEO-06 failed
1 runs, 6,136 tokens (0% of the suite), 13 s ...; P(something broke) = 1.00
blamed: agent:seo.tools 0.77, code:tools/content_tools.py::set_page_metadata 0.55, ...
```

The SEO agent's lost tool is the culprit; the other members stay near their prior of one half, untested.
[RESEARCH_PLAN.md](RESEARCH_PLAN.md) §5.6 has the three batches, including the nine harmless edits that break a
test together, and the twenty batches of two to eight changes drawn at random, on which the size makes no
difference and the blame falls on a member that is a regression on its own every time.

## 5. The evidence over all changes (4 minutes)

Open `docs/results/gemma7/report.md`, the replay of every strategy on every change, from the recording of the
current app ([USER_GUIDE.md](USER_GUIDE.md) §4 says how to read it):

- Section 1, the ground truth: 29 of the 34 regressions are revealed and no benign change fails a test; the five
  Gemma cannot see are in [EXPERIMENT.md](EXPERIMENT.md) §7.
- Section 2 and `figures/detection_vs_cost.png`: detection against the tokens actually spent. At a 20% budget,
  hand-written dependencies find 62% of the regressions, traces 86%, TF-IDF 93%, and the adaptive method 78% for 3%
  of the tokens, which puts it at the left of the figure; it catches 84% of the changes that break a safety
  property.
- Section 3: the tokens spent on the changes no test reveals, and why the adaptive method stopped; it never calls
  one of them a regression.
- Section 5: the catalog of properties, with each property's pass rate against its threshold.
- Section 6: the coverage of [AEM_ALIGNMENT.md](AEM_ALIGNMENT.md) §3.5. Point at the `not covered` column (the
  tests reach 15 of the 31 places where a tool refuses) and at one declared-against-invoked gap. `traceeval
  coverage --history runs/gemma7` prints the same in the terminal.

Mention the finding of [RESEARCH_PLAN.md](RESEARCH_PLAN.md) §5.3: the mandatory rule is what catches the publishing
skill without its link check. Its §5.1 goes through the results by research question, and §5.5 has the take-aways.

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
  link check failed (WF5-02) and stops a whole plan after a refused export (WF6-02); [EXPERIMENT.md](EXPERIMENT.md)
  §6 lists them. A test the model already fails cannot reveal a change, which is why the method discounts it.
- *Why only Gemma's numbers?* Qwen's and gpt-oss's recordings of the same app are not clean ground truths
  ([RESEARCH_PLAN.md](RESEARCH_PLAN.md) §5.4): recorded many tests at once, a change that alters nothing appears to
  break a few tests. Recorded one test at a time, Qwen is as repeatable as Gemma; gpt-oss is not, and its outcomes
  change with a restart of the server. A larger model does not automatically give a cleaner ground truth, and the
  lesson for Adobe is to measure first how much the answers vary under the real serving setup.
- *How would this run at Adobe?* Nightly full-suite runs provide the recordings the method learns from. For each
  change, `traceeval check` selects the tests, orders them and decides when to stop. The traces are OpenTelemetry,
  and the catalog of properties maps onto the metrics of DeepEval, the evaluation library the AEM team uses.
- *Does the replay predict the live run?* Yes: run live on all 43 changes, the check gives the replayed verdict on
  42, with the same tests and tokens. The exception is a live false alarm on a benign change, the one-off
  difference in the model's answer that [EXPERIMENT.md](EXPERIMENT.md) §3 describes; recorded five more times one
  test at a time, the change does not repeat it, and the live check reads one run where the replay reads five. On
  twenty batches of changes drawn at random, the live verdict is the replay's on 19.
- *What is next?* Re-planning after a failed step is built on a branch and recorded with three models. It waits for
  one decision: whether a single publication with a broken link is repaired or refused
  ([AEM_ALIGNMENT.md](AEM_ALIGNMENT.md) §4.1). Then tau2-bench, a public agent benchmark, as a second application.

## Questions for the AEM team

Close with the questions for the AEM team, the re-planning decision first: should a single publish request for a
page with a broken link be repaired or refused? [RESEARCH_PLAN.md](RESEARCH_PLAN.md) §8 keeps the list, with what
each answer decides.
