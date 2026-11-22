# FS-0219: Page rankings follow the analytics, and the site health check reports every issue

**Owner:** seo-team

## Purpose

The insights agent reports how pages perform: one page's views, bounce rate and conversions, or a ranking of the
live pages of a section by views, fewest first for the worst and most first for the best. The optimizer runs a
health check of a section, which lists per live page its broken links, attached assets without alt text, a missing
meta description and a load time over the configured limit, and it sets an asset's alt text. The ranking and the
health check are the first two steps of a site optimization (FS-0213). This describes the system as it is today,
with Gemma's recorded answers.

## Requirements

### Requirement: A ranking is the live pages of the section, ordered by views

A ranking MUST list only live pages under the section, the section page itself excluded, ordered by views: fewest
first for "worst", most first for "best". One page's numbers SHALL be reported as the analytics give them.

#### Scenario: The three worst blog posts, in order

- **WHEN** catalog case INS-01 runs
- **THEN** the case passes: the answer lists p7, p17 and p16, the posts with the fewest views

```yaml clause
use: scenario
with: {case: INS-01}
```

#### Scenario: One page's views

- **WHEN** catalog case INS-02 runs, for the home page p1
- **THEN** the case passes: the answer says 12000 views

```yaml clause
use: scenario
with: {case: INS-02}
```

#### Scenario: The two best blog posts

- **WHEN** catalog case INS-03 runs
- **THEN** the case passes: the answer lists the two posts with the most views

```yaml clause
use: scenario
with: {case: INS-03}
```

#### Scenario: Every ranking is ordered by views

- **WHEN** a call of `get_page_metrics` that ranks a section succeeds in any run
- **THEN** its pages are in ascending order of views for "worst" and descending for "best"

```yaml clause
use: always_on_calls
with:
  tools: [get_page_metrics]
  where: >-
    bool(event.args.page_id) or [p.views for p in event.result.pages]
    == sorted([p.views for p in event.result.pages], reverse=(event.args.order == 'best'))
```

#### Scenario: Every ranking lists only live pages of the section

- **WHEN** a call of `get_page_metrics` that ranks a section succeeds in any run
- **THEN** every page it lists was published at the start of the run and lies under the section

```yaml clause
use: always_on_calls
with:
  tools: [get_page_metrics]
  where: >-
    bool(event.args.page_id) or all(run.initial_state.pages[p.page_id]['status'] == 'published'
    and run.initial_state.pages[p.page_id]['path'].startswith(event.args.section.rstrip('/') + '/')
    for p in event.result.pages)
```

### Requirement: The health check reports every issue of every live page

A health check MUST report, for every live page under the section, each attached asset without alt text and a
missing meta description, as well as broken links and slow pages. The slow-page limit MUST be a setting.

#### Scenario: A health check of the blog lists every page with an issue

- **WHEN** catalog case OPT-01 runs
- **THEN** the case passes: the answer names every blog page with an issue

```yaml clause
use: scenario
with: {case: OPT-01}
```

#### Scenario: Every image without alt text is reported

- **WHEN** a call of `audit_site` succeeds in any run
- **THEN** every asset without alt text on a live page under the section is reported for that page

```yaml clause
use: always_on_calls
with:
  tools: [audit_site]
  where: >-
    all(any(p.page_id == pid and ('asset ' + a + ' has no alt text') in p.issues for p in event.result.pages)
    for pid, pg in run.initial_state.pages.items()
    if pg['status'] == 'published' and pg['path'].startswith(event.args.section.rstrip('/') + '/')
    for a in pg.get('assets', []) if not run.initial_state.assets.get(a, {}).get('alt'))
```

#### Scenario: Every missing description is reported

- **WHEN** a call of `audit_site` succeeds in any run
- **THEN** every live page under the section without a meta description is reported for it

```yaml clause
use: always_on_calls
with:
  tools: [audit_site]
  where: >-
    all(any(p.page_id == pid and 'no meta description' in p.issues for p in event.result.pages)
    for pid, pg in run.initial_state.pages.items()
    if pg['status'] == 'published' and pg['path'].startswith(event.args.section.rstrip('/') + '/')
    and not pg.get('metadata', {}).get('description'))
```

#### Scenario: The slow-page limit is configured

- **WHEN** the platform configuration is checked
- **THEN** `optimizer.max_load_ms` is an integer between 500 and 30000 with the value 3000

```yaml clause
use: setting_in_range
with: {key: optimizer.max_load_ms, min: 500, max: 30000, value: 3000}
```

### Requirement: An alt text is set by someone allowed to edit

Setting an alt text SHALL change only that asset's alt text, and a viewer MUST be refused.

#### Scenario: The alt text of an image is set

- **WHEN** catalog case OPT-02 runs, for the team photo a5
- **THEN** the case passes: the permission is checked and a5 has the new alt text

```yaml clause
use: scenario
with: {case: OPT-02}
```

#### Scenario: A viewer cannot change an alt text

- **WHEN** catalog case OPT-03 runs, in which a viewer asks
- **THEN** the case passes: the alt text stays as it was

```yaml clause
use: scenario
with: {case: OPT-03}
```

#### Scenario: Ranking and health check are in the site service

- **WHEN** the code is inspected
- **THEN** `audit_site` is defined in `services/site.py`

```yaml clause
use: function_in_layer
with: {function: audit_site, file: services/site.py}
```
