# FS-0101: An editorial approval is valid for 30 days

**Owner:** content-ops

## Purpose

A page may only be published or scheduled while its editorial approval is recent. The validity
window is a platform setting (30 days to start with), not a number in code. A stale approval is
refused with an explanation and leaves an audit entry; the author has to request a new review.
Approving a review records the approval date.

## Requirements

### Requirement: The validity window is a bounded platform setting

The setting `publishing.review_max_age_days` MUST be an integer between 1 and 365, set to 30.

#### Scenario: The configured window is valid

- **WHEN** the platform configuration is checked
- **THEN** `publishing.review_max_age_days` is an integer between 1 and 365 with the value 30

```yaml clause
use: setting_in_range
with: {key: publishing.review_max_age_days, min: 1, max: 365, value: 30}
```

### Requirement: The age rule is an inclusive window

`review_age_ok` SHALL accept an approval age exactly when it is between 0 and the maximum age, both
included. The rule MUST be proven for all inputs (rung L5), not only tested on examples.

#### Scenario: The rule holds for every age and window

- **WHEN** `review_age_ok` receives any `age_days` and any `max_age_days` of at least 1
- **THEN** the result is true exactly when `0 <= age_days <= max_age_days`

```yaml clause
use: function_contract
with:
  function: services/workflow.py::review_age_ok
  inputs: {age_days: int, max_age_days: int}
  assume: max_age_days >= 1
  ensures: result == (0 <= age_days <= max_age_days)
  examples: 300
require: L5
```

### Requirement: Going live needs a recent approval

A page MUST NOT be published or scheduled when its approval is older than the configured window. A
stale approval SHALL be refused with an explanation and an audit entry, and SHALL NOT trigger a review
request by itself.

#### Scenario: Every successful publish or schedule had a recent approval

- **WHEN** a call of `publish_page` or `schedule_publish` succeeds in any run
- **THEN** the approval age of that page is at most `publishing.review_max_age_days`

```yaml clause
use: always_on_calls
with:
  tools: [publish_page, schedule_publish]
  where: approval_age(run, event.args.page_id) <= config('publishing.review_max_age_days')
```

#### Scenario: A stale approval is refused

- **GIVEN** page p11, whose approval is 45 days old
- **WHEN** bob asks to publish it
- **THEN** the page stays a draft, no `publish_page` entry is audited and no review is requested
- **AND** one `publish_refused` entry is audited with rule FS-0101
- **AND** the response states the window in days and says a new review is needed

```yaml clause
use: scenario
with:
  case:
    agent: orchestrator
    request: "Please publish the stale-approval page"
    context: {user_id: bob, page_id: p11}
  expect:
    state: [["pages.p11.status", "==", "draft"]]
    tools_forbidden: [request_review]
    audit:
      - {action: publish_refused, page_id: p11, rule_id: FS-0101, count: 1}
      - {action: publish_page, page_id: p11, count: 0}
    response_contains: ["=str(config('publishing.review_max_age_days')) + ' days'", "new review"]
```

#### Scenario: An approval exactly at the limit is still valid

- **GIVEN** page p4 with its approval patched to 2026-09-28, exactly 30 days before the fixture's date
- **WHEN** catalog case PUB-01 runs
- **THEN** the case passes and the page is published

```yaml clause
use: scenario
with: {case: PUB-01, fixture_patch: {pages.p4.review.approved_on: "2026-09-28"}}
```

#### Scenario: A recent approval publishes normally

- **WHEN** catalog case PUB-01 runs on the unchanged fixture
- **THEN** the case passes and the page is published

```yaml clause
use: scenario
with: {case: PUB-01}
```

### Requirement: The rule lives in the service layer

The age logic MUST be defined in `services/workflow.py`. Tools and the harness MUST NOT do date
arithmetic, and the value 30 MUST NOT be hard-coded in the workflow service, tools or skills.

#### Scenario: The age rule is in the workflow service

- **WHEN** the code is inspected
- **THEN** `review_age_ok` is defined in `services/workflow.py`

```yaml clause
use: function_in_layer
with: {function: review_age_ok, file: services/workflow.py}
```

#### Scenario: The age computation is in the workflow service

- **WHEN** the code is inspected
- **THEN** `approval_age_days` is defined in `services/workflow.py`

```yaml clause
use: function_in_layer
with: {function: approval_age_days, file: services/workflow.py}
```

#### Scenario: Adapters and the harness do no date arithmetic

- **WHEN** the code under `tools` and `harness` is inspected
- **THEN** nothing there imports `datetime`

```yaml clause
use: forbid_import_in
with: {module: datetime, dirs: [tools, harness]}
```

#### Scenario: The window is not hard-coded

- **WHEN** `services/workflow.py`, `tools` and `skills` are inspected
- **THEN** none of them hard-codes the value 30

```yaml clause
use: forbid_literal_in
with: {value: 30, dirs: [services/workflow.py, tools, skills]}
```
