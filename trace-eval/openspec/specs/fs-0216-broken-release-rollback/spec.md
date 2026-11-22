# FS-0216: A broken release is rolled back, re-checked, and republished only when its links are clean

**Owner:** content-ops

## Purpose

Workflow W5, the broken release rollback: one request restores the version of a live page from before a broken edit
and republishes it. The orchestrator plans two steps: maintenance restores the version, which checks the links of
the restored body itself, and publishing republishes the page after a person approved it. A rollback leaves the
review as it is (FS-0205), so the approver approves the restored page before it goes live again. When the restored
body has a broken link too, the plan should stop before republishing. This describes the system as it is today, with
Gemma's recorded answers.

Gemma does not stop there: in WF5-02 (one of its known mistakes) it goes on to the publishing step after the
rollback's link check failed, and only the publishing step's own link check keeps the page from going out. That case
is not used here; the rule that no page goes out after a failed link check holds in every recorded run.

## Requirements

### Requirement: The restored page goes out after its links checked clean and a new approval

A rollback SHALL restore the requested version as a new version and SHALL be followed by a link check of the page.
The page SHALL be republished after the approver approved it.

#### Scenario: A broken edit is rolled back, re-checked and republished

- **WHEN** catalog case WF5-01 runs, which restores version 1 of the welcome page p22
- **THEN** the case passes: the page has 3 versions with version 1's body, carol approves the review, and the page is
  republished

```yaml clause
use: scenario
with: {case: WF5-01}
```

#### Scenario: Every rollback is followed by a link check of the page

- **WHEN** a call of `rollback_page` succeeds in any run
- **THEN** a link check of the same page follows it in the run

```yaml clause
use: always_on_calls
with:
  tools: [rollback_page]
  where: >-
    any(e.kind == 'tool.call' and e.tool == 'validate_links' and e.args.page_id == event.args.page_id
    and e.t > event.t for e in run.events)
```

### Requirement: A failed link check keeps the page off the site

A page whose latest link check in the run found a broken link MUST NOT be published, and the routing skill MUST
stop a plan at a failed check.

#### Scenario: No page goes out after its latest link check failed

- **WHEN** any call of `publish_page` is made
- **THEN** it never succeeds for a page whose latest link check earlier in the run found a broken link

```yaml clause
use: never_on_calls
with:
  tools: [publish_page]
  where: >-
    event.status == 'ok'
    and any(v.result.broken_count > 0 for v in [e for e in run.events if e.kind == 'tool.call'
    and e.tool == 'validate_links' and e.status == 'ok' and e.args.page_id == event.args.page_id
    and e.t < event.t][-1:])
```

#### Scenario: The routing skill stops a plan at a failed check

- **WHEN** the `routing` skill is inspected
- **THEN** it says that a plan stops when a step fails, the specialist could not do it or a check failed

```yaml clause
use: skill_states
with:
  skill: routing
  text: "5. If a step fails (the specialist could not do it, or a check failed), stop: do not run the steps that depend on it."
```

#### Scenario: The rollback checks the restored body's links itself

- **WHEN** the procedure of the `rollback` skill is inspected
- **THEN** the step `restore` comes before the step including `link-validation`

```yaml clause
use: skill_step_order
with: {skill: rollback, first: {id: restore}, then: {include: link-validation}}
```
