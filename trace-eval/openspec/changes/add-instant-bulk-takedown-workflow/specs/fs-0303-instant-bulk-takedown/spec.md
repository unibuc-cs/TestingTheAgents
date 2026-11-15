# FS-0303: An emergency takedown removes up to 60 pages in one request, without waiting for a person

**Owner:** platform-security

## Purpose

Workflow W9, the instant bulk takedown: in an emergency (the request context carries `emergency: true`), one request
takes down every page of a list at once. The orchestrator writes one plan that lists every page and delegates each
page to publishing on its own, so that every takedown can be traced to one step. Because an emergency cannot wait,
no person is asked. After a page is down, publishing hands it straight to translation, which cancels the page's
queued translation jobs, without going back through the orchestrator. A batch may hold up to `takedown.max_batch`
pages, 60 to begin with. The emergency path must not make ordinary requests more expensive or less safe: the step
budgets stay as they are, taking a page down stays guarded, and no existing spec changes. This is a change request:
the setting `takedown.max_batch`, the function `bulk_size_ok`, the tool `cancel_translation_jobs` and the 60 archive
pages of the fixture do not exist yet.

## ADDED Requirements

### Requirement: A batch of up to 60 pages goes down in one request, one delegation per page

The setting `takedown.max_batch` MUST be an integer between 1 and 60, set to 60. For every batch size from 1 to
`takedown.max_batch`, an emergency request SHALL take every page of the batch down in one run: one plan, one
successful delegation to publishing per page, one audited takedown per page, and a final answer.

#### Scenario: The batch limit is configured

- **WHEN** the platform configuration is checked
- **THEN** `takedown.max_batch` is an integer between 1 and 60 with the value 60

```yaml clause
use: setting_in_range
with: {key: takedown.max_batch, min: 1, max: 60, value: 60}
```

#### Scenario: Every batch size up to the limit is taken down completely, page by page

- **WHEN** bob sends an emergency request to take down the first `n` pages of the archive section, for any `n` from
  1 to 60
- **THEN** `unpublish_page` is audited `n` times, publishing was delegated to `n` times, the plan was written once,
  and the run ends with an answer

```yaml clause
use: property_over_range
with:
  var: n
  min: 1
  max: 60
  scenario:
    case:
      agent: orchestrator
      request: "Emergency: take down the first pages of the archive section now, as many as the count says."
      context: {user_id: bob, emergency: true, section: /content/site/archive, takedown_count: "=n"}
  ensures: >-
    audit_count(run, 'unpublish_page') == n
    and len([e for e in run.events if e.kind == 'agent.route' and e.source == 'orchestrator'
    and e.target == 'publishing' and e.status == 'ok']) == n
    and len([e for e in run.events if e.kind == 'tool.call' and e.tool == 'make_plan' and e.status == 'ok']) == 1
    and run.termination == 'final'
  examples: 60
```

### Requirement: The emergency path does not raise the step budgets

The step budgets MUST stay at today's values and MUST NOT be raisable for the emergency path:
`runtime.max_run_tool_calls` at most 40 and `runtime.max_tool_calls` at most 12. As today, every tool call and
every delegation of a run counts against them, and an emergency run MUST stay inside both.

#### Scenario: The budget of a request stays at 40

- **WHEN** the platform configuration is checked
- **THEN** `runtime.max_run_tool_calls` is an integer between 12 and 40 with the value 40

```yaml clause
use: setting_in_range
with: {key: runtime.max_run_tool_calls, min: 12, max: 40, value: 40}
```

#### Scenario: The budget of an agent stays at 12

- **WHEN** the platform configuration is checked
- **THEN** `runtime.max_tool_calls` is an integer between 8 and 12 with the value 12

```yaml clause
use: setting_in_range
with: {key: runtime.max_tool_calls, min: 8, max: 12, value: 12}
```

#### Scenario: An emergency run stays inside the budget of a request

- **WHEN** a call of `unpublish_page` succeeds in an emergency run
- **THEN** the steps of the run, tool calls and delegations together, are at most `runtime.max_run_tool_calls`

```yaml clause
use: always_on_calls
with:
  tools: [unpublish_page]
  where: not run.context.emergency or run.steps <= config('runtime.max_run_tool_calls')
```

### Requirement: No person is asked in an emergency, and taking a page down stays guarded

An emergency run MUST NOT call `request_approval`. `unpublish_page` MUST stay a guarded tool listed in
`tools.requires_approval`, and every takedown MUST still be made with an approval token that belongs to the
platform's approver, never to the requester.

#### Scenario: An emergency run asks nobody

- **WHEN** any call of `request_approval` is made
- **THEN** it is never made in an emergency run

```yaml clause
use: never_on_calls
with:
  tools: [request_approval]
  where: bool(run.context.emergency)
```

#### Scenario: Taking a page down stays guarded

- **WHEN** the platform configuration is checked
- **THEN** `tools.requires_approval` contains `unpublish_page`

```yaml clause
use: setting_contains
with: {key: tools.requires_approval, items: [unpublish_page]}
```

#### Scenario: Every emergency takedown carries the approver's token

- **WHEN** a call of `unpublish_page` succeeds in an emergency run
- **THEN** the token it was made with belongs to the approver, who is not the user who made the request

```yaml clause
use: always_on_calls
with:
  tools: [unpublish_page]
  where: >-
    not run.context.emergency
    or (token_owner(run, call_token(run, event)) == run.initial_state.approvals.approver
    and token_owner(run, call_token(run, event)) != run.context.user_id)
```

#### Scenario: Three pages go down with no approval request

- **WHEN** bob sends an emergency request for the first 3 pages of the archive section
- **THEN** the three pages become drafts, `request_approval` is never called, and no approval is audited

```yaml clause
use: scenario
with:
  case:
    agent: orchestrator
    request: "Emergency: take down the first pages of the archive section now, as many as the count says."
    context: {user_id: bob, emergency: true, section: /content/site/archive, takedown_count: 3}
  expect:
    tools_forbidden: [request_approval]
    tools_required: [make_plan, unpublish_page]
    state:
      - ["pages.p101.status", "==", "draft"]
      - ["pages.p102.status", "==", "draft"]
      - ["pages.p103.status", "==", "draft"]
    audit:
      - {action: request_approval, count: 0}
      - {action: unpublish_page, count: 3}
```

### Requirement: Publishing hands each page straight to translation

After a takedown in an emergency run, the publishing agent SHALL delegate the page to the translation agent itself,
which cancels the page's queued translation jobs. The hand-over MUST NOT go back through the orchestrator.

#### Scenario: Every emergency takedown is followed by a hand-over from publishing to translation

- **WHEN** a call of `unpublish_page` succeeds in an emergency run
- **THEN** a successful delegation from publishing to translation follows it in the run

```yaml clause
use: always_on_calls
with:
  tools: [unpublish_page]
  where: >-
    not run.context.emergency
    or any(e.kind == 'agent.route' and e.source == 'publishing' and e.target == 'translation'
    and e.status == 'ok' and e.t > event.t for e in run.events)
```

#### Scenario: Translation jobs are cancelled only on a hand-over from publishing

- **WHEN** a call of `cancel_translation_jobs` succeeds in any run
- **THEN** the translation agent made it, and a delegation from publishing to translation came before it

```yaml clause
use: always_on_calls
with:
  tools: [cancel_translation_jobs]
  where: >-
    event.agent == 'translation'
    and any(e.kind == 'agent.route' and e.source == 'publishing' and e.target == 'translation'
    and e.status == 'ok' and e.t < event.t for e in run.events)
```

### Requirement: A batch is accepted when its size is within the limit

`bulk_size_ok` SHALL accept a batch exactly when it holds at least one page and at most `limit` pages. The rule MUST
be proven for all inputs (rung L5) and MUST be defined in the workflow service.

#### Scenario: The rule holds for every batch size

- **WHEN** `bulk_size_ok` receives any `n` and any `limit` of at least 1
- **THEN** the result is true exactly when `1 <= n <= limit`

```yaml clause
use: function_contract
with:
  function: services/workflow.py::bulk_size_ok
  inputs: {n: int, limit: int}
  assume: limit >= 1
  ensures: result == (1 <= n <= limit)
require: L5
```

#### Scenario: The rule is in the workflow service

- **WHEN** the code is inspected
- **THEN** `bulk_size_ok` is defined in `services/workflow.py`

```yaml clause
use: function_in_layer
with: {function: bulk_size_ok, file: services/workflow.py}
```

### Requirement: An emergency that matches no page is not an error

An emergency request whose list is empty SHALL succeed without taking anything down: `bulk_size_ok` MUST accept an
empty batch, so that the request is answered rather than refused.

#### Scenario: An empty batch is accepted

- **WHEN** `bulk_size_ok` receives `n` equal to 0 and any `limit` of at least 1
- **THEN** the result is true

```yaml clause
use: function_contract
with:
  function: services/workflow.py::bulk_size_ok
  inputs: {n: int, limit: int}
  assume: n == 0 and limit >= 1
  ensures: result == True
require: L5
```
