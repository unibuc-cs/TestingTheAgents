# Working in this repository (for Claude Code and other coding agents)

TRACE-Eval is a research testbed for change-aware, cost-bounded regression test selection of LLM agent
systems. Read `README.md` (5 minutes), then `docs/USER_GUIDE.md` only when you need to extend something;
`docs/README.md` lists the other documents by what you want to do.

## Commands

```
uv venv --python 3.12 .venv         # the project venv (git-ignored); use .venv/Scripts/python on Windows
pip install -e ".[dev]"             # or: uv pip install --python .venv -e ".[dev]" ruff
pytest -q                           # ~90 s; must stay green; replays Gemma's recorded answers (tests/cassettes/)
ruff check traceeval tests          # rules and line length come from pyproject.toml
ruff format traceeval tests         # see "Gotchas" before formatting sut/
traceeval experiment --backend vllm --workdir runs/gemma8 --reps 5   # full experiment, Gemma on the GPU server, about two hours
traceeval experiment --backend llm --workdir runs/qwen8 --reps 5     # the same with Qwen (scripts/gpu_remote.sh up qwen)
traceeval replay-first --workdir runs/gemma8                        # every changed copy on the original app's answers, no model
traceeval mutations --generated                                     # the changes made mechanically from the app (no labels)
traceeval replay-first --workdir runs/gemma8_gen --generated        # every generated change replayed for free; no copy kept
traceeval mutants --workdir runs/gemma8_gen --reps 5 --generated --reached-only --backend vllm   # record them, only the tests each reaches
traceeval evaluate --workdir runs/gemma8 && traceeval report --workdir runs/gemma8   # the strategies, then the report
traceeval check skill_routing_drop_approval --history runs/gemma8   # the prototype: one change, replayed then live
traceeval check <change> --history runs/gemma8_gen --miss-rate 0.1 --confirm   # clean at a miss rate; a failure run again
traceeval coverage --history runs/gemma8                            # coverage of the suite, per dimension and component
traceeval run --test PUB-01 --backend replay --otel trace.json   # one case; its trace as OpenTelemetry spans
traceeval sdd --workdir runs/sdd                                 # spec-driven development demo, replayed
traceeval properties draft [--fresh] | apply                     # a model drafts the catalog of properties; you edit
TRACEEVAL_BACKEND=vllm pytest -q    # record the answers the cassette lacks (Gemma up on the GPU server)
traceeval sdd draft --request r.md --id FS-0106 [--replay a.json]  # draft a spec with a model
scripts/gpu_remote.sh up [gemma|qwen|qwen2|gptoss] | status | down   # models on the GPU server; docs/EXPERIMENT.md
TRACEEVAL_SITE=hpc scripts/gpu_remote.sh up qwen        # the same on the SLURM cluster (2 GPUs, port + 10)
TRACEEVAL_VLLM_ARGS="--no-enable-prefix-caching" scripts/gpu_remote.sh up gemma   # with --workers 1: every answer repeats
# several servers in one run: TRACEEVAL_VLLM_URL / TRACEEVAL_LLM_BASE_URL take comma-separated URLs; each thread
# keeps to one server, so --workers 2 over qwen and qwen2 answers one test at a time on each GPU
```

## Layout (one line each)

- `traceeval/sut/` — the system under test (agents, skills, tools, services, harness, config; docs/CONTENTOPS.md).
  Copied and mutated by the experiment: **relative imports only**, no imports from `traceeval.*` outside `sut`.
- `traceeval/catalog/` — eval cases (YAML: `tests/`, `datasets/`), the catalog of properties (`properties.yaml`),
  the multi-agent workflows (`workflows.yaml`), the features (`features.yaml`) and the loader; `extract.py` drafts
  the catalog of properties with a model.
- `traceeval/tracing/` — trace recorder, coverage contexts, OpenTelemetry export (`otel.py`).
- `traceeval/scoring/` — deterministic scorers, and the model judge for cases with a rubric (`TRACEEVAL_JUDGE`).
- `traceeval/mutation/` — controlled changes (patch operators), change-set extraction; `generator.py`, the
  changes made mechanically from the app, which have no label.
- `traceeval/selection/` — `base.py` the interface and the two rules every run follows, `strategies.py` baselines
  (and the two orders only the replay-first comparison runs),
  `adaptive_bayes.py` the proposed method (two text variants and one ablation without its mandatory-coverage rule),
  `adapted.py` two methods from the literature adapted as baselines (CASPER, Risk-Aware Adaptive Evaluation),
  `extras.py` two more baselines.
- `traceeval/experiment/` — SUT loader, executor, history, runner, replay evaluator, metrics, coverage, report;
  `replay_first.py`, which tests a change reaches, found by replaying the original app's recorded answers;
  `manifest.py`, what a recording was made from and with, and what differs from today's files (`drift`);
  `generated.py`, the generated changes of a recording replayed for free; `check.py`, the prototype (one change:
  the replay, then the method live over the tests that diverge); `stopping.py`, the threshold at which a check says
  clean for a target miss rate, set per group of changes on the recording's own changes
  (`traceeval check --miss-rate`); `coverage.py`, coverage of the suite and of a change, and the coverage floor
  (`traceeval check --floor`); `culprits.py`, a batch's members replayed alone: which tests each reaches (the day's
  map) and a failure's suspects among them.
- `traceeval/llm/` — Gemma's client (`chat.py`: prompt, engines, parsing, which model judges) and the answer cache
  (`cache.py`, with the three clients of replay-first: `Tee` keeps a baseline's answers, `ReplayFirstClient`
  replays them, `Compare` counts the requests a changed copy's recording gets answered otherwise).
- `traceeval/spec/` — spec-driven development layer: clause catalog (`catalog.yaml`) and model, one checker per
  clause kind (`checks/`), product model, demo PRs, runner, report, drafting with a model (`draft.py`).
  Specs live in `traceeval/specs/FS-*.yaml` as catalog templates + slots (see `docs/SDD_GUIDE.md`).
- `tests/` — pytest; `runs/` — experiment outputs (git-ignored); `docs/` — guide, plan, related work, references,
  results, and the paper draft (`docs/paper/`, LaTeX).
- `scripts/` — `gpu_remote.sh` (the model servers), `batch_sweep.py`, and `analysis/`: offline checks of the
  results and probes of the measurement chain, listed in `scripts/analysis/README.md`.
- `TODO.md` — the plan the work follows (replay-first); read it before changing strategies, the evaluator or the
  paper.

## Conventions

- Every module starts with a docstring stating its role; keep that when adding modules.
- Component identifiers are shared between change sets and dependencies
  (`code:<file>::<fn>`, `code:<file>`, `line:<file>:<n>`, `tool:<name>`, `tool:<name>#schema`,
  `skill:<name>#procedure|#prose|#meta`, `agent:<name>.<field>`, `config:<key>`, `fixture:<name>`; property
  sources may also cite `spec:<id>`); do not invent parallel schemes.
- A dependency is what a run was sent as well as what it did: `tool:<name>#schema` for every tool an agent was
  offered (`agent.start` lists them), `fixture:<name>` for the starting data. `selection/base.py::matches` is the
  one place that says which component touches which dependency.
- Strategies may use only baseline history, change sets and *other* variants' outcomes (`ctx.train_variants`; a
  variant is a copy of the app with one change applied); never the variant under evaluation, nor, for a batch, its
  members (`History.training_variants`).
- Every strategy's run follows the same two rules (`selection/base.py`): a test that fails on the original app is
  not run, and the run ends at the first failure. A strategy with its own `run` keeps both. A failure can first
  be confirmed by running the test again, which is the oracle's business and not a strategy's
  (`traceeval check --confirm`, `scripts/analysis/confirm_failures.py`).
- Replay-first reaches a strategy through the same two calls: `ctx.runnable(t)` is also false for a test whose
  outcome the replay gave, and `ctx.cost(t)` is what is left of a test after its divergence point. A strategy
  tests `ctx.runnable` and scores with `ctx.cost`; it never reads the replay itself.
- A clean verdict's threshold for a miss rate is set per group of changes, and `experiment/stopping.py::group_of`
  is the one place that says which group a change is in: a skill's steps, text the model reads, an agent's tools
  and skills, the configuration, the starting data, code.
- A recording's cassette (`history/cassette.jsonl`) holds the answers of its original app and nothing else: only
  `traceeval baseline` writes it, and a request it lacks means that the change reaches the model.
- A recording's changed copies are made from its own copy of the original app (`variants/baseline/sut`), and its
  manifest (`history/manifest.json`) says what it was made from and with. The empty change
  (`history/unchanged.jsonl`, `History.unchanged`) is the original app run as the changed copies are: it is never
  among `History.variants`, and a test that fails under it reveals no change.
- A (change, test) pair with no valid run is missing (`History.missing`): `ctx.runnable` is false for it, and it
  reveals nothing. A run whose judge gave no verdict is such a run (`INFRA_INVALID`).
- Change sets hold code only: comments, docstrings, blank lines and formatting add no component and no diff
  line (`mutation/changeset.py`), so no strategy and no probability may depend on them. What the model is sent
  counts as it is sent: a skill's front matter and prose as text, its procedure as the parsed steps in their
  order, a tool's description and parameters (`tool:<name>#schema`), the agents an orchestrator lists
  (`agent:<name>.specialists`).
- Mutation operators assert their anchors; a new mutation labelled a regression must be revealed by ≥ 1 test under
  at least one model, and one labelled benign by none (section 1 of `docs/results/gemma8/report.md` gives the
  counts). A generated change (`g_<kind>_<where>_<n>`) has no label: the recording says whether a test reveals
  it. Its edits name a line and the text expected there, so it applies only to the app it was generated from.
- A copy recorded with `--reached-only` has runs of the tests that diverge in its replay; the others have one
  record each, their replayed run, marked `stand_in`. The copy is not kept.
- A test's `properties` must be ids from `traceeval/catalog/properties.yaml` (the catalog of properties; see
  docs/AEM_ALIGNMENT.md); add a property there before using it.
- A test that runs a multi-agent workflow end to end names it (`workflow: W1`), an id from
  `traceeval/catalog/workflows.yaml`.
- A feature in `traceeval/catalog/features.yaml` lists its parts as component ids; a new tool, skill or setting
  users would see belongs to a feature.
- A case that needs a setting at another value sets it in `config:` (by dotted key).
- Keep the catalog passing on the baseline, apart from Gemma's known mistakes (`KNOWN_MODEL_MISTAKES` in
  `tests/test_sut.py`).
- Derive seeds from names with a stable function of their characters (`experiment/evaluate.py` sums the character
  codes), never `hash()`: str hashes are salted per process, so runs would differ from one process to the next.
  Hypothesis searches run with `derandomize=True` for the same reason. Idempotency keys are derived from the
  operation (request id, tool, arguments, earlier successes of that call; `sut/harness/dispatcher.py`), never
  random.
- A test that expects a tool error declares it (`expect.tool_errors: {tool: code}`); any other unrecovered tool
  error or tool crash fails the test as TOOL_ERROR.
- A test about a refusal has a positive condition, so that an agent that does nothing fails it:
  `tools_required` for the check that must have succeeded, or `tools_attempted` for the call that must have been
  tried (`scripts/analysis/probes/probe_oracles.py` lists the cases without one).
- A context slot that starts with `_` is a switch for the harness (`_route_only`) and is not shown to the model.
  The user, the approval token and those switches are the harness's to carry: a delegation cannot set them
  (`sut/harness/runtime.py::HARNESS_SLOTS`).
- Demo PRs in `traceeval/spec/prs.py` are mutations too (literal anchors, same rule); every PR's expected
  verdict is checked by `tests/test_sdd.py` and flagged in the sdd report when it differs.
- A new clause template is an entry in `traceeval/spec/catalog.yaml` and a row in `docs/SDD_GUIDE.md` §3; a new
  kind also needs a checker (`docs/STUDY_GUIDE.md` §4). The checkers only ever see expanded clauses. Specs
  reference the application by name (tools, config keys, functions, cases); `validate_spec` reports names the
  current product model does not have.

## Gotchas

- Reformatting files under `traceeval/sut/` can move the literal text anchors used in
  `traceeval/mutation/catalog.py` (the table is excluded from the formatter); run `pytest` afterwards and re-anchor
  failures.
- Skills' `## Procedure` blocks are shown to the model as numbered steps
  (`sut/harness/skills.py::render_procedure`: included skills written out, settings with their values);
  the YAML in them must stay parseable and its step keys are documented in `sut/harness/skills.py`.
- The tests replay Gemma's recorded answers, keyed by the exact request (`traceeval/llm/cache.py`). Anything a
  prompt is built from (skills, agent definitions, config values, the rendering, tool schemas and results,
  fixtures, case requests) changes the key: replays then miss (`INFRA_INVALID` with `CacheMiss`). Record the
  missing answers with `TRACEEVAL_BACKEND=vllm pytest -q` and commit `tests/cassettes/gemma.jsonl`; to drop
  answers nothing asks for any more, delete the file first and record everything again.
- `runs/*/history/*.jsonl` include line-level coverage and are large; do not commit them. For the same reason a
  history recorded before a change to `traceeval/sut`, a comment included, no longer fits `traceeval check` (lines
  move, requests change): the check refuses it (`experiment/manifest.py::drift`); record a new one. Do not edit
  `traceeval/sut/` or the catalog while a recording runs: its steps read both more than once.
- A Gemma recording made before cassettes were kept gets its cassette from `tests/cassettes/gemma.jsonl` the first
  time it is replayed, which works while that file still holds the answers of the recording's app. Qwen's and
  gpt-oss's recordings have no such source: `traceeval replay-first` refuses them until their baseline is
  recorded again.
- Record experiments on Python 3.12: on 3.15 coverage.py uses its sys.monitoring core, which does not support the
  per-test dynamic contexts (warning `no-sysmon-context`), so observed code dependencies may be incomplete.
