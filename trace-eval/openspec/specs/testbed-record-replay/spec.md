# Testbed: record-then-replay experiments and metrics

## Purpose

Strategies are compared without re-running agents: the full suite is recorded once per change, and every strategy is
then replayed offline against those recordings. This decouples method development from execution cost, and is what lets
detection be measured honestly against a known fault matrix. Code: `traceeval/experiment/`, `traceeval/cli.py`.

## Requirements

### Requirement: Runs are recorded once per variant

The baseline SHALL be recorded with per-test coverage and the variants without it, each for K repetitions of the whole
suite.

#### Scenario: Baseline

- **WHEN** the baseline is recorded
- **THEN** `history/baseline.jsonl` holds every case times K, with observed dependencies including code functions and lines

#### Scenario: A variant

- **WHEN** a change is recorded
- **THEN** `history/variants/<id>.jsonl` holds every case times K for the materialised copy

#### Scenario: Variants coexist in one process

- **WHEN** several variants are loaded
- **THEN** each loads under a unique module name, so a code mutation takes effect only in its own variant

### Requirement: Runs reproduce across processes

Seeds MUST be derived with a stable hash, never Python's `hash`, because string hashes are salted per process.

#### Scenario: Different hash salts

- **WHEN** the same cases run under different values of `PYTHONHASHSEED`
- **THEN** their token counts are the same

### Requirement: Ground truth is a majority flip

A test SHALL reveal a change when its baseline pass rate is at least 0.5 and its pass rate under the change is below 0.5.
A change with at least one revealing test is a regression.

#### Scenario: One flaky failure is not a reveal

- **WHEN** a test fails in a minority of its repetitions under a change
- **THEN** it does not reveal the change

#### Scenario: A test already failing does not reveal

- **WHEN** a test's baseline pass rate is below 0.5
- **THEN** it reveals no change

### Requirement: Replay answers from the recordings

Every (variant, strategy, budget, seed) SHALL build its context from baseline facts and the variant's change set, and
each test it runs MUST be answered from a recorded run of that variant.

#### Scenario: A test is executed in replay

- **WHEN** a strategy asks the oracle for a test
- **THEN** the outcome and the cost come from one repetition of that variant's recording, chosen by the seeded generator

#### Scenario: The defaults of a replay

- **WHEN** no budgets are given
- **THEN** they are 2, 5, 10, 20, 30, 50 and 100 percent of the full-suite tokens

#### Scenario: The results are kept

- **WHEN** evaluation finishes
- **THEN** `results/replay.csv` has one row per replay and `results/prioritization.csv` one per strategy, seed and change with a revealing test

### Requirement: Metrics separate detection from false alarms

A change SHALL count as detected when a revealing test ran and failed. A failure of a non-revealing test MUST count as a
false alarm and not as detection.

#### Scenario: A non-revealing test fails

- **WHEN** a test outside the revealing set fails in a replay
- **THEN** `false_alarm` is true and `detected` is not set by it

#### Scenario: Cost to detection

- **WHEN** a revealing test fails
- **THEN** the cost to detection is the tokens spent up to and including the first such test

#### Scenario: A stop is judged correct

- **WHEN** the reason is `clean`, or `regression`, or one of `budget`, `exhausted`, `uninformative`
- **THEN** it is correct if the change is benign, or a regression, or the detection outcome matches the change, respectively

#### Scenario: Nothing to reason about is judged

- **WHEN** the stop reason is `no_components`
- **THEN** it is correct only if the change is benign

### Requirement: Prioritization is measured on the complete order

APFD and cost-cognizant APFD SHALL be computed on a strategy's order extended with the tests it left out, and MUST be
undefined when no test reveals the change.

#### Scenario: A revealing test early scores higher

- **WHEN** one test of four reveals the change
- **THEN** APFD is higher with that test first than last

#### Scenario: A revealing test outside the order

- **WHEN** a revealing test is not in the order passed to APFD
- **THEN** it counts as never detected

#### Scenario: No revealing test

- **WHEN** nothing reveals the change
- **THEN** both metrics are `None`

### Requirement: The report states whether the testbed is sound

The report SHALL show the ground truth, detection against budget and against tokens spent, benign waste and adaptive
stop reasons, and MUST state the testbed's sanity before any comparison.

#### Scenario: A regression nobody reveals

- **WHEN** a change labelled a regression has no revealing test, or a benign change has one
- **THEN** the sanity line reads VIOLATED
