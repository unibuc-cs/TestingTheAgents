# Testbed: adaptive Bayesian selection with stopping

## Purpose

`adaptive_bayes` is the proposed method. It treats selection, prioritization and stopping as one sequential decision:
keep a probability over which changed components are broken, run the test with the best expected information per
token, update, and stop when the evidence is good enough. The rules here are what the published results rest on. Code:
`traceeval/selection/adaptive_bayes.py`.

## Requirements

### Requirement: Hypotheses are combinations of broken components

The method SHALL keep an exact posterior over every subset of the changed components, with at most 8 components, each
with a prior that depends on its kind. Tool and line components MUST NOT be hypotheses of their own, because they are
facets of the code component.

#### Scenario: Too many components

- **WHEN** a change has more than 8 hypothesis components
- **THEN** the 8 with the highest priors are kept

#### Scenario: Prior by kind

- **WHEN** a component's kind is code, tool or skill; config or agent; agent prompt; or skill prose
- **THEN** its prior is 0.5; 0.45; 0.15; or 0.12

### Requirement: Sensitivities are calibrated from other changes

A test's sensitivity to a component SHALL be a reveal ratio measured on the training changes, scaled by how often the
test exercised the component and by a tilt for its lexical relevance and for a declared dependency. Calibration MUST use
only the training variants.

#### Scenario: The reveal ratio is measured

- **WHEN** training changes are available for a component kind
- **THEN** the ratio is the mean share of statically impacted tests that actually revealed the change, kept between 0.01 and 0.9

#### Scenario: Code separates line hits from function hits

- **WHEN** a component is code
- **THEN** executing a changed line and executing only the changed function are calibrated separately

#### Scenario: No history

- **WHEN** no training change covers a kind
- **THEN** the default ratio for that kind is used

#### Scenario: A sensitivity stays bounded

- **WHEN** a test's dependencies match the component
- **THEN** its sensitivity is kept between 0.02 and 0.9, and a test with no link at all gets the indirect value 0.02

### Requirement: The next test is the best information per token

The next test SHALL maximise expected information gain, tilted by risk, per token, among tests that fit the remaining
budget and still have a run left.

#### Scenario: A flaky test may run twice

- **WHEN** a test's baseline failure rate is above 0.1
- **THEN** it may be run a second time, and any other test only once

#### Scenario: The likelihood allows for flakiness

- **WHEN** a test's failure probability is computed under a hypothesis
- **THEN** its baseline flakiness is part of it, floored at 0.01, so one failure of a flaky test is weak evidence

#### Scenario: Near-duplicates of a passed test count for less

- **WHEN** a test passes
- **THEN** the sensitivities of tests with the same agents, tools, fault profile and dataset are multiplied by 0.35

### Requirement: Stopping has an explicit reason

The method MUST report why it stopped. A `regression` stop MUST require an observed failure.

#### Scenario: Stop clean

- **WHEN** the probability that anything is broken falls below 0.05
- **THEN** the method stops with reason `clean`

#### Scenario: Stop regression

- **WHEN** a failure has been observed and the probability that something is broken exceeds 0.98
- **THEN** the method stops with reason `regression`

#### Scenario: High belief without a failure does not stop

- **WHEN** the probability is above 0.98 and no test has failed
- **THEN** the method does not stop with reason `regression`

#### Scenario: Nothing left to learn or afford

- **WHEN** no remaining test has a positive score
- **THEN** the reason is `budget` if the remaining budget is below the cheapest test, and otherwise `uninformative`

#### Scenario: Nothing to reason about

- **WHEN** the change set has no hypothesis components, such as a comment-only change
- **THEN** no test runs and the reason is `no_components`

### Requirement: The order can be read without running anything

The method SHALL offer a non-adaptive order for prioritization metrics, without stopping and without using any outcome.

#### Scenario: The order for APFD

- **WHEN** `order` is called
- **THEN** it gives the greedy order assuming every test passes, then the remaining tests in cost-aware order
