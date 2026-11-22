# FS-0217: A privacy request exports a consenting subject's data and republishes the pages without their name

**Owner:** platform-security

## Purpose

Workflow W6, the privacy request: one request exports a data subject's personal data and removes their name from
the bylines of their pages, which are then republished. The orchestrator plans the steps in this order: governance
(the export), authoring (one edit per page), publishing (after a person approved it). The export is guarded: it runs
only for an admin with their own approval token, and only for a subject who has consented (FS-0209). Editing a body
withdraws the page's review, so the approver approves the new text before it goes live again. This describes the
system as it is today, with Gemma's recorded answers.

The routing skill says that steps which do not depend on a failed one go on, so a refused export should not stop
the byline edits. Gemma stops the whole plan instead in WF6-02 (one of its known mistakes), so that case is not used
here.

## Requirements

### Requirement: The data is exported and the bylines removed

For a consenting subject, the export SHALL run and each page SHALL be edited, approved and republished.

#### Scenario: A consenting subject's data is exported and their name removed

- **WHEN** catalog case WF6-01 runs, for subject s1 and pages p7 and p17
- **THEN** the case passes: export exp-s1 is audited, both bodies lose the byline, carol approves both reviews and
  both pages are republished

```yaml clause
use: scenario
with: {case: WF6-01}
```

### Requirement: An export is made by an admin with their own token, for a subject who consented

An export MUST carry the approval token of the user who asked for it, that user MUST be an admin, and the subject
MUST have consented. Consent is checked by the governance skill, not by the service.

#### Scenario: Every export carries the requester's own token

- **WHEN** a call of `export_user_data` succeeds in any run
- **THEN** the approval token it was made with belongs to the user who made the request

```yaml clause
use: always_on_calls
with:
  tools: [export_user_data]
  where: token_owner(run, call_token(run, event)) == run.context.user_id
```

#### Scenario: Every export is for a subject who consented

- **WHEN** a call of `export_user_data` succeeds in any run
- **THEN** the subject has a consent on record at the start of the run

```yaml clause
use: always_on_calls
with:
  tools: [export_user_data]
  where: bool(run.initial_state.consents.get(event.args.subject_id))
```

#### Scenario: Consent is checked before the export

- **WHEN** the procedure of the `governance-ops` skill is inspected
- **THEN** the step `consent` comes before the step `export`

```yaml clause
use: skill_step_order
with: {skill: governance-ops, first: {id: consent}, then: {id: export}}
```

### Requirement: The routing skill keeps independent steps going

The `routing` skill MUST tell the orchestrator to go on with the steps that do not depend on a failed one.

#### Scenario: A failed step stops only what depends on it

- **WHEN** the `routing` skill is inspected
- **THEN** it says that a failed step stops only the steps that depend on it

```yaml clause
use: skill_states
with: {skill: routing, text: "do not run the steps that depend on it."}
```
