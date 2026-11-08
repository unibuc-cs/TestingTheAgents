# Spec-driven development on the testbed: a starting prototype

**Question.** Can a change request be written as a spec formal enough for a machine to check, and where
possible prove, that a PR implements it in the right place and with the smallest necessary change? And
can a coding agent then read less and run fewer checks than "read the repo, run everything"?

**What this adds.** A spec layer (`traceeval/spec/`) on top of the ContentOps testbed: five change
requests written as specs (`traceeval/specs/FS-010x.yaml`, clauses picked from the template catalog
`traceeval/spec/catalog.yaml`), 25 pull requests with known verdicts (`traceeval/spec/prs.py`; every
accepted PR is a code change of 1–4 files), a command that produces the evidence report, and a command
that drafts a spec from a prose request with a model. If you are new to this, read
[SDD_GUIDE.md](SDD_GUIDE.md) first. [CONTENTOPS.md](CONTENTOPS.md) describes the application.

```bash
pip install -e ".[dev]"                 # adds hypothesis + z3-solver
traceeval sdd --workdir runs/sdd        # ~1 min, replays Gemma's recorded answers  ->  runs/sdd/report.md
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

Clauses are written as catalog templates plus slot values (`use: setting_in_range`, `with: {...}`). The
loader expands them, generates ids and the one-line readings, and validates slot values against the
product model. The catalog is `traceeval/spec/catalog.yaml` (documented in [SDD_GUIDE.md §3](SDD_GUIDE.md)).
The checker fields are described in the docstrings of `traceeval/spec/checks/*.py`, and the helpers usable
in expressions are in `traceeval/spec/context.py`. L0 (reviewed) is the prose `intent`. Every clause has a
*required* rung (template default or `require:`), and a clause that holds below it is reported as a gap.

## The five requests, chosen for diversity

| request | the correct PR | what it demonstrates |
|---|---|---|
| FS-0101 approvals expire after 30 days | new feature, 4 files (config, workflow service, publish adapters, skill prose), 45 diff lines | a **proof** (L5) of the rule for all inputs; the proof catches a future-dated approval no fixture has; an off-by-one; the same logic in the wrong layer (placement fails, and the contract cannot find the function in the service); a proven function that is never wired in (only the stale-approval example fails); a correct but branchy implementation that the prover cannot translate, reported *with a gap* because the clause requires L5 |
| FS-0102 guarded operations need a *valid* token and record the approver | security fix, 2 files (permissions service, dispatcher), 13 diff lines | the spec first **exposes a weakness of the current code** (any made-up token passes); the property and an example catch a "self-approved" variant; a lookup written inside the harness is caught only by placement |
| FS-0103 nothing goes live without a clean link check of its current version | defence in depth, 2 files (links service, workflow service), 22 diff lines | the rule moves from a skill procedure (a prompt) into the service and is **proven**; a gate that ignores the check's version is missed by 200 random examples and found by the solver; a **temporal** rule (`precedes`) with completeness against the product model; a skill reordering is stopped by the service gate and still rejected |
| FS-0104 SEO title limit raised to 70 | configuration only, 1 file, 2 diff lines | a property over **agent behaviour** (titles of every length); boundary examples computed from config; a hard-coded constant caught only by placement |
| FS-0105 retried publishing writes never duplicate | bug fix, 2 files (workflow service, publish adapters), 33 diff lines | the spec, quantified over the write tools the publishing skill uses (from the product model), **finds a latent defect** in the current code; a partial fix is caught by the same quantifier |

The FS-0105 clause ranges over the write tools the publishing skill calls, taken from the product model, so
it followed the skill when the approver's sign-off added `approve_review` to it: the correct PR threads the key
through that tool too, and the partial fix that forgets one tool is caught.

## What the report shows per PR

The verdict (accepted / accepted with gaps / rejected), the failing or gapped clauses, the rung each
clause reached, and the cost: clause runs, change-selected regression cases (trace-eval's observed
dependency selection, which answers Q12), tokens and seconds. For each request it also shows which checks
will run and the **agent brief**. The brief is the locate step: the files and functions a coding agent
needs to read, as a fraction of the repository. It comes from the product model: the tool adapters, the
services behind them, the skills that call them, and the config keys.

Headline numbers from `runs/sdd`: the brief is 9–20% of the repository (12% on average), and all 25
verdicts are as expected. Every wrong PR is rejected, with the clause, the counterexample or the
misplaced code named. Two rules are proven for all inputs (FS-0101, FS-0103). Two specs find defects in
the current code before any PR is written (FS-0102, FS-0105).

## With a real model playing the agents

The agents are played by Gemma 4 E4B. Its answers are recorded (`tests/cassettes/`), so `traceeval sdd` replays them without
a GPU. Three things follow from playing the agents with a real model:

- **The regression line counts only cases that pass on the original app.** Gemma gets four catalog cases
  wrong on the original app (AUT-04, PUB-10, SEO-02, WF1-01). They would fail under every PR and say nothing
  about it.
- **Two correct PRs are rejected, and the evidence says why.**
  - FS-0103 `pr_correct`: the service now refuses to publish or schedule without a fresh link check, and in
    DS-INTENTS/i02 and i05 Gemma does so without one, so those regression cases fail.
  - FS-0104 `pr_config_70`: Gemma applies an over-long title whatever the limit (as in SEO-02), and the
    property over title lengths finds one.
- **Two wrong PRs are caught in more ways.** FS-0101 `pr_in_adapter` lets Gemma's schedule of an unapproved
  page (PUB-10) through, which the service version refuses: the monitor catches it. FS-0103
  `pr_gate_ignores_version` lets the unchecked publish and schedule of i02 and i05 through, and the `precedes`
  rule catches it.

So the accepted PRs are FS-0101 `pr_correct` (and `pr_branchy`, with its gap), FS-0102 `pr_correct` and
FS-0105 `pr_fix`. A spec checks the whole system, model
included: a correct code change can still be rejected when the model doesn't do what the skill or the spec
asks, and the evidence names the run where it didn't.

## How this maps to the direction note

- *Formal-enough spec, machine-checked, proven where possible*: each clause kind has one compiler. A
  solver gives L5 for pure, straight-line functions; everything else is property-tested, monitored or
  linted. There is no single proof language (Q1): the clause file is the intermediate representation, and
  the languages sit behind the checkers (Z3 today; Dafny/TLA+ could sit behind `contract` later).
- *Up-to-date product model driving verification* (Q2): extracted by tools and recomputed for each PR. It
  holds files, functions, the tool registry, skill procedures and config, plus the recorded traces (which
  runs touch what). The brief (locate), the trace scopes (which runs to monitor), `forall: write_tools`
  and the completeness check (`must_cover`) all use it.
- *Trace rules at run time* (Q3): the `trace` checker is the monitor. It runs over recorded runs now and
  could run over production traces unchanged.
- *Settings and data* (Q4): `setting` clauses are a schema; CUE/Dhall would be a drop-in replacement.
- *Run only what a change touches* (Q12): the regression line of every evidence record is trace-eval's
  selection on the PR's change set.
- *Spec is not intent*: the prose is L0, and gaps (an unexercised tool, an uncovered path) are reported,
  not hidden. *Model is not code*: every run-time rung (L1–L3) executes the system itself.

## What is not here yet

Missing so far: the generation side (an agent that reads the brief and writes the PR, with the repair loop
against the evidence), a real repository (this is the testbed), and a second proof backend. The next step is to
run the loop spec -> brief -> coding agent -> PR -> evidence, and to measure first-pass acceptance,
placement, minimality and cost against the same requests done without a spec.
