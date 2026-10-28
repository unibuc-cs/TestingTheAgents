# Working in this repository (for Claude Code and other coding agents)

TRACE-Eval is a research testbed for change-aware, cost-bounded regression test selection of LLM agent
systems. Read `README.md` (5 minutes), then `docs/USER_GUIDE.md` only when you need to extend something.

## Commands

```
pip install -e ".[dev,ml]"          # or: uv pip install -e ".[dev,ml]"
pytest -q                           # ~40 s; must stay green
ruff check traceeval tests --select E,F,W,I,B --line-length 120
ruff format traceeval tests --line-length 120   # see "Gotchas" before formatting sut/
traceeval experiment --workdir runs/exp1 --reps 3 --seeds 10     # full simulated experiment, ~5 min
traceeval sdd --workdir runs/sdd                                 # spec-driven development demo, ~25 s
```

## Layout (one line each)

- `traceeval/sut/` — the system under test (agents, skills, tools, services, harness, config). Copied and
  mutated by the experiment: **relative imports only**, no imports from `traceeval.*` outside `sut`.
- `traceeval/catalog/` — eval cases (YAML) and loader.
- `traceeval/tracing/` — trace recorder, coverage contexts.
- `traceeval/scoring/` — deterministic scorers.
- `traceeval/mutation/` — controlled changes (patch operators), change-set extraction.
- `traceeval/selection/` — `strategies.py` baselines, `adaptive_bayes.py` the proposed method, `extras.py` optional baselines.
- `traceeval/experiment/` — SUT loader, executor, history, runner, replay evaluator, metrics, report.
- `traceeval/spec/` — spec-driven development layer: clause model, one checker per clause kind (`checks/`),
  product model, demo PRs, runner, report. Specs live in `traceeval/specs/FS-*.yaml` (see `docs/SDD_DEMO.md`).
- `tests/` — pytest; `runs/` — experiment outputs (git-ignored); `docs/` — guide, plan, related work, results.

## Conventions

- Every module starts with a docstring stating its role; keep that when adding modules.
- Component identifiers are shared between change sets and dependencies
  (`code:<file>::<fn>`, `line:<file>:<n>`, `tool:`, `skill:<name>#procedure|#prose`, `agent:<name>.<field>`,
  `config:<key>`); do not invent parallel schemes.
- Strategies may use only baseline history, change sets and *other* variants' outcomes (`ctx.train_variants`);
  never the variant under evaluation.
- Mutation operators assert their anchors; a new mutation must be revealed by ≥ 1 test if labelled a regression
  and by none if labelled benign (the report's sanity line checks this).
- Keep the catalog passing on the baseline (`tests/test_sut.py::test_full_catalog_passes_on_baseline`).
- Demo PRs in `traceeval/spec/prs.py` are mutations too (literal anchors, same rule); every PR's expected
  verdict is checked by `tests/test_sdd.py` and flagged in the sdd report when it differs.

## Gotchas

- Reformatting files under `traceeval/sut/` can move the literal text anchors used in
  `traceeval/mutation/catalog.py` (the table is excluded from the formatter); run `pytest` afterwards and re-anchor failures.
- Skills' `## Procedure` blocks are executed by the simulated backend and read verbatim by the LLM backend;
  the YAML in them must stay parseable and its step keys are documented in `sut/harness/backends/simulated.py`.
- `runs/*/history/*.jsonl` include line-level coverage and are large; do not commit them.
