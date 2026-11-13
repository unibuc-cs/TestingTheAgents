# FS-0206: Only supported assets are uploaded, and only existing ones are attached

**Owner:** content-ops

## Purpose

The assets agent registers files in the digital asset library and attaches assets to pages. The library holds
images, videos and PDFs only. Both the page and the asset must exist before anything is attached, and an asset
is attached to a page at most once. This describes the system as it is today.

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

### Requirement: Attaching needs an existing page and asset

Attaching MUST fail cleanly when the page or the asset does not exist, and an attached asset SHALL be listed once.

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

#### Scenario: Attaching an attached asset does not list it twice

- **GIVEN** page p1, which already carries asset a1
- **WHEN** alice asks to attach asset a1 to it
- **THEN** page p1 still carries exactly one asset

```yaml clause
use: scenario
with:
  case:
    agent: orchestrator
    request: "Attach the hero image to the home page"
    context: {user_id: alice, page_id: p1, asset_id: a1}
  expect:
    route_to: assets
    state: [["pages.p1.assets", "len", 1]]
    tools_required: [attach_asset]
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
