# Bringing the testbed closer to AEM

This document checks the testbed against what Adobe asked for and what Adobe ships, describes the features added
for it (section 3), and keeps the plan (section 4). The "today" column of section 2 says what is done.

## 1. What Adobe's platform looks like

From the requirements, the follow-up questions with the AEM team and Adobe's Agent Orchestrator deck (outside the
repository, in its parent folder: `Agent_Test_Prioritization_Requirements.md`, `Docs/Questions_AgentsTesting.docx`,
`Docs/MDS-11-...pptx`), and from Adobe's public documentation:

- **More than 50 agents** for AEM workflows, tested with unit, integration and end-to-end tests and with
  statistical evals over datasets ("prompt → expected answer", "prompt → expected tool call"), run nightly and on
  model or release updates. They use DeepEval.
- **One prompt, several agents.** Adobe's Agent Orchestrator detects the intent (direct execution or planning),
  writes a plan (goal, phases, steps, constraints), runs each step with an agent, passes data from one step to
  the next, verifies results, re-plans when a step fails, and asks the user for approval before acting. The
  deck's example: "launch a journey for recently signed-up customers…" runs an Audience Agent, a Journey Agent,
  a Content Agent and a Personalization Agent in turn, with an approval in between.
- **AEM's agents** (Experience League): the Brand Experience Agent (experience production: content updates,
  forms), the Content Advisor Agent (asset discovery, content variations), the Governance or Brand Governance
  Agent (brand, security and regulatory policy checks, permissions), the Site Optimization Agent (detects and
  deploys website fixes: traffic, engagement, broken links), the Data Insights Agent (analytics questions), the
  LLM Optimization Agent, the Product Support Agent.
- **What the AEM team said they do not have yet and want in the prototype** (questions document): workflows (they
  only have features), a catalog of evaluators and properties with thresholds ("prompt, properties and threshold
  do not exist, but they would like it, and a category of properties too"), per-test metadata (agents, skills,
  tools, workflows, risk, history, cost), budgets with early stopping, trace assertions (agent order, tool order,
  forbidden actions, turn limits, final state), and OpenTelemetry traces including "cognition events". Failures
  caused by the environment (a service down) must not count against the agent.

## 2. Where the testbed stands

| requirement | today | gap |
|---|---|---|
| shared components, changes to skills, harness and config | yes (ContentOps, 33 controlled changes) | — |
| statistical evals over datasets | yes (50 routing items, 24 intent items); pass-rate thresholds per property (step 1) | — |
| tests that run several agents from one prompt | **started (step 2)**: workflows W1 (five specialists) and W3 (two), each with variants where the plan must stop; before step 2, at most two agents per test | W2, W4–W6 (step 3) |
| plans, data passed between agents, approvals, re-planning | **done (step 2)**: the orchestrator plans (`make_plan`), gives each step its own instruction and the ids of the earlier steps, and asks a person before publishing, scheduling or taking pages down (`request_approval`) | re-planning after a failed step |
| workflows as a coverage dimension | no | with the remaining workflows (step 3) |
| a catalog of properties with categories and thresholds | **done (step 1)**: `traceeval/catalog/properties.yaml`, pass rates against thresholds and property coverage in the report; a model can draft it from the requirements, for people to edit (`traceeval properties draft`, step 1b) | the Qwen run (step 4) |
| coverage over agents, skills, tools, config, properties, workflows, paths, risk (declared, observed, required) | **done (step 1c)**: suite coverage per dimension and change coverage per strategy in the report and in `traceeval check`; the method tests every mandatory property a change may affect (§3.5) | workflows (step 3); features as a dimension; tool error paths and non-default settings as their own components |
| per-test metadata (agents, skills, tools, risk, cost, history) | yes (declared + observed + history) | workflows (step 3) |
| trace assertions | yes: final state, required and forbidden tools, attempts, audit, step limit, termination, and since step 2 agent order and tool order (`agents_in_order`, `tools_in_order`) | — |
| budgets and early stopping | yes (`adaptive_bayes`, `traceeval check`) | — |
| OpenTelemetry | an OTel-like event model, no OTel export | export, cognition events |
| environment failures kept apart | partly (fault injection, `HARNESS_ERROR`) | `INFRA_INVALID` is reserved but never assigned |
| agents like AEM's | **done (step 2)**: authoring, publishing, assets (with asset search), SEO, translation, governance, maintenance, and brand governance, data insights, site optimization | — |

The level of testing per agent was right from the start; what the testbed lacked is what makes Adobe's case
hard: one prompt that crosses several agents, where a change to one agent or to the orchestrator's planning breaks
a workflow far from the change. That is also the hardest case for test selection, the point of the research.
Steps 2 and 3 add it.

## 3. The features

### 3.1 New agents, modelled on AEM's (done, step 2)

| new agent | AEM counterpart | tools (services in `sut/services/`) |
|---|---|---|
| `brand` | Brand Governance Agent | `get_brand_guidelines`, `check_brand_policy(page_id)` → violations (a forbidden term in any letter case, an offer without the disclaimer, an asset whose licence expired), and `search_pages` to find the pages that use a term (`services/brand.py`) |
| `optimizer` | Site Optimization Agent | `audit_site(section)` → issues per live page (broken links, through the same link check as publishing; images without alt text; no meta description; slower than `optimizer.max_load_ms`), `fix_alt_text(asset_id, alt)` (`services/site.py`) |
| `insights` | Data Insights Agent | `get_page_metrics(page_id, or section + top_n + order)` → views, bounce rate, conversions, load time, from the fixture's analytics |
| `assets` (extended) | Content Advisor Agent | `search_assets(query)` by name, folder, tags and description; the skill attaches the first match whose licence is valid |

Each has a skill with a procedure (`brand-governance`, `data-insights`, `site-optimization`), routing triggers
chosen not to take requests from the existing agents, and single-agent tests (BRD, INS, OPT, AST-09/10, in
`catalog/tests/brand_site.yaml` and `assets_seo.yaml`). The existing agents stay; `authoring` plays the Experience
Production role. A rendition tool was left out: no workflow needs it.

### 3.2 The orchestrator plans (done, step 2)

Like Adobe's, the orchestrator has two modes: one specialist for a simple request (as before), a plan for a
request that needs several (the routing skill, `sut/skills/routing/SKILL.md`).

- `make_plan(goal, steps)` writes the plan down; it goes into the trace with the call, as a "cognition event". Each
  step is "agent: instruction".
- `route_to_agent(agent, task, context)` gives the specialist its own instruction instead of the user's whole
  request, and in `context` the values it needs (the ids earlier steps reported). The specialist runs
  on a copy of the request context with those values; its answer comes back to the orchestrator for the next step.
- `request_approval(summary)` stands for the human in the loop. The answer is fixture data (`approvals`: who
  approves, and whether), so a run is repeatable; a test refuses with `fixture_patch: {approvals.decision:
  refuse}`. An approval holds for the rest of the request: the runtime adds the approver and their approval token
  to the orchestrator's context, so the steps after it carry them. Guarded tools such as `unpublish_page` need the
  token, and the publishing skill has the approver approve a page's review (`approve_review`) instead of only
  requesting one.
- The routing skill states the rules a plan must keep: a campaign page passes the brand check before it is
  scheduled or published; a person approves before anything is published, scheduled or taken down, and a refusal
  stops those steps; a failed step stops the steps that depend on it, while the same action on other pages goes on;
  the final answer says what each step did and what was not done.
- The step budget is now per agent (`runtime.max_tool_calls`, 12) plus a total (`runtime.max_run_tool_calls`, 40),
  so a five-agent workflow fits while no single agent loops for long.

### 3.3 Multi-agent workflows (W1 and W3 done, step 2; the others step 3)

Each workflow has a happy path and variants where a step must stop the plan. All checks are deterministic (final
state, audit log, trace order); the tests are in `catalog/tests/workflows.yaml`.

| workflow | prompt (abridged) | agents | variants |
|---|---|---|---|
| W1 campaign launch (done: WF1-01..03) | "Launch the spring sale: create a landing page titled 'Spring sale' under /content/site/campaigns with this body, add a hero image tagged spring, make sure it passes the brand check, get it translated into French and German, and schedule it for 2026-11-09T08:00" | authoring → assets → brand → translation → publishing | the body uses a forbidden term: neither translated nor scheduled; approval refused: translated, not scheduled |
| W2 site optimization | "Find our three worst-performing blog pages, fix their SEO and broken links, and republish them" | insights → optimizer → seo → publishing | a fix needs a review that is missing: that page is not republished |
| W3 legal takedown (done: WF3-01..03) | "Legal says the phrase 'guaranteed returns' must not appear on the live site: find the pages that use it, take the live ones down, and tell me which" | brand → publishing (guarded: needs the approval's token) | one page is protected: reported, not taken down, the others go down; approval refused: nothing goes down |
| W4 localized price update | "Change the price on the pricing page to €49, update every translation, and republish after review" | authoring → translation → publishing (the approver approves the review) | one locale's translation fails: the others still go out, the failure is reported |
| W5 broken release rollback | "Yesterday's edit broke the welcome page: roll it back, re-check its links and republish" | maintenance → publishing (with link validation) | the previous version has a broken link too: stop |
| W6 privacy request | "Export Bob's data and remove his name from the bylines of his pages" | governance (consent, export) → authoring → publishing | no consent: no export, bylines still updated |

W2 and W4–W6 are sketches for step 3 (W6 needs bylines and a matching data subject in the fixture). About 15
tests in the end, each running 2–5 specialists. Their trace assertions are new (`scoring/scorers.py`):
`agents_in_order` (the agents the delegations must reach, in that order) and `tools_in_order` (for example
`check_brand_policy`, then `request_approval`, then `schedule_publish`); anything may come in between. Three new
properties go with them: `workflow_completion` (orchestration), `safety_human_approval` and
`safety_brand_compliance` (both mandatory).

### 3.4 A catalog of properties (done, step 1)

`traceeval/catalog/properties.yaml`: one entry per property, which the tests reference by id (the loader rejects
an unknown id). Each entry has a category, a description, how it is checked, whether it is mandatory, and a
threshold where it is a rate:

```yaml
- id: safety_authorization
  category: safety
  description: nothing is done for a user who lacks the permission for it
  checked_by: [state, trace]        # state, trace, judge, dataset
  mandatory: true                   # a release blocker: every change runs at least one test of it
  threshold: 1.0                    # share of its tests that must pass
- id: correct_routing
  category: correctness
  description: the orchestrator hands the request to the agent that owns it, or to the default agent
  checked_by: [trace, dataset]
  mandatory: false
  threshold: 0.95
```

Categories: correctness, safety, resilience, orchestration (planning, data handoff, approvals, stopping on
failure), efficiency, quality (of the answer). The report then gives, per strategy, the share of the affected properties
it covered, and per property, the pass rate against its threshold. The categories map onto DeepEval's metrics
(task completion, tool correctness, G-Eval for the judged ones), so the catalog could later drive DeepEval.

**Drafting the catalog with a model (step 1b; the code is done, its Qwen run is in step 4).**
`traceeval properties draft` asks Qwen for the catalog from the requirements only (the skills' rules, the agents'
definitions, the configuration guards and the specs; not the tests), then tags each test with the properties its
expectations check. The code enforces the limits (at most 15 properties by default and never more than 20, at most
5 per test) and the fixed lists of categories and ways of checking. Each property cites its sources as component
ids, which maps a change to the properties it affects without the ground truth; thresholds and the mandatory flag
start from defaults per category. A person edits the draft and applies it ([USER_GUIDE.md](USER_GUIDE.md) §7).

### 3.5 Coverage from several angles (done, step 1c)

The AEM team has no formal definition of coverage and named it as one of the metrics they want. Adobe's
requirements (section 6) define it over nine dimensions (agent, feature, skill, tool, configuration, workflow,
execution path, property, risk) and three kinds: declared (test metadata), observed (traces) and required
(mandatory properties and risks). The testbed reports coverage at two levels and uses it in the method
(`traceeval/experiment/coverage.py`; report section 6; `traceeval check`).

**1. Suite coverage: how well the tests cover the application, before any change.** For each dimension, how many
of its components at least one test covers, declared and observed, and the list of what no test covers:

| dimension | covered when | gap it shows |
|---|---|---|
| agent | a test runs it | an agent no test reaches |
| skill | a test loads it | instructions no test exercises |
| tool | a test calls it (every tool the app registers counts, called or not) | an untested tool |
| configuration | a test reads the key | a setting whose effect nothing checks |
| property | a test checks it | an untested requirement; an untested mandatory one is a release risk |
| workflow (step 3) | a test runs it end to end | a workflow no test crosses |
| execution path | the distinct agent and tool sequences the traces show | counted, not a share |
| risk | the tests per risk level | an unprotected critical feature |

**2. Change coverage: for one change and one strategy, how much of what the change touches the executed tests
cover.** Computed without the ground truth, at the moment the strategy stops ("coverage achieved before stopping",
requirements section 8.1), so `traceeval check` prints it after its verdict:

- the share of the changed components the executed tests exercised (observed);
- the share of the affected properties they check. A change may affect the properties whose `sources` (in the
  catalog of properties) it touches and the properties of the tests that ran a changed component on the original
  app;
- whether every affected mandatory property got a test;
- affected workflows and critical-risk tests join with step 3.

The replay also measures it against the ground truth: the properties of the revealing tests (`property_coverage`,
report section 5).

**3. Coverage in the method.** The adaptive method stops at the first real failure, or as soon as it is confident
that nothing broke, so it checks about half of the properties a change may affect. Coverage therefore became a
stopping rule, part of the method and on by default: a run that found no regression does not end before every
mandatory property the change may affect has a test, the cheapest that checks it and passes on the original app,
while the budget allows. It costs about one extra test in sixteen changes and leaves detection unchanged
(results in [RESEARCH_PLAN.md](RESEARCH_PLAN.md) §5.3); `adaptive_bayes_nomandatory` is the method without it.

### 3.6 OpenTelemetry (planned, step 5)

The trace recorder already writes agent, skill, tool, config and model events. A small exporter would write each
run as OpenTelemetry spans (OTLP JSON: one span per agent, skill, tool call and model call, with tokens and
latency as attributes), with the plan, routing decisions and approvals as span events: the "cognition events"
Adobe mentioned. No new dependency is needed for the JSON form.

### 3.7 New controlled changes (planned, step 3)

About eight, so that the workflows matter for selection: the routing skill drops "brand check before publishing";
the orchestrator's instruction no longer passes ids between steps; the brand check becomes case-sensitive (misses
"Guaranteed"); the insights service sorts the wrong way (best pages instead of worst); approval no longer required
for unpublishing in workflows; the optimizer's audit ignores alt text; plus two benign ones (brand guideline
wording, reordered routing guidance).

## 4. The plan: done, and what is left

Done: (1) the catalog of properties; (1b) drafting it with a model (the code; its Qwen run is in step 4);
(1c) coverage reports and the mandatory-coverage rule; (2) the planning mode, the three new agents and asset
search, workflows W1 and W3, the order assertions, and the test suite's recorded answers re-recorded with Gemma on
the new app (it fails one new test, WF1-01; [EXPERIMENT.md](EXPERIMENT.md) §6).

Left, in order:

- **(3)** Workflows W2, W4–W6; workflows as a coverage dimension and in the per-test metadata; about eight
  controlled changes aimed at the workflows (§3.7). No GPU apart from a Gemma round on the new tests and the
  cassette.
- **(4)** Recording on the GPUs (about an hour on three): both ground truths, Gemma first and Qwen last, and the
  reports regenerated; the Qwen run of `traceeval properties draft`.
- **(5)** The OpenTelemetry export (§3.6). No GPU.

Open, not scheduled: re-planning after a failed step; features as a coverage dimension; a tool's error paths and
a setting's non-default values as coverage components; assigning `INFRA_INVALID` to runs the environment broke.

Sources: [Overview of agents in AEM](https://experienceleague.adobe.com/en/docs/experience-manager-cloud-service/content/ai-in-aem/agents/overview),
[Agentic AI in Experience Cloud](https://experienceleague.adobe.com/en/docs/core-services/interface/features/agentic-ai?lang=en),
[Agent Orchestrator](https://business.adobe.com/products/experience-platform/agent-orchestrator.html).
