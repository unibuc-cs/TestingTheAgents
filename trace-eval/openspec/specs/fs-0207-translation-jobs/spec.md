# FS-0207: A translation request queues one job, for the requested or the default locales

**Owner:** content-ops

## Purpose

The translation agent queues one job per request, covering all the requested locales; when none are given it
uses the platform's default locales, which are a setting. An unsupported locale refuses the whole request. A
question about a job's status only reads, so it needs no permission check. Nothing in the platform moves a job
past `queued`. This describes the system as it is today.

## Requirements

### Requirement: The default locales are a setting

The setting `translation.default_locales` MUST list `de-DE` and `fr-FR`, and tools and skills MUST NOT hard-code
them.

#### Scenario: The defaults are configured

- **WHEN** the platform configuration is checked
- **THEN** `translation.default_locales` contains `de-DE` and `fr-FR`

```yaml clause
use: setting_contains
with: {key: translation.default_locales, items: [de-DE, fr-FR]}
```

#### Scenario: The first default is not hard-coded

- **WHEN** `tools` and `skills` are inspected
- **THEN** neither of them hard-codes the value `de-DE`

```yaml clause
use: forbid_literal_in
with: {value: de-DE, dirs: [tools, skills]}
```

#### Scenario: The second default is not hard-coded

- **WHEN** `tools` and `skills` are inspected
- **THEN** neither of them hard-codes the value `fr-FR`

```yaml clause
use: forbid_literal_in
with: {value: fr-FR, dirs: [tools, skills]}
```

### Requirement: A request queues one job

A translation request SHALL queue one job covering all its locales, and MUST use the default locales when it names
none. A request with an unsupported locale MUST queue nothing.

#### Scenario: One locale is queued and shown on the page

- **WHEN** catalog case TRN-01 runs
- **THEN** the case passes: job tj-1 covers `de-DE` and page p4 shows that locale as queued

```yaml clause
use: scenario
with: {case: TRN-01}
```

#### Scenario: No locale means the defaults

- **WHEN** catalog case TRN-02 runs, whose request names no locale
- **THEN** the case passes: job tj-1 covers `de-DE` and `fr-FR`

```yaml clause
use: scenario
with: {case: TRN-02}
```

#### Scenario: Several locales share one job

- **WHEN** catalog case TRN-07 runs, whose request names three locales
- **THEN** the case passes: job tj-1 covers all three

```yaml clause
use: scenario
with: {case: TRN-07}
```

#### Scenario: An unsupported locale queues nothing

- **WHEN** catalog case TRN-03 runs, whose request names `tlh-XX`
- **THEN** the case passes: no job exists and the response says the request could not be completed

```yaml clause
use: scenario
with: {case: TRN-03}
```

#### Scenario: Every queued job names at least one locale

- **WHEN** a call of `create_translation_job` succeeds in any run
- **THEN** its locale list is not empty

```yaml clause
use: always_on_calls
with:
  tools: [create_translation_job]
  where: len(event.args.locales) >= 1
```

### Requirement: A status question only reads

A question about a job's status MUST be answered from the job and MUST NOT create a job or ask for a permission.

#### Scenario: A status question reports the job

- **WHEN** catalog case TRN-04 runs, which asks about job tj-1
- **THEN** the case passes: the response names its status, and neither `create_translation_job` nor `check_permission` succeeds

```yaml clause
use: scenario
with: {case: TRN-04}
```

#### Scenario: The status path comes before the permission check

- **WHEN** the procedure of the `translation` skill is inspected
- **THEN** the step `status` comes before the step including `governance-checks`

```yaml clause
use: skill_step_order
with: {skill: translation, first: {id: status}, then: {include: governance-checks}}
```

#### Scenario: Creating a job is checked first

- **WHEN** the procedure of the `translation` skill is inspected
- **THEN** the step including `governance-checks` comes before the step `job`

```yaml clause
use: skill_step_order
with: {skill: translation, first: {include: governance-checks}, then: {id: job}}
```
