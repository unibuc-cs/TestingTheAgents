# Testbed: traces and observed dependencies

## Purpose

A run of a case produces a trace, and the trace says what the run touched. These observed dependencies are the
central input of trace-informed selection and of the spec layer's product model, and they use the same identifiers
as change sets so that the two can be intersected directly. A trace can also leave the testbed as OpenTelemetry
spans, and the traces of the whole suite give its coverage by dimension. Code: `traceeval/tracing/`,
`traceeval/experiment/executor.py`, `traceeval/experiment/coverage.py`, and the events emitted in
`traceeval/sut/harness/`.

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

#### Scenario: An agent's start records the tools it is offered

- **WHEN** an agent starts
- **THEN** its `agent.start` event lists the tools of its definition that the registry knows, whose schemas are in
  its requests

#### Scenario: A delegation the gates refuse is traced

- **WHEN** the dispatcher's gates refuse a delegation, or its arguments are not an object
- **THEN** an `agent.route` event records the source, no target, the status `error` and the reason

### Requirement: A trace reduces to observed components

The executor SHALL turn a trace into component identifiers: `agent:<name>`, `skill:<name>`, `tool:<name>`,
`config:<key>`, the agent fields the orchestrator consulted, `tool:<name>#schema` for every tool an agent was offered,
`fixture:<name>` for the case's starting data, and the code functions and lines that ran. No parallel identifier
scheme MUST be introduced.

#### Scenario: A run depends on the tools it is offered

- **WHEN** an agent is offered a tool it never calls
- **THEN** the run still depends on `tool:<name>#schema`, since the model read what the schema says

#### Scenario: The orchestrator depends on every specialist's routing fields

- **WHEN** the orchestrator starts
- **THEN** the trace records `agent:<name>.triggers` and `agent:<name>.description` for every specialist, not only the chosen one

#### Scenario: Only accepted delegations are routes

- **WHEN** a delegation is refused, because the gates refuse it, the target is unknown or the depth limit is reached
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

### Requirement: A trace exports as OpenTelemetry spans

A run's trace SHALL export as one OTLP/JSON document, built without the OpenTelemetry packages: a root span for the
run, a span per agent turn (a delegated agent's under the delegating one's), a span per tool call, model call and skill
load, and the plan, delegations, approvals and consultations as span events. The same trace MUST always give the same
document.

#### Scenario: One run as spans

- **WHEN** `traceeval run --test <id> --otel trace.json` runs a case
- **THEN** the file holds the run's spans: `run <id>`, an `invoke_agent` span per agent turn and an `execute_tool`
  span per tool call under its agent's span

#### Scenario: Ids do not come from a random source

- **WHEN** the same trace is exported twice
- **THEN** the documents are equal, because span ids are digests of the run id and the index of the event that opens
  the span

### Requirement: Coverage is reported by dimension

The suite's coverage SHALL be reported per dimension (agent, feature, skill, tool, tool error path, configuration,
setting value, property, workflow, execution path, risk), declared by the tests and observed in their traces, with
what no test covers. A change's coverage MUST need no ground truth: what of the change the tests a strategy ran
exercised.

#### Scenario: Coverage of the suite

- **WHEN** `traceeval coverage --history <dir>` runs
- **THEN** each dimension shows the share of its components that at least one test covers, declared and observed,
  and lists the ones no test covers

#### Scenario: What a change may affect

- **WHEN** a change touches components
- **THEN** the properties it may affect are those whose sources it touches and those of the tests that exercised a
  changed component on the original app, and the workflows are those of the same tests
