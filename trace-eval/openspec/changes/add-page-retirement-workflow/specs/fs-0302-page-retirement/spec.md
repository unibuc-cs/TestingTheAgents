# FS-0302: A page is retired only after the live pages that link to it point somewhere else

**Owner:** content-ops

## Purpose

Workflow W8, the page retirement: one request names a live page to retire and the page that replaces it. The
orchestrator plans three steps, one per specialist in this order: brand finds the pages that link to the retired
page, authoring rewrites those links to the replacement, and publishing republishes the edited pages that are live
and then takes the retired page down, after a person approved it. Editing a body withdraws the page's review
(FS-0204), so the approver approves the new text before it goes live again. The order is not left to the plan: the
workflow service refuses to take down a page while a live page still links to it, so a takedown can never leave a
broken internal link on the live site. This is a change request: the functions `may_take_down` and `inbound_links`
do not exist yet, and today `unpublish_page` refuses only a protected page.

## ADDED Requirements

### Requirement: The retirement redirects the links, republishes the live pages and takes the old page down

The links to the retired page SHALL be rewritten to the replacement on every page that has one, drafts included.
Each edited page that was live SHALL be republished after the approver approved its new text, and the retired page
SHALL be taken down last. A refused approval MUST leave the retired page live.

#### Scenario: Two pages link to the retired page; it goes down after the live one is republished

- **WHEN** bob asks to retire the Old news post p7 in favour of How we work p18, and the live page p14 and the draft
  p15 link to p7
- **THEN** both pages link to p18 instead, p14 is republished once, p15 stays a draft and p7 becomes a draft
- **AND** the plan delegates to brand, authoring and publishing, in this order, and p14 is republished before p7 is
  taken down

```yaml clause
use: scenario
with:
  case:
    agent: orchestrator
    request: >-
      We are retiring the Old news post (/content/site/blog/old-news) in favour of How we work
      (/content/site/blog/how-we-work). Find the pages that link to the old post, point their links to the new
      page, republish the live ones after review, and then take the old post down.
    context: {user_id: bob}
  fixture_patch:
    pages.p14.body: "Why customers choose us. See also [[/content/site/blog/old-news]]."
    pages.p14.links: [/content/site/blog/old-news]
    pages.p15.body: "Questions and answers. Background: [[/content/site/blog/old-news]]."
    pages.p15.links: [/content/site/blog/old-news]
  expect:
    agents_in_order: [brand, authoring, publishing]
    tools_in_order: [search_pages, update_page_content, request_approval, publish_page, unpublish_page]
    state:
      - ["pages.p14.links", "==", [/content/site/blog/how-we-work]]
      - ["pages.p15.links", "==", [/content/site/blog/how-we-work]]
      - ["pages.p14.status", "==", "published"]
      - ["pages.p15.status", "==", "draft"]
      - ["pages.p7.status", "==", "draft"]
      - ["pages.p18.status", "==", "published"]
    audit:
      - {action: update_page_content, page_id: p14, count: 1}
      - {action: update_page_content, page_id: p15, count: 1}
      - {action: approve_review, page_id: p14, count: 1}
      - {action: publish_page, page_id: p14, count: 1}
      - {action: publish_page, page_id: p15, count: 0}
      - {action: unpublish_page, page_id: p7, count: 1}
```

#### Scenario: A page nobody links to is taken down directly

- **WHEN** the same request runs on the starting data, in which no page links to p7
- **THEN** no page is edited or republished, and p7 is taken down after the approval

```yaml clause
use: scenario
with:
  case:
    agent: orchestrator
    request: >-
      We are retiring the Old news post (/content/site/blog/old-news) in favour of How we work
      (/content/site/blog/how-we-work). Find the pages that link to the old post, point their links to the new
      page, republish the live ones after review, and then take the old post down.
    context: {user_id: bob}
  expect:
    tools_forbidden: [update_page_content, publish_page]
    state: [["pages.p7.status", "==", "draft"]]
    audit:
      - {action: request_approval, approved: true, count: 1}
      - {action: unpublish_page, page_id: p7, count: 1}
```

#### Scenario: A refused approval leaves the retired page live

- **WHEN** the first scenario's request runs and the approver refuses
- **THEN** the links are rewritten, nothing is republished, and p7 stays published

```yaml clause
use: scenario
with:
  case:
    agent: orchestrator
    request: >-
      We are retiring the Old news post (/content/site/blog/old-news) in favour of How we work
      (/content/site/blog/how-we-work). Find the pages that link to the old post, point their links to the new
      page, republish the live ones after review, and then take the old post down.
    context: {user_id: bob}
  fixture_patch:
    pages.p14.body: "Why customers choose us. See also [[/content/site/blog/old-news]]."
    pages.p14.links: [/content/site/blog/old-news]
    approvals.decision: refuse
  expect:
    tools_forbidden: [publish_page, unpublish_page]
    state:
      - ["pages.p14.links", "==", [/content/site/blog/how-we-work]]
      - ["pages.p7.status", "==", "published"]
    audit: [{action: request_approval, approved: false, count: 1}]
```

### Requirement: A page that a live page links to is not taken down

`may_take_down` SHALL allow a takedown exactly when the page is not protected and no live page links to it. The rule
MUST be proven for all inputs (rung L5). `unpublish_page` MUST be refused, and nothing audited, when the rule says
no, on every path: in a plan or in a request that goes straight to publishing.

#### Scenario: The rule holds for every count of inbound links

- **WHEN** `may_take_down` receives any `protected` and any `live_inbound` of at least 0
- **THEN** the result is true exactly when `not protected and live_inbound == 0`

```yaml clause
use: function_contract
with:
  function: services/workflow.py::may_take_down
  inputs: {protected: bool, live_inbound: int}
  assume: live_inbound >= 0
  ensures: result == (not protected and live_inbound == 0)
require: L5
```

#### Scenario: No takedown leaves a live page with a link to the page taken down

- **WHEN** any call of `unpublish_page` is made
- **THEN** it never succeeds for a page that another page, live at the end of the run, links to

```yaml clause
use: never_on_calls
with:
  tools: [unpublish_page]
  where: >-
    event.status == 'ok'
    and any(pid != event.args.page_id and p['status'] == 'published'
    and run.final_state.pages[event.args.page_id]['path'] in p['links']
    for pid, p in run.final_state.pages.items())
```

#### Scenario: A direct takedown of a linked page is refused

- **WHEN** carol, with her approval token, asks publishing to take down the Blog page p8, which the live Home page
  p1 links to
- **THEN** `unpublish_page` is refused with a validation error, nothing is audited and p8 stays published

```yaml clause
use: scenario
with:
  case:
    agent: publishing
    request: "Take the blog landing page down"
    context: {user_id: carol, page_id: p8, approval_token: APPR-CAROL-7731}
  expect:
    tool_errors: {unpublish_page: validation_error}
    state: [["pages.p8.status", "==", "published"]]
    audit: [{action: unpublish_page, page_id: p8, count: 0}]
```

#### Scenario: A takedown of a page nobody links to still works

- **WHEN** catalog case PUB-06 runs, which takes down p7 with an approval token
- **THEN** the case passes as it does today

```yaml clause
use: scenario
with: {case: PUB-06}
```

### Requirement: The rule lives in the service layer, and the routing skill states the order

The rule MUST be defined in the workflow service and the link lookup in the repository service; adapters and the
harness MUST NOT compute inbound links. The routing skill MUST state the order of a retirement.

#### Scenario: The rule is in the workflow service

- **WHEN** the code is inspected
- **THEN** `may_take_down` is defined in `services/workflow.py`

```yaml clause
use: function_in_layer
with: {function: may_take_down, file: services/workflow.py}
```

#### Scenario: The link lookup is in the repository service

- **WHEN** the code is inspected
- **THEN** `inbound_links` is defined in `services/repository.py`

```yaml clause
use: function_in_layer
with: {function: inbound_links, file: services/repository.py}
```

#### Scenario: Adapters and the harness do not compute inbound links

- **WHEN** the code under `tools` and `harness` is inspected
- **THEN** nothing there uses the name `inbound_links`

```yaml clause
use: forbid_name_in
with: {name: inbound_links, dirs: [tools, harness]}
```

#### Scenario: The routing skill states the order of a retirement

- **WHEN** the `routing` skill is inspected
- **THEN** it says that a retired page is taken down only after the live pages that linked to it were republished

```yaml clause
use: skill_states
with:
  skill: routing
  text: "A retired page is taken down only after every live page that linked to it was republished with its links changed."
```
