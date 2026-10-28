# User guide

Read the README first. This guide adds the minimum needed to work *inside* the repository.

## 1. Data flow

```
 catalog (134 tests) ─┐                                 ┌─ strategy picks tests from: the change set +
                      ▼                                 │  baseline traces + costs + flakiness
 baseline app ──► run all tests K× ──► traces, costs ───┤
                                                        ├─► "execute" = look up the recorded outcome
 35 changes ──► 35 edited copies ──► diff ─► change set ┤   of that test under that change
       │                                                │
       └─────► run all tests K× ──► which tests fail ───┘─► metrics ─► report
```

Record once (free with the simulated agent), replay thousands of times. `runs/<name>/` holds the edited
copies (`variants/`), the recordings (`history/*.jsonl`) and the results (`results/`).

## 2. Vocabulary

- **Case / test**: one entry of the catalog. Scenario tests in `catalog/tests/*.yaml`; dataset items in
  `catalog/datasets/*.yaml` (ids `DS-ROUTING/r01` etc.).
- **Declared dependencies**: the `declared:` block a test author writes — deliberately incomplete.
- **Observed dependencies**: what the trace shows the run touched: `agent:x`, `skill:x`, `tool:x`,
  `config:key`, `code:file::function`, `line:file:n`.
- **Change set**: the diff turned into components with the same identifiers (`traceeval/mutation/changeset.py`).
  Comment-only edits are flagged `semantic=False`.
- **Revealing test**: passes on the baseline, fails on the changed copy (majority over K repetitions).
- **Budget**: tokens, shown as a fraction of the full-suite cost.
- **Stop reason** (`adaptive_bayes` only): `clean`, `regression`, `budget`, `uninformative`.

## 3. Where to look in the code (in this order)

| Want to understand… | Read |
|---|---|
| what the agents do | `sut/skills/publishing-workflow/SKILL.md`, `sut/agents/publishing.yaml`, `sut/config/runtime.yaml` |
| how a request becomes tool calls | `sut/harness/runtime.py` (`_run_agent`), `dispatcher.py`, `backends/simulated.py` |
| how a test is run and scored | `experiment/executor.py` (`run_case`), `scoring/scorers.py` |
| how a change becomes components | `mutation/catalog.py` (data), `mutation/changeset.py` |
| the baselines | `selection/strategies.py` (140 lines) |
| the proposed method | `selection/adaptive_bayes.py` — the docstring explains the four ideas |
| the metrics | `experiment/metrics.py`, `experiment/evaluate.py` |

Everything else is plumbing (loaders, tracing, report).

## 4. How to read the report

- **Section 1** must say sanity **OK** — otherwise the testbed, not the strategies, is broken.
- **Section 2**: `detected` = fraction of changes where at least one revealing test was run *and failed*.
  Compare strategies by the second table (tokens actually *spent*), not by the nominal budget: selecting
  strategies run out of tests, the adaptive one stops early, the rest always spend everything.
- **Section 3**: tokens burned on changes that break nothing; the stop-reason table shows whether the
  adaptive strategy said `clean` on benign changes and `regression` on real ones.
- **Section 4**: APFD / APFD_c of the complete order (prioritization quality) and selection recall.
- `replay.csv` has one row per (change, strategy, budget, seed) if you want to slice it yourself.

## 5. How to extend

- **Test**: add a YAML entry; `expect` supports `route_to`, `state` (`[path, op, value]` with `==`, `!=`, `len`,
  `contains`, `in`, `>=`, `<=`, `absent`, `exists`), `tools_required`, `tools_forbidden`, `tool_attempts`,
  `audit`, `response_contains`, `max_steps`, `termination`; optional `fixture_patch`, `fault_profile`
  (`transient_once:<tool>`, `ack_timeout_once:<tool>`, `permanent_down:<tool>`). `pytest` checks the whole
  catalog passes on the baseline.
- **Change**: add a `Mutation(...)` to the table in `mutation/catalog.py` with `replace` / `delete_line` /
  `delete_block` / `append` edits. Anchors are literal text (reformatting `sut/` breaks them; the operators
  raise). A regression must be revealed by ≥1 test, a benign change by none.
- **Strategy**: subclass `Strategy` in `selection/strategies.py`, implement `order(ctx)` (a prioritized list;
  leaving tests out = not selecting them) and decorate with `@register`. Adaptive strategies implement
  `run(ctx, oracle)`. Use only `ctx.change`, `ctx.catalog`, `ctx.history` baseline facts and the other
  changes' outcomes (`ctx.train_variants`). Add the name to `CORE` to include it in the default comparison.
- **LLM backend**: `pip install -e ".[llm]"`, set `TRACEEVAL_LLM_BASE_URL`, `TRACEEVAL_LLM_API_KEY`,
  `TRACEEVAL_LLM_MODEL`, use `--backend llm`. Start with `traceeval run --test PUB-01 --backend llm`.

## 6. Gotchas

- Simulated tokens are synthetic (shape is realistic, absolute values are not).
- Test texts share vocabulary with skills and config keys, which is why `ir_tfidf` is strong here.
- `history_ml` (needs scikit-learn) and `observed_diverse` are optional: `--strategies all`.
- `runs/` is git-ignored and large (line-level coverage); copy `results/` into `docs/results/` to keep one.
