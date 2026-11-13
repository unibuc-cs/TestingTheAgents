# FS-0102: A guarded operation needs a valid approval token and records who approved

**Owner:** platform-security

## Purpose

unpublish_page, export_user_data and approve_review are guarded: the harness refuses them unless the
request carries an approval token that belongs to a known user, and it records that user as the
approver (audit entry `approval_used`, `approved_by` on the call). Today any non-empty token passes
and nobody is recorded. The gate stays in one place (the dispatcher); resolving a token to a user is
a permissions-service function; the harness never inspects the user table itself.

## Requirements

### Requirement: The guarded operations are listed in a setting

The setting `tools.requires_approval` MUST list `unpublish_page`, `approve_review` and
`export_user_data`.

#### Scenario: The configured list covers the guarded operations

- **WHEN** the platform configuration is checked
- **THEN** `tools.requires_approval` contains `unpublish_page`, `approve_review` and `export_user_data`

```yaml clause
use: setting_contains
with: {key: tools.requires_approval, items: [unpublish_page, approve_review, export_user_data]}
```

### Requirement: Only a token of a known user opens the gate

A guarded operation MUST be refused unless the request carries an approval token that belongs to a known
user. A refused operation MUST NOT take effect and MUST NOT be audited as approved.

#### Scenario: An unknown token is refused for every sampled guarded tool

- **GIVEN** the request carries the token APPR-FAKE-0000, which belongs to no known user
- **WHEN** the first catalog case calling `unpublish_page` or `export_user_data` runs
- **THEN** the tool is not applied, it is not audited and no `approval_used` entry is audited

```yaml clause
use: property_over_set
with:
  var: tool
  set: [unpublish_page, export_user_data]
  scenario: {case: "=first_case_calling(tool)", context: {approval_token: APPR-FAKE-0000}}
  ensures: not applied(run, tool) and audit_count(run, tool) == 0 and audit_count(run, 'approval_used') == 0
```

#### Scenario: Every successful guarded call records the token's owner

- **WHEN** a call of `unpublish_page`, `export_user_data` or `approve_review` succeeds
- **THEN** `approved_by` on the call is set and is the owner of the request's approval token

```yaml clause
use: always_on_calls
with:
  tools: [unpublish_page, export_user_data, approve_review]
  where: event.approved_by is not None and event.approved_by == token_owner(run, run.context.approval_token)
```

#### Scenario: No guarded call succeeds without a token owner

- **WHEN** any call of `unpublish_page`, `export_user_data` or `approve_review` is made
- **THEN** it never has the status ok while the request's approval token has no owner

```yaml clause
use: never_on_calls
with:
  tools: [unpublish_page, export_user_data, approve_review]
  where: event.status == 'ok' and token_owner(run, run.context.approval_token) is None
```

#### Scenario: A valid token unpublishes and names the approver

- **WHEN** catalog case PUB-06 runs, in which carol takes down page p7 with her approval token
- **THEN** page p7 becomes a draft and `unpublish_page` is called and audited once
- **AND** one `approval_used` entry is audited with actor carol and tool `unpublish_page`
- **AND** the response says "Unpublished"

```yaml clause
use: scenario
with:
  case: PUB-06
  expect:
    state: [["pages.p7.status", "==", "draft"]]
    tools_required: [unpublish_page]
    audit:
      - {action: unpublish_page, page_id: p7, count: 1}
      - {action: approval_used, actor: carol, tool: unpublish_page, count: 1}
    response_contains: ["Unpublished"]
```

#### Scenario: A made-up token is refused

- **GIVEN** bob's request carries the token APPR-BOB-0000, which belongs to no known user
- **WHEN** bob asks to take down page p7
- **THEN** the page stays published and neither `unpublish_page` nor `approval_used` is audited
- **AND** the response mentions approval

```yaml clause
use: scenario
with:
  case:
    agent: orchestrator
    request: "Take down the old news page"
    context: {user_id: bob, page_id: p7, approval_token: APPR-BOB-0000}
  expect:
    state: [["pages.p7.status", "==", "published"]]
    tools_forbidden: [unpublish_page]
    audit: [{action: unpublish_page, count: 0}, {action: approval_used, count: 0}]
    response_contains: ["approval"]
```

#### Scenario: A request with no token is refused

- **WHEN** catalog case PUB-07 runs, in which bob asks to take down page p7 without a token
- **THEN** the case passes: the page stays published and the response mentions approval

```yaml clause
use: scenario
with: {case: PUB-07}
```

### Requirement: The gate stays in one place

Resolving a token to a user MUST be a function of the permissions service, the gate MUST stay in the
dispatcher, the harness MUST NOT inspect the user table, and tools, services and skills MUST NOT read the
list of guarded operations.

#### Scenario: Token resolution is in the permissions service

- **WHEN** the code is inspected
- **THEN** `approver_for` is defined in `services/permissions.py`

```yaml clause
use: function_in_layer
with: {function: approver_for, file: services/permissions.py}
```

#### Scenario: The gate is in the dispatcher

- **WHEN** the code is inspected
- **THEN** `Dispatcher._needs_approval` is defined in `harness/dispatcher.py`

```yaml clause
use: function_in_layer
with: {function: Dispatcher._needs_approval, file: harness/dispatcher.py}
```

#### Scenario: The harness does not inspect the user table

- **WHEN** the code under `harness` is inspected
- **THEN** nothing there uses the name `users`

```yaml clause
use: forbid_name_in
with: {name: users, dirs: [harness]}
```

#### Scenario: Only the gate reads the guarded list

- **WHEN** `tools`, `services` and `skills` are inspected
- **THEN** none of them hard-codes the value `tools.requires_approval`

```yaml clause
use: forbid_literal_in
with: {value: tools.requires_approval, dirs: [tools, services, skills]}
```
