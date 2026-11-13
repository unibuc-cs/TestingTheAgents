# FS-0204: Authors create drafts and save edits as versions that withdraw any approval

**Owner:** content-ops

## Purpose

The authoring agent creates draft pages and replaces page bodies. A new page starts as a draft, with its SEO
metadata set from the request. Every edit is saved as a new version, and because an approval was given for the
old text, the edit withdraws it. A broken link does not stop the edit from being saved, but the author is told.
Authoring never takes anything live. This describes the system as it is today.

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

#### Scenario: Editing adds a version and resets the review

- **WHEN** catalog case AUT-04 runs, which edits the approved page p4
- **THEN** the case passes: the page has 2 versions and its review status is none

```yaml clause
use: scenario
with: {case: AUT-04}
```

#### Scenario: No edited page keeps its approval

- **WHEN** a call of `update_page_content` succeeds in any run
- **THEN** that page's review is not approved at the end of the run

```yaml clause
use: always_on_calls
with:
  tools: [update_page_content]
  where: run.final_state.pages[event.args.page_id]['review']['status'] != 'approved'
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

#### Scenario: Spaces around a link are removed

- **WHEN** a request edits page p4 with a body whose link has spaces inside the brackets
- **THEN** page p4 records the link without the spaces

```yaml clause
use: scenario
with:
  case:
    agent: orchestrator
    request: "Update the body of the welcome post"
    context: {user_id: alice, page_id: p4, body: "See [[ /content/site/home ]]."}
  expect:
    route_to: authoring
    state: [["pages.p4.links", "==", ["/content/site/home"]]]
```

#### Scenario: Link extraction is in the repository service

- **WHEN** the code is inspected
- **THEN** `_extract_links` is defined in `services/repository.py`

```yaml clause
use: function_in_layer
with: {function: _extract_links, file: services/repository.py}
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
