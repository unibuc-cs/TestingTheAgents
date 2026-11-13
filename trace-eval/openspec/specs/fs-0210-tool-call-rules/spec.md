# FS-0210: Every tool call passes one dispatcher, inside a step budget, through clean layers

**Owner:** platform-reliability

## Purpose

Agents act on the world only through tool calls, and every call passes through the dispatcher, whatever the agent
or the backend. A run has a budget of tool calls shared by all its agents, tools can be switched off by
configuration, and an unexpected exception in a tool is a defect to be reported, never a normal outcome. The code
is layered: backends do not touch tools directly, adapters do not depend on the harness, and services know neither.
This describes the system as it is today.

## Requirements

### Requirement: The budget and the feature flags are settings

A run MUST have a budget of 12 tool calls, and no tool MUST be switched off.

#### Scenario: The budget is configured

- **WHEN** the platform configuration is checked
- **THEN** `runtime.max_tool_calls` is an integer between 8 and 50 with the value 12

```yaml clause
use: setting_in_range
with: {key: runtime.max_tool_calls, min: 8, max: 50, value: 12}
```

#### Scenario: No tool is switched off

- **WHEN** the platform configuration is checked
- **THEN** `tools.disabled` is an empty list

```yaml clause
use: setting_equals
with: {key: tools.disabled, value: [], type: list}
```

### Requirement: A run stays inside its budget

A run MUST NOT make more steps than the budget, the normal requests of the platform MUST finish within it, and a
call MUST NOT be tried more often than the retry setting allows.

#### Scenario: No run exceeds the budget

- **WHEN** a call of `get_page` or `check_permission` succeeds in any run
- **THEN** the run's steps are at most `runtime.max_tool_calls`

```yaml clause
use: always_on_calls
with:
  tools: [get_page, check_permission]
  where: run.steps <= config('runtime.max_tool_calls')
```

#### Scenario: A long request finishes normally

- **WHEN** catalog case ORC-03 runs, one of the two longest requests in the catalog
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
  tools: [search_pages, get_page, create_page, update_page_content, set_page_metadata, list_versions, rollback_page, validate_links, request_review, approve_review, publish_page, schedule_publish, unpublish_page, upload_asset, get_asset, attach_asset, create_translation_job, get_translation_status, get_seo_report, check_permission, check_consent, export_user_data, get_audit_log]
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
