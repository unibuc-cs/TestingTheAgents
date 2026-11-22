# Testbed: the agents' model, its engines and the skills it reads

## Purpose

An agent's next move comes from a chat model. One backend, `llm_openai`, asks the model at every step through an
OpenAI-style client, and the same runtime carries out what it proposes, whichever engine serves the model: `hf`
(Gemma in-process), `vllm` (Gemma on a vLLM server), `llm` (Qwen or gpt-oss through vLLM's chat API) or `replay`
(recorded answers, no model). A skill is the workflow the model reads: its procedure is shown as numbered plain
steps, with included skills written out and settings shown with their values. Code: `traceeval/sut/harness/backends/`,
`traceeval/sut/harness/skills.py`, `traceeval/sut/harness/runtime.py`, `traceeval/llm/`.

## Requirements

### Requirement: The model only proposes; the runtime acts

A backend SHALL only propose the next action, a tool call or the final answer. The runtime MUST carry it out through
the dispatcher and the step budgets, for every engine.

#### Scenario: A scripted client drives a request

- **WHEN** a scripted OpenAI-style client plays a catalog case through the backend
- **THEN** its tool calls go through the dispatcher and the tokens the client reports are the run's tokens

#### Scenario: The default engine replays

- **WHEN** a run names no backend and `TRACEEVAL_BACKEND` is not set
- **THEN** it runs on `replay`, answering from the test suite's cassette `tests/cassettes/gemma.jsonl`

#### Scenario: Several servers of one model

- **WHEN** `TRACEEVAL_VLLM_URL` or `TRACEEVAL_LLM_BASE_URL` lists several comma-separated URLs
- **THEN** each thread keeps to one server, the next in turn at its first call, so that all the calls of a test, the
  judge's included, go to the same server

### Requirement: The prompt holds the agent, its skills and the request

The system prompt SHALL be the agent's own prompt, then for the orchestrator every specialist with its description and
triggers and the default agent, then the agent's intents, then its skills, then a few operating rules. The first user
message SHALL be the request and its context as JSON, without the harness's switches.

#### Scenario: The harness's switches stay out of the prompt

- **WHEN** the context has a slot whose name starts with an underscore, such as `_route_only`
- **THEN** the model is not shown it

#### Scenario: A delegation cannot set who asks or the approval

- **WHEN** a delegation passes `user_id`, `approval_token` or a slot starting with an underscore
- **THEN** the runtime drops them, and the next agent gets the request's own values and those of an approval

#### Scenario: The orchestrator sees every specialist

- **WHEN** the orchestrator's prompt is built
- **THEN** it lists every other agent with its description and triggers, and names `routing.default_agent` for a
  request no specialist owns

#### Scenario: The entry skill's procedure is written out as steps

- **WHEN** an agent's prompt is built
- **THEN** its entry skill's `## Procedure` block is replaced by numbered sentences, included skills written out in
  place, and a skill it includes points there instead of repeating its steps

#### Scenario: A setting in a procedure is shown with its value

- **WHEN** a procedure step reads `config('<key>')`
- **THEN** the prompt shows the key with its current value, and the read is recorded as a `config.read` event

### Requirement: A skill's procedure is read, not executed

A skill SHALL be front matter, prose and a `## Procedure` YAML block. Nothing MUST evaluate the procedure's
expressions: the model reads them, rewritten as plain text where that helps.

#### Scenario: An included skill is inlined

- **WHEN** a step says `include: <skill>`
- **THEN** the step is replaced by that skill's steps, and the load is recorded in the trace

#### Scenario: An include cycle is refused

- **WHEN** a skill ends up including itself
- **THEN** expansion raises `ValueError`

#### Scenario: A shared skill may be included twice

- **WHEN** two steps of one procedure include the same skill, with no cycle
- **THEN** both are expanded

### Requirement: The backend keeps a run alive when the model misbehaves

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

#### Scenario: An empty answer

- **WHEN** the model answers with neither a tool call nor any text
- **THEN** it is asked once more to reply, and its next answer is the agent's final message

### Requirement: A run replays exactly from recorded answers

Decoding SHALL be greedy, at temperature 0, and the app has no clock and no randomness, so the same request MUST build
the same prompts. An answer SHALL be recorded under a hash of the whole request and replayed from it.

#### Scenario: A recorded request is answered from the file

- **WHEN** a request was recorded before
- **THEN** it is answered from the cache, and a run that starts from recorded answers replays exactly, tool-call ids
  and token counts included

#### Scenario: A request that was never recorded

- **WHEN** a replay meets a request it has not recorded
- **THEN** the cache raises `CacheMiss` and the run is classified `INFRA_INVALID`

#### Scenario: Servers that make up tool-call ids

- **WHEN** the `llm` engine is cached
- **THEN** the key numbers the tool calls by their order of appearance instead of carrying the ids the server made up
