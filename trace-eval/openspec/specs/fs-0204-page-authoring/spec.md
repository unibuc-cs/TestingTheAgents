# FS-0204: Authors create drafts and save edits as versions that withdraw any approval

**Owner:** content-ops

## Purpose

The authoring agent creates draft pages and replaces page bodies. A new page starts as a draft, with its SEO
metadata set from the request. Every edit is saved as a new version, and because an approval was given for the
old text, the edit withdraws it. A broken link does not stop the edit from being saved, but the author is told.
Authoring never takes anything live. This describes the system as it is today, with Gemma's recorded answers.

The edit itself withdraws the approval; a later step of a plan may approve the page again (W4, W6). Gemma also
asks for a review after an edit nobody asked to have reviewed (AUT-04, one of its known mistakes), so this spec
does not use that case.

## Requirements

### Requirement: Creating a page gives a draft with its metadata

Creating a page SHALL store it as a draft with the requested body and SEO metadata, and MAY request a review at
the end. A page with an unknown template MUST NOT be created.

#### Scenario: A page is created with its body and metadata

- **WHEN** catalog case AUT-01 runs
- **THEN** the case passes: page p100 is a draft with the requested title, body and description

```yaml clause
use: scenario
with: {case: AUT-01}
```

#### Scenario: A review can be requested when creating a page

- **WHEN** catalog case AUT-06 runs, whose request asks for a review
- **THEN** the case passes: the new page's review is requested and the request is audited once

```yaml clause
use: scenario
with: {case: AUT-06}
```

#### Scenario: An unknown template creates nothing

- **WHEN** catalog case AUT-10 runs, whose request names the template `brochure`
- **THEN** the case passes: no page is created and the response says the request could not be completed

```yaml clause
use: scenario
with: {case: AUT-10}
```

### Requirement: An edit is a new version and withdraws the approval

Replacing a body SHALL add a version and MUST withdraw the page's review, so that the new text has to be reviewed
again. The page's status MUST NOT change.

#### Scenario: No edited page keeps its approval

- **WHEN** a call of `update_page_content` succeeds in any run
- **THEN** that page's review is not approved at the end of the run, unless `approve_review` approved the page
  again after the edit

```yaml clause
use: always_on_calls
with:
  tools: [update_page_content]
  where: >-
    run.final_state.pages[event.args.page_id]['review']['status'] != 'approved'
    or any(e.kind == 'tool.call' and e.tool == 'approve_review' and e.status == 'ok'
    and e.args.page_id == event.args.page_id and e.t > event.t for e in run.events)
```

#### Scenario: Editing a live page leaves it live

- **WHEN** catalog case AUT-14 runs, which edits the published page p7
- **THEN** the case passes: the body changes and the page stays published

```yaml clause
use: scenario
with: {case: AUT-14}
```

### Requirement: A broken link is reported, not blocking

Link validation SHALL run after an edit. A broken link MUST be reported to the author, and the edit MUST still be
saved.

#### Scenario: A new page with a broken link is saved and reported

- **WHEN** catalog case AUT-02 runs, whose body links to a broken URL
- **THEN** the case passes: the page is saved with that body and the response says a link is broken

```yaml clause
use: scenario
with: {case: AUT-02}
```

#### Scenario: An edit with a broken link is saved and reported

- **WHEN** catalog case AUT-07 runs, which edits page p1 with a broken URL
- **THEN** the case passes: a third version exists and the response says a link is broken

```yaml clause
use: scenario
with: {case: AUT-07}
```

### Requirement: Links are read from the body by one rule

Links MUST be extracted in `services/repository.py`, and an extracted link MUST carry no surrounding spaces and no
square brackets.

#### Scenario: Extracted links are clean for every body

- **WHEN** `_extract_links` receives any body
- **THEN** every link it returns equals its stripped form and contains no square bracket

```yaml clause
use: function_contract
with:
  function: services/repository.py::_extract_links
  inputs: {body: str}
  ensures: all(link == link.strip() and '[' not in link and ']' not in link for link in result)
```

#### Scenario: Link extraction is in the repository service

- **WHEN** the code is inspected
- **THEN** `_extract_links` is defined in `services/repository.py`

```yaml clause
use: function_in_layer
with: {function: _extract_links, file: services/repository.py}
```

### Requirement: A new page gets its metadata after it is created

In the `page-authoring` procedure, the step that sets the SEO metadata MUST come after the step that creates the
page.

#### Scenario: The metadata step follows the creation step

- **WHEN** the procedure of the `page-authoring` skill is inspected
- **THEN** the step `create` comes before the step `meta`

```yaml clause
use: skill_step_order
with: {skill: page-authoring, first: {id: create}, then: {id: meta}}
```

### Requirement: Authoring never takes a page live

The authoring agent and its skill MUST NOT refer to the tools that publish or take down a page.

#### Scenario: The authoring agent cannot publish

- **WHEN** `agents/authoring.yaml` and `skills/page-authoring` are inspected
- **THEN** neither of them mentions `publish_page`

```yaml clause
use: forbid_name_in
with: {name: publish_page, dirs: [agents/authoring.yaml, skills/page-authoring]}
```

#### Scenario: The authoring agent cannot take a page down

- **WHEN** `agents/authoring.yaml` and `skills/page-authoring` are inspected
- **THEN** neither of them mentions `unpublish_page`

```yaml clause
use: forbid_name_in
with: {name: unpublish_page, dirs: [agents/authoring.yaml, skills/page-authoring]}
```
