# FS-0101: Editorial approvals expire after a configurable number of days

> DRAFT - generated from a change request; review, edit, then rename to `spec.md` to confirm.

## Purpose

An approval is valid for a configurable number of days (30 to start). Publishing or scheduling a page whose approval is older is refused with a message that asks for a new review, and the refusal is audited. Approving a review records the approval date.

## Requirements

### Requirement: setting_in_range:publishing.review_max_age_days

The system MUST satisfy: publishing.review_max_age_days is an integer between 1 and 365

#### Scenario: setting check, must reach L4

- **WHEN** the setting check of this clause runs
- **THEN** publishing.review_max_age_days is an integer between 1 and 365

```yaml clause
use: setting_in_range
with:
  key: publishing.review_max_age_days
  min: 1
  max: 365
  value: 30
```

### Requirement: function_contract:review_age_ok

The system MUST satisfy: services/workflow.py::review_age_ok: for every input with max_age_days >= 1, result == (0 <= age_days <= max_age_days)

#### Scenario: contract check, must reach L5

- **WHEN** the contract check of this clause runs
- **THEN** services/workflow.py::review_age_ok: for every input with max_age_days >= 1, result == (0 <= age_days <= max_age_days)

```yaml clause
use: function_contract
with:
  function: services/workflow.py::review_age_ok
  inputs:
    age_days: int
    max_age_days: int
  assume: max_age_days >= 1
  ensures: result == (0 <= age_days <= max_age_days)
require: L5
```

### Requirement: always_on_calls:publish_page+schedule_publish

The system MUST satisfy: every successful call of publish_page, schedule_publish satisfies: approval_age(run, event.args.page_id) <= config('publishing.review_max_age_days')

#### Scenario: trace check, must reach L3

- **WHEN** the trace check of this clause runs
- **THEN** every successful call of publish_page, schedule_publish satisfies: approval_age(run, event.args.page_id) <= config('publishing.review_max_age_days')

```yaml clause
use: always_on_calls
with:
  tools:
  - publish_page
  - schedule_publish
  where: approval_age(run, event.args.page_id) <= config('publishing.review_max_age_days')
```

### Requirement: scenario:please-publish-the-staleapproval

The system MUST satisfy: scenario 'Please publish the stale-approval page' ends as expected

#### Scenario: example check, must reach L1

- **WHEN** the example check of this clause runs
- **THEN** scenario 'Please publish the stale-approval page' ends as expected

```yaml clause
use: scenario
with:
  case:
    agent: orchestrator
    request: Please publish the stale-approval page
    context:
      user_id: bob
      page_id: p11
  expect:
    state:
    - - pages.p11.status
      - ==
      - draft
    audit:
    - action: publish_refused
      page_id: p11
      count: 1
    response_contains:
    - new review
```

### Requirement: scenario:PUB-01

The system MUST satisfy: scenario PUB-01 ends as expected

#### Scenario: example check, must reach L1

- **WHEN** the example check of this clause runs
- **THEN** scenario PUB-01 ends as expected

```yaml clause
use: scenario
with:
  case: PUB-01
```

### Requirement: scenario:PUB-01#2

The system MUST satisfy: scenario PUB-01 ends as expected

#### Scenario: example check, must reach L1

- **WHEN** the example check of this clause runs
- **THEN** scenario PUB-01 ends as expected

```yaml clause
use: scenario
with:
  case: PUB-01
  fixture_patch:
    pages.p4.review.approved_on: '2026-09-28'
```

### Requirement: function_in_layer:review_age_ok

The system MUST satisfy: review_age_ok is defined in services/workflow.py

#### Scenario: placement check, must reach L4

- **WHEN** the placement check of this clause runs
- **THEN** review_age_ok is defined in services/workflow.py

```yaml clause
use: function_in_layer
with:
  function: review_age_ok
  file: services/workflow.py
```

### Requirement: forbid_literal_in:30

The system MUST satisfy: nothing under services/workflow.py, tools, skills hard-codes the value 30

#### Scenario: placement check, must reach L4

- **WHEN** the placement check of this clause runs
- **THEN** nothing under services/workflow.py, tools, skills hard-codes the value 30

```yaml clause
use: forbid_literal_in
with:
  value: 30
  dirs:
  - services/workflow.py
  - tools
  - skills
```

### Requirement: forbid_import_in:datetime

The system MUST satisfy: nothing under tools, harness imports datetime

#### Scenario: placement check, must reach L4

- **WHEN** the placement check of this clause runs
- **THEN** nothing under tools, harness imports datetime

```yaml clause
use: forbid_import_in
with:
  module: datetime
  dirs:
  - tools
  - harness
```

## Notes from the checks before any run

- note: setting_in_range:publishing.review_max_age_days (key): config key publishing.review_max_age_days is not in the current configuration - the request introduces it
- note: function_contract:review_age_ok (function): services/workflow.py::review_age_ok is not in the current code - the request introduces it
