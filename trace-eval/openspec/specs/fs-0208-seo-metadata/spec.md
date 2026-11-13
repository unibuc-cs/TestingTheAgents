# FS-0208: SEO metadata is applied field by field and the new score is reported

**Owner:** seo-team

## Purpose

The SEO agent reads a page's report, applies the requested metadata and quotes the new score. Only the fields a
request names change, a title over the configured limit changes nothing, and the SEO title never renames the page.
The title limit's value is the subject of FS-0104, so nothing here pins it: every check reads it from the
configuration. This describes the system as it is today.

## Requirements

### Requirement: A description is required for a full score

The setting `seo.require_description` MUST be the boolean true.

#### Scenario: A description is required

- **WHEN** the platform configuration is checked
- **THEN** `seo.require_description` is the boolean true

```yaml clause
use: setting_equals
with: {key: seo.require_description, value: true, type: boolean}
```

### Requirement: Metadata is applied field by field

Applying metadata SHALL change only the fields the request names, and the response MUST quote the new score.

#### Scenario: Title, description and keywords are applied

- **WHEN** catalog case SEO-01 runs
- **THEN** the case passes: page p4 has the requested title and description and the score is now 100

```yaml clause
use: scenario
with: {case: SEO-01}
```

#### Scenario: Setting a description keeps the title

- **WHEN** catalog case SEO-04 runs, whose request gives a description and keywords
- **THEN** the case passes: page p2 keeps its title and gains the description

```yaml clause
use: scenario
with: {case: SEO-04}
```

#### Scenario: Setting a title keeps the description and keywords

- **WHEN** catalog case SEO-08 runs, whose request gives only a title
- **THEN** the case passes: page p4 gains the title and keeps its description and keywords

```yaml clause
use: scenario
with: {case: SEO-08}
```

#### Scenario: Setting keywords is confirmed with the score

- **WHEN** catalog case SEO-07 runs, whose request gives only keywords and whose answer is judged
- **THEN** the case passes: page p1 has the keywords and the response quotes the score

```yaml clause
use: scenario
with: {case: SEO-07}
```

### Requirement: A title over the limit changes nothing

A title longer than `seo.max_title_length` MUST be refused without any change, and a title within it MUST be
accepted.

#### Scenario: An over-long title is refused

- **WHEN** catalog case SEO-02 runs, whose title is longer than the limit
- **THEN** the case passes: `set_page_metadata` does not succeed and the response says the title is above the limit

```yaml clause
use: scenario
with: {case: SEO-02}
```

#### Scenario: A long title within the limit is accepted

- **WHEN** catalog case SEO-05 runs, whose title has 60 characters
- **THEN** the case passes: page p4 has that title

```yaml clause
use: scenario
with: {case: SEO-05}
```

### Requirement: The SEO title does not rename the page

The SEO title MUST be stored in the page's metadata and MUST NOT change the page's own title.

#### Scenario: The page keeps its own title

- **GIVEN** page p4, whose own title is "Welcome post"
- **WHEN** catalog case SEO-01 runs with its requested SEO title
- **THEN** the page's own title is still "Welcome post"

```yaml clause
use: scenario
with:
  case: SEO-01
  expect:
    state: [["pages.p4.title", "==", "Welcome post"], ["pages.p4.metadata.title", "==", "Welcome to Example"]]
    tools_required: [set_page_metadata]
```

### Requirement: The procedure verifies its own work

The skill MUST read the report before it applies metadata, and MUST read it again afterwards.

#### Scenario: The report is read first

- **WHEN** the procedure of the `seo-metadata` skill is inspected
- **THEN** the step `report` comes before the step `meta`

```yaml clause
use: skill_step_order
with: {skill: seo-metadata, first: {id: report}, then: {id: meta}}
```

#### Scenario: The report is read again afterwards

- **WHEN** the procedure of the `seo-metadata` skill is inspected
- **THEN** the step `meta` comes before the step `verify`

```yaml clause
use: skill_step_order
with: {skill: seo-metadata, first: {id: meta}, then: {id: verify}}
```

#### Scenario: The scoring is in the SEO service

- **WHEN** the code is inspected
- **THEN** `get_seo_report` is defined in `services/seo.py`

```yaml clause
use: function_in_layer
with: {function: get_seo_report, file: services/seo.py}
```
