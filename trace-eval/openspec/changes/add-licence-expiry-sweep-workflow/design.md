## Context

Assets are attached to pages by id (`page["assets"]`); each asset has a `license` ("licensed" or "expired", absent
means licensed). `repository.attach_asset` only adds. The brand check (`services/brand.py::check_page`) already
reports an attached asset whose licence is not "licensed". Plans are run by the orchestrator following the `routing`
skill: one `make_plan`, one `route_to_agent` per step, `request_approval` before a step that publishes. The runtime
counts every tool call and delegation against `runtime.max_run_tool_calls` (40) and each agent's against
`runtime.max_tool_calls` (12).

## Goals / Non-Goals

**Goals:**
- One request replaces an expired asset everywhere and republishes the live pages, through the existing plan
  mechanism and the existing approval.
- The replacement rule holds whatever the skill does: it is checked in the service.

**Non-Goals:**
- No change to the dispatcher, the runtime, the budgets or the approval mechanism.
- No automatic detection of expiry (the platform has no wall clock); the request names the asset.
- Detaching an asset without a replacement.

## Decisions

- **The rule is a pure function in the service.** `replacement_allowed(old_attached, new_licensed, same_asset)` is
  straight-line boolean code, so the Z3 backend can prove it. `replace_asset` computes the three facts from the
  state and raises `ValidationError` when the rule says no. Alternative: check the licence in the skill only, as the
  attach step does today; rejected because a skill rule is a prompt, and FS-0103 already moved one such rule down.
- **Replacing does not withdraw the review.** `attach_asset` does not either; only a change of the body does
  (FS-0204). The republication is still approved by a person, as in every plan.
- **Two tools instead of one bulk tool.** `find_asset_usage` then one `replace_asset` per page keeps every write
  about one page, so the audit log, the idempotency key and the trace rules stay per page. `replace_asset` takes an
  idempotency key like the other repository writes.
- **One delegation per specialist, not per page.** The assets step replaces on all pages inside one delegation, and
  so do brand and publishing. With the two pages of the scenarios this is well inside both budgets
  (assets: 1 usage + 1 search + 1 permission + 2 replacements).
- **The brand gate is stated for sweep runs only.** The monitors are scoped with `applied(run, 'find_asset_usage')`,
  because recorded runs outside the sweep publish pages without a brand check.

## Risks / Trade-offs

- The model may pick an unlicensed replacement → the service refuses it, and the trace rule on `replace_asset` shows
  any that got through.
- A sweep over many pages can exceed the assets agent's budget of 12 calls → out of scope here; the scenarios use
  two pages, and a larger sweep is a request the orchestrator splits into several replacement steps.
- The routing skill changes, so every recorded orchestrator answer is invalidated → record the cassette again.
