# Testbed: controlled changes and change sets

## Purpose

Controlled changes give the ground truth of the experiments, and a change set is the only thing a selection strategy
learns about a change. A change set therefore holds what can alter behaviour and nothing else, so that no strategy and
no probability can depend on a comment. Code: `traceeval/mutation/`.

## Requirements

### Requirement: A change is a real edit with a stated expectation

A controlled change SHALL be applied as real file edits to a copy of the application and MUST state whether at least
one test is expected to reveal it. An edit whose anchor is not found MUST raise rather than do nothing.

#### Scenario: A missing anchor raises

- **WHEN** a `replace` edit's text does not occur in the file, or occurs a different number of times than expected
- **THEN** `PatchError` is raised and no silent no-op results

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

#### Scenario: Module-level code changes

- **WHEN** code outside any function changes
- **THEN** the change set has a `code:<file>` component

#### Scenario: An insertion anchors to its neighbours

- **WHEN** code lines are only inserted
- **THEN** the line components name the baseline code lines just before and after the insertion

#### Scenario: A skill changes

- **WHEN** a `SKILL.md` changes in its procedure, its prose or its front matter
- **THEN** the component is `skill:<name>#procedure`, `#prose` or `#meta`, and a whitespace-only change gives none

#### Scenario: An agent definition changes

- **WHEN** a key of an agent definition changes, including only the order of a mapping such as its intents
- **THEN** the component is `agent:<name>.<key>`

#### Scenario: A configuration value changes

- **WHEN** an effective configuration value is added, removed or modified
- **THEN** the component is `config:<dotted.key>`

### Requirement: Skill text counts word for word

Skill prose MUST count as a change even though the simulated backend does not read it, because a model reads it word
for word.

#### Scenario: Prose is reworded

- **WHEN** a skill's prose changes and its procedure does not
- **THEN** the change set has `skill:<name>#prose` with kind `skill-prose`

### Requirement: The catalogue of changes is sound

Every change expected to be a regression MUST be revealed by at least one test, and no benign change MUST be revealed
by any test.

#### Scenario: The report checks the expectation

- **WHEN** the experiment report is written
- **THEN** its sanity line reads OK only if both conditions hold for every recorded variant

#### Scenario: Every change has an effect or is known not to

- **WHEN** each catalogue entry is materialised
- **THEN** it yields files and components, except the two comment- and format-only changes, which yield none
