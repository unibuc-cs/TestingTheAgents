# FS-0104: The SEO title limit is a setting, raised to 70

**Owner:** seo-team

## Purpose

The maximum length of an SEO title is a platform setting. Raise it from 60 to 70 characters.
The SEO agent applies a requested title exactly when it is within the limit, and tells the user the
limit when it refuses. Nothing in code, skills or adapters may hold the number itself.

## Requirements

### Requirement: The title limit is a bounded platform setting

The setting `seo.max_title_length` MUST be an integer between 10 and 120, set to 70.

#### Scenario: The configured limit is valid

- **WHEN** the platform configuration is checked
- **THEN** `seo.max_title_length` is an integer between 10 and 120 with the value 70

```yaml clause
use: setting_in_range
with: {key: seo.max_title_length, min: 10, max: 120, value: 70}
```

### Requirement: A title is applied exactly when it is within the limit

The SEO agent SHALL apply a requested title when its length is at most the configured limit and MUST
refuse it otherwise, telling the user the limit.

#### Scenario: The rule holds for every title length

- **WHEN** catalog case SEO-01 runs with a requested title of any length from 1 to 120
- **THEN** `set_page_metadata` is applied exactly when the length is at most `seo.max_title_length`

```yaml clause
use: property_over_range
with:
  var: n
  min: 1
  max: 120
  scenario: {case: SEO-01, context: {seo_title: "=title_of_length(n)"}}
  ensures: applied(run, 'set_page_metadata') == (n <= config('seo.max_title_length'))
  examples: 60
```

#### Scenario: No applied title ever exceeds the limit

- **WHEN** a call of `set_page_metadata` succeeds in any run
- **THEN** its title is absent or at most `seo.max_title_length` characters long

```yaml clause
use: always_on_calls
with:
  tools: [set_page_metadata]
  where: event.args.get('title') is None or len(event.args['title']) <= config('seo.max_title_length')
```

#### Scenario: A title exactly at the limit is applied

- **WHEN** catalog case SEO-01 runs with a title of exactly `seo.max_title_length` characters
- **THEN** `set_page_metadata` is called and page p4 carries that title

```yaml clause
use: scenario
with:
  case: SEO-01
  context: {seo_title: "=title_of_length(config('seo.max_title_length'))"}
  expect:
    state: [["pages.p4.metadata.title", "==", "=title_of_length(config('seo.max_title_length'))"]]
    tools_required: [set_page_metadata]
```

#### Scenario: A title one character over the limit is refused

- **WHEN** catalog case SEO-01 runs with a title one character longer than `seo.max_title_length`
- **THEN** `set_page_metadata` is not called and page p4 keeps its title "Welcome post"
- **AND** the response states the limit

```yaml clause
use: scenario
with:
  case: SEO-01
  context: {seo_title: "=title_of_length(config('seo.max_title_length') + 1)"}
  expect:
    state: [["pages.p4.metadata.title", "==", "Welcome post"]]
    tools_forbidden: [set_page_metadata]
    response_contains: ["=str(config('seo.max_title_length'))"]
```

### Requirement: The number is held only in the setting

The new limit MUST NOT be hard-coded in tools, services or skills, and the old limit MUST NOT remain
hard-coded in tools or skills.

#### Scenario: The new limit is not hard-coded

- **WHEN** `tools`, `services` and `skills` are inspected
- **THEN** none of them hard-codes the value 70

```yaml clause
use: forbid_literal_in
with: {value: 70, dirs: [tools, services, skills]}
```

#### Scenario: The old limit is not hard-coded

- **WHEN** `tools` and `skills` are inspected
- **THEN** neither of them hard-codes the value 60

```yaml clause
use: forbid_literal_in
with: {value: 60, dirs: [tools, skills]}
```
