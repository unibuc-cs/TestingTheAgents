# FS-0213: A site optimization republishes every fixed page whose links are clean, and only those

**Owner:** seo-team

## Purpose

Workflow W2, the site optimization: one request finds the worst-performing pages of a section, runs a health check
of the section, fixes the pages' SEO and republishes them. The orchestrator plans four steps, one per specialist in
this order: insights, optimizer, seo, publishing. A page without a meta description gets its title as its
description. Before republishing, the publishing step checks each page's links: a page with a broken link stays as
it was and is reported, and the other pages still go out, because the same action on another page does not depend
on it. This describes the system as it is today, with Gemma's recorded answers.

The ranking and the health check themselves are the subject of FS-0219. In WF2-03, where the broken page is ranked
first, Gemma sends all three pages to publishing in one step, publishing stops at the broken one, and the
orchestrator tells the user the other two were republished when they were not: one of Gemma's known mistakes, so that
case is not used here.

## Requirements

### Requirement: The fixed pages are republished, except one with a broken link

The pages the ranking returns SHALL get their SEO fixed and be republished after an approval. A page whose link check
finds a broken link MUST NOT be republished, and the others MUST still be.

#### Scenario: Three pages are fixed and republished

- **WHEN** catalog case WF2-01 runs, in which none of the three pages has a broken link
- **THEN** the case passes: p17 gets its title as its description, and p7, p17 and p16 are each republished once

```yaml clause
use: scenario
with: {case: WF2-01}
```

#### Scenario: The page with a broken link stays as it was; the others go out

- **WHEN** catalog case WF2-02 runs, in which p16 links to a page that does not exist
- **THEN** the case passes: p7 and p17 are republished, p16 is not, and the answer names p16 and its broken link

```yaml clause
use: scenario
with: {case: WF2-02}
```

#### Scenario: No page is published while its last link check found a broken link

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

### Requirement: The routing skill keeps independent pages going

The `routing` skill MUST tell the orchestrator that the same action on other pages does not depend on a failed step,
so a plan goes on with those pages and reports every failure.

#### Scenario: A failure on one page does not stop the others

- **WHEN** the `routing` skill is inspected
- **THEN** it says that the same action on other pages does not depend on a failed step

```yaml clause
use: skill_states
with:
  skill: routing
  text: "The same action on other pages does not depend on it: go on with those, and report every failure."
```

#### Scenario: Publishing checks the links before it publishes

- **WHEN** the procedure of the `publishing-workflow` skill is inspected
- **THEN** the step including `link-validation` comes before the step `publish`

```yaml clause
use: skill_step_order
with: {skill: publishing-workflow, first: {include: link-validation}, then: {id: publish}}
```
