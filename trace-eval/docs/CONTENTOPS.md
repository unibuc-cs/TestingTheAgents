# ContentOps: the application under test

ContentOps is a small content-management platform operated by agents — a toy version of what a CMS such
as AEM looks like when an LLM agent sits in front of it. It is the system that every test, every
controlled change and every spec in this repository talks about. Everything is in `traceeval/sut/`.

## What a user can do

Users (an author, a publisher, an admin, a viewer) write requests in natural language: "publish the
welcome page", "set the SEO title of the launch post", "translate the widget page into German and
French", "export the personal data of subject s1", "roll back the history page to version 2". The
platform answers in prose and changes its state: pages, their versions, links and metadata; assets;
translation jobs; an audit log of every write.

## How it is built

```
request --> orchestrator (routes by trigger words) --> one specialist agent --> its skills --> tools --> services --> state
```

| layer | what it is | where |
|---|---|---|
| agents (8) | YAML definitions: system prompt, the skills they may use, the tools they may call, trigger words for routing | `sut/agents/*.yaml` |
| skills (10) | markdown files with a machine-readable `Procedure` (the steps to follow) plus prose rules; shared skills (`governance-checks`, `link-validation`) are included by others | `sut/skills/*/SKILL.md` |
| tools (22) | thin adapters with a name, a kind (`read`, `write`, `guarded`) and a JSON schema, registered with a decorator | `sut/tools/*.py` |
| services | the business logic: repository (pages, versions, assets), workflow (review, publish, schedule, unpublish), links, SEO, permissions, governance, translation | `sut/services/*.py` |
| state | an in-memory copy of a JSON fixture: users, pages, assets, consents, audit log; idempotency memory | `sut/services/state.py`, `sut/fixtures/base.json` |
| harness | the agent loop (`runtime.py`), the dispatcher that governs every tool call (`dispatcher.py`), the router, the skill loader, the config reader, fault injection, retries | `sut/harness/` |
| config | the runtime settings: step budget, retries, idempotency keys, disabled and guarded tools, default agent, review/scheduling flags, SEO limits, default locales | `sut/config/runtime.yaml` |
| backends | *simulated*: executes the skill's procedure step by step, deterministic and free; *LLM*: a real model on an OpenAI-compatible endpoint, with tool calling | `sut/harness/backends/` |

The agents and what they own:

| agent | does | skills |
|---|---|---|
| orchestrator | front door: routes every request to the specialist that owns the workflow | routing |
| authoring | creates draft pages, edits page bodies | page-authoring, governance-checks, link-validation |
| publishing | publishes, schedules, unpublishes, with permission, link and review gates | publishing-workflow, governance-checks, link-validation |
| seo | reviews and sets SEO metadata within the configured limits | seo-metadata, governance-checks |
| assets | uploads assets to the DAM and attaches them to pages | asset-management, governance-checks |
| translation | creates translation jobs, reports their status | translation, governance-checks |
| governance | data-subject exports under consent, audit-log questions | governance-ops, governance-checks |
| maintenance | restores earlier page versions | rollback, governance-checks, link-validation |

## The rules the harness enforces on every tool call

Role permissions (`check_permission` before any write), approval tokens for guarded tools
(`approve_review`, `export_user_data`, `unpublish_page`), retries on transient failures with an
idempotency key so that a lost acknowledgement does not duplicate a write, a per-request step budget,
tool enablement by configuration, delegation depth, and a trace event for every call. Fault profiles
(`transient_once:<tool>`, `ack_timeout_once:<tool>`, `permanent_down:<tool>`) inject failures on
purpose so that the resilience rules can be tested.

## Why it is shaped like this

It is deliberately *small but real*: enough layers (prompt, skill, tool, service, config, harness) that a
change can land in the wrong one, enough rules (gates, retries, budgets) that a change can break one
without touching the feature it was meant for, and fully deterministic under the simulated backend so
that thousands of runs cost nothing. A one-line walkthrough of a request is in
[STUDY_GUIDE.md §1.1](STUDY_GUIDE.md); the 134 scenarios that exercise it are in `traceeval/catalog/`.
