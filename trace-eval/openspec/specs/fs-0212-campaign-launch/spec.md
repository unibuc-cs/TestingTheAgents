# FS-0212: A campaign launch passes the brand check before it is translated or goes live

**Owner:** content-ops

## Purpose

Workflow W1, the campaign launch: one request makes a landing page, adds a hero image, checks the page against the
brand guidelines, has it translated and schedules it. The orchestrator plans five steps, one per specialist in this
order: authoring, assets, brand, translation, publishing. The brand check is the campaign's gate: a page that fails
it is neither translated nor scheduled, and the plan stops there. As in every plan, a person approves the
scheduling first, and a refusal stops the plan. This describes the system as it is today, with Gemma's recorded
answers.

Gemma completes the launch in WF1-01 except for one step: it schedules the page without having its review approved
by the approver, so that case is one of its known mistakes and is not used here. The gate itself holds in every
recorded run.

## Requirements

### Requirement: The launch stops at a failed brand check or a refused approval

A campaign page whose brand check fails MUST NOT be translated, scheduled or published, and a refused approval MUST
stop the launch before scheduling.

#### Scenario: A page with a forbidden term goes no further

- **WHEN** catalog case WF1-02 runs, whose body promises "risk-free" savings
- **THEN** the case passes: the plan runs authoring, assets and brand, the brand check fails, and nothing is
  translated, scheduled or published

```yaml clause
use: scenario
with: {case: WF1-02}
```

#### Scenario: A refused approval stops the launch before scheduling

- **WHEN** catalog case WF1-03 runs, in which the approver refuses
- **THEN** the case passes: the page is created, checked and translated, the refusal is audited, and the page stays
  a draft

```yaml clause
use: scenario
with: {case: WF1-03}
```

#### Scenario: No step follows a failed brand check of the page

- **WHEN** any call of `create_translation_job`, `schedule_publish` or `publish_page` is made
- **THEN** it never succeeds for a page whose brand check failed earlier in the run

```yaml clause
use: never_on_calls
with:
  tools: [create_translation_job, schedule_publish, publish_page]
  where: >-
    event.status == 'ok'
    and any(e.kind == 'tool.call' and e.tool == 'check_brand_policy' and e.status == 'ok'
    and not e.result.compliant and e.args.page_id == event.args.page_id and e.t < event.t for e in run.events)
```

#### Scenario: A page created in the run goes live only after it passed the brand check

- **WHEN** a call of `schedule_publish` or `publish_page` succeeds for a page created in the same run
- **THEN** a brand check of that page found it compliant earlier in the run

```yaml clause
use: always_on_calls
with:
  tools: [schedule_publish, publish_page]
  where: >-
    not any(e.kind == 'tool.call' and e.tool == 'create_page' and e.status == 'ok'
    and e.result.page_id == event.args.page_id for e in run.events)
    or any(e.kind == 'tool.call' and e.tool == 'check_brand_policy' and e.status == 'ok' and e.result.compliant
    and e.args.page_id == event.args.page_id and e.t < event.t for e in run.events)
```

### Requirement: The routing skill states the brand gate

The `routing` skill MUST tell the orchestrator that a campaign page passes the brand check before it is scheduled or
published, and that no step runs after a failed check it depends on. The model reads these rules from the skill;
nothing below the orchestrator enforces them.

#### Scenario: The brand gate is a rule of the plan

- **WHEN** the `routing` skill is inspected
- **THEN** it says that a campaign page passes the brand check before it is scheduled or published

```yaml clause
use: skill_states
with: {skill: routing, text: "4. A campaign page passes the brand check before it is scheduled or published."}
```

#### Scenario: A failed check stops the steps that depend on it

- **WHEN** the `routing` skill is inspected
- **THEN** its rules forbid going on with steps that depend on a failed step or check

```yaml clause
use: skill_states
with: {skill: routing, text: "- Never go on with steps that depend on a failed step or check."}
```
