## Context

A plan is run by the orchestrator: one `make_plan`, then one `route_to_agent` per step. The runtime counts every
tool call and every delegation as a step, against the agent's own budget (`runtime.max_tool_calls`, 12) and the
request's (`runtime.max_run_tool_calls`, 40). `unpublish_page` is guarded: the dispatcher refuses it unless the
request context carries an approval token, and in a plan that token comes from an approved `request_approval`. Only
the orchestrator has `route_to_agent`. Translation jobs are created and read, never cancelled.

## Goals / Non-Goals

**Goals:**
- Up to 60 pages down in one request, each by its own step of the plan.
- No waiting for a person in an emergency.
- Translations of a page cancelled right after the page is down.

**Non-Goals:**
- Changing the step budgets, the dispatcher's guard or any existing spec.
- An emergency path for publishing or scheduling.

## Decisions

- **One delegation per page.** The audit trail of an incident must show one step per page, so the plan lists every
  page and publishing is delegated to once for each.
- **The emergency flag is part of the request context** (`emergency: true`), set by whoever sends the request; the
  routing skill tells the orchestrator to skip `request_approval` when it is set.
- **Publishing hands over to translation itself**, so that the cancellation follows the takedown without another
  round through the orchestrator.
- **The batch rule is a pure function** in `services/workflow.py`, read by the publishing adapter with the limit
  from the configuration, as FS-0101 passes its limit.
- **The budgets stay.** The spec pins them at today's values, so the emergency path cannot be made to work by
  loosening them for every request.

## Risks / Trade-offs

- The emergency flag is not authenticated → any user who may unpublish can set it; accepted for the first version.
- 60 fixture pages make every prompt that lists pages longer → the cassette is recorded again.
- A takedown without a person is a larger blast radius → limited by `takedown.max_batch`.
