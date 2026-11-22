# FS-0215: A price change is translated into each supported language and republished after a new review

**Owner:** content-ops

## Purpose

Workflow W4, the localized price update: one request changes the body of a live page, has every translation of it
redone, one job per language, and republishes it after review. The orchestrator plans the steps in this order:
authoring, translation (once per language), publishing. Editing the body withdraws the page's review (FS-0204), so
the approver approves the new text before it goes live again. A language the platform does not translate into is
refused on its own; the other languages are still queued and the page still goes out. This describes the system as
it is today, with Gemma's recorded answers.

## Requirements

### Requirement: The new text is translated and republished after a new approval

The edit SHALL be saved, one translation job SHALL be queued per supported language, and the page SHALL be
republished only after the approver approved the edited text.

#### Scenario: The price is changed, translated three times and republished

- **WHEN** catalog case WF4-01 runs, for French, German and Spanish
- **THEN** the case passes: the body says €49, jobs tj-1 to tj-3 are queued, carol approves the review and the
  page is republished once

```yaml clause
use: scenario
with: {case: WF4-01}
```

#### Scenario: An unsupported language fails alone

- **WHEN** catalog case WF4-02 runs, for French, German and Brazilian Portuguese
- **THEN** the case passes: the pt-BR job is refused, the other two are queued, and the page is still republished

```yaml clause
use: scenario
with: {case: WF4-02}
```

### Requirement: Only supported languages are queued

A translation job MUST name only locales the platform translates into (de-DE, fr-FR, es-ES, it-IT, ja-JP and ro-RO),
and a job that names another one MUST be refused whole.

#### Scenario: Every queued job names supported locales only

- **WHEN** a call of `create_translation_job` succeeds in any run
- **THEN** every locale it names is one of the supported ones

```yaml clause
use: always_on_calls
with:
  tools: [create_translation_job]
  where: >-
    all(loc in ('de-DE', 'fr-FR', 'es-ES', 'it-IT', 'ja-JP', 'ro-RO') for loc in event.result.locales)
```

#### Scenario: The supported locales are listed in the translation service

- **WHEN** the code under `tools` and `skills` is inspected
- **THEN** nothing there hard-codes the locale `ro-RO`, which only the translation service lists

```yaml clause
use: forbid_literal_in
with: {value: ro-RO, dirs: [tools, skills]}
```
