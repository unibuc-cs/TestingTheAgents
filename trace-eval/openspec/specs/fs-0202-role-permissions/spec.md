# FS-0202: Every specialist checks the user's role before it changes anything

**Owner:** platform-security

## Purpose

What a user may do follows from their roles: a viewer only reads, an author edits content, a publisher takes
pages live, and an admin may also approve reviews, roll pages back and export personal data. Most services do
not check permissions themselves, so the shared `governance-checks` skill must run before any write in every
specialist's procedure. This describes the system as it is today.

## Requirements

### Requirement: A user may only do what their roles allow

A user whose roles do not allow an action MUST be refused with an explanation and MUST NOT change anything. A
user SHALL be allowed what any one of their roles allows.

#### Scenario: A viewer is refused by every specialist

- **WHEN** any of the cases PUB-05, AUT-05, AST-05, SEO-03 or TRN-05 runs, in which a viewer asks for a change
- **THEN** the case passes: nothing changes and the response says the user is not allowed

```yaml clause
use: property_over_set
with:
  var: item
  set: [PUB-05, AUT-05, AST-05, SEO-03, TRN-05]
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

### Requirement: Every write is preceded by a permission check

A write tool MUST NOT succeed in a run unless a permission check succeeded in that run, and in every specialist's
procedure the `governance-checks` skill MUST come before the write.

#### Scenario: No write succeeds without a permission check in its run

- **WHEN** any write tool other than `approve_review`, which no procedure calls, succeeds in any run
- **THEN** the run contains a successful `check_permission` call

```yaml clause
use: always_on_calls
with:
  tools: [create_page, update_page_content, set_page_metadata, request_review, publish_page, schedule_publish, unpublish_page, upload_asset, attach_asset, create_translation_job, rollback_page, export_user_data]
  where: any(e.tool == 'check_permission' and e.status == 'ok' for e in run.events)
```

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
