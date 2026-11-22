# Testbed: selection and prioritization strategies

## Purpose

After a change, a strategy decides which tests run and in what order under a token budget. Strategies are compared by
replay, so what each may know has to be strict: otherwise a result could come from information a real selector would
not have. Every run follows the same two rules, so that strategies are compared like for like. Code:
`traceeval/selection/` (`base.py` the interface and the two rules, `strategies.py` the baselines, `adaptive_bayes.py`
the proposed method, `adapted.py` two methods from the literature, `extras.py` two more baselines).

## Requirements

### Requirement: Every run follows the same two rules

A test the model already fails on the original app MUST NOT be run, since it cannot reveal a change, and a run MUST
end at its first failure with the stop reason `regression`. With replay-first, the tests whose outcome the replay gave
MUST NOT be run either, and a test MUST cost only what is left of it after the requests that replay.

#### Scenario: A test that fails on the original app

- **WHEN** a test's baseline pass rate is below 0.5
- **THEN** no strategy runs it

#### Scenario: The first failure

- **WHEN** a test that passes on the original app fails on the changed one
- **THEN** the run stops at once with `regression`, whatever the strategy

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

The default comparison MUST hold `full`, `random`, `declared`, `ir_tfidf`, `observed`, `observed_diverse`,
`cost_aware`, `history_ml`, the two methods from the literature adapted as baselines `casper_slices` and
`risk_aware_ts`, and `adaptive_bayes`. The replay-first comparison SHALL add `cheapest` and `late_divergence`
(`testbed-replay-first`). The variants of the proposed method (`adaptive_bayes_tfidf`, `adaptive_bayes_notext`,
`adaptive_bayes_nomandatory`, `adaptive_bayes_floor`) and of the bandit (`risk_aware_ts_per_token`) SHALL be
optional and run only with `--strategies all` or by name.

#### Scenario: Reference order

- **WHEN** `full` orders the tests
- **THEN** it returns the whole suite in catalog order

#### Scenario: Declared dependencies select

- **WHEN** `declared` orders the tests
- **THEN** it keeps only tests whose hand-written dependencies touch the change, by risk, then affinity, then cost

#### Scenario: Observed dependencies select

- **WHEN** `observed` orders the tests
- **THEN** it keeps only tests whose baseline traces touch the change, by affinity times severity divided by cost

#### Scenario: Observed dependencies, spread over behaviours

- **WHEN** `observed_diverse` orders the tests
- **THEN** it takes the tests `observed` would select one group of behaviour (agents, tools, faulty or not) at a
  time, so that the budget covers many behaviours before it repeats one

#### Scenario: The cheapest first

- **WHEN** `cheapest` orders the tests
- **THEN** it returns the whole suite by cost, the cheapest first

#### Scenario: Text similarity ranks everything

- **WHEN** `ir_tfidf` orders the tests
- **THEN** it ranks every test by TF-IDF cosine similarity between the change text and the test text

#### Scenario: Cost-aware ranking keeps every test

- **WHEN** `cost_aware` orders the tests
- **THEN** it ranks every test by `severity * (0.05 + affinity) * (2 - pass_rate) / cost`, with 1 added to the affinity of a test that executed a changed line

#### Scenario: Slices of tests that behave alike

- **WHEN** `casper_slices` runs
- **THEN** it cuts the suite into slices of tests that behave alike on the original app, runs two representatives of
  every slice (cheaper slices first), and then the slices whose failure rate moved, without looking at the diff

#### Scenario: A bandit over the tests' risk

- **WHEN** `risk_aware_ts` runs
- **THEN** it runs, one test at a time and each at most once, the test whose sampled failure probability times its
  risk weight is highest, until no unrun test fits the budget or a test fails, without looking at the diff

#### Scenario: Adaptations, not reproductions

- **WHEN** `casper_slices` or `risk_aware_ts` is read
- **THEN** its docstring says where the testbed differs from the paper's setting and what was done about it

#### Scenario: Prediction learns from the other changes

- **WHEN** `history_ml` orders the tests
- **THEN** it ranks them by a balanced logistic regression trained on the outcomes of the other changes, fitted
  in-house without scikit-learn, the one baseline that learns from the same history as the proposed method

#### Scenario: Prediction falls back when it cannot learn

- **WHEN** `history_ml` has no usable training data, such as only one outcome class
- **THEN** it returns the `cost_aware` order

### Requirement: A non-adaptive strategy is run greedily within the budget

The default run SHALL execute a strategy's order without the tests that fail on the original app, skip a test whose
expected cost does not fit what remains, and stop at the first failure or when the budget is spent.

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
