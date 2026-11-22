# Testbed: replay-first testing of a change

## Purpose

The models decode greedily and the app has no clock and no randomness, so a model call is a function of its request.
The answers recorded on the original app (a recording's cassette) can therefore stand in for the model on a changed
copy for as long as the copy sends requests the original app sent. Replaying every test that way, with no model,
splits the suite in two: the tests that replay to the end, whose outcome on the copy is known for no tokens, and the
tests that diverge at the first request the original app never made, which need the model from there on. The same
replay drives the evaluation (`testbed-record-replay`), the live check of one change, the generated changes, and the
culprits of a failing batch. The condition it rests on is the serving setup's to keep, and is measured on a
recording. Code: `traceeval/experiment/replay_first.py`, `check.py`, `stopping.py`, `generated.py`, `culprits.py`,
`traceeval/llm/cache.py`, `traceeval/mutation/generator.py`.

## Requirements

### Requirement: The replay sorts the tests of a changed copy

Every test SHALL be run on the changed copy with the model's calls answered from the recording's cassette alone.
A test that replays to the end MUST have its outcome without any model call, and a test that diverges MUST say how
far the cassette carried it.

#### Scenario: A test replays to the end

- **WHEN** every request a test makes on the copy is one the original app made
- **THEN** its outcome on the copy is known, for no tokens

#### Scenario: A test diverges

- **WHEN** a test makes a request the original app never made
- **THEN** it is marked diverged at that request, and the tokens of the requests before it are its replayed prefix

#### Scenario: The replay of a recording is kept

- **WHEN** `traceeval replay-first --workdir <run>` runs
- **THEN** `history/replay_first.jsonl` holds one row per changed copy and test, each copy replayed in a process of
  its own, with no model called

### Requirement: The clients around the cassette keep the replay honest

Three clients SHALL serve replay-first. `Tee` MUST pass every answer through unchanged while the original app is
recorded, and keep it as the recording's cassette. `ReplayFirstClient` MUST answer from that cassette on a changed copy
and pass on, or report, the requests the original app never made. `Compare` MUST answer nothing from the cassette while
a copy is recorded, and count how the model's answers compare with the original app's for the same requests.

#### Scenario: The same request reaches the model several times

- **WHEN** the original app is recorded with several repetitions
- **THEN** `Tee` never answers in the model's place, so each repetition asks the model

#### Scenario: A copy's recording checks the condition

- **WHEN** a changed copy is recorded behind `Compare`
- **THEN** each record says how its requests compare with the answers of the original app

### Requirement: A live check replays first and then asks the model

`traceeval check <change>` SHALL first replay the change, and end with a regression when a replayed test fails that
passes on the original app. The adaptive method then MUST pick among the diverged tests only, each run with the real
model behind the cassette, so that only the requests from its divergence on are paid for.

#### Scenario: A replayed failure

- **WHEN** a test that passes on the original app fails in the replay of the change
- **THEN** the check ends with `regression` and calls no model

#### Scenario: A failure is confirmed

- **WHEN** `--confirm` is given and a test fails
- **THEN** it runs again, and a third time when the second run passes; two failures of three count

#### Scenario: The check stops

- **WHEN** a test fails, every diverged test has passed, the method is confident nothing broke, or the budget is spent
- **THEN** the check stops and says why

### Requirement: A clean verdict can promise a miss rate

With a target miss rate `alpha` (`--miss-rate`), the threshold under which the method says clean SHALL be set on
the recording's own changes: per group of changes, the k-th smallest of the n values of the regressions the replay
leaves open, with `k = floor(alpha (n + 1))`. A change MUST get the threshold of its own group, and a group with too
few recorded regressions MUST have none.

#### Scenario: The value of a regression

- **WHEN** a recorded regression is followed in the method's order while each test passes
- **THEN** its value is the probability the method has reached at the first test that reveals it

#### Scenario: No safe threshold

- **WHEN** `k` is 0
- **THEN** no threshold is safe, and every test the change reaches runs

#### Scenario: The groups

- **WHEN** a change is checked
- **THEN** its group is read off the kinds of its changed components before any test runs: a skill's steps, text the
  model reads, an agent's tools and skills, the configuration, the starting data, or code

#### Scenario: The method learns from the other half

- **WHEN** a threshold is set
- **THEN** the recorded changes are split into two fixed halves, the values are taken from one, and the method learns
  from the other, both while setting the threshold and in the check

### Requirement: A clean verdict can require the coverage floor

With `--floor`, a check SHALL NOT say clean before the coverage floor has run: the cheapest set of tests that covers
every changed component some test exercised on the original app, and every affected mandatory property some test
checks. The tests whose outcome is already known MUST count as covering, for free.

#### Scenario: The floor is a greedy cover

- **WHEN** the floor is chosen
- **THEN** the next test is the one that adds the most uncovered items per token

#### Scenario: A test that fails on the original app

- **WHEN** a test fails on the original app
- **THEN** it covers nothing in the floor

### Requirement: Generated changes are enumerated from the app and replayed for free

Next to the 43 hand-written changes, `mutation/generator.py` SHALL enumerate every edit of a fixed set of kinds that
the app's own files allow, with no label: the recording decides whether one is a regression. Replaying them MUST cost
CPU only, each on a temporary copy that is thrown away.

#### Scenario: The kinds of edit

- **WHEN** the changes are generated
- **THEN** they are skill steps deleted, swapped or negated, guards deleted, prose rules deleted or rewrapped, tools
  dropped from agents, settings changed, call arguments swapped, conditions negated, comments added, fixture values
  replaced, and text the model reads cut (agent prompts and descriptions, tool and parameter descriptions)

#### Scenario: A generated change fits one version of the app

- **WHEN** a generated change is applied to another version of the app
- **THEN** the operator raises, because every edit names the line it starts at and the text it expects there

#### Scenario: The generated changes of a recording

- **WHEN** `traceeval replay-first --generated` runs
- **THEN** `history/generated.jsonl` holds one line per change, the first being the original app, with what its
  diff touched and the replay of every test

#### Scenario: Learning and evaluation stay apart

- **WHEN** generated changes are split
- **THEN** within each kind, in a fixed shuffle that depends on the ids and the seed only, every other change is held
  out for evaluation

### Requirement: A failing batch points to its culprits before any model call

A batch's members SHALL each be replayed alone against the cassette. Before any model call, those replays MUST give
the tests each member reaches, the members that reach no test and fail none, and the members whose own replay fails
a test that passes on the original app.

#### Scenario: The suspects of a failure

- **WHEN** a test fails on the batch
- **THEN** the suspects are the members whose own replay reaches or fails that test

#### Scenario: One suspect, several, or none

- **WHEN** the suspects are known
- **THEN** one is the culprit with no further run; several are told apart by running the failing test on halves of
  them; none means the failure comes from the members together

### Requirement: Two orders use nothing but the replay

The replay-first comparison SHALL add two orders to the default strategies: `cheapest`, the tests by cost after the
requests that replay, and `late_divergence`, the tests the change reaches latest first.

#### Scenario: The latest divergence first

- **WHEN** `late_divergence` orders the tests
- **THEN** they come by the share of the test that replays before its first new request, the cheaper first among
  equals, and every share is 0 without a replay
