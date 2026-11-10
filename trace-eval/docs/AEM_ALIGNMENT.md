# The testbed against AEM's requirements

This document checks the testbed against what Adobe asked for and what Adobe ships, describes the features built
for it (section 3), and plans the next steps (section 4). The "today" column of section 2 says what is done.

## 1. What Adobe's platform looks like

From Adobe's requirements, the AEM team's written answers to our questions about their test practice, Adobe's
Agent Orchestrator deck and Adobe's public documentation:

- **More than 50 agents** for AEM workflows, tested with unit, integration and end-to-end tests and with
  statistical evals over datasets ("prompt → expected answer", "prompt → expected tool call"), run nightly and on
  model or release updates. They use DeepEval, an open-source LLM evaluation framework.
- **One prompt, several agents.** Adobe's Agent Orchestrator detects the intent (direct execution or planning),
  writes a plan (goal, phases, steps, constraints), runs each step with an agent, passes data from one step to
  the next, verifies results, re-plans when a step fails, and asks the user for approval before acting. The
  deck's example: "launch a journey for recently signed-up customers…" runs an Audience Agent, a Journey Agent,
  a Content Agent and a Personalization Agent in turn, with an approval in between.
- **AEM's agents** (Experience League, Adobe's documentation site): the Brand Experience Agent (experience
  production: content updates, forms), the Content Advisor Agent (asset discovery, content variations), the
  Governance or Brand Governance Agent (brand, security and regulatory policy checks, permissions), the Site
  Optimization Agent (detects and deploys website fixes: traffic, engagement, broken links), the Data Insights
  Agent (analytics questions), the LLM Optimization Agent, the Product Support Agent.
- **What the AEM team said they do not have yet and want in the prototype** (the AEM team's answers to the
  follow-up questions): workflows (they only have features), a catalog of evaluators and properties with thresholds
  ("prompt, properties and threshold do not exist, but they would like it, and a category of properties too"),
  per-test metadata (agents, skills, tools, workflows, risk, history, cost), budgets with early stopping, trace
  assertions (agent order, tool order, forbidden actions, turn limits, final state), and OpenTelemetry traces
  including "cognition events". Failures caused by the environment (a service down) must not count against the
  agent.

## 2. Where the testbed stands

| requirement | today | gap |
|---|---|---|
| shared components, changes to skills, harness and config | yes (ContentOps, 43 controlled changes, ten of them aimed at the workflows) | — |
| statistical evals over datasets | yes (50 routing items, 24 intent items); pass-rate thresholds per property | — |
| tests that run several agents from one prompt | yes: six workflows of two to five specialists (§3.3), each with a variant where a step must stop | — |
| plans, data passed between agents, approvals, re-planning | yes: the orchestrator plans (`make_plan`), gives each step its own instruction and the ids of the earlier steps, and asks a person before publishing, scheduling or taking pages down (`request_approval`) | re-planning after a failed step: our routing skill says stop; Qwen re-plans on its own (WF1-02, WF5-02; [EXPERIMENT.md](EXPERIMENT.md) §6). Built on a branch and recorded with three models (§4.1) |
| workflows as a coverage dimension | yes: `catalog/workflows.yaml` lists the six; suite and change coverage count them (§3.5) | — |
| a catalog of properties with categories and thresholds | yes: `traceeval/catalog/properties.yaml`, pass rates against thresholds and property coverage in the report; a model can draft it from the requirements, for people to edit (`traceeval properties draft`; Qwen's draft in §3.4) | — |
| coverage over the requirements' dimensions, declared, observed and required | yes: suite coverage per dimension and change coverage per strategy in the report and in `traceeval check`; the method tests every mandatory property a change may affect (§3.5) | — |
| per-test metadata (agents, skills, tools, workflow, risk, cost, history) | yes (declared + observed + history; a workflow test names its workflow) | — |
| trace assertions | yes: final state, required and forbidden tools, attempts, audit, step limit, termination, agent order and tool order (`agents_in_order`, `tools_in_order`) | — |
| budgets and early stopping | yes (`adaptive_bayes`, `traceeval check`) | — |
| OpenTelemetry | yes: `traceeval run --otel` exports a run as OTLP JSON spans, with the plan, the routing decisions and the approvals as span events (§3.6) | pushing to a collector, if wanted |
| environment failures kept apart | yes: such a run is `INFRA_INVALID` and left out of pass rates, the ground truth and the replays ([USER_GUIDE.md](USER_GUIDE.md) §8) | — |
| agents like AEM's | yes: authoring, publishing, assets (with asset search), SEO, translation, governance, maintenance, and brand governance, data insights, site optimization | — |

Testing one agent at a time is the easy part. What makes Adobe's case hard is one prompt that crosses several
agents, where a change to one agent or to the orchestrator's planning breaks a workflow far from the change. That
is also the hardest case for test selection, the point of the research, and the reason for the workflows of
section 3.3.

## 3. The features

All of them are in the testbed and in the recordings.

### 3.1 Agents modelled on AEM's

| agent | AEM counterpart | tools (services in `sut/services/`) |
|---|---|---|
| `brand` | Brand Governance Agent | `get_brand_guidelines`, `check_brand_policy(page_id)` → violations (a forbidden term in any letter case, an offer without the disclaimer, an asset whose licence expired), and `search_pages` to find the pages that use a term (`services/brand.py`, `services/repository.py`) |
| `optimizer` | Site Optimization Agent | `audit_site(section)` → issues per live page (broken links, through the same link check as publishing; images without alt text; no meta description; slower than `optimizer.max_load_ms`), `fix_alt_text(asset_id, alt)` (`services/site.py`, `services/repository.py`) |
| `insights` | Data Insights Agent | `get_page_metrics(page_id, or section + top_n + order)` → views, bounce rate, conversions, load time, from the fixture's analytics |
| `assets` (extended) | Content Advisor Agent | `search_assets(query)` by name, folder, tags and description; the skill attaches the first match whose licence is valid |

Each has a skill with a procedure (`brand-governance`, `data-insights`, `site-optimization`), routing triggers
chosen not to take requests from the existing agents, and single-agent tests (BRD, INS, OPT, AST-09/10, in
`catalog/tests/brand_site.yaml` and `assets_seo.yaml`).

### 3.2 The orchestrator plans

Like Adobe's, the orchestrator has two modes: one specialist for a simple request, a plan for a request that
needs several (the routing skill, `sut/skills/routing/SKILL.md`). A plan, step by step:

```mermaid
sequenceDiagram
    participant U as User
    participant O as Orchestrator
    participant A as Specialist
    participant P as Person (approver)
    participant B as Next specialist
    U->>O: a request that needs several specialists
    O->>O: make_plan(goal, steps)
    O->>A: route_to_agent(its own instruction)
    A-->>O: answer, with the ids it produced
    O->>P: request_approval(summary)
    P-->>O: approved, with a token, or refused
    O->>B: route_to_agent(instruction, context: the ids and the token)
    B-->>O: answer
    O-->>U: what each step did, and what was not done
```

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
- The step budget is per agent (`runtime.max_tool_calls`, 12) plus a total (`runtime.max_run_tool_calls`, 40),
  so a five-agent workflow fits while no single agent loops for long.

### 3.3 Multi-agent workflows

Each workflow has a happy path and variants where a step must stop the plan. All checks are deterministic (final
state, audit log, trace order); the tests are in `catalog/tests/workflows.yaml`.

| workflow | prompt (abridged) | agents | variants |
|---|---|---|---|
| W1 campaign launch (WF1-01..03) | "Launch the spring sale: create a landing page titled 'Spring sale' under /content/site/campaigns with this body, add a hero image tagged spring, make sure it passes the brand check, get it translated into French and German, and schedule it for 2026-11-09T08:00" | authoring → assets → brand → translation → publishing | the body uses a forbidden term: neither translated nor scheduled; approval refused: translated, not scheduled |
| W2 site optimization (WF2-01..03) | "Find the three worst-performing pages of our blog, run a health check of the blog section, fix their SEO (a page without a meta description gets its title as its description), and republish all three" | insights → optimizer → seo → publishing | one of the three pages has a broken link: publishing refuses it, the other two go out, and the answer names it (WF2-02, the broken page last); the same with the broken page first |
| W3 legal takedown (WF3-01..03) | "Legal says the phrase 'guaranteed returns' must not appear on the live site: find the pages that use it, take the live ones down, and tell me which" | brand → publishing (guarded: needs the approval's token) | one page is protected: reported, not taken down, the others go down; approval refused: nothing goes down |
| W4 localized price update (WF4-01..02) | "Change the price on the pricing page to €49 (the new body given), update every translation, one job per language, and republish after review" | authoring → translation → publishing (the approver approves the review the edit withdrew) | one language is one the platform does not translate into: its job is refused, the other two are queued, the page still goes out and the answer names the language |
| W5 broken release rollback (WF5-01..02) | "Yesterday's edit broke the welcome page (p22): roll it back to version 1 and republish it" (the rollback re-checks the links itself) | maintenance → publishing (the approver approves the review before the republish) | the previous version has a broken link too: the plan stops before publishing |
| W6 privacy request (WF6-01..02) | "Privacy request from Sam Lee (data subject s1): export his personal data and remove his name from the bylines of his two blog posts, then republish both pages" (the request gives the bodies without the byline) | governance (consent, export) → authoring → publishing | no consent: no export, the bylines are still removed and the pages republished |

Fifteen tests in all, each running two to five specialists, with `agents_in_order` and `tools_in_order` as their
trace assertions ([USER_GUIDE.md](USER_GUIDE.md) §7) and three properties: `workflow_completion` (orchestration),
`safety_human_approval` and `safety_brand_compliance` (both mandatory). Gemma fails WF2-03, WF5-02 and WF6-02 on
the original app ([EXPERIMENT.md](EXPERIMENT.md) §6).

### 3.4 A catalog of properties

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
failure), efficiency, quality (of the answer). The categories map onto DeepEval's metrics (task completion, tool
correctness, G-Eval for the judged ones), so the catalog can drive DeepEval. What each field means and
where the testbed uses it:

| field | meaning | used by |
|---|---|---|
| `category` | the kind of requirement, one of the six above | the report, which groups by it; `properties draft`, which takes a new property's mandatory flag and threshold from it (safety: mandatory, 1.0) |
| `description` | the requirement in one sentence | people, and the model that tags the tests |
| `checked_by` | how its tests verify it: `state` (the final application state), `trace` (tool calls, agents, audit, steps), `judge` (a model reads the answer against a rubric), `dataset` (prompt → expected item) | documentation of the oracle; `properties draft` accepts only these values |
| `mandatory` | a release blocker | the adaptive method's last step: before calling a change clean it runs a test of every mandatory property the change may affect (§3.5); `traceeval check`, which names the affected properties left unchecked; the report, which counts the runs that covered them |
| `threshold` | the share of its tests that must pass on the current app for the property to count as met | the report's section 5: the mean pass rate of its tests over the recorded runs, against the threshold; the safety properties require 1.0 |
| `sources` | the components that state the requirement, as component ids (`skill:<name>#procedure`, `agent:<name>.<field>`, `config:<key>`, `spec:<id>`) | the map from a change to the properties it may affect: a property one of whose sources the change set touches, plus the properties of the tests whose traces reached a changed component |

Where the catalog comes from, and where each field goes:

```mermaid
flowchart LR
    REQ["requirements: the skills' rules,<br/>agent definitions, config guards, specs"] -->|"traceeval properties draft"| DR["draft catalog and tags,<br/>by a model within fixed limits"]
    DR -->|"a person edits"| APP["traceeval properties apply"]
    HAND["entries written by hand"] --> CAT["catalog of properties<br/>properties.yaml"]
    APP --> CAT
    CAT -->|"ids"| TESTS["each test lists the<br/>properties it checks"]
    CAT -->|"threshold"| REP["report: pass rate per property<br/>against its threshold"]
    CAT -->|"sources"| AFF["the properties a<br/>change may affect"]
    AFF -->|"mandatory"| MET["adaptive method: before clean,<br/>test every affected mandatory property"]
    AFF --> CHK["traceeval check: affected<br/>properties left unchecked"]
```

**Drafting the catalog with a model.** A model can draft the catalog from the requirements only, within fixed
limits, for a person to edit and apply ([USER_GUIDE.md](USER_GUIDE.md) §7).

Qwen's draft from the requirements alone (`--fresh`) is in [properties/draft_qwen/](properties/draft_qwen/), with
its answers, so `traceeval properties draft --fresh --replay docs/properties/draft_qwen/answers.json` reproduces it
without a model. The catalog is good: fifteen properties, each traced to the skill, configuration key or spec that
states it, nine of them safety properties and so mandatory, and finer-grained than the hand-written catalog (the
review gate, the asset licence, the SEO title limit and the default languages are properties of their own). It also
finds a requirement no test checks: the 30-day approval window, which only spec FS-0101 states, since that feature
is not built. The tags are weaker: 38 of the 104 cases the draft was made on get only the routing property,
because every request passes the orchestrator, while 32 of the 36 that the hand-written tags mark as checking a
mandatory property get one too. Asked to extend the existing catalog instead, Qwen keeps its fifteen properties,
adds sources to three, and tags 86 of its 104 with `correct_routing`, finding only 19 of those 36. The model is a
good first author of the catalog; the tags need the person's review the workflow already asks for.

### 3.5 Coverage from several angles

The AEM team has no formal definition of coverage and named it as one of the metrics they want. Adobe's
requirements name nine dimensions (agent, feature, skill, tool, configuration, workflow, execution path, property,
risk) and three kinds: declared (test metadata), observed (traces) and required (mandatory properties and risks);
the testbed adds tool error paths and setting values, eleven in all. The testbed reports coverage at two levels and
uses it in the method (`traceeval/experiment/coverage.py`; report section 6; `traceeval check`).

**1. Suite coverage: how well the tests cover the application, before any change.** For each dimension, how many
of its components at least one test covers, declared and observed, and the list of what no test covers:

| dimension | covered when | gap it shows |
|---|---|---|
| agent | a test runs it | an agent no test reaches |
| feature | a test declares or calls one of its tools (`catalog/features.yaml` lists 19, each with its tools and the skills, agents, settings and code it is made of) | a capability the user sees that no test exercises; the report also counts the tests per feature, which shows the thinly tested ones |
| skill | a test loads it | instructions no test exercises |
| tool | a test calls it (every tool the app registers counts, called or not) | an untested tool |
| tool error path | a run executes it. An error path is a place in the code where a tool call is refused: a `raise` of one of the errors of `sut/services/errors.py`, or an error result the dispatcher writes out. The testbed finds them by scanning the code, not by running it | a refusal no test provokes |
| configuration | a test reads the key | a setting whose effect nothing checks |
| setting value | a case runs with the setting at a value other than its default (its `config:` block: declared) and its recorded run reads the setting (observed). The values are the other value of each on/off setting and every value a case sets | a setting whose other value nothing checks |
| property | a test checks it | an untested requirement; an untested mandatory one is a release risk |
| workflow | a test names it (declared), or a recorded run delegates to exactly its agents in order (observed) | a workflow no test runs |
| execution path | the distinct agent and tool sequences the traces show | counted, not a share |
| risk | the tests per risk level | an unprotected critical feature |

On Gemma's recording every feature has a test; the thinnest are the site health check (five tests), then
scheduling, page analytics and rollback (six each). The tests reach 15 of the 31 places where a tool refuses. No
test asks for the data of a person the platform does not know, has a service refuse a user for a missing role, or
sends the dispatcher an unknown tool or malformed arguments.

Every test runs with the default settings unless it sets its own. Three cases do (`catalog/tests/settings.yaml`):
publishing without a required review, scheduling switched off, and the link check switched off. They cover three of
the five settings at a non-default value; no case runs with idempotency keys or the required meta description
switched off.

The report, and `traceeval coverage --history runs/gemma7` in the terminal, also give for each agent, skill, tool
and feature the number of tests that declare it and the number that invoke it. On Gemma's recording the two counts
disagree in telling ways. The routing datasets name the agent a request should go to, but only the hand-off runs,
so the assets agent is declared by 37 tests and invoked by 17. The `governance-checks` skill, which every
specialist loads, is invoked in 120 tests and declared by none. `get_asset` is invoked by none.

**2. Change coverage: for one change and one strategy, how much of what the change touches the executed tests
cover.** Computed without the ground truth, at the moment the strategy stops (the requirements' "coverage achieved
before stopping"), so `traceeval check` prints it after its verdict:

- the share of the changed components the executed tests exercised (observed);
- the share of the affected properties they check. A change may affect the properties whose `sources` (in the
  catalog of properties) it touches and the properties of the tests that ran a changed component on the original
  app;
- whether every affected mandatory property got a test;
- the share of the affected workflows (those of the tests that exercised a changed component) the executed tests
  ran;
- the share of the affected features they reached. A change affects the features with a tool or a part it
  touches; 35 of the 43 changes affect one. A change to code that every feature runs through, such as the agent
  loop or the retries, affects none in particular;
- the share of the refusals in the changed code they reached, for a change to a function that can refuse a tool
  call. `traceeval check` names the ones no executed test reached.

`traceeval check` also prints what its tests invoked, out of what the application has ("invoked: 2 of 11 agents, 2
of 13 skills, 4 of 32 tools, 4 of 19 features").

On Gemma's recording, at a budget of 20% of the suite's tokens, the tests the adaptive method runs reach 89% of the
affected features: it stops once it is confident. The trace-based strategy (`observed`) reaches all of them, for
five times the tokens.

The replay also measures it against the ground truth: the properties of the revealing tests (`property_coverage`,
report section 5).

**3. Coverage in the method.** The mandatory flag is also a stopping rule (the `mandatory` row of §3.4): the method
tests every affected mandatory property before it calls a change clean, for under one extra test per change
([RESEARCH_PLAN.md](RESEARCH_PLAN.md) §5.3); `adaptive_bayes_nomandatory` is the method without it.

### 3.6 OpenTelemetry export

`traceeval run --test <id> --otel trace.json` writes the run's trace as OpenTelemetry spans in OTLP JSON, the
form an OpenTelemetry collector accepts on `/v1/traces` (`traceeval/tracing/otel.py`, without a dependency). The
root span covers the run (test, run id, variant, backend, termination, steps, token totals). Under it, each
agent turn is an `invoke_agent` span, nested by delegation, and each tool call (`execute_tool`), model call
(`chat`, with its tokens) and skill load (`load_skill`, with name, version and digest) is a child of the agent
turn that made it. Names and attributes follow the OpenTelemetry GenAI semantic conventions where they apply
(`gen_ai.operation.name`, `gen_ai.agent.name`, `gen_ai.tool.name`, `gen_ai.usage.*`, `error.type`); the rest
are under `traceeval.*`. The "cognition events" Adobe mentioned are span events on the agent span: `plan` (the
goal and steps of a `make_plan` call), `route` (each delegation with its target, task, status and reason),
`approval` (whether the step was approved, and by whom) and `consult` (the specialist definitions the
orchestrator read to choose). A refused tool call carries `error.type`; a crashed one also has status ERROR.
Span and trace ids are derived from the run id and the event index, so the same run always exports the same
ids.

### 3.7 Controlled changes aimed at the workflows

Ten changes, so that the workflows matter for selection: eight regressions and two benign ones, each checked under
Gemma ([USER_GUIDE.md](USER_GUIDE.md) §6 lists them with the tests that reveal each). The orchestrator's approval
rule, removed from the routing skill, is revealed by eleven tests, in four of the six workflows (W1 to W4); the
brand gate and the hand-off of ids between steps by the W1 and W2 tests; the insights ranking and the page search
by their single-agent tests and by W2 and W3. Three regressions are revealed by no workflow test although a
workflow runs the changed code (the audit's alt-text rule, the brand check's letter case, the approval gate on
taking pages down): covering a change is not revealing it, the case the method is built for.

## 4. Next steps

The demo for the AEM team shows the testbed, the features of section 3 and the method on Gemma's recording, with
one change checked live ([DEMO.md](DEMO.md)). The questions for the AEM team close the walkthrough. One item of
section 2 is open: re-planning after a failed step. It is built and recorded on a branch, and waits for one product
decision (§4.1).

### 4.1 Re-planning after a failed step

Adobe's orchestrator re-plans when a step fails. Ours stops: the routing skill's rule is that a failed step stops
the steps that depend on it. Re-planning is built on the branch `replanning` and recorded there with three models
(three repetitions each): Gemma, Qwen and gpt-oss-120b. The application in the demo does not have it.

- **What may be re-planned.** Broken links only: the one failure another specialist can repair without changing
  what the user asked for. The optimizer unlinks them with a tool of its own, `fix_broken_links`, which checks the
  permission to edit and writes an audit entry. A refusal stays a stop: a refused approval, a brand or policy
  violation, a missing permission or consent. Re-planning must never route around a safety check.
- **How.** When publishing refuses a page for broken links, or a rollback's link check fails, the orchestrator
calls `make_plan` again, with the repair before the publication, and runs it (a rule of the branch's routing
skill). A setting limits the number of new plans (`routing.max_replans`, 1), and `make_plan` refuses a plan beyond
it, so the limit holds even when the model ignores it. Every plan is in the trace and is a `plan` event in the
OpenTelemetry export.
- **Tests and changes.** The branch adds a `replans` expectation (the number of `make_plan` calls after the first),
  a property `orchestration_replanning`, three repair cases (WF5-02, WF2-02 and WF2-03), a case with re-planning
  switched off (WF5-03) and five controlled changes: four regressions, which Gemma and Qwen each reveal, and one
  benign rewording of the rule.

What the recordings show:

| case | expected | Gemma | Qwen | gpt-oss |
|---|---|---|---|---|
| WF5-02 | the restored page has a broken link: a new plan fixes it and republishes the page | re-plans | re-plans | stops |
| WF5-03 | the same with re-planning switched off: the run stops and names the link | right | right | right |
| WF2-02 | one of three pages is refused for a broken link: a new plan fixes it and publishes it | does not re-plan | re-plans | does not re-plan |
| WF2-03 | the same, with the broken page ranked first | fails | fails | fails |
| OPT-04 | the links of a page fixed, the page not published | publishes it | right | right |
| WF1-02, WF1-03, WF3-03 | a refusal stays a stop, without a new plan | WF3-03 fails | right | WF1-03 and WF3-03 fail |
| PUB-02, PUB-03, PUB-21 | one page to publish, with a broken link: refused, the link named | right | fixed and published | fixed and published (PUB-02, PUB-03) |

- **Whether the orchestrator re-plans depends on the model more than on the rule.** Qwen follows the rule inside
  plans, Gemma only after a rollback, and gpt-oss not at all. The limit holds under all three, because `make_plan`
  enforces it.
- **The rule changes cases it does not concern.** Under Gemma, the three W3 cases fail on the branch (it takes the
  pages down without the approval), and AUT-02/03 pass in two runs of three, which is enough for some benign
  changes to appear to break them. Every wording of the rule moves some case of this kind.
- **Qwen and gpt-oss also repair a single publication.** The rule does not limit re-planning to plans. Asked to
  publish one page that has a broken link, they have the link removed and publish the page, where PUB-02, PUB-03
  and PUB-21 expect a refusal that names the link. Whether a single request should be repaired or refused is a
  product decision. If repaired, these become repair cases; if refused, the rule needs a limit that Gemma follows
  too, and the wording "in a plan" broke the W3 cases under Gemma.

The branch is merged after the demo, once that decision is made. Gemma's known mistakes change with it, and the
replay answers are recorded again.

gpt-oss-120b varies more from run to run than the other two models ([RESEARCH_PLAN.md](RESEARCH_PLAN.md) §5.4),
so its column is the least firm.

### 4.2 Order

| step | changes the application | new recording | when |
|---|---|---|---|
| re-planning after a failed step | yes: the routing skill, one setting, `make_plan`, a repair tool | recorded on the branch with three models; recorded again with Gemma once merged | after the demo, once single publications are decided |
| tau2-bench as a second application | no | its own | after re-planning |

### 4.3 Limits

Three limits go with the results. Some tests fail under Gemma on the original app, the model's own mistakes
([EXPERIMENT.md](EXPERIMENT.md) §6), so they cannot reveal a change; WF2-03 among them, which replays in the demo
([DEMO.md](DEMO.md) §3). A one-off difference between runs can make a benign change look revealed or a regression
look invisible, which the report's sanity line shows as VIOLATED; several repetitions and the majority vote absorb
most of it ([RESEARCH_PLAN.md](RESEARCH_PLAN.md) §5.4). And the ground truth belongs to the model: Qwen gets some
of Gemma's cases right and makes mistakes of its own.

Sources: [Overview of agents in AEM](https://experienceleague.adobe.com/en/docs/experience-manager-cloud-service/content/ai-in-aem/agents/overview),
[Agentic AI in Experience Cloud](https://experienceleague.adobe.com/en/docs/core-services/interface/features/agentic-ai?lang=en),
[Agent Orchestrator](https://business.adobe.com/products/experience-platform/agent-orchestrator.html).
