# FS-0201: The orchestrator delegates each request once, to the specialist that owns it

**Owner:** platform-reliability

## Purpose

Every request enters through the orchestrator, which reads the triggers of the specialists and hands the
request to the best match. A phrase trigger counts for more than a single word, and a request that matches
nothing goes to the configured default agent. The orchestrator never touches content itself: it delegates, and
returns the answer. This describes the system as it is today.

## Requirements

### Requirement: The fallback agent is a setting

The setting `routing.default_agent` MUST name `authoring`, the agent that receives a request no trigger matches.

#### Scenario: The fallback is configured

- **WHEN** the platform configuration is checked
- **THEN** `routing.default_agent` is the string `authoring`

```yaml clause
use: setting_equals
with: {key: routing.default_agent, value: authoring, type: string}
```

### Requirement: A request reaches the specialist that owns it

The orchestrator SHALL delegate a request to the specialist whose triggers match it best. A phrase trigger MUST
outweigh a single-word trigger of another agent, and a request with no match MUST go to the default agent.

#### Scenario: Every item of the routing dataset is delegated correctly

- **WHEN** any of the 40 items of the DS-ROUTING dataset runs
- **THEN** the request is delegated to the agent the item expects, including the near-misses and the requests with no trigger

```yaml clause
use: property_over_set
with:
  var: item
  set: [DS-ROUTING/r01, DS-ROUTING/r02, DS-ROUTING/r03, DS-ROUTING/r04, DS-ROUTING/r05, DS-ROUTING/r06, DS-ROUTING/r07, DS-ROUTING/r08, DS-ROUTING/r09, DS-ROUTING/r10, DS-ROUTING/r11, DS-ROUTING/r12, DS-ROUTING/r13, DS-ROUTING/r14, DS-ROUTING/r15, DS-ROUTING/r16, DS-ROUTING/r17, DS-ROUTING/r18, DS-ROUTING/r19, DS-ROUTING/r20, DS-ROUTING/r21, DS-ROUTING/r22, DS-ROUTING/r23, DS-ROUTING/r24, DS-ROUTING/r25, DS-ROUTING/r26, DS-ROUTING/r27, DS-ROUTING/r28, DS-ROUTING/r29, DS-ROUTING/r30, DS-ROUTING/r31, DS-ROUTING/r32, DS-ROUTING/r33, DS-ROUTING/r34, DS-ROUTING/r35, DS-ROUTING/r36, DS-ROUTING/r37, DS-ROUTING/r38, DS-ROUTING/r39, DS-ROUTING/r40]
  scenario: {case: "=item"}
  ensures: run.passed
```

#### Scenario: A phrase trigger beats a single word, end to end

- **WHEN** catalog case ORC-02 runs, whose request says both "take it down" and "update"
- **THEN** the case passes: publishing takes page p7 down

```yaml clause
use: scenario
with: {case: ORC-02}
```

#### Scenario: A request with no trigger goes to the default agent

- **WHEN** catalog case ORC-01 runs, whose request matches no trigger
- **THEN** the case passes: authoring receives the request and creates nothing

```yaml clause
use: scenario
with: {case: ORC-01}
```

### Requirement: The orchestrator only delegates

The orchestrator MUST NOT call a tool through the dispatcher, and a run SHALL contain at most one delegation.

#### Scenario: The orchestrator makes no tool call of its own

- **WHEN** a call of `get_page`, `check_permission`, `publish_page` or `update_page_content` is made in any run
- **THEN** the agent making it is never the orchestrator

```yaml clause
use: never_on_calls
with:
  tools: [get_page, check_permission, publish_page, update_page_content]
  where: event.agent == 'orchestrator'
```

#### Scenario: A run delegates at most once

- **WHEN** a call of `get_page` succeeds in any run
- **THEN** the run contains at most one delegation

```yaml clause
use: always_on_calls
with:
  tools: [get_page]
  where: len(run.routes) <= 1
```

### Requirement: Routing lives in the harness

The router MUST be defined in `harness/router.py`, and tools and services MUST NOT use it.

#### Scenario: The router is in the harness

- **WHEN** the code is inspected
- **THEN** `route` is defined in `harness/router.py`

```yaml clause
use: function_in_layer
with: {function: route, file: harness/router.py}
```

#### Scenario: Tools and services do not route

- **WHEN** the code under `tools` and `services` is inspected
- **THEN** nothing there uses the name `route`

```yaml clause
use: forbid_name_in
with: {name: route, dirs: [tools, services]}
```
