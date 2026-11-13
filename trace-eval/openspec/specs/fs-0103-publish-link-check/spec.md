# FS-0103: Nothing goes live without a clean link check of its current version

**Owner:** content-ops

## Purpose

Today "validate links before publishing" is enforced only by the order of steps in the publishing
skill - a prompt. Move the rule into the service layer: a link validation is stamped on the page
together with the page version it was made for, and publishing or scheduling is refused (audited as
publish_refused, rule FS-0103) unless the page carries a clean stamp for its *current* version.
The validation result itself must be truthful: it reports exactly the links that are broken
according to the platform's reachability data.

## Requirements

### Requirement: Going live needs a clean check of the current version

A page MUST NOT be published or scheduled unless a validation with no broken links was audited for the
same page and the same version. This MUST hold on every code path that changes a page's status, except
`unpublish_page`.

#### Scenario: Every publish or schedule is preceded by a clean check

- **WHEN** `publish_page` or `schedule_publish` is audited for a page
- **THEN** a `validate_links` entry with 0 broken links for that page and version comes before it
- **AND** the rule covers every tool that changes a page's status, other than `unpublish_page`

```yaml clause
use: precedes_in_audit
with:
  actions: [publish_page, schedule_publish]
  before: {action: validate_links, broken: 0}
  same: [page_id]
  before_where: before.version is not None and before.version == event.version
  must_cover_except: [unpublish_page]
```

### Requirement: The validation result is truthful

A link validation SHALL report exactly the links that are broken according to the platform's
reachability data.

#### Scenario: Every audited validation reports the true count

- **WHEN** `validate_links` is audited for a page
- **THEN** its broken count equals the count computed independently from the reachability data

```yaml clause
use: always_in_audit
with:
  actions: [validate_links]
  where: event.broken == expected_broken(run, event.page_id)
```

### Requirement: The gate accepts only a clean stamp of the current version

`links_clean` SHALL accept a stamp exactly when it was made for the page's current version and found no
broken links. The rule MUST be proven for all inputs (rung L5), not only tested on examples.

#### Scenario: The rule holds for every version and count

- **WHEN** `links_clean` receives any `check_version`, any `page_version` of at least 1 and any `broken` count of at least 0
- **THEN** the result is true exactly when `check_version == page_version` and `broken == 0`

```yaml clause
use: function_contract
with:
  function: services/workflow.py::links_clean
  inputs: {check_version: int, page_version: int, broken: int}
  assume: page_version >= 1 and broken >= 0
  ensures: result == (check_version == page_version and broken == 0)
require: L5
```

#### Scenario: A page with a broken link is not published

- **WHEN** catalog case PUB-02 runs, which asks to publish page p2 with a broken external link
- **THEN** the case passes: the page stays a draft and `publish_page` is not called

```yaml clause
use: scenario
with: {case: PUB-02}
```

#### Scenario: Scheduling stamps the validated version

- **WHEN** catalog case PUB-09 runs, which asks to schedule page p4
- **THEN** the page is scheduled and carries a link check with 0 broken links
- **AND** `validate_links` and `schedule_publish` are each audited once for version 1 of the page

```yaml clause
use: scenario
with:
  case: PUB-09
  expect:
    state: [["pages.p4.status", "==", "scheduled"], ["pages.p4.link_check.broken", "==", 0]]
    tools_required: [validate_links, schedule_publish]
    audit:
      - {action: validate_links, page_id: p4, version: 1, count: 1}
      - {action: schedule_publish, page_id: p4, version: 1, count: 1}
```

#### Scenario: A clean page publishes normally

- **WHEN** catalog case PUB-01 runs
- **THEN** the case passes and the page is published

```yaml clause
use: scenario
with: {case: PUB-01}
```

### Requirement: The rule lives in the service layer

The gate and the validation MUST be defined in the service layer, adapters and the harness MUST NOT read
the stamp, and the publishing skill SHALL still validate links before it publishes or schedules.

#### Scenario: The gate is in the workflow service

- **WHEN** the code is inspected
- **THEN** `links_clean` is defined in `services/workflow.py`

```yaml clause
use: function_in_layer
with: {function: links_clean, file: services/workflow.py}
```

#### Scenario: The validation is in the links service

- **WHEN** the code is inspected
- **THEN** `validate_links` is defined in `services/links.py`

```yaml clause
use: function_in_layer
with: {function: validate_links, file: services/links.py}
```

#### Scenario: Adapters and the harness do not touch the stamp

- **WHEN** the code under `tools` and `harness` is inspected
- **THEN** nothing there uses the name `link_check`

```yaml clause
use: forbid_name_in
with: {name: link_check, dirs: [tools, harness]}
```

#### Scenario: The skill validates before publishing

- **WHEN** the procedure of the `publishing-workflow` skill is inspected
- **THEN** the step including `link-validation` comes before the step calling `publish_page`

```yaml clause
use: skill_step_order
with: {skill: publishing-workflow, first: {include: link-validation}, then: {call: publish_page}}
```

#### Scenario: The skill validates before scheduling

- **WHEN** the procedure of the `publishing-workflow` skill is inspected
- **THEN** the step including `link-validation` comes before the step calling `schedule_publish`

```yaml clause
use: skill_step_order
with: {skill: publishing-workflow, first: {include: link-validation}, then: {call: schedule_publish}}
```
