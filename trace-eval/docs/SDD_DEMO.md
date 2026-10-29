# Spec-driven development on the testbed: a starting prototype

**Question.** Can a change request be written as a spec that is formal enough for a machine to check
(and where possible prove) that a PR implements it - in the right place, with the smallest necessary
change - while a coding agent reads less and runs fewer checks than "read the repo, run everything"?

**What this adds.** A spec layer (`traceeval/spec/`) on top of the ContentOps testbed: five change
requests written as specs (`traceeval/specs/FS-010x.yaml`, clauses picked from the template catalog
`traceeval/spec/catalog.yaml`), 25 pull requests with known verdicts (`traceeval/spec/prs.py`; every
accepted PR is a real code change of 1–4 files), a command that produces the evidence report, and a
command that drafts a spec from a prose request with a model. New to this? Read [SDD_GUIDE.md](SDD_GUIDE.md)
first; the application is described in [CONTENTOPS.md](CONTENTOPS.md).

```bash
pip install -e ".[dev]"                 # adds hypothesis + z3-solver
traceeval sdd --workdir runs/sdd        # ~30 s  ->  runs/sdd/report.md (+ evidence/*.json, one figure)
traceeval sdd draft --request docs/sdd/draft_example/request.md --id FS-0101 \
    --replay docs/sdd/draft_example/answer.json --out /tmp/FS-0101.draft.yaml   # draft a spec (offline example)
```

A copy of the report is in [`docs/sdd/report.md`](sdd/report.md).

## A spec is prose intent plus clauses of five kinds

| kind | what it says | how it is checked | rung |
|---|---|---|---|
| `setting` | a typed constraint on a configuration key | schema check of the effective config, no run | L4 static |
| `contract` | pre/post-condition of a pure function, or a property of agent behaviour quantified over data or over the product model | Hypothesis property test; for straight-line functions also a Z3 proof (`assume ∧ ¬ensures` unsat) | L2 / L5 |
| `trace` | a temporal rule over recorded runs (`always`, `never`, `precedes`), with a completeness check against the product model | monitor over the catalog runs in scope | L3 |
| `example` | one scenario with an expected outcome (catalog case or inline, values may be `=expressions`) | one run | L1 |
| `placement` | where code must (not) live: `define`, `forbid_import`, `forbid_name`, `forbid_literal`, `skill_order` | AST / procedure lint, no run | L4 static |

Clauses are written as catalog templates plus slot values (`use: setting_in_range`, `with: {...}`); the
loader expands them, generates ids and the one-line readings, and validates slot values against the
product model. The catalog is `traceeval/spec/catalog.yaml` (documented in [SDD_GUIDE.md §3](SDD_GUIDE.md));
the checker fields are in the docstrings of `traceeval/spec/checks/*.py`; the helpers usable in
expressions in `traceeval/spec/context.py`. L0 (reviewed) is the prose `intent`. Every clause has a
*required* rung (template default or `require:`); a clause that holds below it is reported as a gap.

## The five requests, chosen for diversity

| request | the accepted PR | what it demonstrates |
|---|---|---|
| FS-0101 approvals expire after 30 days | new feature, 4 files (config, workflow service, publish adapters, skill prose), 55 diff lines | a **proof** (L5) of the rule for all inputs; the proof catches a future-dated approval no fixture has; an off-by-one; the same logic in the wrong layer (only placement fails); a proven function that is never wired in (only the monitor and example fail); a correct but branchy implementation that the prover cannot translate — accepted *with a gap* because the clause requires L5 |
| FS-0102 guarded operations need a *valid* token and record the approver | security fix, 2 files (permissions service, dispatcher), 17 diff lines | the spec first **exposes a weakness of the current code** (any made-up token passes); the property, the monitor and the example catch a "self-approved" variant; a lookup written inside the harness is caught only by placement |
| FS-0103 nothing goes live without a clean link check of its current version | defence in depth, 2 files (links service, workflow service), 28 diff lines | the rule moves from a skill procedure (a prompt) into the service and is **proven**; a gate that ignores the check's version is missed by 200 random examples and found by the solver; a **temporal** rule (`precedes`) with completeness against the product model; a skill reordering is stopped by the service gate and still rejected |
| FS-0104 SEO title limit raised to 70 | configuration only, 1 file, 2 diff lines | a property over **agent behaviour** (titles of every length); boundary examples computed from config; a hard-coded constant caught only by placement |
| FS-0105 retried publishing writes never duplicate | bug fix, 2 files (workflow service, publish adapters), 22 diff lines | the spec, quantified over the write tools the publishing skill uses (from the product model), **finds a latent defect** in the current code; a partial fix is caught by the same quantifier |

(The same FS-0105 clause with `forall: {tool: write_tools}` ranges over the whole platform and finds 6
of 12 write tools affected; the request was scoped to the publishing workflow to keep the PR small.)

## What the report shows per PR

Verdict (accepted / accepted with gaps / rejected), the failing or gapped clauses, the rung reached
by each clause, and the cost: clause runs, change-selected regression cases (trace-eval's observed
dependency selection: the Q12 answer), tokens, seconds. Per request it also shows the **agent brief**
- the locate step: which files and functions a coding agent needs to read (from the product model:
tool adapters, the services behind them, the skills calling them, the config keys), as a fraction of
the repository - and which checks will run.

Headline numbers from `runs/sdd`: the brief is 10–18% of the repository (12% on average); all 25
verdicts are as expected; every wrong PR is rejected with the clause, the counterexample or the
misplaced code named; two rules are proven for all inputs (FS-0101, FS-0103); two specs find defects in
the current code before any PR is written (FS-0102, FS-0105).

## How this maps to the direction note

- *Formal-enough spec, machine-checked, proven where possible*: clause kinds with one compiler each; L5
  by solver for pure, straight-line functions; everything else property-tested, monitored or linted.
  No single proof language (Q1): the clause file is the intermediate representation, the languages are
  behind the checkers (Z3 today; Dafny/TLA+ could sit behind `contract` later).
- *Up-to-date product model driving verification* (Q2): tool-extracted and recomputed per PR: files,
  functions, tool registry, skill procedures, config, plus the recorded traces (which runs touch what).
  Used by the brief (locate), by trace scopes (which runs to monitor), by `forall: write_tools`, and by
  the completeness check (`must_cover`).
- *Trace rules at run time* (Q3): the `trace` checker is the monitor; it runs over recorded runs now and
  could run over production traces unchanged.
- *Settings and data* (Q4): `setting` clauses are a schema; CUE/Dhall would be a drop-in replacement.
- *Run only what a change touches* (Q12): the regression line of every evidence record is trace-eval's
  selection on the PR's change set.
- *Spec is not intent*: the prose is L0; the gaps (unexercised tool, uncovered path) are reported, not
  hidden. *Model is not code*: every rung above L4 executes the real system.

## What is not here yet

The generation side (an agent that reads the brief and writes the PR, with the repair loop against the
evidence), the LLM backend for the agent system itself (the simulated agent follows the skills), a
real repository (this is the testbed), and a second proof backend. The next step is to run the loop:
spec -> brief -> coding agent -> PR -> evidence, and measure first-pass acceptance, placement,
minimality and cost against the same requests done without a spec.
