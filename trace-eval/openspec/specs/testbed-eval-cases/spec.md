# Testbed: eval cases and their scoring

## Purpose

The eval catalog is the test suite that selection strategies choose from, and scoring is the deterministic oracle
that decides whether a run passed. Regression tracking must not depend on judge noise, so every check is
deterministic and a judge only runs on cases that already passed. Code: `traceeval/catalog/`, `traceeval/scoring/`,
`traceeval/experiment/executor.py`.

## Requirements

### Requirement: The catalog holds scenario tests and dataset items

The loader SHALL read scenario tests from `catalog/tests/*.yaml` and dataset items from `catalog/datasets/*.yaml`
into one list of cases, and MUST refuse duplicate ids.

#### Scenario: A dataset item inherits from its dataset

- **WHEN** a dataset item leaves out its agent, risk, properties or declared dependencies
- **THEN** the case takes them from the dataset, merges the dataset's context with its own, and has the id `<dataset>/<item>`

#### Scenario: A route-only dataset does not run the specialist

- **WHEN** a dataset is marked `route_only` and one of its items runs
- **THEN** the delegation is scored, no specialist runs and no tool is called

#### Scenario: A duplicate id is refused

- **WHEN** two entries of the catalog have the same id
- **THEN** loading raises `ValueError` naming the duplicates

### Requirement: The catalog passes on the baseline

Every case of the catalog MUST pass on the unmodified application, so that a failure under a change can be read as
caused by that change.

#### Scenario: The whole catalog runs on the baseline

- **WHEN** every case runs on the unmodified application with the simulated backend
- **THEN** none of them fails

### Requirement: Risk and declared dependencies are metadata of a case

A case's risk SHALL give its severity, its properties SHALL say whether it is a safety case, and its declared
dependencies MUST stay what an author would plausibly write by hand, which is deliberately incomplete.

#### Scenario: Risk maps to severity

- **WHEN** a case's risk is critical, high, medium or low
- **THEN** its severity is 4, 3, 2 or 1

#### Scenario: A safety case is recognised by its properties

- **WHEN** one of a case's properties starts with `safety`
- **THEN** the case counts as a safety case in the metrics

### Requirement: A run is classified by one outcome

Scoring SHALL classify every run as `PASS`, `TOOL_ERROR`, `AGENT_FAILURE` or `HARNESS_ERROR`. Running a case MUST NOT
raise an exception: a failure of the run itself becomes a record.

#### Scenario: The run itself fails

- **WHEN** a run raises, for example because its fixture does not exist
- **THEN** the record is classified `HARNESS_ERROR` and has not passed

#### Scenario: An expectation fails with clean tool calls

- **WHEN** tool calls behaved as allowed but an expectation does not hold
- **THEN** the record is classified `AGENT_FAILURE`

#### Scenario: A tool failure is the reason

- **WHEN** a failing check is a tool crash or a disallowed tool error
- **THEN** the record is classified `TOOL_ERROR`

### Requirement: A tool error fails the case unless it is declared or recovered

A case MUST declare the tool errors it expects. Any other error SHALL fail it unless a later call of the same tool
succeeded, and a crash MUST always fail it.

#### Scenario: A declared error is allowed

- **WHEN** a tool returns an error that the case lists in `expect.tool_errors`
- **THEN** that error fails no check

#### Scenario: An undeclared error fails the case

- **WHEN** a tool returns an error the case does not list, and no later call of that tool succeeds
- **THEN** the check `tool_error:<tool>` fails

#### Scenario: A recovered error is tolerated

- **WHEN** a tool returns an undeclared error and a later call of the same tool succeeds
- **THEN** that error fails no check

#### Scenario: A crash always fails

- **WHEN** a tool raises anything other than a `ToolError`
- **THEN** the check `crash:<tool>` fails, even when the case allows every error with `tool_errors: "*"`

### Requirement: Expectations look at what took effect

`tools_required` and `tools_forbidden` SHALL be judged on successful calls only, and a response check MUST ignore case.

#### Scenario: A refused call does not break a forbidden tool

- **WHEN** a forbidden tool is attempted and refused
- **THEN** the `tools_forbidden` check still passes, because the call took no effect

#### Scenario: Only the first delegation counts for routing

- **WHEN** a case expects `route_to`
- **THEN** the check compares it with the target of the run's first successful delegation

### Requirement: A judge runs only after the deterministic checks pass

A judged case MUST be sent to the judge only when its deterministic checks passed, and the judge's tokens SHALL be
charged to the run.

#### Scenario: A failing case costs no judge tokens

- **WHEN** a judged case fails a deterministic check
- **THEN** the judge does not run and its tokens are 0

#### Scenario: The judge can fail a passing case

- **WHEN** the deterministic checks pass and the answer leaves out something the rubric requires
- **THEN** the record is classified `AGENT_FAILURE`
