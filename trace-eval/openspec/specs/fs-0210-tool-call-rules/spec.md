# FS-0210: Every tool call passes one dispatcher, inside a step budget, through clean layers

**Owner:** platform-reliability

## Purpose

Agents act on the world only through tool calls, and every call passes through the dispatcher, whatever the agent
or the backend. Each agent has a budget of steps (its tool calls and delegations), and the whole request has a
larger one shared by all its agents, so that a plan over several specialists fits while no single agent loops for
long. Tools can be switched off by configuration, and an unexpected exception in a tool is a defect to be reported,
never a normal outcome. The code is layered: backends do not touch tools directly, adapters do not depend on the
harness, and services know neither. This describes the system as it is today, with Gemma's recorded answers.

## Requirements

### Requirement: The budgets and the feature flags are settings

Each agent MUST have a budget of 12 steps and a request one of 40, and no tool MUST be switched off.

#### Scenario: The budget of an agent is configured

- **WHEN** the platform configuration is checked
- **THEN** `runtime.max_tool_calls` is an integer between 8 and 50 with the value 12

```yaml clause
use: setting_in_range
with: {key: runtime.max_tool_calls, min: 8, max: 50, value: 12}
```

#### Scenario: The budget of a request is configured

- **WHEN** the platform configuration is checked
- **THEN** `runtime.max_run_tool_calls` is an integer between 12 and 200 with the value 40

```yaml clause
use: setting_in_range
with: {key: runtime.max_run_tool_calls, min: 12, max: 200, value: 40}
```

#### Scenario: No tool is switched off

- **WHEN** the platform configuration is checked
- **THEN** `tools.disabled` is an empty list

```yaml clause
use: setting_equals
with: {key: tools.disabled, value: [], type: list}
```

### Requirement: A run stays inside its budgets

No agent MUST make more steps than its budget and no request more than the request's budget, every request of the
catalog MUST end with a final answer rather than at a budget, and a call MUST NOT be tried more often than the
retry setting allows.

#### Scenario: No agent exceeds its budget

- **WHEN** a call of `get_page`, `check_permission` or `validate_links` succeeds in any run
- **THEN** the agent making it has made at most `runtime.max_tool_calls` tool calls and delegations in the run

```yaml clause
use: always_on_calls
with:
  tools: [get_page, check_permission, validate_links]
  where: >-
    len([e for e in run.events if (e.kind == 'tool.call' and e.agent == event.agent)
    or (e.kind == 'agent.route' and e.source == event.agent)]) <= config('runtime.max_tool_calls')
```

#### Scenario: No request exceeds its budget

- **WHEN** a call of `get_page`, `check_permission` or `validate_links` succeeds in any run
- **THEN** the run's steps are at most `runtime.max_run_tool_calls` (a run cut short because a recorded answer is
  missing, `INFRA_INVALID`, has no step count and says nothing about the budget)

```yaml clause
use: always_on_calls
with:
  tools: [get_page, check_permission, validate_links]
  where: run.classification == 'INFRA_INVALID' or run.steps <= config('runtime.max_run_tool_calls')
```

#### Scenario: Every request ends with an answer, not at a budget

- **WHEN** a call of `get_page`, `check_permission` or `validate_links` succeeds in any run
- **THEN** the run ended with the agents' final answer, unless it was cut short because a recorded answer is
  missing (`INFRA_INVALID`)

```yaml clause
use: always_on_calls
with:
  tools: [get_page, check_permission, validate_links]
  where: run.classification == 'INFRA_INVALID' or run.termination == 'final'
```

#### Scenario: A request with several steps for one specialist finishes normally

- **WHEN** catalog case ORC-03 runs, which creates a page, sets its metadata, checks its links and requests a review
- **THEN** the case passes: it takes at most 8 steps and ends with a final answer

```yaml clause
use: scenario
with: {case: ORC-03}
```

#### Scenario: A request can go straight to a specialist

- **WHEN** catalog case PUB-16 runs, which addresses the publishing agent directly
- **THEN** the case passes: the page is published

```yaml clause
use: scenario
with: {case: PUB-16}
```

#### Scenario: A page with several links fits the budget

- **WHEN** catalog case AUT-13 runs, which creates a page with several links
- **THEN** the case passes: the page records its 4 links and the response confirms the save

```yaml clause
use: scenario
with: {case: AUT-13}
```

#### Scenario: A call is not tried more often than allowed

- **WHEN** a call of `publish_page`, `validate_links` or `create_page` succeeds in any run
- **THEN** its attempts are at most `runtime.retries` plus one

```yaml clause
use: always_on_calls
with:
  tools: [publish_page, validate_links, create_page]
  where: event.attempts <= config('runtime.retries') + 1
```

### Requirement: No tool crashes on a recorded request

A tool MUST NOT raise an unexpected exception on any request of the catalog.

#### Scenario: No call in the catalog crashes

- **WHEN** a call of any of the platform's tools is made in any run
- **THEN** its status is never `crash`

```yaml clause
use: never_on_calls
with:
  tools: [search_pages, get_page, create_page, update_page_content, set_page_metadata, list_versions, rollback_page, validate_links, request_review, approve_review, publish_page, schedule_publish, unpublish_page, upload_asset, get_asset, search_assets, attach_asset, create_translation_job, get_translation_status, get_seo_report, check_permission, check_consent, export_user_data, get_audit_log, get_brand_guidelines, check_brand_policy, get_page_metrics, audit_site, fix_alt_text, make_plan, request_approval]
  where: event.status == 'crash'
```

### Requirement: The layers stay apart

Every tool call MUST go through `Dispatcher.call`. Backends MUST NOT import tools, adapters and services MUST NOT
import the harness, services MUST NOT import adapters, and services MUST NOT read the configuration.

#### Scenario: The dispatcher is the one door

- **WHEN** the code is inspected
- **THEN** `Dispatcher.call` is defined in `harness/dispatcher.py`

```yaml clause
use: function_in_layer
with: {function: Dispatcher.call, file: harness/dispatcher.py}
```

#### Scenario: Backends do not import tools

- **WHEN** the code under `harness/backends` is inspected
- **THEN** nothing there imports `tools`

```yaml clause
use: forbid_import_in
with: {module: tools, dirs: [harness/backends]}
```

#### Scenario: Adapters and services do not import the harness

- **WHEN** the code under `tools` and `services` is inspected
- **THEN** nothing there imports `harness`

```yaml clause
use: forbid_import_in
with: {module: harness, dirs: [tools, services]}
```

#### Scenario: Services do not import adapters

- **WHEN** the code under `services` is inspected
- **THEN** nothing there imports `tools`

```yaml clause
use: forbid_import_in
with: {module: tools, dirs: [services]}
```

#### Scenario: Services do not read the configuration

- **WHEN** the code under `services` is inspected
- **THEN** nothing there uses the name `config`

```yaml clause
use: forbid_name_in
with: {name: config, dirs: [services]}
```
