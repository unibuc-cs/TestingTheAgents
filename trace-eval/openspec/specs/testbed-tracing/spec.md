# Testbed: traces and observed dependencies

## Purpose

A run of a case produces a trace, and the trace says what the run touched. These observed dependencies are the
central input of trace-informed selection and of the spec layer's product model, and they use the same identifiers
as change sets so that the two can be intersected directly. Code: `traceeval/tracing/`,
`traceeval/experiment/executor.py`, and the events emitted in `traceeval/sut/harness/`.

## Requirements

### Requirement: Every tool call and agent step is traced

The harness SHALL emit an event for every tool call, whatever its outcome, and for every agent start, skill load,
configuration read, delegation and model call.

#### Scenario: A refused call is still traced

- **WHEN** a gate of the dispatcher refuses a tool call
- **THEN** one `tool.call` event records the tool, its status `error`, the error code and 0 attempts

#### Scenario: A configuration read is traced

- **WHEN** code reads a setting through `Config.get`, even one that does not exist
- **THEN** a `config.read` event records the key

#### Scenario: Harness switches stay out of the trace

- **WHEN** a request's context has a key starting with an underscore, such as `_route_only`
- **THEN** the `run.start` event leaves that key out

### Requirement: A trace reduces to observed components

The executor SHALL turn a trace into component identifiers: `agent:<name>`, `skill:<name>`, `tool:<name>`,
`config:<key>`, the agent fields the orchestrator consulted, and the code functions and lines that ran. No parallel
identifier scheme MUST be introduced.

#### Scenario: The orchestrator depends on every specialist's routing fields

- **WHEN** the orchestrator starts
- **THEN** the trace records `agent:<name>.triggers` and `agent:<name>.description` for every specialist, not only the chosen one

#### Scenario: Only accepted delegations are routes

- **WHEN** a delegation is refused, because the target is unknown or the depth limit is reached
- **THEN** it is left out of the trace's routes

### Requirement: Coverage is attributed per test

The coverage session SHALL record which application code each test executed, as both `code:<file>::<function>` and
`line:<file>:<n>`, with one context per test and repetition.

#### Scenario: A line maps to its innermost function

- **WHEN** an executed line lies inside nested functions
- **THEN** it is attributed to the innermost one

#### Scenario: Setup is attributed to no test

- **WHEN** code runs before the first test's context begins
- **THEN** that coverage belongs to no test

#### Scenario: A module-level line maps to its file

- **WHEN** an executed line lies outside any function
- **THEN** it is attributed to `code:<file>`
