## Why

An asset whose licence has expired may not be used on the site (the brand check reports it, FS-0218), but today
nothing removes it: someone has to find the pages by hand, attach another image to each, and republish. The
platform cannot even answer "which pages use this asset", and an asset can be attached but never taken off a page.

## What Changes

- A seventh multi-agent workflow, **W7 licence expiry sweep**: assets → brand → publishing. One request names the
  expired asset; it is replaced on every page that carries it, each page is checked against the brand guidelines,
  and the pages that were live are republished after a person approved it.
- Two new tools for the `assets` agent: `find_asset_usage` (read: the pages an asset is attached to) and
  `replace_asset` (write: swap one attached asset for another on one page).
- A replacement rule in the repository service, `replacement_allowed`: the old asset is attached, the new one is
  licensed, and they differ. It is a pure function, to be proven (L5).
- The `asset-management` skill gains the steps of the sweep; the `routing` skill gains one sentence on its order.
- No existing requirement changes. The new tools are content tools, so they join the two tool lists that the
  as-built specs enumerate (see Impact).

## Capabilities

### New Capabilities
- `fs-0301-licence-expiry-sweep`: workflow W7, the replacement rule, and the gates a swept page passes before it
  goes live again.

### Modified Capabilities

None. FS-0201 and FS-0210 enumerate the content tools in two clauses (the orchestrator calls none of them; none of
them crashes); the two new tools are added to those lists when this change is archived, which widens the clauses
without changing a requirement.

## Impact

- `traceeval/sut/services/repository.py`: `asset_usage`, `replace_asset`, `replacement_allowed`.
- `traceeval/sut/tools/asset_tools.py`: the two adapters; `traceeval/sut/agents/assets.yaml`: the two tools.
- `traceeval/sut/skills/asset-management/SKILL.md`, `traceeval/sut/skills/routing/SKILL.md`.
- `traceeval/catalog/workflows.yaml` (W7), `features.yaml` (a `licence_sweep` feature), `properties.yaml` if a new
  property is needed, and `tests/workflows.yaml` (cases WF7-01 to WF7-03, the three scenarios of the spec).
- Every prompt of the orchestrator and of the assets agent changes (their skills change), so
  `tests/cassettes/gemma.jsonl` must be recorded again (`TRACEEVAL_BACKEND=vllm pytest -q`).
- `traceeval/spec/prs.py`: PRs for FS-0301 (a correct one, and wrong ones: the licence not checked, the rule in the
  adapter, the brand step dropped from the plan).
