## Why

A legal takedown (W3) waits for a person and handles a handful of pages. In an incident, such as a leaked price list
across an archive section, the security team wants every affected page down in one request, immediately, with the
translations of those pages cancelled as well, and with each takedown traceable to one step of the plan.

## What Changes

- A ninth multi-agent workflow, **W9 instant bulk takedown**: publishing (once per page) → translation. A request
  whose context carries `emergency: true` takes down up to 60 pages in one run.
- A new setting, `takedown.max_batch` (1 to 60, set to 60), and a rule `bulk_size_ok` in the workflow service, to be
  proven (L5).
- In an emergency run no person is asked: `request_approval` is not called.
- After each takedown, publishing delegates the page to translation directly, and a new tool,
  `cancel_translation_jobs`, cancels the page's queued jobs.
- The fixture gains 60 live pages under `/content/site/archive` (p101 to p160) for the scenarios.
- No existing spec changes: the step budgets (FS-0210), the rules of plans and delegation (FS-0201) and the guard on
  taking a page down (FS-0214) hold as they are.

## Capabilities

### New Capabilities
- `fs-0303-instant-bulk-takedown`: workflow W9, the batch rule, and the conditions the emergency path keeps.

### Modified Capabilities

None.

## Impact

- `traceeval/sut/config/runtime.yaml`: `takedown.max_batch`.
- `traceeval/sut/services/workflow.py`: `bulk_size_ok`; `traceeval/sut/services/translation.py`: cancelling jobs.
- `traceeval/sut/tools/translation_tools.py`: `cancel_translation_jobs`; `agents/translation.yaml`,
  `agents/publishing.yaml` (the hand-over).
- `traceeval/sut/skills/routing/SKILL.md`, `skills/publishing-workflow/SKILL.md`, `skills/translation/SKILL.md`.
- `traceeval/sut/fixtures/base.json`: 60 archive pages, so every recorded answer whose prompt shows the fixture
  changes and `tests/cassettes/gemma.jsonl` must be recorded again.
- `traceeval/catalog/workflows.yaml` (W9), `tests/workflows.yaml`, `traceeval/spec/prs.py`.
