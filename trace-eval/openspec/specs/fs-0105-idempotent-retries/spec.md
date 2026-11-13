# FS-0105: A retried publishing write never duplicates its effect

**Owner:** platform-reliability

## Purpose

Transient failures are retried (at least once). When the acknowledgement of a write made by the
publishing workflow is lost and the call is retried, the effect happens once: every write tool the
publishing skill uses is idempotent under its idempotency key. Retrying is the harness's job (one
place); services honour the key; adapters only pass it through.

## Requirements

### Requirement: Retries and idempotency keys are switched on

The platform MUST retry transient failures between 1 and 5 times and MUST have idempotency keys
enabled.

#### Scenario: The retry count is valid

- **WHEN** the platform configuration is checked
- **THEN** `runtime.retries` is an integer between 1 and 5

```yaml clause
use: setting_in_range
with: {key: runtime.retries, min: 1, max: 5}
```

#### Scenario: Idempotency keys are enabled

- **WHEN** the platform configuration is checked
- **THEN** `runtime.idempotency_keys` is the boolean true

```yaml clause
use: setting_equals
with: {key: runtime.idempotency_keys, value: true, type: boolean}
```

### Requirement: A lost acknowledgement does not duplicate a write

Every write tool used by the publishing skill SHALL take effect once when its acknowledgement is lost
and the call is retried, and every such write MUST carry an idempotency key.

#### Scenario: The rule holds for every write tool of the publishing skill

- **GIVEN** a write tool of the `publishing-workflow` skill whose first acknowledgement is lost
- **WHEN** the first catalog case calling that tool runs
- **THEN** the case passes and the tool is audited as many times as in the baseline run of that case

```yaml clause
use: property_over_set
with:
  var: tool
  set: {skill_write_tools: publishing-workflow}
  scenario: {case: "=first_case_calling(tool)", fault_profile: "='ack_timeout_once:' + tool"}
  ensures: run.passed and audit_count(run, tool) == audit_count(baseline_run(run.test_id), tool)
```

#### Scenario: Every successful write carries a key

- **WHEN** a call of `publish_page`, `schedule_publish`, `unpublish_page` or `request_review` succeeds
- **THEN** the call has an idempotency key

```yaml clause
use: always_on_calls
with:
  tools: [publish_page, schedule_publish, unpublish_page, request_review]
  where: event.idempotency_key is not None
```

#### Scenario: A retried publish does not publish twice

- **WHEN** catalog case PUB-12 runs, which loses the first acknowledgement of `publish_page`
- **THEN** the case passes: page p4 is published and `publish_page` is audited once

```yaml clause
use: scenario
with: {case: PUB-12}
```

#### Scenario: A retried schedule does not schedule twice

- **WHEN** catalog case PUB-09 runs with the first acknowledgement of `schedule_publish` lost
- **THEN** page p4 is scheduled and `schedule_publish` is audited once for it

```yaml clause
use: scenario
with:
  case: PUB-09
  fault_profile: ack_timeout_once:schedule_publish
  expect:
    state: [["pages.p4.status", "==", "scheduled"]]
    audit: [{action: schedule_publish, page_id: p4, count: 1}]
```

### Requirement: Retrying happens in one place

Retrying MUST be implemented by `with_retry` in `harness/retry.py`. Adapters MUST NOT handle transient
errors, and adapters and services MUST NOT use the retry helper.

#### Scenario: The retry helper is in the harness

- **WHEN** the code is inspected
- **THEN** `with_retry` is defined in `harness/retry.py`

```yaml clause
use: function_in_layer
with: {function: with_retry, file: harness/retry.py}
```

#### Scenario: Adapters do not handle transient errors

- **WHEN** the code under `tools` is inspected
- **THEN** nothing there uses the name `TransientError`

```yaml clause
use: forbid_name_in
with: {name: TransientError, dirs: [tools]}
```

#### Scenario: Adapters and services do not retry

- **WHEN** the code under `tools` and `services` is inspected
- **THEN** nothing there uses the name `with_retry`

```yaml clause
use: forbid_name_in
with: {name: with_retry, dirs: [tools, services]}
```
