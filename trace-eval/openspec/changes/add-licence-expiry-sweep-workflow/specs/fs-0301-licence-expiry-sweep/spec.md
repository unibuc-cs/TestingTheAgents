# FS-0301: An expired asset is replaced on every page that uses it, and the live pages are republished

**Owner:** content-ops

## Purpose

Workflow W7, the licence expiry sweep: one request names an asset whose licence has expired. The orchestrator plans
three steps, one per specialist in this order: assets finds every page the asset is attached to and replaces it there
with a licensed asset, brand checks each of those pages against the brand guidelines, and publishing republishes the
ones that are live, after a person approved it. A page that was a draft stays a draft. When no licensed replacement
exists, nothing is replaced and nothing is republished. The replacement rule is enforced in the repository service:
an asset is replaced only by a licensed one, on a page that carries the old one. This is a change request: the tools
`find_asset_usage` and `replace_asset`, the functions behind them and the cases named below do not exist yet.

## ADDED Requirements

### Requirement: The sweep replaces the expired asset everywhere and republishes the live pages

The expired asset SHALL be replaced on every page it is attached to, drafts included. Each page that was live SHALL
be republished once, after a person approved it, and a page that was a draft MUST stay a draft.

#### Scenario: The asset is replaced on a live page and on a draft

- **WHEN** bob asks to replace the expired asset a3 with a licensed image tagged spring hero, and a3 is attached to
  the live page p16 and to the draft p20
- **THEN** both pages carry a4 instead of a3, p16 is republished once and p20 stays a draft
- **AND** the plan delegates to assets, brand and publishing, in this order

```yaml clause
use: scenario
with:
  case:
    agent: orchestrator
    request: >-
      The licence of the spring banner (asset a3) has expired. Replace it on every page that uses it with a
      licensed image tagged spring hero, check those pages against the brand rules, and republish the live ones.
    context: {user_id: bob}
  fixture_patch:
    pages.p16.assets: [a3]
  expect:
    agents_in_order: [assets, brand, publishing]
    tools_in_order: [find_asset_usage, replace_asset, check_brand_policy, request_approval, publish_page]
    state:
      - ["pages.p16.assets", "==", [a4]]
      - ["pages.p20.assets", "==", [a4]]
      - ["pages.p16.status", "==", "published"]
      - ["pages.p20.status", "==", "draft"]
    audit:
      - {action: replace_asset, page_id: p16, count: 1}
      - {action: replace_asset, page_id: p20, count: 1}
      - {action: publish_page, page_id: p16, count: 1}
      - {action: publish_page, page_id: p20, count: 0}
```

#### Scenario: Without a licensed replacement nothing changes

- **WHEN** the same request runs while a4, the only other spring hero image, has an expired licence too
- **THEN** no asset is replaced, no page is republished, and the answer says that no licensed replacement was found

```yaml clause
use: scenario
with:
  case:
    agent: orchestrator
    request: >-
      The licence of the spring banner (asset a3) has expired. Replace it on every page that uses it with a
      licensed image tagged spring hero, check those pages against the brand rules, and republish the live ones.
    context: {user_id: bob}
  fixture_patch:
    pages.p16.assets: [a3]
    assets.a4.license: expired
  expect:
    tools_forbidden: [replace_asset, publish_page]
    state:
      - ["pages.p16.assets", "==", [a3]]
      - ["pages.p20.assets", "==", [a3]]
    response_contains: [["no licensed", "not replaced", "could not", "couldn't", "cannot"]]
```

#### Scenario: A refused approval republishes nothing

- **WHEN** the same request runs and the approver refuses
- **THEN** the asset is replaced on both pages, the refusal is audited, and `publish_page` is never called

```yaml clause
use: scenario
with:
  case:
    agent: orchestrator
    request: >-
      The licence of the spring banner (asset a3) has expired. Replace it on every page that uses it with a
      licensed image tagged spring hero, check those pages against the brand rules, and republish the live ones.
    context: {user_id: bob}
  fixture_patch:
    pages.p16.assets: [a3]
    approvals.decision: refuse
  expect:
    tools_forbidden: [publish_page]
    state:
      - ["pages.p16.assets", "==", [a4]]
      - ["pages.p20.assets", "==", [a4]]
    audit:
      - {action: request_approval, approved: false, count: 1}
      - {action: publish_page, count: 0}
```

### Requirement: An asset is replaced only by a licensed one, on a page that carries the old one

`replacement_allowed` SHALL accept a replacement exactly when the old asset is attached to the page, the new asset is
licensed and the two are different assets. The rule MUST be proven for all inputs (rung L5). Every replacement that
goes through MUST leave the page with the new asset and without the old one.

#### Scenario: The rule holds for every combination

- **WHEN** `replacement_allowed` receives any `old_attached`, `new_licensed` and `same_asset`
- **THEN** the result is true exactly when `old_attached and new_licensed and not same_asset`

```yaml clause
use: function_contract
with:
  function: services/repository.py::replacement_allowed
  inputs: {old_attached: bool, new_licensed: bool, same_asset: bool}
  ensures: result == (old_attached and new_licensed and not same_asset)
require: L5
```

#### Scenario: Every replacement puts a licensed asset on the page

- **WHEN** a call of `replace_asset` succeeds in any run
- **THEN** the new asset is licensed at the end of the run

```yaml clause
use: always_on_calls
with:
  tools: [replace_asset]
  where: (run.final_state.assets.get(event.args.new_asset_id) or {}).get('license', 'licensed') == 'licensed'
```

#### Scenario: Every replacement removes the old asset and adds the new one

- **WHEN** a call of `replace_asset` succeeds in any run
- **THEN** the page's assets it returns contain the new asset and not the old one

```yaml clause
use: always_on_calls
with:
  tools: [replace_asset]
  where: >-
    event.args.new_asset_id in event.result.assets and event.args.old_asset_id not in event.result.assets
```

#### Scenario: The usage search names only pages that carried the asset

- **WHEN** a call of `find_asset_usage` succeeds in any run
- **THEN** every page it returns had the asset attached at the start of the run

```yaml clause
use: always_on_calls
with:
  tools: [find_asset_usage]
  where: >-
    all(event.args.asset_id in run.initial_state.pages[r.page_id]['assets'] for r in event.result.pages)
```

### Requirement: A swept page goes live only after it passed the brand check, with no expired asset on it

In a run of the sweep, a page MUST NOT be published or scheduled unless a brand check found it compliant earlier in
the run, and no page that still carries an asset with an expired licence MUST be published or scheduled.

#### Scenario: A swept page is republished only after a compliant brand check

- **WHEN** a call of `publish_page` or `schedule_publish` succeeds in a run that called `find_asset_usage`
- **THEN** a brand check of that page found it compliant earlier in the run

```yaml clause
use: always_on_calls
with:
  tools: [publish_page, schedule_publish]
  where: >-
    not applied(run, 'find_asset_usage')
    or any(e.kind == 'tool.call' and e.tool == 'check_brand_policy' and e.status == 'ok' and e.result.compliant
    and e.args.page_id == event.args.page_id and e.t < event.t for e in run.events)
```

#### Scenario: No page with an expired asset goes live in a sweep

- **WHEN** any call of `publish_page` or `schedule_publish` is made in a run that called `find_asset_usage`
- **THEN** it never succeeds for a page that carries an asset with an expired licence at the end of the run

```yaml clause
use: never_on_calls
with:
  tools: [publish_page, schedule_publish]
  where: >-
    event.status == 'ok' and applied(run, 'find_asset_usage')
    and any((run.final_state.assets.get(a) or {}).get('license', 'licensed') != 'licensed'
    for a in run.final_state.pages[event.args.page_id]['assets'])
```

### Requirement: The rule lives in the repository service, and the skills say so

The replacement and its rule MUST be defined in the repository service, the assets skill MUST check the permission
before it replaces anything, and the routing skill MUST state the order of the sweep.

#### Scenario: The rule is in the repository service

- **WHEN** the code is inspected
- **THEN** `replacement_allowed` is defined in `services/repository.py`

```yaml clause
use: function_in_layer
with: {function: replacement_allowed, file: services/repository.py}
```

#### Scenario: The replacement is in the repository service

- **WHEN** the code is inspected
- **THEN** `replace_asset` is defined in `services/repository.py`

```yaml clause
use: function_in_layer
with: {function: replace_asset, file: services/repository.py}
```

#### Scenario: The permission is checked before the replacement

- **WHEN** the procedure of the `asset-management` skill is inspected
- **THEN** the step including `governance-checks` comes before the step calling `replace_asset`

```yaml clause
use: skill_step_order
with: {skill: asset-management, first: {include: governance-checks}, then: {call: replace_asset}}
```

#### Scenario: The usage is looked up before the replacement

- **WHEN** the procedure of the `asset-management` skill is inspected
- **THEN** the step calling `find_asset_usage` comes before the step calling `replace_asset`

```yaml clause
use: skill_step_order
with: {skill: asset-management, first: {call: find_asset_usage}, then: {call: replace_asset}}
```

#### Scenario: The routing skill states the order of the sweep

- **WHEN** the `routing` skill is inspected
- **THEN** it says that an expired asset is replaced on every page that uses it before any of them is republished

```yaml clause
use: skill_states
with:
  skill: routing
  text: "An expired asset is replaced on every page that uses it before any of those pages is republished."
```
