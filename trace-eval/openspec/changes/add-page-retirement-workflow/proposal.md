## Why

Taking a live page down today checks one thing in the service: that the page is not protected. Nothing looks at who
links to it, so retiring a page leaves broken internal links on the live site, which only the next link check of
each linking page will find. Retiring a page properly is a job for three specialists, and the platform has no
workflow for it.

## What Changes

- An eighth multi-agent workflow, **W8 page retirement**: brand → authoring → publishing. One request names the page
  to retire and its replacement; the links to the old page are rewritten, the edited live pages are republished
  after a new approval, and the old page is taken down last.
- A new rule in the workflow service, `may_take_down`: a page is taken down only when it is not protected and no
  live page links to it. It is a pure function, to be proven (L5). `repository.inbound_links` counts the links.
- `unpublish_page` is refused with a validation error while a live page links to the page. This holds on every
  path, so it also changes the legal takedown (W3): a page that a live page links to stays up and is reported, as a
  protected page is today.
- The `routing` skill gains one sentence on the order of a retirement. No new tool, agent or setting.

## Capabilities

### New Capabilities
- `fs-0302-page-retirement`: workflow W8 and the takedown rule.

### Modified Capabilities
- `fs-0214-legal-takedown`: the requirement "Only live, unprotected pages go down" now also keeps up a page that a
  live page links to, and reports it.

## Impact

- `traceeval/sut/services/workflow.py`: `may_take_down`, and the check in `unpublish_page`.
- `traceeval/sut/services/repository.py`: `inbound_links`.
- `traceeval/sut/skills/routing/SKILL.md`: one sentence, so every orchestrator prompt changes and
  `tests/cassettes/gemma.jsonl` must be recorded again.
- `traceeval/catalog/workflows.yaml` (W8), `tests/workflows.yaml` (cases WF8-01 to WF8-03, and WF3-04 for the legal
  takedown of a linked page), `tests/publishing.yaml` (the refused direct takedown).
- The recorded takedowns stay valid: the catalog takes down p7, p13 and p14, and no page links to any of them in the
  starting data.
- `traceeval/spec/prs.py`: PRs for FS-0302 (a correct one, and wrong ones: drafts counted as inbound links, the rule
  in the adapter, the takedown planned before the republication).
