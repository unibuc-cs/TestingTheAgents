# FS-0201: The orchestrator delegates every request, and plans the requests that need several specialists

**Owner:** platform-reliability

## Purpose

Every request enters through the orchestrator. It reads the specialists' descriptions and triggers and decides,
following the `routing` skill, which specialist owns the request. A request one specialist owns is delegated
exactly once; a request no specialist owns goes to the configured default agent. A request that needs several
specialists gets a plan: the orchestrator writes it down once with `make_plan`, delegates its steps one at a time,
asks a person with `request_approval` before a step that publishes, schedules or takes pages down, and stops when
the person refuses. The orchestrator never touches content itself, and only the orchestrator delegates. The
delegation itself is carried out by the runtime. This describes the system as it is today, with Gemma's recorded
answers; the six multi-agent workflows have specs of their own (FS-0212 to FS-0217).

## Requirements

### Requirement: The fallback agent is a setting

The setting `routing.default_agent` MUST name `authoring`, the agent that receives a request no specialist owns.

#### Scenario: The fallback is configured

- **WHEN** the platform configuration is checked
- **THEN** `routing.default_agent` is the string `authoring`

```yaml clause
use: setting_equals
with: {key: routing.default_agent, value: authoring, type: string}
```

### Requirement: A request reaches the specialist that owns it

The orchestrator SHALL delegate a request to the specialist that owns it, and a request no specialist owns MUST go to
the default agent.

#### Scenario: Every item of the routing dataset is delegated correctly

- **WHEN** any of the 40 items of the DS-ROUTING dataset runs
- **THEN** the request is delegated to the agent the item expects

```yaml clause
use: property_over_set
with:
  var: item
  set: [DS-ROUTING/r01, DS-ROUTING/r02, DS-ROUTING/r03, DS-ROUTING/r04, DS-ROUTING/r05, DS-ROUTING/r06, DS-ROUTING/r07, DS-ROUTING/r08, DS-ROUTING/r09, DS-ROUTING/r10, DS-ROUTING/r11, DS-ROUTING/r12, DS-ROUTING/r13, DS-ROUTING/r14, DS-ROUTING/r15, DS-ROUTING/r16, DS-ROUTING/r17, DS-ROUTING/r18, DS-ROUTING/r19, DS-ROUTING/r20, DS-ROUTING/r21, DS-ROUTING/r22, DS-ROUTING/r23, DS-ROUTING/r24, DS-ROUTING/r25, DS-ROUTING/r26, DS-ROUTING/r27, DS-ROUTING/r28, DS-ROUTING/r29, DS-ROUTING/r30, DS-ROUTING/r31, DS-ROUTING/r32, DS-ROUTING/r33, DS-ROUTING/r34, DS-ROUTING/r35, DS-ROUTING/r36, DS-ROUTING/r37, DS-ROUTING/r38, DS-ROUTING/r39, DS-ROUTING/r40]
  scenario: {case: "=item"}
  ensures: run.passed
```

#### Scenario: A request that names two actions goes to the one it asks for

- **WHEN** catalog case ORC-02 runs, whose request says both "take it down" and "update"
- **THEN** the case passes: publishing takes page p7 down

```yaml clause
use: scenario
with: {case: ORC-02}
```

#### Scenario: A request no specialist owns goes to the default agent

- **WHEN** catalog case ORC-01 runs, a greeting that no specialist owns
- **THEN** the case passes: authoring receives the request and creates nothing

```yaml clause
use: scenario
with: {case: ORC-01}
```

### Requirement: The orchestrator only delegates, plans and asks for approval

The orchestrator MUST NOT call a content tool, and no specialist MUST call the orchestrator's own tools. A request
without a plan MUST be delegated at most once.

#### Scenario: The orchestrator makes no content call

- **WHEN** a call of any content tool is made in any run
- **THEN** the agent making it is never the orchestrator

```yaml clause
use: never_on_calls
with:
  tools: [search_pages, get_page, create_page, update_page_content, set_page_metadata, list_versions, rollback_page, validate_links, request_review, approve_review, publish_page, schedule_publish, unpublish_page, upload_asset, get_asset, search_assets, attach_asset, create_translation_job, get_translation_status, get_seo_report, check_permission, check_consent, export_user_data, get_audit_log, get_brand_guidelines, check_brand_policy, get_page_metrics, audit_site, fix_alt_text]
  where: event.agent == 'orchestrator'
```

#### Scenario: Only the orchestrator plans and asks for approval

- **WHEN** a call of `make_plan` or `request_approval` is made in any run
- **THEN** the agent making it is the orchestrator

```yaml clause
use: never_on_calls
with:
  tools: [make_plan, request_approval]
  where: event.agent != 'orchestrator'
```

#### Scenario: A request without a plan is delegated once

- **WHEN** a call of `get_page`, `check_permission` or `validate_links` succeeds in a run without a plan
- **THEN** the run contains at most one delegation, and only the orchestrator delegates

```yaml clause
use: always_on_calls
with:
  tools: [get_page, check_permission, validate_links]
  where: >-
    all(e.source == 'orchestrator' for e in run.events if e.kind == 'agent.route')
    and (applied(run, 'make_plan')
    or len([e for e in run.events if e.kind == 'agent.route' and e.status == 'ok']) <= 1)
```

### Requirement: A plan is written once, and its consequential steps wait for a person

A request that needs several specialists MUST get one plan, written before its first delegation. In a plan, a step
that publishes, schedules or takes pages down MUST come after a person approved it, and after a refusal no further
step MUST be delegated.

#### Scenario: One plan, before the first delegation

- **WHEN** a call of `make_plan` is made in any run
- **THEN** it is the run's only call of `make_plan` and no delegation came before it

```yaml clause
use: never_on_calls
with:
  tools: [make_plan]
  where: >-
    len([e for e in run.events if e.kind == 'tool.call' and e.tool == 'make_plan']) > 1
    or any(e.kind == 'agent.route' and e.t < event.t for e in run.events)
```

#### Scenario: Nothing goes live or down in a plan without an approval

- **WHEN** a call of `publish_page`, `schedule_publish` or `unpublish_page` succeeds in a run with a plan
- **THEN** an earlier `request_approval` in the run was approved

```yaml clause
use: always_on_calls
with:
  tools: [publish_page, schedule_publish, unpublish_page]
  where: >-
    not applied(run, 'make_plan')
    or any(e.kind == 'tool.call' and e.tool == 'request_approval' and e.status == 'ok' and e.result.approved
    and e.t < event.t for e in run.events)
```

#### Scenario: A refusal stops the plan

- **WHEN** a call of `request_approval` returns a refusal
- **THEN** no step is delegated after it

```yaml clause
use: never_on_calls
with:
  tools: [request_approval]
  where: >-
    event.status == 'ok' and not event.result.approved
    and any(e.kind == 'agent.route' and e.t > event.t for e in run.events)
```

#### Scenario: An approval reaches the steps after it

- **WHEN** a call of a guarded tool succeeds after an approval in any run
- **THEN** it was made with the approver's token

```yaml clause
use: always_on_calls
with:
  tools: [unpublish_page, approve_review, export_user_data]
  where: >-
    not any(e.kind == 'tool.call' and e.tool == 'request_approval' and e.status == 'ok' and e.result.approved
    and e.t < event.t for e in run.events)
    or call_token(run, event) == run.initial_state.users[run.initial_state.approvals.approver]['approval_token']
```

#### Scenario: The answer is the approver's

- **WHEN** a call of `request_approval` succeeds in any run
- **THEN** it approves exactly when the approver's decision in the platform data is to approve

```yaml clause
use: always_on_calls
with:
  tools: [request_approval]
  where: event.result.approved == (run.initial_state.approvals.get('decision', 'approve') == 'approve')
```

#### Scenario: The routing skill asks for approval before a consequential step

- **WHEN** the `routing` skill is inspected
- **THEN** its plan steps say to call `request_approval` before a step that publishes, schedules or takes pages down

```yaml clause
use: skill_states
with:
  skill: routing
  text: "3. Before a step that publishes, schedules or takes pages down, call `request_approval`"
```

#### Scenario: The routing skill forbids going live in a plan without an approval

- **WHEN** the `routing` skill is inspected
- **THEN** its rules forbid running such a step without an approval in a plan

```yaml clause
use: skill_states
with:
  skill: routing
  text: "- Never run a step that publishes, schedules or takes pages down without an approval in a plan."
```

### Requirement: Delegation is carried out by the runtime

The runtime MUST carry out every delegation in `harness/runtime.py`, and tools and services MUST NOT reach the
runtime.

#### Scenario: Delegation is in the runtime

- **WHEN** the code is inspected
- **THEN** `Runtime._delegate` is defined in `harness/runtime.py`

```yaml clause
use: function_in_layer
with: {function: Runtime._delegate, file: harness/runtime.py}
```

#### Scenario: Tools and services do not reach the runtime

- **WHEN** the code under `tools` and `services` is inspected
- **THEN** nothing there uses the name `Runtime`

```yaml clause
use: forbid_name_in
with: {name: Runtime, dirs: [tools, services]}
```
