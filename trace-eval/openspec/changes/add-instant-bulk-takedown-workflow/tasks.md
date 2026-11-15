## 1. Setting, rule and service

- [ ] 1.1 Add `takedown.max_batch: 60` to `config/runtime.yaml`
- [ ] 1.2 Add `bulk_size_ok(n, limit)` to `services/workflow.py` (straight-line)
- [ ] 1.3 Add job cancellation to `services/translation.py` and the tool `cancel_translation_jobs` to `tools/translation_tools.py`

## 2. Agents and skills

- [ ] 2.1 Tell the orchestrator in `skills/routing/SKILL.md` to skip `request_approval` in an emergency and to delegate one step per page
- [ ] 2.2 Let publishing hand a page to translation after a takedown (`agents/publishing.yaml`, `skills/publishing-workflow/SKILL.md`)
- [ ] 2.3 Add the cancellation steps to `skills/translation/SKILL.md` and the tool to `agents/translation.yaml`

## 3. Fixture and catalog

- [ ] 3.1 Add the 60 live archive pages p101 to p160 to `fixtures/base.json`
- [ ] 3.2 Add W9 to `catalog/workflows.yaml` and its cases to `catalog/tests/workflows.yaml`

## 4. Spec layer

- [ ] 4.1 Add the PRs of FS-0303 to `traceeval/spec/prs.py` and their verdicts to `tests/test_sdd.py`
- [ ] 4.2 Record the cassette again and run `pytest -q`, `openspec validate --specs --strict`
