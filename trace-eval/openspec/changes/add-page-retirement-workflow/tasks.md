## 1. Services

- [ ] 1.1 Add `inbound_links(state, page_id)` to `services/repository.py`: the published pages, other than the page, whose `links` contain its path
- [ ] 1.2 Add `may_take_down(protected, live_inbound)` to `services/workflow.py` (straight-line)
- [ ] 1.3 Make `unpublish_page` raise `ValidationError` when the rule says no, before any change or audit entry

## 2. Skill

- [ ] 2.1 Add the retirement sentence and an example to `skills/routing/SKILL.md`

## 3. Catalog

- [ ] 3.1 Add W8 (`agents: [brand, authoring, publishing]`) to `catalog/workflows.yaml`
- [ ] 3.2 Add cases WF8-01 to WF8-03 to `catalog/tests/workflows.yaml`, from the three scenarios of FS-0302
- [ ] 3.3 Add WF3-04 (legal takedown of a linked page) and the refused direct takedown of p8 to the catalog
- [ ] 3.4 Add `code:services/workflow.py::may_take_down` and `code:services/repository.py::inbound_links` to the `takedown` feature

## 4. Spec layer

- [ ] 4.1 Add the PRs of FS-0302 to `traceeval/spec/prs.py` (correct; drafts counted; rule in the adapter; takedown before republication) and their verdicts to `tests/test_sdd.py`
- [ ] 4.2 Apply the FS-0214 delta and add a rejected change for it to `AS_BUILT`
- [ ] 4.3 Record the cassette again (`TRACEEVAL_BACKEND=vllm pytest -q`) and run `pytest -q`, `openspec validate --specs --strict`
