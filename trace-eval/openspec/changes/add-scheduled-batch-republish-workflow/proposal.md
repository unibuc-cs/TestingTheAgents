## Why

Content teams often coordinate releases: multiple pages with related content (e.g., a marketing campaign, a
documentation set, a localized version of a site section) should go live at the same time. Today, each page goes
through the publishing workflow independently. Scheduling multiple pages for the same time and batching them
ensures a coordinated, atomic release where all pages publish together or none do.

## What Changes

- A tenth multi-agent workflow, **W10 scheduled batch republish**: authoring → brand → publishing. A request
  carrying a scheduled time in its context republishes multiple pages that match that schedule, all in one plan.
- A new setting, `republish.batch_window_minutes` (1 to 120, set to 60), defining how close pages' scheduled times
  must be to batch together.
- A new service function, `can_batch_republish` in `services/workflow.py`, which checks that pages in a batch
  have no conflicts (e.g., overlapping asset updates), proven at L5.
- No approval changes: batches of pages may be scheduled by authors and require no additional approval gates.
- No existing spec changes: the orchestrator still delegates (FS-0201), pages must still be ready (FS-0203), and
  publishing checks permissions (FS-0202).

## Capabilities

### New Capabilities
- `fs-0304-scheduled-batch-republish`: workflow W10, the batch window setting, the conflict-checking rule, and the
  conditions a scheduled batch must satisfy.

### Modified Capabilities

None.

## Impact

- `traceeval/sut/config/runtime.yaml`: `republish.batch_window_minutes`.
- `traceeval/sut/services/workflow.py`: `can_batch_republish`; `traceeval/sut/services/brand.py`: tracking
  scheduled republish times per page.
- `traceeval/sut/agents/orchestrator.yaml`, `traceeval/sut/skills/routing/SKILL.md` (schedule batching logic).
- `traceeval/sut/fixtures/base.json`: pages with scheduled times added; `tests/cassettes/gemma.jsonl` if prompts
  change.
- `traceeval/catalog/workflows.yaml` (W10), `tests/workflows.yaml`, `traceeval/spec/prs.py`.
