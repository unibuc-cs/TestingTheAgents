# ContentOps: the application under test

ContentOps is a small, made-up content platform run by AI agents. Picture a content management system (CMS) such as
Adobe Experience Manager (AEM) with an assistant in front of it: instead of clicking through screens, people type
what they want and a team of agents does the work. Every test, every controlled change and every spec in this
repository is about this one application, and all of its code lives in [`traceeval/sut/`](../traceeval/sut/).

## What people ask it to do

The platform starts with a few users, each with a different job. Alice is an author. Bob writes and
publishes. Erin only publishes. Carol is the administrator, the one who can approve sensitive operations.
Dave can only look. They are in the platform's starting data,
[`fixtures/base.json`](../traceeval/sut/fixtures/base.json), next to a small website of pages, some assets,
and the people whose personal data the platform holds.

They talk to the platform in plain language. Some requests from the test catalog:

- "Please publish the welcome page"
- "Update the SEO title tag of the welcome post"
- "Translate the welcome post into German"
- "Upload a new image banner.png and attach it to the welcome post"
- "Export the personal data of subject s1 (GDPR access request)"
- "Revert the history page to version 1"
- "Who changed the home page? Show me the audit history"
- "Which three blog posts got the fewest views?"
- "Launch the spring sale: create a landing page, add a hero image tagged spring, make sure it passes the brand
  check, get it translated into French and German, and schedule it" (five specialists, one after the other)
- "Find the three worst-performing pages of our blog, run a health check of the blog section, fix their SEO,
  and republish all three" (four specialists)
- "Change the price on the pricing page to €49, update every translation, one job per language, and republish
  it after review" (three specialists)
- "Yesterday's edit broke the welcome page: roll it back to version 1 and republish it" (two specialists)
- "Privacy request from Sam Lee: export his personal data, remove his name from the bylines of his two blog
  posts, then republish both pages" (three specialists)

The platform answers in prose and, when the request calls for it, changes its data: pages with their
versions, links and metadata; assets; translation jobs; and an audit log that records every change. It also
holds the brand guidelines, the site's analytics, and who approves consequential steps.

## How it is built

![ContentOps: the user, the orchestrator, the specialists, the shared skills, the dispatcher, tools, services, state and configuration](figures/contentops_agents.svg)

*One request, top to bottom. The orchestrator hands the request to one specialist, or, for a request that
needs several, plans the steps and hands them over one at a time. A specialist follows its skill's procedure.
Every tool call it makes passes through the dispatcher. The tools pass the work on to the services, which
change the data and write the audit log.*

Each layer is a folder or file you can open:

| Layer | What it is | Open it |
|---|---|---|
| Agents | One YAML file per agent: its instructions, the skills it follows, the tools it may call, and the trigger words that send requests its way | [`sut/agents/`](../traceeval/sut/agents/) |
| Skills | One `SKILL.md` per skill: a `Procedure` block with the steps to follow, plus rules in plain prose. Two skills are shared by several agents | [`sut/skills/`](../traceeval/sut/skills/) |
| Tools | Thin adapters. Each has a name, a kind (`read`, `write` or `guarded`) and a parameter schema. The orchestrator also has a control tool, `route_to_agent`, and two of its own, `make_plan` and `request_approval` | [`sut/tools/`](../traceeval/sut/tools/) |
| Services | The business logic: pages, versions and assets; review, publish, schedule and unpublish; links; SEO; roles and permissions; consent, export, audit and approvals; translation; brand guidelines; analytics and the site audit | [`sut/services/`](../traceeval/sut/services/) |
| Data | An in-memory copy of a JSON file with the users, pages, assets, consents, translation jobs, brand guidelines, analytics, approver and audit log, plus a memory of idempotency keys | [`fixtures/base.json`](../traceeval/sut/fixtures/base.json), [`services/state.py`](../traceeval/sut/services/state.py) |
| Harness | What runs the agents: the agent loop, the dispatcher that every tool call passes through, the skill loader, fault injection and retries | [`sut/harness/`](../traceeval/sut/harness/) |
| Settings | The step budgets (per agent and per request), retries, idempotency keys, disabled and guarded tools, the default agent, the review and scheduling switches, SEO limits, default languages and the slow-page limit | [`config/runtime.yaml`](../traceeval/sut/config/runtime.yaml) |
| Backends | What makes the decisions: a model, behind an OpenAI-style chat client. Gemma 4 E4B by default (on the local GPU, on a GPU server, or replayed from its recorded answers), or any OpenAI-compatible endpoint that supports tool calling | [`harness/backends/`](../traceeval/sut/harness/backends/), [`traceeval/llm/chat.py`](../traceeval/llm/chat.py) |

## The agents, and how they work together

Agents do not chat with each other. The only hand-off is the orchestrator passing work to a specialist with
`route_to_agent`. The only way any agent changes anything is by calling a tool. Everything else, such as
which skill to follow and what to do next, happens inside a single agent.

The orchestrator is the front door. It reads the request and looks at every specialist's description and
trigger words. A request one specialist owns is delegated exactly once. When no specialist owns it, it goes
to the default agent named in the settings, which is `authoring`.

A request that needs several specialists gets a plan, as in AEM's Agent Orchestrator. The orchestrator writes
the steps down (`make_plan`), then delegates them one at a time. Each step gets its own instruction (`task`)
and the values it needs (`context`), which are the ids that earlier steps reported. Before a step that
publishes, schedules or takes pages down, the orchestrator asks a person (`request_approval`), and the approval
then holds for the steps after it. A failed step stops the steps that depend on it. The orchestrator never
touches content itself.

Click an agent to see its definition, or a skill to read its procedure:

| Agent | Looks after | Follows | May call |
|---|---|---|---|
| [orchestrator](../traceeval/sut/agents/orchestrator.yaml) | sending each request to the right specialist, or planning and running the steps of a request that needs several | [routing](../traceeval/sut/skills/routing/SKILL.md) | `route_to_agent`, `make_plan`, `request_approval` |
| [authoring](../traceeval/sut/agents/authoring.yaml) | creating draft pages and editing page text, and asking for a review when told to | [page-authoring](../traceeval/sut/skills/page-authoring/SKILL.md) | `search_pages`, `get_page`, `create_page`, `update_page_content`, `set_page_metadata`, `validate_links`, `request_review`, `list_versions`, `check_permission` |
| [publishing](../traceeval/sut/agents/publishing.yaml) | putting pages live, scheduling them, taking them down | [publishing-workflow](../traceeval/sut/skills/publishing-workflow/SKILL.md) | `get_page`, `check_permission`, `validate_links`, `request_review`, `approve_review`†, `publish_page`, `schedule_publish`, `unpublish_page`† |
| [seo](../traceeval/sut/agents/seo.yaml) | checking and setting a page's title, description and keywords, within the title-length limit | [seo-metadata](../traceeval/sut/skills/seo-metadata/SKILL.md) | `get_page`, `get_seo_report`, `set_page_metadata`, `check_permission` |
| [assets](../traceeval/sut/agents/assets.yaml) | uploading files to the asset library, finding assets by their tags (only licensed ones may be used), and attaching them to pages | [asset-management](../traceeval/sut/skills/asset-management/SKILL.md) | `get_page`, `upload_asset`, `search_assets`, `get_asset`, `attach_asset`, `check_permission` |
| [translation](../traceeval/sut/agents/translation.yaml) | starting translation jobs and reporting how far they are | [translation](../traceeval/sut/skills/translation/SKILL.md) | `get_page`, `check_permission`, `create_translation_job`, `get_translation_status` |
| [governance](../traceeval/sut/agents/governance.yaml) | exporting a person's data when they have consented, and answering audit questions | [governance-ops](../traceeval/sut/skills/governance-ops/SKILL.md) | `check_permission`, `check_consent`, `export_user_data`†, `get_audit_log` |
| [maintenance](../traceeval/sut/agents/maintenance.yaml) | restoring an earlier version of a page | [rollback](../traceeval/sut/skills/rollback/SKILL.md) | `get_page`, `list_versions`, `rollback_page`, `validate_links`, `check_permission` |
| [brand](../traceeval/sut/agents/brand.yaml) | checking pages against the brand guidelines (forbidden terms, the offer disclaimer, licensed assets) and finding the pages that use a term | [brand-governance](../traceeval/sut/skills/brand-governance/SKILL.md) | `get_brand_guidelines`, `check_brand_policy`, `search_pages` |
| [insights](../traceeval/sut/agents/insights.yaml) | how pages perform: views, bounce rate, conversions, and the best or worst pages of a section | [data-insights](../traceeval/sut/skills/data-insights/SKILL.md) | `get_page_metrics` |
| [optimizer](../traceeval/sut/agents/optimizer.yaml) | site health checks (broken links, images without alt text, missing descriptions, slow pages) and alt texts | [site-optimization](../traceeval/sut/skills/site-optimization/SKILL.md) | `audit_site`, `fix_alt_text`, `check_permission` |

The last three agents, and asset search, are modelled on AEM's Brand Governance, Data Insights, Site
Optimization and Content Advisor agents ([AEM_ALIGNMENT.md](AEM_ALIGNMENT.md)).

† A *guarded* tool. The dispatcher refuses the call unless the request carries an approval token, but it
only checks that a token is there, not whose it is. The services check the rest: `approve_review` needs the
named reviewer's own token and a role that may approve, and `export_user_data` needs the requesting user's own
token and the `export_data` permission. `unpublish_page` gets no such check, so any token will do, but a
protected page never goes down.

### The shared skills

Two skills are shared, for the steps every specialist does the same way:

- [governance-checks](../traceeval/sut/skills/governance-checks/SKILL.md) asks `check_permission` whether
  the user may do what they asked, and stops with an explanation if they may not. Every specialist that
  changes something includes it.
- [link-validation](../traceeval/sut/skills/link-validation/SKILL.md) runs `validate_links` on the page and
  stops if any link is broken. Authoring includes it after writing a page, publishing before putting one
  live or scheduling it, and maintenance after a rollback.

Specialists *include* these skills rather than copying them, so a change to a shared skill changes every
agent that includes it. Test selection has to follow that ripple.

### One request, step by step

![One run of a case, end to end](figures/guide_2_run.png)

*Bob asks: "Please publish the welcome page". The executor (`traceeval/experiment/executor.py`, the code that runs
one test) starts the orchestrator, which routes the request to publishing. The publishing agent follows its
procedure: fetch the page, check the permission, check the links, publish. Each step goes through the dispatcher
and is recorded. At the end, the final data and the answer are scored against what the test case expects.*

## Who enforces which rule

The rules sit in three places, and the difference matters: when a change removes a check from a skill,
usually nothing below the skill catches the mistake.

The harness checks every tool call. The dispatcher refuses a call when the tool does not exist, when the
settings have switched it off, when this agent is not allowed to use it, when it is guarded and the request
has no approval token, or when the arguments do not fit. A call that gets through runs with fault injection,
and transient failures are retried. Write tools also get an idempotency key, a key that identifies the
operation so that a service can recognise a repeat. It is derived from the request, the tool, its arguments
and how often that call has already gone through. A retry, or a failed write the agent repeats, is then not
applied twice by the services that honour the key. Every call leaves a `tool.call` event in the trace.

Around the dispatcher, the agent loop limits how many steps each agent may take, how many the whole request may
take (delegations count too), and how deep delegation may go. The code is in
[`dispatcher.py`](../traceeval/sut/harness/dispatcher.py) and [`runtime.py`](../traceeval/sut/harness/runtime.py).

The skills hold most of the business rules: check the permission before acting, never publish a page with
broken links, get a review approved before going live, keep the SEO title within the limit, and export
nobody's data without their consent. Most services do not check permissions themselves. They trust the skill
to have asked first.

The services and tools check a few rules again, at the bottom. Approving a review and exporting personal data
need the right role and the user's own approval token. Rolling a page back needs the right role, so a rollback
skill that forgot to ask would still be refused. The page stays safe, but the agent makes a call it should not
have made. Scheduling is refused when the settings switch it off, and taking down a protected page is always
refused.

Tests can also break things on purpose, to check that the resilience rules hold. A fault profile names the
tool it hits ([`faults.py`](../traceeval/sut/harness/faults.py)):

- `transient_once:<tool>`: the first call fails before it runs, so a retry is safe.
- `ack_timeout_once:<tool>`: the first call runs but its acknowledgement is lost, so a retry without an
  idempotency key makes the change twice.
- `permanent_down:<tool>`: every call fails.

## Why it is shaped like this

The application is small but realistic. It has enough layers (instructions, skills, tools, services, settings,
harness) that a change can land in the wrong one. It has enough rules (gates, retries, budgets) that a change can
break one without touching the feature it was aimed at. Finally, the model decodes greedily (it always takes its
most likely next token), and the app has no wall clock (timestamps come from a counter) and no randomness. A run
therefore replays exactly from recorded answers, so the whole catalog can be run again and again for free.

To follow a single request through the code, see [STUDY_GUIDE.md §1.1](STUDY_GUIDE.md#11-one-run-end-to-end).
The test scenarios that exercise the platform are in [`traceeval/catalog/tests/`](../traceeval/catalog/tests/).
