# TRACE-Eval and the SDD layer: a study guide

Two to three hours of reading through the code of the spec-driven development (SDD) layer, in order. Read
[SDD_GUIDE.md](SDD_GUIDE.md) first; this guide uses its vocabulary (clause, template, kind, rung). Paths are
relative to `traceeval/`, except `docs/` and `tests/`, which are at the repository root. The diagrams are images
rendered from the Mermaid sources in `docs/diagrams/`.

## 1. What is in the repository

The repository has three layers:

- the bottom one is ContentOps, a small, working multi-agent application;
- the middle one is the testbed: it runs the application, records what each run touched, and applies controlled
  changes to it;
- the top one holds the two research questions that use the testbed: test selection and spec-driven development.

![The layers of the repository](figures/guide_1_layers.png)

A run of a case produces a trace, which records the agents, skills, tools, configuration keys and code
functions the run touched. Test selection, its ground truth and the SDD layer are all built on these runs and
traces, and on controlled edits of the application, called mutations.

### 1.1 One run, end to end

![One run of a case, end to end](figures/guide_2_run.png)

Open these three files side by side as you read:

- `catalog/tests/publishing.yaml`, which holds the case PUB-01;
- `sut/skills/publishing-workflow/SKILL.md`, whose Procedure the model reads as numbered steps;
- `sut/harness/dispatcher.py`, where every tool call is governed and recorded.

### 1.2 What the SDD layer reuses

Test selection is the README's subject; the SDD layer reuses the executor, the catalog, the recorder with coverage,
the mutation machinery, the change-set extraction and the `observed` strategy (§2.1).

## 2. How SDD connects to it

### 2.1 Conceptually

The SDD layer answers a direction note on spec-driven development, which is kept outside the repository. The
note asks for four things:

- a spec that machines can check, and prove where possible;
- an up-to-date product model, a queryable description of the application, that drives generation and
  verification;
- generation of only the needed code, in the right place;
- an evidence record.

The testbed provides the raw material for most of it:

| what the note asks for | the testbed provides | the SDD layer adds |
|---|---|---|
| a spec that machines can check | none | `specs/FS-*.yaml`: prose intent plus clauses of five kinds; `spec/checks/` holds one checker per kind |
| an up-to-date product model | files, functions, the tool registry, skill procedures and config (static); traces (dynamic) | `spec/product.py` puts both behind queries: `locate(tools)`, `cases_calling(tools)`, `status_setters()`, `skill_write_tools(skill)` |
| generation of only the needed code, in the right place | the mutation machinery: a PR is a set of file edits applied to a copy of the app | `spec/prs.py`, 25 PRs with expected verdicts |
| an evidence record | the `observed` strategy on a change set, as the regression line of every record | `spec/runner.py` (evidence record and agent brief), `spec/report.py` |

Each kind has one checker and a rung it can reach ([SDD_GUIDE.md](SDD_GUIDE.md) §3, §5):

![Clause kinds, their checkers and the rung they reach](figures/guide_3_clauses.png)

### 2.2 What happens when `traceeval sdd` runs

![The traceeval sdd pipeline](figures/guide_4_pipeline.png)

A PR is evaluated against a *variant* of the application: a copy of the baseline with the PR's edits applied,
loaded under a fresh module name so that several variants can coexist. The checkers never see the expected
verdict.

### 2.3 Design decisions you will be asked about

- There is no single proof language. The YAML clause file is the intermediate representation, and the proof
  languages sit behind the checkers. Z3 is the one in use; a Dafny or TLA+ backend would be another `contract`
  checker.
- Monitors run over recorded runs here, and would run over production traces unchanged, since they need only the
  event format.
- The other questions (why YAML, what stops the model from inventing things, what "proven" proves) are answered in
  [SDD_GUIDE.md](SDD_GUIDE.md) §8.

## 3. The five examples

[SDD_DEMO.md](SDD_DEMO.md) has the five requests, their correct PRs and what each one shows (its section "The five
requests, one of each kind of change"). The verdicts are in `docs/sdd/report.md`.

### 3.1 FS-0101 in detail

`specs/FS-0101.yaml` has ten clauses written against the clause catalog. Each one names a template
(`use: <template>`) and fills its slots (`with: {slots}`); the clause ids and texts are generated. The first
section of `spec/prs.py` holds the correct PR, four wrong ones, and one that is correct but written
with a branch. In the matrix below, taken from `docs/sdd/report.md`, each wrong PR fails a different
combination of clauses.

| clause (kind) | pr_correct | no lower bound | off by one (`<`) | logic in adapter | not wired in |
|---|---|---|---|---|---|
| `setting_in_range:publishing.review_max_age_days` (setting) | pass | pass | pass | pass | pass |
| `function_contract:review_age_ok` (contract, proof) | **L5** | fail: age = -1 | fail: age = max | fail: not in the service | **L5** |
| `always_on_calls:publish_page+schedule_publish` (trace) | pass | pass | pass | **fail** (PUB-10) | **fail** (PUB-10) |
| `scenario:please-publish-the-staleapproval` (p11, 45 days) | pass | pass | pass | pass | **fail: published** |
| `scenario:PUB-01` (an approval exactly 30 days old) | pass | pass | **fail** | pass | pass |
| `scenario:PUB-01#2` (a fresh approval) | pass | pass | pass | pass | pass |
| placement (`function_in_layer` twice, `forbid_import_in`, `forbid_literal_in`) | pass | pass | pass | **fail** (three) | pass |
| `regression-tests` (the change-selected cases) | pass | pass | pass | pass | pass |

The trace monitor's failures come from Gemma. In PUB-10 it schedules a page with no approved review. The PRs
that put the rule in the service refuse that, and the other two let it through.

`pr_branchy`, the sixth PR, is the gap example of [SDD_GUIDE.md](SDD_GUIDE.md) §5.

The proof works as follows:

1. the source of `review_age_ok` is parsed, and its single `return` expression is rewritten into Z3 operators:
   `and`, `or`, `not` and chained comparisons become `z3.And/Or/Not`;
2. the inputs become `z3.Int` symbols, and the solver is asked for an input that satisfies
   $\mathit{assume} \land \lnot\,\mathit{ensures}$, that is, one that meets the precondition and breaks the
   postcondition;
3. if the answer is `unsat`, no such input exists, and that is the proof; if the solver finds a model, a concrete
   assignment of the inputs, that model is the counterexample.

Loops, branches and calls are not translated; for those the clause stays at L2 and the evidence record says so.

## 4. The code, in reading order

| file | role |
|---|---|
| `spec/catalog.yaml` + `model.py` | the clause templates; `Spec`, `Clause`, `ClauseResult`; expansion of `use/with` clauses, generated ids and texts; `validate_spec` against the product model |
| `spec/draft.py` | `traceeval sdd draft`: product-model slice and catalog $\to$ prompt $\to$ model answer $\to$ expanded, validated draft spec and its plain-language rendering |
| `spec/product.py` | the product model: files and token counts, functions (AST), tool registry (from decorators), skill procedures, config; queries `locate`, `cases_calling`, `status_setters`, `skill_write_tools`, `model_set` |
| `spec/context.py` | `CheckContext`: runs cases on the variant with cost accounting (in parallel when asked), builds the expression environment; the helpers usable in clauses ([SDD_GUIDE.md](SDD_GUIDE.md) §3) |
| `spec/checks/settings.py` | schema check |
| `spec/checks/examples.py` | one run, catalog-format expectations, `=expr` values |
| `spec/checks/placement.py` | the five lint rules |
| `spec/checks/traces.py` | `always` / `never` / `precedes`, `must_cover`; `cases_in_scope` resolves a clause's scope to catalog cases |
| `spec/checks/contracts.py` | Hypothesis `find`; `_ToZ3` AST rewriter, `_symbolic_call`, `_prove`; behavioural `forall` |
| `spec/runner.py` | `record_baseline`, `agent_brief`, `evaluate_pr`, `run_demo` |
| `spec/report.py` | markdown report and the figure |
| `spec/prs.py` | the PR table; open it only to see how a PR is written (a `Mutation` with literal-anchor edits) |
| `cli.py::cmd_sdd`, `tests/test_sdd.py` | the command and the tests that pin the expected verdicts |

To extend the layer:

- a new clause kind is one checker module, one line in `checks/__init__.py`, its name in `KINDS` in
  `model.py` and a template in `catalog.yaml`;
- a new proof backend is another branch in `contracts._prove`;
- a new product-model query is a method on `ProductModel`;
- a new helper for clause expressions is a function in `context.py`, added to `CheckContext.env` and described in
  `draft.py`'s `HELPERS`.

## 5. Suggested two to three hours

1. (30 min) Section 1 of this guide, with `README.md` and `docs/USER_GUIDE.md`. Open PUB-01, the publishing
   skill and the dispatcher side by side, run `traceeval run --test PUB-01 --backend replay --otel trace.json`:
   the printed verdict, and the trace as spans in `trace.json`.
2. (30 min) `docs/SDD_DEMO.md`, then `docs/sdd/report.md`: the verdict table, the resources table, and
   FS-0101's section in full, with the brief and the six PR records.
3. (60 min) The code in the order of section 4, with `specs/FS-0101.yaml` next to `checks/contracts.py`
   and `checks/traces.py`; then `specs/FS-0105.yaml` next to the behavioural `forall` branch.
4. (30 min) The design decisions of §2.3 and [SDD_GUIDE.md](SDD_GUIDE.md) §8, and "What is not here yet" in
   [SDD_DEMO.md](SDD_DEMO.md).
