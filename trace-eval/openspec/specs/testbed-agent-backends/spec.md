# Testbed: agent backends and the skill procedure language

## Purpose

An agent's next move comes from a backend, and the same runtime drives both: a simulated backend that follows a skill's
machine-readable procedure, so runs are free and deterministic, and an LLM backend over any OpenAI-compatible endpoint.
A change to a procedure therefore changes both at the same place. Code: `traceeval/sut/harness/backends/`,
`skills.py`, `expressions.py`, `runtime.py`.

## Requirements

### Requirement: Both backends drive the same runtime

A backend SHALL only propose the next action. The runtime MUST carry it out through the same dispatcher and budget for
both backends.

#### Scenario: A scripted model drives a request

- **WHEN** a scripted OpenAI-compatible client plays case PUB-01 through the LLM backend
- **THEN** the case passes, and the tokens the server reports are the run's tokens

### Requirement: A skill's procedure is the canonical workflow

A skill SHALL be front matter, prose and a `## Procedure` YAML block. The simulated backend MUST execute the block, and
the LLM backend MUST receive the skill's whole text.

#### Scenario: An included skill is inlined

- **WHEN** a step says `include: <skill>`
- **THEN** the step is replaced by that skill's steps, and the load is recorded in the trace

#### Scenario: An include cycle is refused

- **WHEN** a skill ends up including itself
- **THEN** expansion raises `ValueError`

#### Scenario: A shared skill may be included twice

- **WHEN** two steps of one procedure include the same skill, with no cycle
- **THEN** both are expanded

### Requirement: Procedure steps stop on failure unless they say otherwise

An error result MUST stop the agent unless its step says `on_error: continue`, and a false `require` MUST stop it with the
step's message unless it says `on_fail: continue`.

#### Scenario: A tool error

- **WHEN** a call returns an error and the step has no handler
- **THEN** the agent answers "I could not complete the request (<code>): <message>"

#### Scenario: An unmet requirement

- **WHEN** a call succeeds and its `require` expression is false
- **THEN** the agent stops and answers the step's `fail_message`

#### Scenario: A step's guard is false

- **WHEN** a step's `when` is false
- **THEN** the step is skipped, whatever it would have done

### Requirement: Procedure expressions run in a whitelist

Expressions MUST be parsed and checked before they run, against a whitelist of syntax, and MUST NOT see Python's builtins
beyond a safe list.

#### Scenario: An attempt to reach the interpreter

- **WHEN** an expression uses a dunder name such as `__import__`, an attribute starting with an underscore, or a syntax outside the whitelist
- **THEN** evaluation raises `ValueError` before anything runs

#### Scenario: A failing placeholder

- **WHEN** a placeholder of a message cannot be evaluated
- **THEN** it renders as `?` and the message still goes out

### Requirement: Simulated runs are deterministic unless flakiness is asked for

With flakiness 0 the same case SHALL give the same outcome and tokens. With flakiness above 0 an agent MAY slip once, by
garbling one identifier, and the slip MUST be reproducible from the seed.

#### Scenario: The draw does not depend on the setting

- **WHEN** the flakiness setting changes
- **THEN** the draw is still made, so the token jitter uses the same random numbers

#### Scenario: Tokens are synthesised

- **WHEN** a simulated run books a model call
- **THEN** the prompt tokens come from the prompt material it read, plus 28 per earlier tool call and up to 7 of seeded jitter

### Requirement: The LLM backend keeps a run alive when the model misbehaves

Malformed output from a model MUST reach the runtime as a refused call and MUST NOT crash the run.

#### Scenario: Arguments that are not JSON

- **WHEN** a tool call's arguments do not parse
- **THEN** they are passed on as `_raw`, the dispatcher refuses the call as `invalid_arguments`, and the model sees the error

#### Scenario: An invented tool

- **WHEN** the model calls a tool that does not exist
- **THEN** the dispatcher answers `unknown_tool`

#### Scenario: Too many calls in one answer

- **WHEN** an answer asks for more than 4 tool calls
- **THEN** only the first 4 are kept, both as actions and in the conversation

#### Scenario: A very large result

- **WHEN** a tool result is long
- **THEN** it is sent to the model cut to 4000 characters
