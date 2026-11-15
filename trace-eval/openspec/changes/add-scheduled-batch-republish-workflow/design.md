## Context

The orchestrator plans and delegates: one `make_plan`, one `route_to_agent` per task. Authors set republish times
on pages; the brand service tracks those times. Publishing checks permissions before republishing (FS-0202). The
runtime counts every tool call and delegation against budgets (12 per agent, 40 per run).

## Goals / Non-Goals

**Goals:**
- Batch pages with scheduled times within a configurable window into one plan.
- Verify no conflicts exist in the batch before delegating (asset updates, permission changes, interdependencies).
- Each page still has its own step in the plan so the audit trail shows what was republished.

**Non-Goals:**
- Approval gates or security changes.
- Automatic scheduling: pages are pre-scheduled by authors; the batch workflow just groups them.
- Transaction semantics (all-or-nothing atomicity of the batch). If one page fails to republish, the others may
  still proceed.

## Decisions

- **One delegation per page in the batch.** The audit trail shows which pages were republished as a unit, and each
  gets its own step, so failures are traceable.
- **The batch window is configured.** Pages within `republish.batch_window_minutes` of each other's scheduled time
  are batched. This allows tuning for different release cadences.
- **The conflict checker is a pure function.** It examines the pages, their assets, permissions and dependencies
  to determine if they can republish together, without side effects.
- **The orchestrator remains the planner.** No new delegation topology; the routing skill tells the orchestrator
  to batch pages when it sees multiple scheduled times.
- **Budgets stay.** A batch of up to 19 pages fits (1 plan + 19 delegations = 20 steps, leaving room for publishing
  tool calls). Larger batches are split across multiple requests.

## Risks / Trade-offs

- The conflict checker must know about page interdependencies and asset state; it grows with new relationships.
  Mitigated: it is L5 proven, so its logic is verifiable.
- If pages in a batch conflict, the whole batch is rejected, not just the conflicting pages. Simpler to verify;
  authors can adjust the window or remove pages.
