# Spec-driven development on the testbed: a starting prototype

This prototype asks two questions. Can a change request be written as a spec formal enough for a machine to
check, and where possible prove, that a PR implements it in the right place and with the smallest necessary
change? And can a coding agent then read less and run fewer checks than it would by reading the whole
repository and running everything?

It adds a spec layer (`traceeval/spec/`) on top of the ContentOps testbed:

- five change requests written as specs (`traceeval/specs/FS-010x.yaml`), with clauses picked from the
  template catalog `traceeval/spec/catalog.yaml`;
- 25 pull requests with known verdicts (`traceeval/spec/prs.py`); every correct PR is a code change of 1–4
  files;
- a command that produces the evidence report;
- a command that drafts a spec from a prose request with a model.

If you are new to this, read [SDD_GUIDE.md](SDD_GUIDE.md) first. [CONTENTOPS.md](CONTENTOPS.md) describes the
application.

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
| `trace` | a temporal rule over recorded runs (`always_on_calls`, `never_on_calls`, `always_in_audit`, `precedes_in_audit`), with a completeness check against the product model | monitor over the catalog runs in scope | L3 |
| `example` | one scenario with an expected outcome (catalog case or inline, values may be `=expressions`) | one run | L1 |
| `placement` | where code must or must not live: `function_in_layer`, `forbid_import_in`, `forbid_name_in`, `forbid_literal_in`, `skill_step_order` | AST / procedure lint, no run | L4 static |

A spec picks these templates and fills their slots. [SDD_GUIDE.md](SDD_GUIDE.md) §2–§5 explains the catalog,
the generated ids and the required rungs.

## The five requests, chosen for diversity

| request | the correct PR | what it demonstrates |
|---|---|---|
| FS-0101 approvals expire after 30 days | new feature, 4 files (config, workflow service, publish adapters, skill prose), 45 diff lines | a **proof** (L5) of the rule for all inputs, which catches a future-dated approval no fixture has; an off-by-one error; the same logic in the wrong layer (placement fails, and the contract cannot find the function in the service); a proven function that is never wired in (the stale-approval example fails, and so does the monitor, through Gemma's PUB-10); a correct but branchy implementation that the prover cannot translate, reported *with a gap* because the clause requires L5 |
| FS-0102 guarded operations need a *valid* token and record the approver | security fix, 2 files (permissions service, dispatcher), 13 diff lines | the spec first **exposes a weakness of the current code** (any made-up token passes); the property and an example catch a self-approved variant; a lookup written inside the harness is caught only by placement |
| FS-0103 nothing goes live without a clean link check of its current version | defence in depth, 2 files (links service, workflow service), 22 diff lines | the rule moves from a skill procedure (a prompt) into the service and is **proven**; a gate that ignores the check's version is missed by 200 random examples and found by the solver; a **temporal** rule (`precedes`) with completeness against the product model; a skill reordering is stopped by the service gate and still rejected |
| FS-0104 SEO title limit raised to 70 | configuration only, 1 file, 2 diff lines | a property over **agent behaviour** (titles of every length); boundary examples computed from config; a hard-coded constant that only placement tells apart from the correct PR (with Gemma, every FS-0104 PR also fails the title property; see below) |
| FS-0105 retried publishing writes never duplicate | bug fix, 2 files (workflow service, publish adapters), 33 diff lines | the spec, quantified over the write tools the publishing skill uses (from the product model: `schedule_publish`, `unpublish_page`, `approve_review`), **finds a latent defect** in the current code; a partial fix is caught by the same quantifier |

## What the report shows per PR

For each PR the report gives the verdict (accepted / accepted with gaps / rejected), the failing or gapped
clauses, the rung each clause reached, and the cost: clause runs, change-selected regression cases (chosen by
TRACE-Eval's observed-dependency selection), tokens and seconds. For each request it also shows which checks
will run and the **agent brief**. The brief covers the locate step of a coding task: the files and functions a
coding agent needs to read, as a fraction of the repository. It is built from the product model: the tool
adapters, the services behind them, the skills that call them, and the config keys.

The headline numbers from the report ([`docs/sdd/report.md`](sdd/report.md)) are these. The brief is 9–20% of
the repository (12% on average), and all 25 verdicts are as expected. Every wrong PR is rejected, and the report
names the clause, the counterexample or the misplaced code. Two rules are proven for all inputs (FS-0101,
FS-0103). Two specs find defects in the current code before any PR is written (FS-0102, FS-0105).

## With a real model playing the agents

The agents are played by Gemma 4 E4B. Its answers are recorded (`tests/cassettes/`), so `traceeval sdd`
replays them without a GPU. Playing the agents with a real model has three consequences.

- The regression line counts only cases that pass on the original app. Gemma gets seven catalog cases wrong on the
  original app (AUT-04, PUB-10, SEO-02, WF1-01, WF2-03, WF5-02, WF6-02). They would fail under every PR and say
  nothing about it.
- Two correct PRs are rejected, and the evidence says why.
  - FS-0103 `pr_correct` makes the service refuse to publish or schedule without a fresh link check. In
    DS-INTENTS/i02, i05 and PUB-19 Gemma publishes or schedules without one, so those regression cases fail.
  - Under FS-0104 `pr_config_70`, Gemma applies an over-long title whatever the limit (as in SEO-02). The
    property over title lengths, the boundary scenario and the monitor over the SEO runs all find such a title.
- Several wrong PRs are caught in additional ways. FS-0101 `pr_in_adapter` and `pr_unwired` let through Gemma's
  scheduling of an unapproved page (PUB-10), which the service version refuses; the monitor catches both.
  FS-0103 `pr_gate_ignores_version` lets through the unchecked publish and schedule of i02 and i05, and the
  `precedes` rule catches it. The wrong FS-0104 PRs fail the title property too, as the correct one does.

The accepted PRs are therefore FS-0101 `pr_correct` (and `pr_branchy`, with its gap), FS-0102 `pr_correct`
and FS-0105 `pr_fix`. A spec checks the whole system, the model included. A correct code change can still be
rejected when the model does not do what the skill or the spec asks, and the evidence names the run where it
did not.

## How this maps to the direction note on spec-driven development

[STUDY_GUIDE.md](STUDY_GUIDE.md) §2 covers this: what the note asks for (it is the request this layer
answers), what the testbed provides on its own, what the SDD layer adds, and the design decisions.

## What is not here yet

The prototype does not include the generation side (an agent that reads the brief and writes the PR, then
repairs it against the evidence), a real repository (it runs on the testbed), or a second proof backend. The
next step is to run the loop spec -> brief -> coding agent -> PR -> evidence, and to measure first-pass
acceptance, placement, minimality and cost against the same requests done without a spec.
