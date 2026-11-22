# FS-0101: Approvals must expire

> DRAFT - generated from a change request; review, edit, then rename to `spec.md` to confirm.

## Purpose

Editorial approvals should be valid for a configurable number of days (default 30) instead of forever. When a reviewer approves a page, the approval date must be recorded so the expiry can be computed. Publishing or scheduling a page whose approval has expired must be refused with a clear message and the refusal must be visible in the audit log.

## Requirements

### Requirement: setting_in_range:publishing.approval_validity_days

The system MUST satisfy: publishing.approval_validity_days is an integer between 1 and 365

#### Scenario: setting check, must reach L4

- **WHEN** the setting check of this clause runs
- **THEN** publishing.approval_validity_days is an integer between 1 and 365

```yaml clause
use: setting_in_range
with:
  key: publishing.approval_validity_days
  min: 1
  max: 365
  value: 30
```

### Requirement: function_contract:approval_is_valid

The system MUST satisfy: services/workflow.py::approval_is_valid: for every input with approval_age(run, page_id) is not None, approval_age(run, page_id) <= config('publishing.approval_validity_days')

#### Scenario: contract check, must reach L5

- **WHEN** the contract check of this clause runs
- **THEN** services/workflow.py::approval_is_valid: for every input with approval_age(run, page_id) is not None, approval_age(run, page_id) <= config('publishing.approval_validity_days')

```yaml clause
use: function_contract
with:
  function: services/workflow.py::approval_is_valid
  inputs: run, page_id
  ensures: approval_age(run, page_id) <= config('publishing.approval_validity_days')
  assume: approval_age(run, page_id) is not None
  examples: 5
require: L5
```

### Requirement: function_in_layer:approval_is_valid

The system MUST satisfy: approval_is_valid is defined in services/workflow.py

#### Scenario: placement check, must reach L4

- **WHEN** the placement check of this clause runs
- **THEN** approval_is_valid is defined in services/workflow.py

```yaml clause
use: function_in_layer
with:
  function: approval_is_valid
  file: services/workflow.py
```

### Requirement: forbid_literal_in:30

The system MUST satisfy: nothing under tools/, skills/ hard-codes the value 30

#### Scenario: placement check, must reach L4

- **WHEN** the placement check of this clause runs
- **THEN** nothing under tools/, skills/ hard-codes the value 30

```yaml clause
use: forbid_literal_in
with:
  value: 30
  dirs:
  - tools/
  - skills/
```

### Requirement: always_on_calls:publish_page+schedule_publish

The system MUST satisfy: every successful call of publish_page, schedule_publish satisfies: approval_age(run, event.args.page_id) <= config('publishing.approval_validity_days')

#### Scenario: trace check, must reach L3

- **WHEN** the trace check of this clause runs
- **THEN** every successful call of publish_page, schedule_publish satisfies: approval_age(run, event.args.page_id) <= config('publishing.approval_validity_days')

```yaml clause
use: always_on_calls
with:
  tools:
  - publish_page
  - schedule_publish
  where: approval_age(run, event.args.page_id) <= config('publishing.approval_validity_days')
```

### Requirement: always_in_audit:publish_page+schedule_publish

The system MUST satisfy: every audit entry publish_page, schedule_publish satisfies: event.status == 'error' and 'expired' in event.message

#### Scenario: trace check, must reach L3

- **WHEN** the trace check of this clause runs
- **THEN** every audit entry publish_page, schedule_publish satisfies: event.status == 'error' and 'expired' in event.message

```yaml clause
use: always_in_audit
with:
  actions:
  - publish_page
  - schedule_publish
  where: event.status == 'error' and 'expired' in event.message
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
  context:
    page_id: welcome
    approval_age_days: 5
  expect: run.passed
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
  context:
    page_id: welcome
    approval_age_days: 31
  expect: not run.passed and 'request a new review' in run.message
```

### Requirement: scenario:PUB-01#3

The system MUST satisfy: scenario PUB-01 ends as expected

#### Scenario: example check, must reach L1

- **WHEN** the example check of this clause runs
- **THEN** scenario PUB-01 ends as expected

```yaml clause
use: scenario
with:
  case: PUB-01
  context:
    page_id: welcome
    approval_age_days: 30
  expect: run.passed
```

## Notes from the checks before any run

- note: setting_in_range:publishing.approval_validity_days (key): config key publishing.approval_validity_days is not in the current configuration - the request introduces it
- note: function_contract:approval_is_valid (function): services/workflow.py::approval_is_valid is not in the current code - the request introduces it
- error: function_contract:approval_is_valid (inputs): inputs must map each name to int, bool or str
