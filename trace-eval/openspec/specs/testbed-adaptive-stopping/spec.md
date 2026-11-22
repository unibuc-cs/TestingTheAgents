# Testbed: adaptive Bayesian selection with stopping

## Purpose

`adaptive_bayes` is the proposed method. It treats selection, prioritization and stopping as one sequential decision:
keep a probability over which changed components are broken, run the test with the best expected information per
token, update, and stop when the evidence is good enough. The models decode greedily, so a test that passed on the
original app and fails on the changed one shows a changed behaviour, and a test the model already fails on the
original app tells nothing either way and is not run. The rules here are what the published results rest on. Code:
`traceeval/selection/adaptive_bayes.py`, and `traceeval/experiment/stopping.py` for a threshold set for a miss rate.

## Requirements

### Requirement: Hypotheses are combinations of broken components

The method SHALL keep an exact posterior over every subset of the changed components, with at most 8 components, each
with a prior that depends on its kind. Tool and line components MUST NOT be hypotheses of their own, because they are
facets of the code component.

#### Scenario: Too many components

- **WHEN** a change has more than 8 hypothesis components
- **THEN** the 8 with the highest priors are kept

#### Scenario: Prior by kind

- **WHEN** a component's kind is code or skill; config or agent; fixture; agent prompt or tool schema; or skill prose
- **THEN** its prior is 0.5; 0.45; 0.3; 0.15; or 0.12

### Requirement: Sensitivities are calibrated from other changes

A test's sensitivity to a component SHALL be a reveal ratio measured on the training changes, scaled by the test's own
record on earlier changes, by how often it exercised the component, and by a tilt for its lexical relevance and for a
declared dependency. Calibration MUST use only the training variants.

#### Scenario: The reveal ratio is measured

- **WHEN** training changes are available for a component kind
- **THEN** the ratio is the mean share of statically impacted tests that actually revealed the change, padded towards
  the kind's default so that one or two changes move it little, and kept between 0.01 and 0.9

#### Scenario: A test's own record lifts its sensitivity

- **WHEN** earlier changes of a kind touched a test
- **THEN** its ratio is multiplied by the changes it revealed over those an average impacted test would have
  revealed, both padded by 2

#### Scenario: Code separates line hits from function hits

- **WHEN** a component is code
- **THEN** executing a changed line and executing only the changed function are calibrated separately

#### Scenario: No history

- **WHEN** no training change covers a kind
- **THEN** the default ratio for that kind is used

#### Scenario: A sensitivity stays bounded

- **WHEN** a test's dependencies match the component
- **THEN** its sensitivity is kept between 0.02 and 0.9; a test with no link at all gets the indirect value 0.02

#### Scenario: The text measure is an option

- **WHEN** the method compares a test's text with the change
- **THEN** it uses word overlap by default, the TF-IDF similarity in `adaptive_bayes_tfidf`, and no text at all in
  `adaptive_bayes_notext`

### Requirement: The next test is the best information per token

The next test SHALL maximise expected information gain, tilted by risk, per token, among the tests that can be run
and fit the remaining budget. Each test MUST run at most once, because a rerun would give the same answer.

#### Scenario: A test's own failure rate is part of its likelihood

- **WHEN** a test's failure probability is computed under a hypothesis
- **THEN** its baseline failure rate is part of it, floored at 0.01, so that no single outcome rules a hypothesis out

#### Scenario: Near-duplicates of a passed test count for less

- **WHEN** a test passes
- **THEN** the sensitivities of tests with the same agents, tools, fault profile and dataset are multiplied by 0.35

### Requirement: Stopping has an explicit reason

The method MUST report why it stopped. A `regression` stop MUST require an observed failure of a test that passed on
the original app.

#### Scenario: Stop clean

- **WHEN** the probability that anything is broken falls below `eps_clean`, 0.05 unless a check set it for a miss rate
- **THEN** the method stops with reason `clean`

#### Scenario: Stop regression

- **WHEN** a test that passes on the original app fails on the changed one
- **THEN** the method stops at once with reason `regression`, as every strategy does

#### Scenario: A test the model already fails is not run

- **WHEN** a test fails on the original app, or with replay-first its outcome on the copy is already known
- **THEN** the method never chooses it

#### Scenario: Every test that can run has passed

- **WHEN** no test that can be run is left unrun, and all have passed
- **THEN** the method stops with reason `exhausted`

#### Scenario: A threshold set for a miss rate runs every reached test

- **WHEN** the clean threshold was set for a miss rate (`exhaustive`)
- **THEN** the tests that can no longer move the probability run too, the cheapest first, so that `exhausted` means
  every test the change reaches has run

#### Scenario: Nothing left to learn or afford

- **WHEN** no remaining test has a positive score
- **THEN** the reason is `budget` if the remaining budget is below the cheapest test, and otherwise `uninformative`

#### Scenario: Nothing to reason about

- **WHEN** the change set has no hypothesis components, such as a comment-only change
- **THEN** no test runs and the reason is `no_components`

### Requirement: Every mandatory property the change may affect gets a test

A run that found no regression MUST NOT end before every mandatory property the change may affect has a test, the
cheapest unrun one that checks it and passes on the original app, while the budget allows.

#### Scenario: A mandatory property is still unchecked

- **WHEN** a run ends without a regression, and a mandatory property the change may affect has no test yet
- **THEN** the cheapest affordable test that checks it and can be run runs, and a failure there stops the run with
  `regression`; with replay-first, a test whose passing outcome the replay gave already checks its properties

#### Scenario: The rule switched off

- **WHEN** `adaptive_bayes_nomandatory` runs
- **THEN** it is the same method without this rule, to measure what the rule costs and adds

#### Scenario: The coverage floor instead

- **WHEN** `adaptive_bayes_floor` runs, or `traceeval check --floor`
- **THEN** the rule is the coverage floor (`testbed-replay-first`): the cheapest set of tests that also covers every
  changed component, with the tests already run and those the replay settled counting as covering

### Requirement: The order can be read without running anything

The method SHALL offer a non-adaptive order for prioritization metrics, without stopping and without using any outcome.

#### Scenario: The order for APFD

- **WHEN** `order` is called
- **THEN** it gives the greedy order assuming every test passes, then the remaining tests in cost-aware order
