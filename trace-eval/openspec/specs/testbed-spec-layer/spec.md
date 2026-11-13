# Testbed: the spec-driven development layer

## Purpose

The spec layer checks a pull request against a spec and writes evidence: which clause failed, the counterexample or the
misplaced code, and how strong each piece of evidence is. A spec is prose a person reviews plus clauses a machine checks,
and nothing enters it that the clause catalog and the product model do not know. These are the rules of that layer,
which the `fs-*` specs are written against. Code: `traceeval/spec/`.

## Requirements

### Requirement: The `fs-*` capabilities are the executable specs

`load_specs` SHALL load `openspec/specs/fs-*/spec.md` and read only each file's heading, owner, purpose and fenced
clauses. Every scenario there MUST carry exactly one clause, and a file that breaks this MUST be refused.

#### Scenario: A scenario without a clause

- **WHEN** a scenario of an `fs-*` spec has no ```` ```yaml clause ```` block, or more than one
- **THEN** loading raises `ValueError` naming the file

#### Scenario: A clause outside a scenario

- **WHEN** a clause block comes before the first scenario
- **THEN** loading raises `ValueError`

#### Scenario: Rewording prose changes nothing

- **WHEN** only the WHEN/THEN lines of a scenario change
- **THEN** the loaded clauses and the agent brief stay the same

#### Scenario: Other capabilities are not loaded

- **WHEN** `load_specs` runs
- **THEN** `testbed-*` capabilities and unconfirmed `spec.draft.md` files are not among the specs

### Requirement: A clause is a template from a closed catalog

A clause MUST name a template of `traceeval/spec/catalog.yaml` and give its slots. The loader SHALL generate its id and
its one-line reading.

#### Scenario: Unknown template or wrong slots

- **WHEN** a clause names an unknown template, leaves out a required slot or gives an unknown one
- **THEN** expansion raises `ValueError`

#### Scenario: Repeated clause ids

- **WHEN** two clauses of a spec generate the same id
- **THEN** the later one gets the suffix `#2`, and so on, in document order

### Requirement: Names are checked against the product model

A spec SHALL be validated against the product model before anything runs. A name that cannot be right MUST be an error,
and a name a request introduces MUST be a note.

#### Scenario: A name that cannot be right

- **WHEN** a clause names an unknown tool, case, skill or file, or an expression that does not parse
- **THEN** validation reports an error

#### Scenario: A name the request introduces

- **WHEN** a clause names a config key or a function the current system does not have, in an existing file
- **THEN** validation reports a note

### Requirement: Each kind of clause has one checker and one rung

A clause SHALL be checked by the checker of its kind and report the rung it reached: L1 for an example, L2 for a property
over data or a set, L3 for a monitor, L4 for a static check, L5 for a proof.

#### Scenario: A function contract

- **WHEN** a straight-line function over int and bool inputs is checked
- **THEN** it is property-tested, and the solver may raise it to L5 with `assume ∧ ¬ensures` unsat, or fail it with a counterexample

#### Scenario: A proof that cannot be attempted

- **WHEN** a function has a branch, a loop or inputs other than int and bool
- **THEN** the clause stays at L2 and the record says why

#### Scenario: A monitor that cannot be evaluated

- **WHEN** a trace rule's expression raises on an event
- **THEN** that counts as a violation, not as a crash

#### Scenario: A checker that crashes

- **WHEN** a checker raises
- **THEN** the clause fails at L0 with the error as its summary

### Requirement: The verdict compares reached and required rungs

A PR SHALL be rejected if any clause or regression test fails, accepted with gaps if something holds below its required
rung or does not cover what the product model found, and accepted otherwise.

#### Scenario: A clause holds below its required rung

- **WHEN** a clause passes at L2 and requires L5
- **THEN** its status is `gap` and the verdict is "accepted with gaps"

#### Scenario: A rule leaves a path uncovered

- **WHEN** a `must_cover` rule does not list a tool the product model says can change a page status
- **THEN** its status is `gap`

#### Scenario: A change-selected regression test fails

- **WHEN** a catalog case whose baseline trace touches the change set fails
- **THEN** the `regression-tests` entry fails and the verdict is "rejected", whatever the clauses say

### Requirement: The demo's expected verdicts stay hidden from the checkers

A PR's expected verdict MUST NOT reach a checker. The report SHALL compare it with the verdict and flag any disagreement.

#### Scenario: The default run

- **WHEN** `traceeval sdd` runs without `--specs`
- **THEN** it evaluates the five change requests of the demo and their pull requests

#### Scenario: A disagreement

- **WHEN** a PR's verdict differs from its expected verdict
- **THEN** the log and the report mark it as unexpected

### Requirement: A person confirms what a model drafts

A draft MUST be built only from catalog templates and slot values, and MUST NOT become a spec until a person confirms it.

#### Scenario: A clause that does not fit the catalog

- **WHEN** a model's answer holds a clause that does not expand
- **THEN** it is dropped and reported, and the rest of the draft is kept

#### Scenario: A draft is written

- **WHEN** `traceeval sdd draft` finishes
- **THEN** it writes `spec.draft.md` with a plain reading of every clause and the validation notes, and it is not loaded as a spec

#### Scenario: A draft is confirmed

- **WHEN** a person renames `spec.draft.md` to `spec.md`
- **THEN** it loads as a spec and passes `openspec validate --strict`

### Requirement: The agent brief scopes what a coding agent reads

The brief SHALL name the files and functions a request touches, from the spec and the product model. It MUST NOT depend on
the WHEN/THEN prose.

#### Scenario: The tools a spec names

- **WHEN** a brief is built
- **THEN** it lists the tools named in the title, intent or clauses, their adapters, the services behind them and the skills calling them

#### Scenario: A quantified clause

- **WHEN** a clause quantifies over a set of tools
- **THEN** all of those tools count as named
