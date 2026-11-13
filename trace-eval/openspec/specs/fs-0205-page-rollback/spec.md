# FS-0205: A rollback restores the requested version without rewriting history

**Owner:** content-ops

## Purpose

The maintenance agent restores an earlier version of a page. History is never rewritten: the old body is saved
again as a new version. Rolling back is reserved for admins, the requested version must exist, and the links of
the restored body are validated afterwards. Unlike an edit, a rollback leaves the page's review as it is. This
describes the system as it is today.

## Requirements

### Requirement: The requested version is restored

A rollback SHALL make the body of the requested version the current body, with its links. A version that does not
exist MUST change nothing.

#### Scenario: A page is restored to an earlier version

- **WHEN** catalog case MNT-01 runs, which restores version 2 of page p5
- **THEN** the case passes: the page has the body of version 2 and 4 versions in all

```yaml clause
use: scenario
with: {case: MNT-01}
```

#### Scenario: The links follow the restored body

- **WHEN** catalog case MNT-04 runs, which restores the first version of page p1
- **THEN** the case passes: the page has the old body and no links

```yaml clause
use: scenario
with: {case: MNT-04}
```

#### Scenario: A missing version changes nothing

- **WHEN** catalog case MNT-02 runs, which asks for version 9 of page p5
- **THEN** the case passes: the page keeps its 3 versions and the response says the request could not be completed

```yaml clause
use: scenario
with: {case: MNT-02}
```

### Requirement: History is only ever added to

A rollback MUST add exactly one version and MUST NOT change the page's review.

#### Scenario: Every rollback adds exactly one version

- **WHEN** a call of `rollback_page` succeeds in any run
- **THEN** the page has one version more at the end of the run than at the start

```yaml clause
use: always_on_calls
with:
  tools: [rollback_page]
  where: len(run.final_state.pages[event.args.page_id]['versions']) == len(run.initial_state.pages[event.args.page_id]['versions']) + 1
```

#### Scenario: A rollback leaves the review as it is

- **WHEN** a call of `rollback_page` succeeds in any run
- **THEN** the page's review at the end of the run equals its review at the start

```yaml clause
use: always_on_calls
with:
  tools: [rollback_page]
  where: run.final_state.pages[event.args.page_id]['review'] == run.initial_state.pages[event.args.page_id]['review']
```

### Requirement: A rollback is checked before and after

The skill MUST check the permission and list the versions before it restores, and MUST validate links after it
restores. A broken link in the restored body SHALL be reported to the user.

#### Scenario: The permission is checked first

- **WHEN** the procedure of the `rollback` skill is inspected
- **THEN** the step including `governance-checks` comes before the step calling `rollback_page`

```yaml clause
use: skill_step_order
with: {skill: rollback, first: {include: governance-checks}, then: {call: rollback_page}}
```

#### Scenario: The versions are listed first

- **WHEN** the procedure of the `rollback` skill is inspected
- **THEN** the step `versions` comes before the step `restore`

```yaml clause
use: skill_step_order
with: {skill: rollback, first: {id: versions}, then: {id: restore}}
```

#### Scenario: The links are validated afterwards

- **WHEN** the procedure of the `rollback` skill is inspected
- **THEN** the step `restore` comes before the step including `link-validation`

```yaml clause
use: skill_step_order
with: {skill: rollback, first: {id: restore}, then: {include: link-validation}}
```

#### Scenario: A broken link in the restored body is reported

- **WHEN** catalog case MNT-05 runs, which restores a version of page p2 with a broken link
- **THEN** the case passes: the new version exists and the response says a link is broken

```yaml clause
use: scenario
with: {case: MNT-05}
```

### Requirement: The restoring logic is in the repository service

The rollback MUST be defined in `services/repository.py`.

#### Scenario: The rollback is in the repository service

- **WHEN** the code is inspected
- **THEN** `rollback_page` is defined in `services/repository.py`

```yaml clause
use: function_in_layer
with: {function: rollback_page, file: services/repository.py}
```
