# Testbed: record-then-replay experiments and metrics

## Purpose

Strategies are compared without re-running agents: the full suite is recorded once per change, and every strategy is
then replayed offline against those recordings. This decouples method development from execution cost, and is what lets
detection be measured honestly against a known fault matrix. The agents are played by a real model (Gemma by default),
so a test may pass in some repetitions and fail in others: the ground truth is a vote over K repetitions, and a run that
the environment broke (`INFRA_INVALID`: a server down, an answer the cassette lacks) is left out of it. A recording
also keeps every answer the model gave on the original app (its cassette), which replay-first testing answers from
(`testbed-replay-first`), and says what it was made from and with (its manifest). Code: `traceeval/experiment/`,
`traceeval/cli.py`.

## Requirements

### Requirement: Runs are recorded once per variant

The baseline SHALL be recorded with per-test coverage and the variants without it, each for K repetitions of the whole
suite. With a served model the cases of a variant MAY run in parallel threads; the baseline MUST run one case at a
time, because its coverage contexts are process-wide.

#### Scenario: Baseline

- **WHEN** the baseline is recorded
- **THEN** `history/baseline.jsonl` holds every case times K, with observed dependencies including code functions and
  lines, and `history/cassette.jsonl` holds every answer the model gave on the way

#### Scenario: The empty change

- **WHEN** the changed copies are recorded
- **THEN** the original app is recorded first the way the copies are (several cases at a time, without coverage), in
  `history/unchanged.jsonl`: what that way of running does to the outcomes on its own

#### Scenario: A variant

- **WHEN** a change is recorded
- **THEN** `history/variants/<id>.jsonl` holds every case times K for the materialised copy, made from the
  recording's own copy of the original app (`variants/baseline/sut`), not from `traceeval/sut` as it is at that time

#### Scenario: A variant recorded for the tests it reaches

- **WHEN** a change is recorded with `reached_only`
- **THEN** the copy is replayed first, only the tests that diverge run with the model, and each test that replays to
  the end has one record, its replayed run, marked `stand_in`

#### Scenario: Variants coexist in one process

- **WHEN** several variants are loaded
- **THEN** each loads under a unique module name, so a code mutation takes effect only in its own variant

### Requirement: Runs reproduce across processes

Seeds MUST be derived from names by a stable function of their characters, never Python's `hash`, because string
hashes are salted per process.

#### Scenario: Different hash salts

- **WHEN** the same cases replay under different values of `PYTHONHASHSEED`
- **THEN** their token counts are the same

#### Scenario: The seed of a replay

- **WHEN** a replay of a change starts with seed number s
- **THEN** its generator is seeded with 1000 × s plus the sum of the character codes of the change's id

### Requirement: Ground truth is a majority flip

A test SHALL reveal a change when its baseline pass rate is at least 0.5 and its pass rate under the change is below 0.5.
A change with at least one revealing test is a regression. Pass rates MUST count only the runs the environment did not
break, and a test that fails under the empty change MUST reveal nothing.

#### Scenario: One unstable failure is not a reveal

- **WHEN** a test fails in a minority of its repetitions under a change
- **THEN** it does not reveal the change

#### Scenario: A run the environment broke counts nowhere

- **WHEN** a recorded run is `INFRA_INVALID`
- **THEN** it is left out of every pass rate and never drawn by the replay, and the report's header counts it

#### Scenario: A test already failing does not reveal

- **WHEN** a test's baseline pass rate is below 0.5
- **THEN** it reveals no change

#### Scenario: The way of running fails a test

- **WHEN** a test's majority outcome under the empty change is a failure
- **THEN** it reveals no change, since the way the copies are run, not the change, fails it

### Requirement: Replay answers from the recordings

Every (variant, strategy, budget, seed) SHALL build its context from baseline facts and the variant's change set, and
each test it runs MUST be answered from a recorded run of that variant. Every run MUST leave out the tests that fail
on the original app and end at its first failure (`testbed-test-selection`).

#### Scenario: A test is executed in replay

- **WHEN** a strategy asks the oracle for a test
- **THEN** the outcome and the cost come from one valid repetition of that variant's recording, chosen by the seeded
  generator; a test the variant never ran validly answers as on the original app

#### Scenario: The defaults of a replay

- **WHEN** no budgets are given
- **THEN** they are 2, 5, 10, 20, 30, 50 and 100 percent of the full-suite tokens

#### Scenario: The results are kept

- **WHEN** evaluation finishes
- **THEN** `results/replay.csv` has one row per replay and `results/prioritization.csv` one per strategy, seed and change with a revealing test

#### Scenario: The evaluation made replay-first

- **WHEN** the recording has been replayed (`history/replay_first.jsonl`)
- **THEN** the evaluation is made a second time into `results/replay_first.csv`: a test that replays to the end is
  not run, a replayed failure ends the run before any test runs, and a diverged test is charged the tokens after its
  divergence point

### Requirement: Metrics separate detection from false alarms

A change SHALL count as detected when a revealing test ran and failed. A failure of a test that passes on the original
app and does not reveal the change MUST count as a false alarm and not as detection.

#### Scenario: A non-revealing test fails

- **WHEN** a test that passes on the original app but is outside the revealing set fails in a replay
- **THEN** `false_alarm` is true, `detected` is not set by it, and the run has stopped on it with a regression verdict
  the ground truth does not back

#### Scenario: Cost to detection

- **WHEN** a revealing test fails
- **THEN** the cost to detection is the tokens spent up to and including the first such test

#### Scenario: A stop is judged correct

- **WHEN** the reason is `clean`, or `regression`, or one of `budget`, `exhausted`, `uninformative`
- **THEN** it is correct if the change is benign, or a regression, or the detection outcome matches the change, respectively

#### Scenario: Coverage counts what was known

- **WHEN** a replay-first run reports its change coverage
- **THEN** the tests whose outcome the replay gave count as run, next to the tests the strategy ran

#### Scenario: Nothing to reason about is judged

- **WHEN** the stop reason is `no_components`
- **THEN** it is correct only if the change is benign

### Requirement: Prioritization is measured on the complete order

APFD and cost-cognizant APFD SHALL be computed on a strategy's order extended with the tests it left out, in suite
order. The change MUST count as one fault, found by the first revealing test of the order, so that its severity
cancels out of APFD_c. Both MUST be undefined when no test reveals the change.

#### Scenario: A revealing test early scores higher

- **WHEN** one test of four reveals the change
- **THEN** APFD is higher with that test first than last

#### Scenario: Only the first revealing test counts

- **WHEN** several tests reveal the change
- **THEN** APFD is `1 - p / n + 1 / (2n)` with `p` the position of the first of them, and APFD_c is the share of the
  order's cost left unspent when it runs, plus half of its own cost

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

#### Scenario: Changes without labels

- **WHEN** the recorded changes have no label (the generated ones)
- **THEN** the sanity line instead says how many of them a test reveals

### Requirement: A recording says what it was made from

A recording SHALL keep a manifest (`history/manifest.json`): the model and the judge, the model servers, the
repository's commit and whether files differed from it, digests of the app's files and of the catalog, and how the
baseline and the changes were run. A recording fits one version of the app and of the tests, so a difference from
today's files MUST be reported, and a live check MUST refuse it.

#### Scenario: The manifest is written

- **WHEN** `traceeval baseline` runs
- **THEN** it starts the manifest anew, and `traceeval mutants` adds how the changed copies were run

#### Scenario: The app changed since the recording

- **WHEN** the app's files differ from the recording's own copy of them
- **THEN** `traceeval check` refuses the recording, and the commands that only read it say what differs and go on

#### Scenario: A digest ignores line endings only

- **WHEN** the same files are checked out on another system
- **THEN** the digest is the same, while any other difference, a comment included, changes it
