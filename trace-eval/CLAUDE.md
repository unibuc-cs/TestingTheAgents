# Working in this repository (for Claude Code and other coding agents)

TRACE-Eval is a research testbed for change-aware, cost-bounded regression test selection of LLM agent
systems. Read `README.md` (5 minutes), then `docs/USER_GUIDE.md` only when you need to extend something.

## Commands

```
uv venv --python 3.12 .venv         # the project venv (git-ignored); use .venv/Scripts/python on Windows
pip install -e ".[dev,ml]"          # or: uv pip install --python .venv -e ".[dev,ml]" ruff
pytest -q                           # ~90 s; must stay green; replays Gemma's recorded answers (tests/cassettes/)
ruff check traceeval tests          # rules and line length come from pyproject.toml
ruff format traceeval tests         # see "Gotchas" before formatting sut/
traceeval experiment --backend vllm --workdir runs/gemma5 --reps 3   # full experiment, Gemma on the GPU server, about an hour
traceeval experiment --backend llm --workdir runs/qwen5 --reps 3     # the same with Qwen (scripts/gpu_remote.sh up qwen)
traceeval check skill_routing_drop_approval --history runs/gemma5   # the prototype: one change, live
traceeval run --test PUB-01 --backend replay --otel trace.json   # one case; its trace as OpenTelemetry spans
traceeval sdd --workdir runs/sdd                                 # spec-driven development demo, replayed
traceeval properties draft [--fresh] | apply                     # a model drafts the catalog of properties; you edit
TRACEEVAL_BACKEND=vllm pytest -q    # record the answers the cassette lacks (Gemma up on the GPU server)
traceeval sdd draft --request r.md --id FS-0106 [--replay a.json]  # draft a spec with a model
scripts/gpu_remote.sh up [gemma|qwen] | status | down   # models on the GPU server; see docs/EXPERIMENT.md
TRACEEVAL_SITE=hpc scripts/gpu_remote.sh up qwen        # the same on the SLURM cluster (2 GPUs, port + 10)
# several servers in one run: TRACEEVAL_VLLM_URL / TRACEEVAL_LLM_BASE_URL take comma-separated URLs
```

## Layout (one line each)

- `traceeval/sut/` — the system under test (agents, skills, tools, services, harness, config; docs/CONTENTOPS.md).
  Copied and mutated by the experiment: **relative imports only**, no imports from `traceeval.*` outside `sut`.
- `traceeval/catalog/` — eval cases (YAML: `tests/`, `datasets/`), the catalog of properties (`properties.yaml`),
  the multi-agent workflows (`workflows.yaml`), the features (`features.yaml`) and the loader; `extract.py` drafts
  the catalog of properties with a model.
- `traceeval/tracing/` — trace recorder, coverage contexts, OpenTelemetry export (`otel.py`).
- `traceeval/scoring/` — deterministic scorers, and the model judge for cases with a rubric (`TRACEEVAL_JUDGE`).
- `traceeval/mutation/` — controlled changes (patch operators), change-set extraction.
- `traceeval/selection/` — `strategies.py` baselines, `adaptive_bayes.py` the proposed method (two text variants and
  one ablation without its mandatory-coverage rule), `extras.py` optional baselines.
- `traceeval/experiment/` — SUT loader, executor, history, runner, replay evaluator, metrics, coverage, report;
  `check.py`, the prototype (one change checked live).
- `traceeval/llm/` — Gemma's client (`chat.py`: prompt, engines, parsing, which model judges) and the answer cache.
- `traceeval/spec/` — spec-driven development layer: clause catalog (`catalog.yaml`) and model, one checker per
  clause kind (`checks/`), product model, demo PRs, runner, report, drafting with a model (`draft.py`).
  Specs live in `traceeval/specs/FS-*.yaml` as catalog templates + slots (see `docs/SDD_GUIDE.md`).
- `tests/` — pytest; `runs/` — experiment outputs (git-ignored); `docs/` — guide, plan, related work, results.

## Conventions

- Every module starts with a docstring stating its role; keep that when adding modules.
- Component identifiers are shared between change sets and dependencies
  (`code:<file>::<fn>`, `code:<file>`, `line:<file>:<n>`, `tool:`, `skill:<name>#procedure|#prose|#meta`,
  `agent:<name>.<field>`, `config:<key>`, `fixture:<name>`; property sources may also cite `spec:<id>`); do not
  invent parallel schemes.
- Strategies may use only baseline history, change sets and *other* variants' outcomes (`ctx.train_variants`);
  never the variant under evaluation.
- Change sets hold code only: comments, docstrings, blank lines and formatting add no component and no diff
  line (`mutation/changeset.py`), so no strategy and no probability may depend on them.
- Mutation operators assert their anchors; a new mutation labelled a regression must be revealed by ≥ 1 test under
  at least one model, and one labelled benign by none (the report's section 1 gives the counts).
- A test's `properties` must be ids from `traceeval/catalog/properties.yaml` (the catalog of properties, a feature
  the AEM team asked for; see docs/AEM_ALIGNMENT.md); add a property there before using it. A test that runs a
  multi-agent workflow end to end names it (`workflow: W1`), an id from `traceeval/catalog/workflows.yaml`. A
  feature in `traceeval/catalog/features.yaml` lists its parts as component ids; a new tool, skill or setting users
  would see belongs to a feature.
- Keep the catalog passing on the baseline, apart from Gemma's known mistakes (`KNOWN_MODEL_MISTAKES` in
  `tests/test_sut.py`).
- Derive seeds from names with a stable function of their characters (`experiment/evaluate.py` sums the
  character codes), never `hash()`: str hashes are salted per process,
  so runs would differ from one process to the next. Hypothesis searches run with `derandomize=True` for the
  same reason. Idempotency keys are derived from the operation (request id, tool, arguments, earlier
  successes of that call; `sut/harness/dispatcher.py`), never random.
- A test that expects a tool error declares it (`expect.tool_errors: {tool: code}`); any other unrecovered tool
  error or tool crash fails the test as TOOL_ERROR.
- Demo PRs in `traceeval/spec/prs.py` are mutations too (literal anchors, same rule); every PR's expected
  verdict is checked by `tests/test_sdd.py` and flagged in the sdd report when it differs.
- A new kind of clause is a template in `traceeval/spec/catalog.yaml` (and a row in `docs/SDD_GUIDE.md`);
  the checkers only ever see expanded clauses. Specs reference the application by name (tools, config keys,
  functions, cases); `validate_spec` reports names the current product model does not have.

## Gotchas

- Reformatting files under `traceeval/sut/` can move the literal text anchors used in
  `traceeval/mutation/catalog.py` (the table is excluded from the formatter); run `pytest` afterwards and re-anchor failures.
- Skills' `## Procedure` blocks are shown to the model as numbered steps
  (`sut/harness/skills.py::render_procedure`: included skills written out, settings with their values);
  the YAML in them must stay parseable and its step keys are documented in `sut/harness/skills.py`.
- The tests replay Gemma's recorded answers, keyed by the exact request (`traceeval/llm/cache.py`). Anything a
  prompt is built from (skills, agent definitions, config values, the rendering, tool schemas and results,
  fixtures, case requests) changes the key: replays then miss (`INFRA_INVALID` with `CacheMiss`). Record the
  missing answers with `TRACEEVAL_BACKEND=vllm pytest -q` and commit `tests/cassettes/gemma.jsonl`; to drop
  answers nothing asks for any more, delete the file first and record everything again.
- `runs/*/history/*.jsonl` include line-level coverage and are large; do not commit them. For the same reason a
  history recorded before a code change no longer fits `traceeval check` (lines move): record a new one.
- Record experiments on Python 3.12: on 3.15 coverage.py uses its sys.monitoring core, which does not support the
  per-test dynamic contexts (warning `no-sysmon-context`), so observed code dependencies may be incomplete.
