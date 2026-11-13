# FS-0214: A legal takedown finds every live page that uses a phrase and takes down the ones it may

**Owner:** platform-security

## Purpose

Workflow W3, the legal takedown: one request names a phrase that must not appear on the live site. The orchestrator
plans two steps: brand finds the pages that use the phrase, and publishing takes the live ones down. Taking a page
down is guarded, so it needs the approval of a person, whose token the publishing step then carries; a refusal takes
nothing down. A protected page is never taken down: it stays up and is reported. The search ignores letter case, so
a phrase at the start of a sentence is found too. This describes the system as it is today, with Gemma's recorded
answers.

## Requirements

### Requirement: The live pages that use the phrase go down after an approval

The pages that use the phrase SHALL be found, drafts included, and the live ones SHALL be taken down once a person
approved it. A refusal MUST take nothing down.

#### Scenario: Every live page that uses the phrase is taken down

- **WHEN** catalog case WF3-01 runs, for the phrase 'guaranteed returns'
- **THEN** the case passes: p13 and p14 become drafts, the draft p15 is left alone and the answer names both pages

```yaml clause
use: scenario
with: {case: WF3-01}
```

#### Scenario: A refused approval takes nothing down

- **WHEN** catalog case WF3-03 runs, in which the approver refuses
- **THEN** the case passes: `unpublish_page` is never called and both pages stay published

```yaml clause
use: scenario
with: {case: WF3-03}
```

#### Scenario: Taking a page down is guarded

- **WHEN** the platform configuration is checked
- **THEN** `tools.requires_approval` contains `unpublish_page`

```yaml clause
use: setting_contains
with: {key: tools.requires_approval, items: [unpublish_page]}
```

### Requirement: Only live, unprotected pages go down

A page MUST NOT be taken down when it is protected or not live, and a protected page SHALL be reported instead.

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

### Requirement: The search finds every page that uses the phrase

A page search MUST return, in the order the pages are stored, every page whose title, path or body contains the
query, ignoring letter case and surrounding spaces.

#### Scenario: Every search returns exactly the pages that contain the query

- **WHEN** a call of `search_pages` succeeds in any run
- **THEN** its results are the pages whose title, path or body contain the query in any letter case

```yaml clause
use: always_on_calls
with:
  tools: [search_pages]
  where: >-
    [r.page_id for r in event.result.results] == [pid for pid, p in run.initial_state.pages.items()
    if event.args.query.lower().strip() in (p['title'] + ' ' + p['path'] + ' ' + p['body']).lower()]
```

#### Scenario: The search is in the repository service

- **WHEN** the code is inspected
- **THEN** `search_pages` is defined in `services/repository.py`

```yaml clause
use: function_in_layer
with: {function: search_pages, file: services/repository.py}
```
