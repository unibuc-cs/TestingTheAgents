# FS-0218: The brand check reports every forbidden term, missing disclaimer and expired asset

**Owner:** content-ops

## Purpose

The brand agent checks a page against the brand guidelines, says which terms the guidelines forbid, and finds the
pages that use a term. The guidelines are platform data: the forbidden terms (never on the site, in any letter
case), the words that make a page an offer, the disclaimer every offer must carry, and the rule that only licensed
assets may be used. The check only reads; it is the gate of a campaign launch (FS-0212), and the search is the first
step of a legal takedown (FS-0214). This describes the system as it is today, with Gemma's recorded answers.

## Requirements

### Requirement: A page is checked against all three rules

The check MUST report a forbidden term in the title or body in any letter case, an offer without the disclaimer and
an attached asset whose licence has expired, and a page with none of these SHALL pass.

#### Scenario: A compliant page passes

- **WHEN** catalog case BRD-01 runs, for the winter sale page p12
- **THEN** the case passes: the page meets the guidelines

```yaml clause
use: scenario
with: {case: BRD-01}
```

#### Scenario: A forbidden term is reported

- **WHEN** catalog case BRD-02 runs, for the investment plan page p13, whose body starts "Guaranteed returns"
- **THEN** the case passes: the term is reported

```yaml clause
use: scenario
with: {case: BRD-02}
```

#### Scenario: An offer without the disclaimer is reported

- **WHEN** catalog case BRD-03 runs, for the autumn offer page p19
- **THEN** the case passes: the missing disclaimer is reported

```yaml clause
use: scenario
with: {case: BRD-03}
```

#### Scenario: An expired asset is reported

- **WHEN** catalog case BRD-04 runs, for the spring teaser page p20, which carries the expired banner a3
- **THEN** the case passes: the asset's licence is reported

```yaml clause
use: scenario
with: {case: BRD-04}
```

#### Scenario: Every check reports every forbidden term the page uses

- **WHEN** a call of `check_brand_policy` succeeds in any run
- **THEN** each forbidden term that occurs in the page's title or body, in any letter case, is reported

```yaml clause
use: always_on_calls
with:
  tools: [check_brand_policy]
  where: >-
    all(any(v.rule == 'forbidden_term' and term in v.detail for v in event.result.violations)
    for term in run.initial_state.brand.forbidden_terms
    if term.lower() in (run.final_state.pages[event.args.page_id]['title'] + ' '
    + run.final_state.pages[event.args.page_id]['body']).lower())
```

#### Scenario: Every check reports every expired asset on the page

- **WHEN** a call of `check_brand_policy` succeeds in any run
- **THEN** each attached asset whose licence is `expired` is reported

```yaml clause
use: always_on_calls
with:
  tools: [check_brand_policy]
  where: >-
    all(any(v.rule == 'asset_license' and a in v.detail for v in event.result.violations)
    for a in run.final_state.pages[event.args.page_id]['assets']
    if run.final_state.assets.get(a, {}).get('license') == 'expired')
```

#### Scenario: A page passes only without violations

- **WHEN** a call of `check_brand_policy` succeeds in any run
- **THEN** the page is compliant exactly when no violation is reported

```yaml clause
use: always_on_calls
with:
  tools: [check_brand_policy]
  where: event.result.compliant == (len(event.result.violations) == 0)
```

### Requirement: The guidelines are data, and pages are found by a term

The guidelines SHALL be answered from the platform data, and the brand rules MUST be applied in the brand service,
not written into the skills or the adapters.

#### Scenario: The forbidden terms are listed

- **WHEN** catalog case BRD-06 runs
- **THEN** the case passes: the answer lists the forbidden terms of the guidelines

```yaml clause
use: scenario
with: {case: BRD-06}
```

#### Scenario: The pages that use a term are found

- **WHEN** catalog case BRD-05 runs, for the phrase 'guaranteed returns'
- **THEN** the case passes: p13, p14 and the draft p15 are listed

```yaml clause
use: scenario
with: {case: BRD-05}
```

#### Scenario: The check is in the brand service

- **WHEN** the code is inspected
- **THEN** `check_page` is defined in `services/brand.py`

```yaml clause
use: function_in_layer
with: {function: check_page, file: services/brand.py}
```

#### Scenario: No forbidden term is written into the skills or adapters

- **WHEN** the code under `skills` and `tools` is inspected
- **THEN** nothing there hard-codes the term `risk-free`

```yaml clause
use: forbid_literal_in
with: {value: risk-free, dirs: [skills, tools]}
```
