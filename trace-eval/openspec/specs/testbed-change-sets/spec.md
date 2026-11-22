# Testbed: controlled changes and change sets

## Purpose

Controlled changes give the ground truth of the experiments, and a change set is the only thing a selection strategy
learns about a change. A change set therefore holds what can alter behaviour and nothing else, so that no strategy and
no probability can depend on a comment. Code: `traceeval/mutation/`.

## Requirements

### Requirement: A change is a real edit with a stated expectation

A controlled change SHALL be applied as real file edits to a copy of the application. A hand-written change MUST
state whether at least one test is expected to reveal it; a generated change (`g_<kind>_...`,
`testbed-replay-first`) has no label, and its recording decides. An edit whose anchor is not found MUST raise rather
than do nothing.

#### Scenario: A missing anchor raises

- **WHEN** a `replace` edit's text does not occur in the file, or occurs a different number of times than expected
- **THEN** `PatchError` is raised and no silent no-op results

#### Scenario: An edit by line number

- **WHEN** a `lines` edit names a line whose text is not the text it expects there
- **THEN** `PatchError` is raised, so that an edit generated from one version of the app cannot apply to another

#### Scenario: Materialising a change records it

- **WHEN** a change is materialised
- **THEN** the variant folder holds the edited copy, `changeset.json`, `diff.patch` and `mutation.json`

#### Scenario: Materialising leaves the baseline untouched

- **WHEN** a change is materialised
- **THEN** only the copy is edited, and an earlier copy of the same variant is replaced

### Requirement: A strategy never sees the label

A mutation's id, description and expected effect MUST NOT reach a selection strategy. The change set and the diff SHALL
be computed only by comparing the two file trees.

#### Scenario: A change set is derived from the trees

- **WHEN** two trees are compared
- **THEN** the change set names the variant and holds the changed files, the components and the diff, and nothing from the mutation's label

### Requirement: Comments and formatting add nothing

An edit that cannot change what the harness does MUST add no component, no file and no diff line. This SHALL cover
Python comments, docstrings, blank lines and formatting, YAML comments, and the order of configuration mappings.

#### Scenario: A comment or docstring edit

- **WHEN** a Python file changes only in comments, docstrings or formatting
- **THEN** the change set is empty and `is_provably_benign` is true

#### Scenario: Reordered configuration sections

- **WHEN** the configuration's sections are reordered and its comments rewritten, with the same values
- **THEN** the change set is empty

#### Scenario: A trailing comment is cut from the diff

- **WHEN** a code or YAML line changes and carries a trailing comment
- **THEN** the diff shows the line without the comment

#### Scenario: A hash inside a YAML scalar stays

- **WHEN** a quoted or block YAML scalar contains a `#`
- **THEN** that text is kept as data and is not treated as a comment

#### Scenario: Commenting the code does not move the result

- **WHEN** the same change is applied to a commented copy of the application
- **THEN** the diff and the non-line components are the same, and line components still name real lines of that file

### Requirement: A change becomes components with shared identifiers

Each kind of file SHALL produce its own components, and these MUST use the same identifiers as observed dependencies.

#### Scenario: A function changes

- **WHEN** a Python function's normalised AST changes
- **THEN** the change set has `code:<file>::<function>` and `line:<file>:<n>` components, and `tool:<name>` when the function is a registered adapter

#### Scenario: What the model is told about a tool changes

- **WHEN** a tool adapter's description or parameters change
- **THEN** the change set has `tool:<name>#schema` of kind `tool-schema`, since the schema reaches every agent offered
  the tool, whether it calls it or not

#### Scenario: An orchestrator is shown other specialists

- **WHEN** a specialist's agent definition is added or taken away
- **THEN** the change set has `agent:<orchestrator>.specialists` for each orchestrator

#### Scenario: Module-level code changes

- **WHEN** code outside any function changes
- **THEN** the change set has a `code:<file>` component

#### Scenario: An insertion anchors to its neighbours

- **WHEN** code lines are only inserted
- **THEN** the line components name the baseline code lines just before and after the insertion

#### Scenario: A skill changes

- **WHEN** a `SKILL.md` changes in its procedure, its prose or its front matter
- **THEN** the component is `skill:<name>#procedure`, `#prose` or `#meta`; a change of the procedure block's
  comments or layout gives none, while re-wrapped prose is another prompt and gives `#prose`

#### Scenario: An agent definition changes

- **WHEN** a key of an agent definition changes, including only the order of a mapping such as its intents
- **THEN** the component is `agent:<name>.<key>`, of kind `agent-prompt` for its system prompt or description and
  `agent` otherwise

#### Scenario: An agent loses tools

- **WHEN** an agent's tool or skill list only loses items
- **THEN** the component names them in its detail (`removed: tool:<name>`), so that only the tests that used one of
  them are reached

#### Scenario: The starting data changes

- **WHEN** a fixture file changes
- **THEN** the component is `fixture:<name>`

#### Scenario: A configuration value changes

- **WHEN** an effective configuration value is added, removed or modified
- **THEN** the component is `config:<dotted.key>`

### Requirement: Skill text counts word for word

What the model is sent MUST count as it is sent. A skill's front matter and prose go into the prompt word for word, so
they SHALL be compared as text, line breaks included. Its procedure is shown as numbered steps written from the parsed
YAML, so it SHALL be compared parsed: the order of the steps and of each call's arguments counts, the order of a step's
keys does not.

#### Scenario: Prose is reworded

- **WHEN** a skill's prose changes and its procedure does not
- **THEN** the change set has `skill:<name>#prose` with kind `skill-prose`

#### Scenario: A step's keys are reordered

- **WHEN** only the order of a procedure step's keys changes
- **THEN** the change set is empty, since the model is shown the step the same way

#### Scenario: A call's arguments are reordered

- **WHEN** only the order of a call's arguments in a step changes
- **THEN** the change set has `skill:<name>#procedure`, since the arguments are shown in the order they are written

### Requirement: The catalogue of changes is sound

Every hand-written change expected to be a regression MUST be revealed by at least one test under at least one model,
and no benign change MUST be revealed by any test. Generated changes have no label and are left out of this check.

#### Scenario: The report checks the expectation

- **WHEN** the experiment report is written
- **THEN** its sanity line reads OK only if both conditions hold for every recorded variant

#### Scenario: Every change has an effect or is known not to

- **WHEN** each catalogue entry is materialised
- **THEN** it yields files and components, except the two comment- and format-only changes, which yield none

### Requirement: Changes can be bundled

A batch SHALL apply several catalogue changes to one copy, as a nightly run or a pull request bundles them. Its members
MUST edit disjoint files, and the batch SHALL count as a regression when any member is one.

#### Scenario: A batch is materialised

- **WHEN** a batch is materialised
- **THEN** every member's edits are applied in order to one copy, and the change set holds the components of all of them
