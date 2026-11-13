# FS-0206: Only supported assets are uploaded, and only existing, licensed ones are attached

**Owner:** content-ops

## Purpose

The assets agent registers files in the digital asset library, finds assets by their tags and attaches assets to
pages. The library holds images, videos and PDFs only. Both the page and the asset must exist before anything is
attached, and an asset whose licence has expired is never used. This describes the system as it is today, with
Gemma's recorded answers.

The repository also lists an asset once when it is attached again, but no catalog case attaches an asset twice,
so nothing here can check that without recording a new case.

## Requirements

### Requirement: Uploads hold images, videos and PDFs only

An upload of another file type MUST be refused and MUST register nothing. An accepted upload SHALL be attached to
the page in the same request.

#### Scenario: An image is uploaded and attached

- **WHEN** catalog case AST-02 runs
- **THEN** the case passes: asset a100 exists, page p4 carries it and the upload is audited once

```yaml clause
use: scenario
with: {case: AST-02}
```

#### Scenario: A PDF is uploaded and attached

- **WHEN** catalog case AST-08 runs
- **THEN** the case passes: page p3 carries asset a100, whose type is `application/pdf`

```yaml clause
use: scenario
with: {case: AST-08}
```

#### Scenario: Another file type registers nothing

- **WHEN** catalog case AST-03 runs, which uploads a `text/plain` file
- **THEN** the case passes: no asset is created, nothing is attached and the response says the request could not be completed

```yaml clause
use: scenario
with: {case: AST-03}
```

#### Scenario: No upload of another type is ever registered

- **WHEN** any call of `upload_asset` is made
- **THEN** it never succeeds for a file whose type is not an image, a video or a PDF

```yaml clause
use: never_on_calls
with:
  tools: [upload_asset]
  where: >-
    event.status == 'ok' and not str(event.args.mime).startswith(('image/', 'video/', 'application/pdf'))
```

### Requirement: Attaching needs an existing page and asset

Attaching MUST fail cleanly when the page or the asset does not exist.

#### Scenario: An existing asset is attached

- **WHEN** catalog case AST-01 runs
- **THEN** the case passes: page p4 carries asset a1

```yaml clause
use: scenario
with: {case: AST-01}
```

#### Scenario: An unknown page attaches nothing

- **WHEN** catalog case AST-04 runs, which names page p99
- **THEN** the case passes: `attach_asset` does not succeed and the response says the request could not be completed

```yaml clause
use: scenario
with: {case: AST-04}
```

#### Scenario: A missing asset attaches nothing

- **WHEN** catalog case AST-07 runs, which names asset a9
- **THEN** the case passes: page p4 carries no assets and the response says the request could not be completed

```yaml clause
use: scenario
with: {case: AST-07}
```

#### Scenario: Every attached asset exists

- **WHEN** a call of `attach_asset` succeeds in any run
- **THEN** the asset exists in the library at the end of the run

```yaml clause
use: always_on_calls
with:
  tools: [attach_asset]
  where: event.args.asset_id in run.final_state.assets
```

### Requirement: Only licensed assets are used

A search by tags SHALL list every matching asset with its licence, and an asset described by its tags MUST be the
first match whose licence is valid. An asset whose licence has expired MUST NOT be attached.

#### Scenario: A search by tag lists the matching assets

- **WHEN** catalog case AST-09 runs, which asks for the images tagged spring
- **THEN** the case passes: the answer lists the matching assets

```yaml clause
use: scenario
with: {case: AST-09}
```

#### Scenario: An asset described by tags is a licensed one

- **WHEN** catalog case AST-10 runs, which asks for a spring hero image on the welcome post
- **THEN** the case passes: the licensed match is attached, not the expired banner a3

```yaml clause
use: scenario
with: {case: AST-10}
```

#### Scenario: No run attaches an asset whose licence has expired

- **WHEN** any call of `attach_asset` is made
- **THEN** it never succeeds for an asset whose licence is `expired`

```yaml clause
use: never_on_calls
with:
  tools: [attach_asset]
  where: event.status == 'ok' and run.final_state.assets[event.args.asset_id].get('license') == 'expired'
```

### Requirement: The procedure confirms the page before attaching

The skill MUST fetch the page before it attaches an asset, and the asset logic MUST be defined in
`services/repository.py`.

#### Scenario: The page is fetched first

- **WHEN** the procedure of the `asset-management` skill is inspected
- **THEN** the step `fetch` comes before the step `attach`

```yaml clause
use: skill_step_order
with: {skill: asset-management, first: {id: fetch}, then: {id: attach}}
```

#### Scenario: The upload rule is in the repository service

- **WHEN** the code is inspected
- **THEN** `upload_asset` is defined in `services/repository.py`

```yaml clause
use: function_in_layer
with: {function: upload_asset, file: services/repository.py}
```
