## 1. Service and tools

- [ ] 1.1 Add `replacement_allowed(old_attached, new_licensed, same_asset)` to `services/repository.py` (straight-line)
- [ ] 1.2 Add `asset_usage(state, asset_id)` and `replace_asset(state, page_id, old_asset_id, new_asset_id, actor, idempotency_key)` to `services/repository.py`; audit `replace_asset`
- [ ] 1.3 Add the adapters `find_asset_usage` (read) and `replace_asset` (write) to `tools/asset_tools.py`
- [ ] 1.4 Give the `assets` agent the two tools (`agents/assets.yaml`)

## 2. Skills

- [ ] 2.1 Add the sweep steps to `skills/asset-management/SKILL.md`: usage, search, permission, one replacement per page
- [ ] 2.2 Add the sweep sentence and the routing guidance to `skills/routing/SKILL.md`

## 3. Catalog

- [ ] 3.1 Add W7 (`agents: [assets, brand, publishing]`) to `catalog/workflows.yaml`
- [ ] 3.2 Add the feature `licence_sweep` to `catalog/features.yaml`
- [ ] 3.3 Add cases WF7-01 to WF7-03 to `catalog/tests/workflows.yaml`, with the requests and expectations of the spec's three scenarios

## 4. Spec layer

- [ ] 4.1 Add the PRs of FS-0301 to `traceeval/spec/prs.py` (correct; licence not checked; rule in the adapter; brand step dropped) and their verdicts to `tests/test_sdd.py`
- [ ] 4.2 Add the two tools to the content-tool lists of FS-0201 and FS-0210
- [ ] 4.3 Record the cassette again (`TRACEEVAL_BACKEND=vllm pytest -q`) and run `pytest -q`, `openspec validate --specs --strict`
