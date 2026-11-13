# Testbed: selection and prioritization strategies

## Purpose

After a change, a strategy decides which tests run and in what order under a token budget. Strategies are compared by
replay, so what each may know has to be strict: otherwise a result could come from information a real selector would
not have. Code: `traceeval/selection/`.

## Requirements

### Requirement: A strategy uses only what is known before running

A strategy MUST use only the change set, the catalog, baseline history and the outcomes of other changes. It MUST NOT
use the mutation's label or any outcome of the variant under evaluation, except through the oracle.

#### Scenario: Learning excludes the change under evaluation

- **WHEN** a strategy is evaluated on a variant
- **THEN** its training variants are all the others, never that variant

#### Scenario: A strategy learns outcomes only by running tests

- **WHEN** an adaptive strategy needs a test's outcome under the change
- **THEN** it gets it by calling the oracle, which also reports what the test cost

### Requirement: A selected test touches the change

A test SHALL count as touched when a changed component's identifier, or its base identifier, is among the test's
dependencies. A module-level code change MUST touch a test that used any function of that file.

#### Scenario: A sub-component matches its base

- **WHEN** `skill:x#procedure` changes and a test depends on `skill:x`
- **THEN** the test is touched

#### Scenario: A module-level change matches the file's functions

- **WHEN** `code:<file>` changes and a test depends on `code:<file>::<function>`
- **THEN** the test is touched

#### Scenario: Line hits count once per file

- **WHEN** a test executed several changed lines of one file
- **THEN** those lines add 1 to its affinity

### Requirement: Each strategy has its own defined behaviour

The default comparison MUST hold `full`, `random`, `declared`, `ir_tfidf`, `observed`, `cost_aware` and `adaptive_bayes`.
`observed_diverse` and `history_ml` SHALL be optional and run only with `--strategies all` or by name.

#### Scenario: Reference order

- **WHEN** `full` orders the tests
- **THEN** it returns the whole suite in catalog order

#### Scenario: Declared dependencies select

- **WHEN** `declared` orders the tests
- **THEN** it keeps only tests whose hand-written dependencies touch the change, by risk, then affinity, then cost

#### Scenario: Observed dependencies select

- **WHEN** `observed` orders the tests
- **THEN** it keeps only tests whose baseline traces touch the change, by affinity times severity divided by cost

#### Scenario: Text similarity ranks everything

- **WHEN** `ir_tfidf` orders the tests
- **THEN** it ranks every test by TF-IDF cosine similarity between the change text and the test text

#### Scenario: Cost-aware ranking keeps every test

- **WHEN** `cost_aware` orders the tests
- **THEN** it ranks every test by `severity * (0.05 + affinity) * (2 - pass_rate) / cost`, with 1 added to the affinity of a test that executed a changed line

#### Scenario: Prediction falls back when it cannot learn

- **WHEN** `history_ml` has no usable training data, such as only one outcome class
- **THEN** it returns the `cost_aware` order

### Requirement: A non-adaptive strategy is run greedily within the budget

The default run SHALL execute a strategy's order, skip a test whose expected cost does not fit what remains, and stop
when the budget is spent.

#### Scenario: A test that does not fit is skipped

- **WHEN** the next test's expected cost is more than the remaining budget
- **THEN** it is skipped and the next one is considered

#### Scenario: A selecting strategy runs out of tests

- **WHEN** the order ends with budget left
- **THEN** the stop reason is `exhausted`, and otherwise `budget`

### Requirement: Only stochastic orders depend on the seed

An order SHALL be cached per strategy and change, and per seed as well only for a strategy marked stochastic.

#### Scenario: A deterministic order is reused across budgets

- **WHEN** a non-stochastic strategy is evaluated at several budgets and seeds for one change
- **THEN** its order is computed once
