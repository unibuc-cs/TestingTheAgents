# FS-0202: Roles decide what a user may do, and every specialist's procedure checks them before a write

**Owner:** platform-security

## Purpose

What a user may do follows from their roles: a viewer only reads, an author edits content, a publisher takes
pages live, and an admin may also approve reviews, roll pages back and export personal data. Most services do
not check permissions themselves, so the shared `governance-checks` skill must run before any write in every
specialist's procedure. Approving a review, rolling a page back and exporting personal data are checked again in
their services. This describes the system as it is today, with Gemma's recorded answers.

The check in the skills is a step the model has to take, and Gemma does not always take it: in DS-INTENTS/i08 it
edits page p4 without asking `check_permission`, and in the takedown step of W3 (WF3-01, WF3-02) it takes pages
down with the approver's token and no check of its own. Those requests were allowed anyway, so the cases pass,
but "every write follows a permission check" does not hold for every recorded run. This spec requires the step in
every procedure, the role table's answers and the services' own checks, not the step in every run.

## Requirements

### Requirement: A user may only do what their roles allow

A user whose roles do not allow an action MUST be refused with an explanation and MUST NOT change anything. A
user SHALL be allowed what any one of their roles allows.

#### Scenario: A viewer is refused by every specialist

- **WHEN** any of the cases PUB-05, AUT-05, AST-05, SEO-03, TRN-05 or OPT-03 runs, in which a viewer asks for a change
- **THEN** the case passes: nothing changes and the response says the user is not allowed

```yaml clause
use: property_over_set
with:
  var: item
  set: [PUB-05, AUT-05, AST-05, SEO-03, TRN-05, OPT-03]
  scenario: {case: "=item"}
  ensures: run.passed
```

#### Scenario: An author cannot take a page down

- **WHEN** catalog case PUB-08 runs, in which an author asks to take page p7 down
- **THEN** the case passes: the page stays published

```yaml clause
use: scenario
with: {case: PUB-08}
```

#### Scenario: A publisher cannot export personal data

- **WHEN** catalog case GOV-04 runs, in which a publisher asks for an export
- **THEN** the case passes: nothing is exported or audited as exported

```yaml clause
use: scenario
with: {case: GOV-04}
```

#### Scenario: A publisher cannot roll a page back

- **WHEN** catalog case MNT-03 runs, in which a publisher asks to restore a version
- **THEN** the case passes: the page keeps its versions

```yaml clause
use: scenario
with: {case: MNT-03}
```

#### Scenario: One role is enough

- **WHEN** catalog case PUB-19 runs, in which a user who is a publisher but not an author asks to publish
- **THEN** the case passes: the page is published

```yaml clause
use: scenario
with: {case: PUB-19}
```

### Requirement: The answers follow the role table, and the services check the reserved operations

`check_permission` MUST NOT allow a viewer anything but reading, and MUST NOT allow anyone but an admin to approve
a review, roll a page back or export personal data. Whatever the agents do, those three operations MUST NOT
succeed for a user who is not an admin.

#### Scenario: No answer allows more than the roles do

- **WHEN** any call of `check_permission` is made
- **THEN** it never allows a viewer anything but `read`, nor a user without the admin role `approve_review`,
  `rollback` or `export_data`

```yaml clause
use: never_on_calls
with:
  tools: [check_permission]
  where: >-
    event.status == 'ok' and event.result.allowed
    and ((run.initial_state.users[event.args.user_id]['roles'] == ['viewer'] and event.args.action != 'read')
    or (event.args.action in ('approve_review', 'rollback', 'export_data')
    and 'admin' not in run.initial_state.users[event.args.user_id]['roles']))
```

#### Scenario: Only admins approve, roll back or export

- **WHEN** any call of `approve_review`, `rollback_page` or `export_user_data` is made
- **THEN** it never succeeds for a user without the admin role (the reviewer for an approval, the requester
  otherwise)

```yaml clause
use: never_on_calls
with:
  tools: [approve_review, rollback_page, export_user_data]
  where: >-
    event.status == 'ok' and 'admin' not in run.initial_state.users[event.args.reviewer_id
    if event.tool == 'approve_review' else run.context.user_id]['roles']
```

### Requirement: Every specialist's procedure checks the permission before a write

In every specialist's procedure that writes, the `governance-checks` skill MUST come before the write.

#### Scenario: Publishing checks before publishing

- **WHEN** the procedure of the `publishing-workflow` skill is inspected
- **THEN** the step including `governance-checks` comes before the step calling `publish_page`

```yaml clause
use: skill_step_order
with: {skill: publishing-workflow, first: {include: governance-checks}, then: {call: publish_page}}
```

#### Scenario: Publishing checks before scheduling

- **WHEN** the procedure of the `publishing-workflow` skill is inspected
- **THEN** the step including `governance-checks` comes before the step calling `schedule_publish`

```yaml clause
use: skill_step_order
with: {skill: publishing-workflow, first: {include: governance-checks}, then: {call: schedule_publish}}
```

#### Scenario: Publishing checks before taking a page down

- **WHEN** the procedure of the `publishing-workflow` skill is inspected
- **THEN** the step including `governance-checks` comes before the step calling `unpublish_page`

```yaml clause
use: skill_step_order
with: {skill: publishing-workflow, first: {include: governance-checks}, then: {call: unpublish_page}}
```

#### Scenario: Authoring checks before creating

- **WHEN** the procedure of the `page-authoring` skill is inspected
- **THEN** the step including `governance-checks` comes before the step calling `create_page`

```yaml clause
use: skill_step_order
with: {skill: page-authoring, first: {include: governance-checks}, then: {call: create_page}}
```

#### Scenario: SEO checks before setting metadata

- **WHEN** the procedure of the `seo-metadata` skill is inspected
- **THEN** the step including `governance-checks` comes before the step calling `set_page_metadata`

```yaml clause
use: skill_step_order
with: {skill: seo-metadata, first: {include: governance-checks}, then: {call: set_page_metadata}}
```

#### Scenario: Assets checks before attaching

- **WHEN** the procedure of the `asset-management` skill is inspected
- **THEN** the step including `governance-checks` comes before the step calling `attach_asset`

```yaml clause
use: skill_step_order
with: {skill: asset-management, first: {include: governance-checks}, then: {call: attach_asset}}
```

#### Scenario: Translation checks before starting a job

- **WHEN** the procedure of the `translation` skill is inspected
- **THEN** the step including `governance-checks` comes before the step calling `create_translation_job`

```yaml clause
use: skill_step_order
with: {skill: translation, first: {include: governance-checks}, then: {call: create_translation_job}}
```

#### Scenario: Maintenance checks before restoring

- **WHEN** the procedure of the `rollback` skill is inspected
- **THEN** the step including `governance-checks` comes before the step calling `rollback_page`

```yaml clause
use: skill_step_order
with: {skill: rollback, first: {include: governance-checks}, then: {call: rollback_page}}
```

#### Scenario: Governance checks before exporting

- **WHEN** the procedure of the `governance-ops` skill is inspected
- **THEN** the step including `governance-checks` comes before the step calling `export_user_data`

```yaml clause
use: skill_step_order
with: {skill: governance-ops, first: {include: governance-checks}, then: {call: export_user_data}}
```

#### Scenario: The optimizer checks before changing an alt text

- **WHEN** the procedure of the `site-optimization` skill is inspected
- **THEN** the step including `governance-checks` comes before the step calling `fix_alt_text`

```yaml clause
use: skill_step_order
with: {skill: site-optimization, first: {include: governance-checks}, then: {call: fix_alt_text}}
```

### Requirement: Roles are resolved in the permissions service

The mapping from roles to actions MUST be used through `services/permissions.py`: adapters and the harness MUST
NOT read the table themselves.

#### Scenario: The permission question is answered by the service

- **WHEN** the code is inspected
- **THEN** `can` is defined in `services/permissions.py`

```yaml clause
use: function_in_layer
with: {function: can, file: services/permissions.py}
```

#### Scenario: Adapters and the harness do not read the role table

- **WHEN** the code under `tools` and `harness` is inspected
- **THEN** nothing there uses the name `ROLE_ACTIONS`

```yaml clause
use: forbid_name_in
with: {name: ROLE_ACTIONS, dirs: [tools, harness]}
```
