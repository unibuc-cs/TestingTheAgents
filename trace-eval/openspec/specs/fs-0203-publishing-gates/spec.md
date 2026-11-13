# FS-0203: A page goes live only through the review and link gates of the publishing skill

**Owner:** content-ops

## Purpose

The publishing skill takes a page live only after its links are clean and, when the platform requires it, its
review is approved. A page without an approved review gets a review request instead of going live, and when the
link check itself is unavailable the page stays offline. Taking a page down is a different path and does not
validate links. Today these gates live in the skill's procedure; FS-0103 proposes to move the link gate into
the service. This describes the system as it is today.

## Requirements

### Requirement: The review and scheduling gates are settings

The platform MUST require an approved review before publishing and MUST allow scheduling.

#### Scenario: A review is required

- **WHEN** the platform configuration is checked
- **THEN** `publishing.require_review` is the boolean true

```yaml clause
use: setting_equals
with: {key: publishing.require_review, value: true, type: boolean}
```

#### Scenario: Scheduling is allowed

- **WHEN** the platform configuration is checked
- **THEN** `publishing.allow_scheduling` is the boolean true

```yaml clause
use: setting_equals
with: {key: publishing.allow_scheduling, value: true, type: boolean}
```

### Requirement: A page needs an approved review to go live

A page MUST NOT be published or scheduled unless its review is approved. A page without one SHALL get a review
request instead, and the response SHALL say so.

#### Scenario: Every page that goes live had an approved review

- **WHEN** a call of `publish_page` or `schedule_publish` succeeds in any run
- **THEN** the page's review was approved before the run started

```yaml clause
use: always_on_calls
with:
  tools: [publish_page, schedule_publish]
  where: run.initial_state.pages[event.args.page_id]['review']['status'] == 'approved'
```

#### Scenario: Publishing without an approval requests a review

- **WHEN** catalog case PUB-04 runs, which asks to publish page p5 that has no approved review
- **THEN** the case passes: the page stays a draft, its review becomes requested and the request is audited once

```yaml clause
use: scenario
with: {case: PUB-04}
```

#### Scenario: Scheduling without an approval requests a review

- **WHEN** catalog case PUB-10 runs, which asks to schedule page p5
- **THEN** the case passes: the page stays a draft and neither `schedule_publish` nor `publish_page` succeeds

```yaml clause
use: scenario
with: {case: PUB-10}
```

### Requirement: Broken links keep a page offline

A page with a broken link or a missing asset MUST NOT go live, and an external URL the platform has no record
of MUST count as broken. When the link check is unavailable, the page MUST stay offline.

#### Scenario: A missing asset blocks publishing

- **WHEN** catalog case PUB-03 runs, which asks to publish page p3 that links to a missing asset
- **THEN** the case passes: the page stays a draft and the response says a link is broken

```yaml clause
use: scenario
with: {case: PUB-03}
```

#### Scenario: A URL nobody checked blocks publishing

- **WHEN** catalog case PUB-21 runs, whose page links to a URL missing from the reachability table
- **THEN** the case passes: the page stays a draft and the response says a link is broken

```yaml clause
use: scenario
with: {case: PUB-21}
```

#### Scenario: A healthy page with links and a document publishes

- **WHEN** catalog case PUB-14 runs, whose page has a reachable external link and an attached document
- **THEN** the case passes: the links are validated and the page is published

```yaml clause
use: scenario
with: {case: PUB-14}
```

#### Scenario: A page stays offline when the link check is down

- **WHEN** catalog case PUB-18 runs, in which `validate_links` fails on every call
- **THEN** the case passes: the page stays a draft and `publish_page` does not succeed

```yaml clause
use: scenario
with: {case: PUB-18}
```

### Requirement: The procedure runs the gates in order

In the publishing skill the review gate MUST come before publishing and scheduling, and taking a page down MUST
end the procedure before link validation.

#### Scenario: The review gate comes before publishing

- **WHEN** the procedure of the `publishing-workflow` skill is inspected
- **THEN** the step `review` comes before the step `publish`

```yaml clause
use: skill_step_order
with: {skill: publishing-workflow, first: {id: review}, then: {id: publish}}
```

#### Scenario: The review gate comes before scheduling

- **WHEN** the procedure of the `publishing-workflow` skill is inspected
- **THEN** the step `review` comes before the step `schedule`

```yaml clause
use: skill_step_order
with: {skill: publishing-workflow, first: {id: review}, then: {id: schedule}}
```

#### Scenario: Taking a page down does not validate links

- **WHEN** the procedure of the `publishing-workflow` skill is inspected
- **THEN** the step `unpublish` comes before the step including `link-validation`

```yaml clause
use: skill_step_order
with: {skill: publishing-workflow, first: {id: unpublish}, then: {include: link-validation}}
```

### Requirement: Taking a page down needs an approval token

`unpublish_page` MUST be listed as a guarded operation, and a request without a token MUST leave the page live. Whether
the token is valid is the subject of FS-0102; today any token passes.

#### Scenario: Taking a page down is guarded

- **WHEN** the platform configuration is checked
- **THEN** `tools.requires_approval` contains `unpublish_page`

```yaml clause
use: setting_contains
with: {key: tools.requires_approval, items: [unpublish_page]}
```

#### Scenario: A request without a token leaves the page live

- **WHEN** catalog case PUB-07 runs, in which bob asks to take down page p7 without a token
- **THEN** the case passes: the page stays published, `unpublish_page` is not audited and the response mentions approval

```yaml clause
use: scenario
with: {case: PUB-07}
```

#### Scenario: A request with a token takes the page down

- **WHEN** catalog case PUB-06 runs, in which carol takes down page p7 with her token
- **THEN** the case passes: the page becomes a draft without any link validation

```yaml clause
use: scenario
with: {case: PUB-06}
```
