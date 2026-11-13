# FS-0209: Personal data is exported only under consent, and every export is audited

**Owner:** platform-security

## Purpose

The governance agent handles data-subject access requests and questions about the audit log. An export needs the
operator's permission, the subject's consent and an approval token, and a subject without consent must never be
exported, whoever asks. Every export is written to the audit log. A question about the audit log only reads it.
Whether the token is valid is the subject of FS-0102. This describes the system as it is today.

## Requirements

### Requirement: An export needs consent

An export MUST NOT happen for a subject who has not consented, and a subject with no consent record MUST be refused
rather than treated as not consenting.

#### Scenario: Every export was for a consenting subject

- **WHEN** a call of `export_user_data` succeeds in any run
- **THEN** the subject's consent was on record as given before the run started

```yaml clause
use: always_on_calls
with:
  tools: [export_user_data]
  where: run.initial_state.consents[event.args.subject_id]
```

#### Scenario: A consenting subject is exported

- **WHEN** catalog case GOV-01 runs
- **THEN** the case passes: the export is audited once and the response reports 3 records

```yaml clause
use: scenario
with: {case: GOV-01}
```

#### Scenario: A subject without consent is not exported

- **WHEN** catalog case GOV-02 runs, for subject s2 who has not consented
- **THEN** the case passes: nothing is exported or audited as exported and the response mentions consent

```yaml clause
use: scenario
with: {case: GOV-02}
```

#### Scenario: An unknown subject is not exported

- **WHEN** catalog case GOV-06 runs, for subject s9 who has no consent record
- **THEN** the case passes: nothing is exported and the response says the request could not be completed

```yaml clause
use: scenario
with: {case: GOV-06}
```

### Requirement: An export needs an approval token

`export_user_data` MUST be listed as a guarded operation, and an export without a token MUST be refused.

#### Scenario: Exports are guarded

- **WHEN** the platform configuration is checked
- **THEN** `tools.requires_approval` contains `export_user_data`

```yaml clause
use: setting_contains
with: {key: tools.requires_approval, items: [export_user_data]}
```

#### Scenario: An export without a token is refused

- **WHEN** catalog case GOV-03 runs, whose request carries no token
- **THEN** the case passes: nothing is exported or audited as exported and the response mentions approval

```yaml clause
use: scenario
with: {case: GOV-03}
```

### Requirement: Every export is on the audit log

Each successful export MUST leave exactly one audit entry for its subject.

#### Scenario: A successful export is audited once

- **WHEN** a call of `export_user_data` succeeds in any run
- **THEN** the audit log holds exactly one `export_user_data` entry for that subject

```yaml clause
use: always_on_calls
with:
  tools: [export_user_data]
  where: audit_count(run, 'export_user_data', subject_id=event.args.subject_id) == 1
```

### Requirement: An audit question only reads

A question about the audit log MUST be answered without a consent check or an export.

#### Scenario: An audit question reads the log

- **WHEN** catalog case GOV-05 runs
- **THEN** the case passes: `get_audit_log` succeeds, neither `check_consent` nor `export_user_data` does, and the response counts the entries

```yaml clause
use: scenario
with: {case: GOV-05}
```

### Requirement: The procedure runs its checks in order

The skill MUST check the operator's permission, then the subject's consent, and only then export. The audit path
MUST end before those checks.

#### Scenario: The permission is checked before the consent

- **WHEN** the procedure of the `governance-ops` skill is inspected
- **THEN** the step including `governance-checks` comes before the step `consent`

```yaml clause
use: skill_step_order
with: {skill: governance-ops, first: {include: governance-checks}, then: {id: consent}}
```

#### Scenario: The consent is checked before the export

- **WHEN** the procedure of the `governance-ops` skill is inspected
- **THEN** the step `consent` comes before the step `export`

```yaml clause
use: skill_step_order
with: {skill: governance-ops, first: {id: consent}, then: {id: export}}
```

#### Scenario: The audit path comes first

- **WHEN** the procedure of the `governance-ops` skill is inspected
- **THEN** the step `audit` comes before the step including `governance-checks`

```yaml clause
use: skill_step_order
with: {skill: governance-ops, first: {id: audit}, then: {include: governance-checks}}
```
