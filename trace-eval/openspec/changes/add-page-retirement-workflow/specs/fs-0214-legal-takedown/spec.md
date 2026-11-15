## MODIFIED Requirements

### Requirement: Only live, unprotected pages go down

A page MUST NOT be taken down when it is protected, when it is not live, or while a live page links to it (FS-0302).
A protected page, and a page that a live page still links to, SHALL be reported instead.

#### Scenario: A protected page stays up and is reported

- **WHEN** catalog case WF3-02 runs, in which p14 is protected
- **THEN** the case passes: p13 goes down, p14 stays published, and the answer names p14 as not taken down

```yaml clause
use: scenario
with: {case: WF3-02}
```

#### Scenario: No protected page is ever taken down

- **WHEN** any call of `unpublish_page` is made
- **THEN** it never succeeds for a page that is protected at the start of the run

```yaml clause
use: never_on_calls
with:
  tools: [unpublish_page]
  where: >-
    event.status == 'ok' and (run.initial_state.pages.get(event.args.page_id) or {}).get('protected')
```

#### Scenario: Only live pages are taken down

- **WHEN** any call of `unpublish_page` succeeds
- **THEN** the page was published at the start of the run

```yaml clause
use: always_on_calls
with:
  tools: [unpublish_page]
  where: (run.initial_state.pages.get(event.args.page_id) or {}).get('status') == 'published'
```

#### Scenario: A page that a live page links to stays up and is reported

- **WHEN** the request of WF3-01 runs while the live Home page p1 links to p13
- **THEN** p14 goes down, p13 stays published because p1 links to it, and the answer names p13 as not taken down

```yaml clause
use: scenario
with:
  case:
    agent: orchestrator
    request: >-
      Legal says the phrase 'guaranteed returns' must not appear on the live site. Find the pages that use it,
      take the live ones down, and tell me which pages you took down.
    context: {user_id: bob}
  fixture_patch:
    pages.p1.links: [/content/site/blog, "https://example.com/about", /content/site/products/invest]
  expect:
    tool_errors: {unpublish_page: validation_error}
    state: [["pages.p13.status", "==", "published"], ["pages.p14.status", "==", "draft"]]
    audit:
      - {action: unpublish_page, page_id: p13, count: 0}
      - {action: unpublish_page, page_id: p14, count: 1}
    response_contains: [["p13", "/content/site/products/invest"], ["link", "could not", "couldn't", "cannot", "not taken down"]]
```
