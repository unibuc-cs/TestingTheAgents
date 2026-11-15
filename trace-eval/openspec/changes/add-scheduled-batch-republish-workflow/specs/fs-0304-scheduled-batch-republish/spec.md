# FS-0304: Multiple pages scheduled for the same time are republished together in one plan

**Owner:** content-ops

## Purpose

Workflow W10, the scheduled batch republish: when multiple pages are scheduled to republish at times within a
configured window, one request bundles them into a single plan with one delegation to publishing per page. The
orchestrator checks that the pages in the batch have no conflicts (interdependencies, competing asset updates,
permission changes) before committing. Each page is delegated to separately, so the audit trail traces every
republish, and failures in one page do not block the others. The batch window is configurable. No approval gates
are added: content teams can schedule releases without additional gatekeeping. This is a change request: the
setting `republish.batch_window_minutes` and the function `can_batch_republish` do not exist yet.

## ADDED Requirements

### Requirement: Pages within a batch window are scheduled together

The setting `republish.batch_window_minutes` MUST be an integer between 1 and 120, set to 60. For any set of
pages whose scheduled republish times all fall within `republish.batch_window_minutes` of each other, a request
SHALL batch them: one plan, one successful delegation to publishing per page, and a final answer.

#### Scenario: The batch window is configured

- **WHEN** the platform configuration is checked
- **THEN** `republish.batch_window_minutes` is an integer between 1 and 120 with the value 60

```yaml clause
use: setting_in_range
with: {key: republish.batch_window_minutes, min: 1, max: 120, value: 60}
```

#### Scenario: Every batch size within the budgets is republished in one plan

- **WHEN** alice sends a request to republish the first `n` pages of a campaign, where those pages have scheduled
  times within the batch window
- **THEN** `publish_page` is audited `n` times, publishing was delegated to `n` times, the plan was written once,
  and the run ends with an answer

```yaml clause
use: property_over_range
with:
  var: n
  min: 1
  max: 15
  scenario:
    case:
      agent: orchestrator
      request: "Batch republish the first pages of the campaign now, they were all scheduled for this window."
      context: {user_id: alice, scheduled_batch: true, batch_size: "=n"}
  ensures: >-
    audit_count(run, 'publish_page') == n
    and len([e for e in run.events if e.kind == 'agent.route' and e.source == 'orchestrator'
    and e.target == 'publishing' and e.status == 'ok']) == n
    and len([e for e in run.events if e.kind == 'tool.call' and e.tool == 'make_plan' and e.status == 'ok']) == 1
    and run.termination == 'final'
  examples: 15
```

### Requirement: No conflicts exist in a batch before it is published

A batch SHALL be checked for conflicts before any page is republished: overlapping asset changes, interdependent
pages where one cannot republish before the other, or incompatible permission updates. The check MUST be passed
to the orchestrator (in its plan or delegation step) and its result MUST be recorded in the audit trail.

#### Scenario: The batch conflict checker is in the workflow service

- **WHEN** the code is inspected
- **THEN** `can_batch_republish` is defined in `services/workflow.py`

```yaml clause
use: function_in_layer
with: {function: can_batch_republish, file: services/workflow.py}
```

#### Scenario: The rule holds for every batch

- **WHEN** `can_batch_republish` receives any batch of pages and the batch window
- **THEN** the result is true exactly when no two pages in the batch have overlapping asset updates, and all
  interdependencies are satisfied

```yaml clause
use: function_contract
with:
  function: services/workflow.py::can_batch_republish
  inputs: {pages: list, window_minutes: int}
  assumes: window_minutes >= 1 and len(pages) >= 1
  ensures: result == (no_overlapping_assets(pages) and dependencies_satisfied(pages))
  require: L5
```

### Requirement: Each page is republished with its own delegation and audit trail

A batch MUST be split into individual delegations: one `route_to_agent` per page to the publishing agent. Each
republish MUST be audited separately so that partial failures are visible.

#### Scenario: Three pages are republished with three separate delegations

- **WHEN** alice sends a batch republish request for three pages from the campaign
- **THEN** three separate delegations to publishing are made, each with a `publish_page` call, and each
  republish is audited

```yaml clause
use: scenario
with:
  case:
    agent: orchestrator
    request: "Batch republish pages p6, p7, p8 from the campaign now."
    context: {user_id: alice, scheduled_batch: true, pages: [p6, p7, p8]}
  expect:
    tools_required: [make_plan, publish_page]
    state:
      - ["pages.p6.status", "==", "published"]
      - ["pages.p7.status", "==", "published"]
      - ["pages.p8.status", "==", "published"]
    audit:
      - {action: publish_page, count: 3}
      - {action: make_plan, count: 1}
```

### Requirement: Pages outside the batch window are not grouped

Pages whose scheduled times differ by more than `republish.batch_window_minutes` MUST NOT be batched together.

#### Scenario: Pages outside the window are separate

- **WHEN** pages p6 and p9 have scheduled times 90 minutes apart, within a window of 60 minutes
- **THEN** requesting both do not batch together; they are two separate requests or the second is rejected

```yaml clause
use: scenario
with:
  case:
    agent: orchestrator
    request: "Republish p6 and p9 from the campaign."
    context: {user_id: alice, scheduled_batch: true, pages: [p6, p9]}
  expect:
    state:
      - ["pages.p6.status", "==", "published"]
```

### Requirement: A batch is atomic with respect to conflicts

If `can_batch_republish` returns false (conflicts detected), NO page in the batch MUST be republished, and the request
MUST fail without proceeding to the orchestrator's plan.

#### Scenario: A batch with conflicts is rejected

- **WHEN** pages p6 and p10 have overlapping asset updates (both try to update asset a1)
- **THEN** `can_batch_republish` returns false, no plan is made, and the run ends without republishing either page

```yaml clause
use: scenario
with:
  case:
    agent: orchestrator
    request: "Batch republish pages p6 and p10 which both use asset a1."
    context: {user_id: alice, scheduled_batch: true, pages: [p6, p10]}
    fixture_patch:
      pages:
        p6: {assets: [a1], scheduled_republish_time: "2024-01-15T10:00:00Z"}
        p10: {assets: [a1], scheduled_republish_time: "2024-01-15T10:30:00Z"}
  expect:
    tools_forbidden: [make_plan]
    audit:
      - {action: publish_page, count: 0}
```

### Requirement: Scheduled times are tracked, and pages without scheduled times are not batched

Pages MUST have a `scheduled_republish_time` field (ISO 8601 date-time or None). Only pages with times within
the window are included in a batch request.

#### Scenario: Only scheduled pages are in the batch

- **WHEN** pages p6, p7, p8 are scheduled, but page p9 is not
- **THEN** a batch republish of the campaign does not attempt to republish p9

```yaml clause
use: always_on_calls
with:
  tools: [publish_page]
  where: >-
    not run.context.scheduled_batch
    or (pages[event.arguments.page].scheduled_republish_time != None)
```

### Requirement: The batching respects the existing budgets

Batch sizes MUST be limited so they fit within the step budgets. A batch of 15 pages uses 1 + 15 = 16 steps
(plan + delegations), leaving room for the delegated publishing steps (up to 24 tool calls at 12 per agent, or
split across multiple requests).

#### Scenario: The batch respects the run budget

- **WHEN** a batch republish succeeds
- **THEN** the run steps (delegations and tool calls) are within `runtime.max_run_tool_calls`

```yaml clause
use: always_on_calls
with:
  tools: [publish_page]
  where: >-
    not run.context.scheduled_batch
    or run.steps <= config('runtime.max_run_tool_calls')
```
