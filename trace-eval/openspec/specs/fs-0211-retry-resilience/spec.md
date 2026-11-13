# FS-0211: Transient failures are retried, and writes that honour a key never run twice

**Owner:** platform-reliability

## Purpose

A transient failure of a tool is retried by the harness. Write tools receive an idempotency key that stays the same
across the retries, so a service that honours it answers a retry with its first result. Reads carry no key. This
covers the six write tools whose services honour the key today; FS-0105 asks for the same of the publishing tools
that do not yet. A tool that stays down is reported, not worked around. This describes the system as it is today.

## Requirements

### Requirement: A transient failure is retried

A failure that happens before a tool runs SHALL be retried, and the request MUST then succeed as if nothing had
happened.

#### Scenario: Every keyed write survives a failure before it runs

- **GIVEN** a tool among `create_page`, `update_page_content`, `upload_asset`, `create_translation_job`, `request_review` and `publish_page` whose first call fails
- **WHEN** the first catalog case calling that tool runs
- **THEN** the case passes and the tool is audited as many times as in the baseline run of that case

```yaml clause
use: property_over_set
with:
  var: tool
  set: [create_page, update_page_content, upload_asset, create_translation_job, request_review, publish_page]
  scenario: {case: "=first_case_calling(tool)", fault_profile: "='transient_once:' + tool"}
  ensures: run.passed and audit_count(run, tool) == audit_count(baseline_run(run.test_id), tool)
```

#### Scenario: A retried publish records its attempts

- **WHEN** catalog case PUB-11 runs, in which `publish_page` fails once before it runs
- **THEN** the case passes: the page is published, the call took at least 2 attempts and the publish is audited once

```yaml clause
use: scenario
with: {case: PUB-11}
```

#### Scenario: A retried read carries on

- **WHEN** catalog case PUB-13 runs, in which `validate_links` fails once
- **THEN** the case passes: the page is published and the check took at least 2 attempts

```yaml clause
use: scenario
with: {case: PUB-13}
```

#### Scenario: A retried create makes one page

- **WHEN** catalog case AUT-08 runs, in which `create_page` fails once before it runs
- **THEN** the case passes: the page exists and `create_page` is audited once

```yaml clause
use: scenario
with: {case: AUT-08}
```

### Requirement: A lost acknowledgement does not repeat a keyed write

When a write's acknowledgement is lost and the call is retried, the effect MUST happen once, for every write whose
service honours the key.

#### Scenario: Every keyed write takes effect once

- **GIVEN** a tool among `create_page`, `update_page_content`, `upload_asset`, `create_translation_job`, `request_review` and `publish_page` whose first acknowledgement is lost
- **WHEN** the first catalog case calling that tool runs
- **THEN** the case passes and the tool is audited as many times as in the baseline run of that case

```yaml clause
use: property_over_set
with:
  var: tool
  set: [create_page, update_page_content, upload_asset, create_translation_job, request_review, publish_page]
  scenario: {case: "=first_case_calling(tool)", fault_profile: "='ack_timeout_once:' + tool"}
  ensures: run.passed and audit_count(run, tool) == audit_count(baseline_run(run.test_id), tool)
```

#### Scenario: A lost acknowledgement creates one page

- **WHEN** catalog case AUT-09 runs
- **THEN** the case passes: page p100 exists, page p101 does not and `create_page` is audited once

```yaml clause
use: scenario
with: {case: AUT-09}
```

#### Scenario: A lost acknowledgement adds one version

- **WHEN** catalog case AUT-11 runs
- **THEN** the case passes: page p4 has 2 versions

```yaml clause
use: scenario
with: {case: AUT-11}
```

#### Scenario: A lost acknowledgement uploads one asset

- **WHEN** catalog case AST-06 runs
- **THEN** the case passes: asset a100 exists, asset a101 does not and `upload_asset` is audited once

```yaml clause
use: scenario
with: {case: AST-06}
```

#### Scenario: A lost acknowledgement queues one job

- **WHEN** catalog case TRN-06 runs
- **THEN** the case passes: job tj-1 exists, job tj-2 does not and `create_translation_job` is audited once

```yaml clause
use: scenario
with: {case: TRN-06}
```

### Requirement: Writes carry a key and reads do not

Every successful call of those write tools MUST carry an idempotency key, and a read MUST NOT.

#### Scenario: Every successful keyed write has its key

- **WHEN** a call of `create_page`, `update_page_content`, `upload_asset`, `create_translation_job`, `request_review` or `publish_page` succeeds
- **THEN** the call has an idempotency key

```yaml clause
use: always_on_calls
with:
  tools: [create_page, update_page_content, upload_asset, create_translation_job, request_review, publish_page]
  where: event.idempotency_key is not None
```

#### Scenario: A read has no key

- **WHEN** a call of `get_page`, `validate_links` or `check_permission` succeeds
- **THEN** the call has no idempotency key

```yaml clause
use: always_on_calls
with:
  tools: [get_page, validate_links, check_permission]
  where: event.idempotency_key is None
```

#### Scenario: Keys are made in the harness

- **WHEN** the code is inspected
- **THEN** `new_idempotency_key` is defined in `harness/retry.py`

```yaml clause
use: function_in_layer
with: {function: new_idempotency_key, file: harness/retry.py}
```

#### Scenario: Adapters and services do not make keys

- **WHEN** the code under `tools` and `services` is inspected
- **THEN** nothing there uses the name `new_idempotency_key`

```yaml clause
use: forbid_name_in
with: {name: new_idempotency_key, dirs: [tools, services]}
```
