## Context

A page's internal links are its `links` list, extracted from the body (`[[/content/site/...]]`) whenever the body
changes (`repository._extract_links`). `workflow.unpublish_page` refuses a protected page and otherwise sets the
page back to `draft`. It is a guarded tool: the dispatcher asks for an approval token, which in a plan comes from
`request_approval`. `search_pages` matches a query against title, path and body, so searching for a path finds the
pages that link to it, and the page itself. Services do not read the configuration (FS-0210 forbids the name
`config` under `services`).

## Goals / Non-Goals

**Goals:**
- A takedown can never leave a live page with a link to a page that is no longer live, whatever the plan did.
- One request retires a page end to end through the existing plan, approval and review mechanisms.

**Non-Goals:**
- HTTP redirects from the old path; rewriting links in translations or in metadata.
- A setting to switch the rule off: the service cannot read one (FS-0210), and passing it through the adapter is not
  worth a second code path.
- Links from drafts and scheduled pages: they do not block a takedown, though the retirement rewrites them too.

## Decisions

- **The rule is a pure function, the lookup is not.** `may_take_down(protected, live_inbound)` is straight-line and
  provable; `inbound_links(state, page_id)` reads the state and returns the ids of the published pages, other than
  the page itself, whose `links` contain its path. `unpublish_page` calls both and raises `ValidationError`, before
  it changes or audits anything. Alternative: order the steps in the routing skill only; rejected, a plan is a
  prompt and Gemma already skips plan rules (WF5-02).
- **The existing protected-page check moves into the rule**, so one function decides, and the error message says
  which of the two reasons applies.
- **The rule applies to every takedown, the legal one included.** A legal takedown of a linked page is refused and
  reported, the way a protected page is (FS-0214, modified here). Alternative: exempt W3; rejected because the
  service cannot tell which workflow called it, and should not.
- **No new tool.** Brand's existing `find` intent searches for the old path; authoring's existing edit rewrites the
  body; publishing's existing steps approve, publish and unpublish.
- **Publishing gets one delegation per page**, as in the other workflows, so the republication of a linking page and
  the takedown are separate steps and the takedown comes last. With two linking pages the run stays well below
  `runtime.max_run_tool_calls`.

## Risks / Trade-offs

- A legal takedown can now be held up by a link → it is reported with the linking page, and the user can run a
  retirement or edit the link first.
- The search finds the retired page itself (its own path matches) → the plan must not edit it; the scenario checks
  that only the linking pages are edited.
- A page that links to itself does not block its own takedown (`inbound_links` leaves the page out).
- The routing skill changes, so every recorded orchestrator answer is invalidated → record the cassette again.
