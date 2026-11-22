## 1. Setting, rule and service

- [ ] 1.1 Add `republish.batch_window_minutes: 60` to `config/runtime.yaml` (integer, 1..120)
- [ ] 1.2 Add `can_batch_republish(pages: list[str], window_minutes: int)` to `services/workflow.py` (straight-line, L5 proven)
- [ ] 1.3 Add scheduled time tracking to `services/brand.py` (`page.scheduled_republish_time` as ISO 8601 or None)

## 2. Agents and skills

- [ ] 2.1 Tell the orchestrator in `skills/routing/SKILL.md` to recognize pages with scheduled times and batch them
- [ ] 2.2 Tell the orchestrator in `agents/orchestrator.yaml` to call `can_batch_republish` before planning a batch
- [ ] 2.3 Update publishing agent and skill to handle multiple pages in one delegation (or keep per-page, if that's cleaner)

## 3. Fixture and catalog

- [ ] 3.1 Add scheduled republish times to pages in `fixtures/base.json` (e.g., p6, p7, p8 at time T; p9, p10 at time T+30)
- [ ] 3.2 Add W10 to `catalog/workflows.yaml` and its test cases to `catalog/tests/workflows.yaml`

## 4. Spec layer

- [ ] 4.1 Add the PRs of FS-0304 to `traceeval/spec/prs.py` and their verdicts to `tests/test_sdd.py`
- [ ] 4.2 Record the cassette again if prompts change and run `pytest -q`, `openspec validate --specs --strict`
