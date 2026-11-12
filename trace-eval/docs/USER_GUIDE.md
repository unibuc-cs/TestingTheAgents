# User guide

Read the README first. This guide adds what you need to work inside the repository.

## 1. Where a run lives

A run of the experiment lives in `runs/<name>/` at the repository root:

```text
runs/<name>/
  variants/<change>/   one changed copy of the app per change, with its diff.patch
  history/             the recorded runs: baseline.jsonl for the original app, variants/ for the changed copies
  results/             report.md, its figures, replay.csv
```

`traceeval check` (`experiment/check.py`) runs the README's loop live for one change: the test runs with the model,
and a recording (`--history`) supplies the baseline traces, the costs and the other changes' outcomes
([EXPERIMENT.md](EXPERIMENT.md) §5).

## 2. Vocabulary

Paths are relative to `traceeval/`.

- **Case / test**: one entry of the catalog, a scenario test in `catalog/tests/*.yaml` or a dataset item in
  `catalog/datasets/*.yaml` (ids such as `DS-ROUTING/r01`).
- **Property**: a behavioural requirement a test checks (`task_completion`, `safety_authorization`, ...), defined
  in the catalog of properties, `catalog/properties.yaml`, with its category, how the tests check it, whether it is
  mandatory and its threshold. A test lists the ids of the properties it checks.
- **Workflow**: a request that needs several specialists, run by a plan ([CONTENTOPS.md](CONTENTOPS.md)). A test
  that runs one end to end names it (`workflow: W1`), an id from `catalog/workflows.yaml`: W1 campaign launch, W2
  site optimization, W3 legal takedown, W4 localized price update, W5 broken release rollback, W6 privacy request.
- **Declared dependencies**: the `declared:` block a test author writes, incomplete on purpose.
- **Observed dependencies**: the components the trace shows the run touched (`agent:x`, `skill:x`, `tool:x`,
  `config:key`, `code:file::function`, `line:file:n`).
- **Change set**: the diff turned into components with the same identifiers (`mutation/changeset.py`). Comments,
  docstrings, blank lines and formatting add no component and no diff line.
- **Revealing test**: a test that passes on the baseline (the original app) and fails on the changed copy, by
  majority over $K$ repetitions (`--reps`).
- **Budget**: tokens, as a fraction of the full-suite cost.
- **Stop reason** (`adaptive_bayes` only): `clean`, `regression` (a test that passed on the original app failed),
  `budget`, `uninformative` (no remaining test could change the verdict) or `no_components` (an empty change set,
  for example after a comment-only edit).

## 3. Where to look in the code (in this order)

| Want to understand… | Read |
|---|---|
| what the agents do | `sut/skills/publishing-workflow/SKILL.md`, `sut/agents/publishing.yaml`, `sut/config/runtime.yaml` |
| how a request becomes tool calls | `sut/harness/runtime.py` (`_run_agent`), `dispatcher.py`, `backends/llm_openai.py` |
| how the orchestrator plans | `sut/skills/routing/SKILL.md`, `sut/tools/control_tools.py`, `runtime.py` (`_delegate`) |
| how a test is run and scored | `experiment/executor.py` (`run_case`), `scoring/scorers.py` |
| how a change becomes components | `mutation/catalog.py` (data), `mutation/changeset.py` |
| the baselines | `selection/strategies.py`; two optional ones in `selection/extras.py`, `observed_diverse` and `history_ml` (needs scikit-learn), included by `--strategies all` |
| two published methods, reproduced | `selection/reproduced.py` (CASPER's slices, Risk-Aware Adaptive Evaluation's bandit; each docstring says what was adapted) |
| the proposed method | `selection/adaptive_bayes.py` (its docstring explains the five steps) |
| the metrics | `experiment/metrics.py`, `experiment/evaluate.py` |
| coverage (of the suite, of a change) | `experiment/coverage.py` |
| the prototype (one change, live) | `experiment/check.py` |
| a run as OpenTelemetry spans | `tracing/otel.py` (`traceeval run --otel`; [AEM_ALIGNMENT.md](AEM_ALIGNMENT.md) §3.6) |

Everything else is plumbing (loaders, tracing, report).

## 4. How to read the report

- **Section 1**: each change with its number of revealing tests, and a sanity line. VIOLATED means a regression
  with no revealing test, one the model cannot see (§6), or a benign change with one, which would mean the testbed
  is broken.
- **Section 2**, four tables:
  - `detected`: the share of changes where a revealing test ran and failed;
  - the tokens actually spent: compare strategies on this column, not on the nominal budget, because the selecting
    strategies run out of tests, the adaptive one stops early and the rest always spend the whole budget;
  - the time spent, from each test's mean run time on the original app;
  - detection over the critical regressions only: the changes with a revealing test that checks a safety property.
- **Section 3**: the tokens spent on the changes no test reveals (the benign ones and the regressions the model
  cannot see), and the adaptive method's stop reasons: `clean` is the right answer on a benign change, `regression`
  on a regression.
- **Section 4**: selection recall (the share of the revealing tests inside the selected subset) and the quality of
  the complete order, by APFD and $\mathrm{APFD}_c$ (`experiment/metrics.py`; the papers are in
  [REFERENCES.md](REFERENCES.md)). Both score the whole suite run in that order with no stopping, each revealing
  test counting as one fault, found when it runs.
  - APFD (Rothermel et al. 2001): with $n$ tests, $m$ faults and $TF_i$ the position of the test that finds fault
    $i$, $\mathrm{APFD} = 1 - (TF_1 + \cdots + TF_m)/(nm) + 1/(2n)$. Near 1 when the first tests find every fault,
    near 0 when the last ones do; a random order scores about 0.5. A fault no test finds counts as found at
    position $n + 1$.
  - $\mathrm{APFD}_c$ (Elbaum, Malishevsky and Rothermel 2001) replaces positions by cost and weighs faults by
    severity: with $c_j$ the cost of the $j$-th test, $s_i$ the severity of fault $i$ (the revealing test's risk
    weight, 1 to 4), $C_i$ the cost spent before the test that finds it and $C$ the cost of the whole order,
    $\mathrm{APFD}_c = \sum_i s_i \,(C - C_i - c_{TF_i}/2) \big/ (C \sum_i s_i)$. Tokens per test vary by a factor
    of ten or more on this suite, so this is the one to read: an order can score well on APFD and poorly on
    $\mathrm{APFD}_c$ by putting the expensive tests first.
  - What to expect: `random` near 0.54 on both, `full` (catalog order) near 0.6, an order that uses the change 0.75
    or more. The adaptive method's order is the one its model would pick if every test passed, then the rest in
    cost-aware order.
- **Section 5**: each property's pass rate on the original app against its threshold, and per strategy the share of
  the properties a change breaks that its tests exercised.
- **Section 6**: coverage, of the suite and of each change. For the suite, per dimension (agent, feature, skill,
  tool, tool error path, configuration, setting value, property, workflow, execution path, risk): what the tests
  declare, what the traces show, what nothing covers; then, per agent, skill, tool and feature, the tests that
  declare it and the tests that invoke it (`traceeval coverage --history runs/gemma7` prints this part). For each
  change, without the ground truth: the changed components the executed tests exercised, the affected properties
  they checked, the affected workflows they ran, the affected features they reached, and how often a run that found
  no regression tested every affected mandatory property. [AEM_ALIGNMENT.md](AEM_ALIGNMENT.md) §3.5 defines the
  dimensions and "affected"; `traceeval check` prints the same for the change it checks.
- `replay.csv`: one row per (change, strategy, budget, seed), for slicing the results yourself.

## 5. How the adaptive method weighs a test

For every changed part of the app (a function, a skill's procedure, a config key) and every test, the method
estimates a **sensitivity**: the probability that the test fails if that part is broken. It runs the test that
tells it the most per token, high sensitivity at low cost, and a sensitive test that passes is strong evidence that
nothing broke. The sensitivity is the product of four factors (`selection/adaptive_bayes.py::sensitivity`); the
examples are for `code_retry_drop_idempotency` (retried writes lose their idempotency key, §6) on `runs/gemma7`:

```mermaid
flowchart LR
    K["kind ratio<br/>(other changes of this kind)"] --> S["sensitivity of the test<br/>to the changed part"]
    L["test record<br/>(what it caught before)"] --> S
    C["coverage<br/>(how often it ran the part)"] --> S
    W["tilt<br/>(text similarity, declared)"] --> S
    S --> I["information per token"]
    F["pass rate on the<br/>original app"] --> I
    O["cost in tokens"] --> I
    I --> P["pick the next test"]
    P --> U["run it, update<br/>the probabilities"]
    U --> Q{"stop?"}
    Q -->|"a test that used<br/>to pass fails"| REG["regression"]
    Q -->|"nothing broken,<br/>with high probability"| MAN["test every affected<br/>mandatory property"] --> CL["clean"]
    Q -->|"budget spent"| BU["budget"]
    Q -->|"no"| P
```

| factor | what it is | example |
|---|---|---|
| kind ratio | over the other recorded changes of this kind (code, skill, prompt or config; §6), the share of the tests a change touched that caught it, averaged; padded with two changes' worth of the kind's default, so a ratio learned from one or two changes stays near it | code changes: tests that ran a changed line caught the change 19% of the time on average (6 of the 12 that ran the changed line of the link check caught `code_links_external_lenient`, 5 of the 180 that ran the changed line of the agent loop caught `code_termination_off_by_six`); tests that only called a changed function caught none, the 1% floor |
| test record | the other changes of this kind that touched the test and that it caught, over the number an average touched test would have caught, both padded with 2 (`prior_strength`) | AUT-02 caught 3 where an average test would have caught 1.03: $(3 + 2)/(1.03 + 2) = 1.65$; AUT-13 caught none: $(0 + 2)/(1.03 + 2) = 0.66$ |
| coverage | how often the test ran the changed code in its runs on the original app, 0 to 1; when an agent loses a tool or a skill, how often the test used it | PUB-12 runs the changed line of `harness/retry.py` in every run: 1.0 |
| tilt | the text similarity between the test and the diff (0.5 to 1.5), plus 0.5 if the test's author declared the dependency; word overlap by default, TF-IDF in `adaptive_bayes_tfidf`, none in `adaptive_bayes_notext` (RESEARCH_PLAN §5.2) | a test whose request mentions publishing gets more weight for a change to the publishing skill |

A test with no known link to the changed part gets a small fixed sensitivity (`indirect`, 0.02).

### Mandatory properties

A run that found no regression does not end until every mandatory property the change may affect has a test: for
each one still unchecked, the cheapest test that checks it and passes on the original app, while the budget allows.
A failure there is a regression, as usual. The rule turns the catalog's mandatory flag into a guarantee at almost
no cost (RESEARCH_PLAN §5.3); `adaptive_bayes_nomandatory` is the ablation without it.

### Weights

`prior_strength` sets how far a short record can move a test, the tilt has a fixed range and `indirect` sets the
floor. The factors are not weighted against each other: with a few dozen changes, extra weights would mostly fit
noise. Only the text factor has been ablated (RESEARCH_PLAN §5.2).

### Where the records come from

Nothing is stored apart from the recordings. Each run recomputes the kind ratios and every test's record from the
recording it is given (`runs/<name>`, or `--history` for `traceeval check`), from every recorded change except the
one under evaluation, so the records grow as changes are recorded. This command adds a change to a recording:

```
traceeval mutants --workdir runs/<name> --only <change> --backend <the recording's>
```

In a team's pipeline, nightly full-suite runs play that role: every change with a known full-suite outcome becomes
one more entry in the record of each test it touched. `traceeval check` does not add its own runs, since a check
runs too few tests to know which the change breaks. Records match code by line number, so record again after
editing the app's code.

## 6. The controlled changes

The 43 changes (`mutation/catalog.py`): what each does, why it is in the set (a kind of change, a reach, or a trap
for selection), and the number of tests that reveal it in `runs/gemma7`. The other models' recordings are not clean
ground truths ([RESEARCH_PLAN.md](RESEARCH_PLAN.md) §5.4), so they have no column.

| change | what it does | why it is in the set | revealing tests (Gemma) |
|---|---|---|---|
| **Code: tools, services, harness** | | | |
| `code_metadata_arg_swap` | the SEO tool writes the title into the description field | a classic bug in a tool adapter; only tests that check the stored metadata see it | 5 |
| `code_retry_drop_idempotency` | retried writes lose their idempotency key, so a write retried after a lost acknowledgement happens twice | a harness bug that shows only under one kind of fault; reused by the SDD demo (FS-0105) | 5 |
| `code_approval_gate_bypass` | the dispatcher stops asking for approval tokens on guarded tools | a narrow safety guard that a single test depends on; reused by the SDD demo (FS-0102) | 1 |
| `code_links_external_lenient` | link validation treats every external URL as reachable | a bug in a service that several skills share; reused by the SDD demo (FS-0103) | 6 |
| `code_get_page_review_flag` | the shared `get_page` tool reports a requested review as approved | a shared tool with a wide reach, and the clearest case of model dependence | 4 |
| `code_edit_keeps_review` | editing a page no longer cancels its approved review | a service bug a model can hide: Gemma requests a review after every edit anyway | 0 |
| **Code: agent loop** | | | |
| `code_termination_off_by_six` | the agent loop stops each agent six tool calls before its configured budget | every test runs the changed line, but only long tasks fail: covering the code is not catching the bug | 5 |
| `code_delegation_truncates_answer` | the orchestrator receives only the first 40 characters of the specialist's answer | a delegation bug that shows only when the answer must carry a fact past 40 characters | 25 |
| **Skills** | | | |
| `skill_publish_drop_link_validation` | publishing no longer validates links | a change to a skill's procedure rather than to code. No test declares the link-check skill. The method alone calls the change clean, and the mandatory-coverage rule catches it | 4 |
| `skill_publish_drop_permission_check` | publishing no longer checks the user's permission | a safety rule enforced only in a skill: nothing below it stops the write | 3 |
| `skill_authoring_drop_metadata` | new pages no longer get SEO metadata | a removed step that one test notices | 1 |
| `skill_translation_wrong_default` | translation uses en-US instead of the configured languages | a skill that ignores a configuration value | 4 |
| `skill_rollback_drop_permission_check` | rollback no longer checks the permission; the service still refuses | defence in depth: the data stays safe and only the behaviour shows the mistake | 1 |
| `skill_rollback_restores_latest` | rollback restores the latest version instead of the requested one | a wrong argument in a procedure step | 3 |
| `skill_linkval_ignore_assets` | the shared link-validation skill lets broken asset references through | a change to a skill included by others, reaching tests that never name it | 0 |
| `skill_governance_drop_consent` | user data is exported without checking consent | a privacy rule enforced in a skill | 5 |
| `skill_seo_drop_length_guard` | SEO no longer refuses over-long titles | a guard the model must apply itself, and Gemma ignores the limit anyway; reused by the SDD demo (FS-0104) | 0 |
| **Agent definitions** | | | |
| `prompt_governance_consent_tool_removed` | the governance agent loses the `check_consent` tool | a change to an agent's tool list | 7 |
| `prompt_seo_tool_removed` | the SEO agent loses `set_page_metadata` | the same for a tool that writes | 8 |
| **Configuration** | | | |
| `config_disable_validate_links` | a feature flag turns link validation off everywhere | one key with a wide reach: the broad change in the set | 49 |
| `config_require_review_false` | pages no longer need an approved review before publishing | a policy switch in configuration; Gemma's own mistake hides it | 0 |
| `config_max_tool_calls_5` | each agent's step budget drops from 12 to 5 tool calls | a value that limits every agent; long tasks fail | 10 |
| `config_retries_0` | temporary tool failures are no longer retried | a change only the tests with an injected fault notice; reused by the SDD demo (FS-0105) | 8 |
| `config_seo_title_20` | the maximum SEO title length drops from 60 to 20 | a boundary value; Gemma ignores the limit anyway | 0 |
| `config_default_agent_publishing` | requests no specialist owns go to publishing instead of authoring | a routing setting the orchestrator reads | 3 |
| **Code and configuration together** | | | |
| `combined_seo_keyword_limit` | a keyword-count rule in code plus a very low limit in config | a regression that needs both edits; each alone is harmless | 1 |
| **Benign: no test should fail** | | | |
| `benign_skill_prose_reflow` | the publishing skill's prose is reworded, its procedure untouched | a wording change: a strategy should spend little on it | 0 |
| `benign_code_comment_docstring` | comments and docstrings change in the links service | leaves an empty change set (code only), so there is nothing to test | 0 |
| `benign_code_rename_locals` | local variables are renamed in the workflow service | a code edit, in a widely used function, that changes nothing | 0 |
| `benign_config_comments_reordered` | config comments are rewritten and sections reordered | an empty change set for configuration | 0 |
| `benign_new_unused_tool` | a new tool is registered that no agent may use | added code that nothing reaches | 0 |
| `benign_orchestrator_prompt_wording` | the orchestrator's prompt is reworded | a prompt edit on the agent every request passes through | 0 |
| `benign_translation_intents_reordered` | the translation agent's intents are reordered | an order a model ignores | 0 |
| **Aimed at the multi-agent workflows: planning, hand-offs, the AEM-style agents** | | | |
| `skill_routing_drop_approval` | the orchestrator no longer asks a person before a step that publishes, schedules or takes pages down | a human-in-the-loop rule that lives only in the orchestrator's skill and reaches every workflow. In W3 the dispatcher's token gate still blocks the takedown; in W1, W2 and W4 nothing below the skill stops the write | 11 |
| `skill_routing_drop_brand_gate` | the plan no longer requires the brand check before scheduling or publishing, and no longer stops at a failed check | a brand gate enforced only in the orchestrator's prose; one test sees it (WF1-02) | 1 |
| `code_delegation_drops_context` | a delegation no longer passes the ids of earlier steps on to the specialist | a bug in the planning path's hand-off. The trace still records the context, so the run looks right, and the tests whose ids travel in the task text do not notice | 4 |
| `code_insights_rank_reversed` | the pages ranked worst are the most viewed, and those ranked best the least viewed | a service bug in an agent modelled on AEM's, reaching its single-agent tests and W2 | 4 |
| `code_search_case_sensitive` | page search no longer lower-cases the page text, so a capitalised occurrence is missed | a shared service the brand agent uses: the legal takedown silently leaves a page up | 3 |
| `code_audit_ignores_alt_text` | the site audit no longer reports images without alt text | W2 runs the audit on every run but works from the missing description: covering the change is not revealing it | 1 |
| `code_brand_case_sensitive` | forbidden terms match only as written, so "Guaranteed returns" passes | W1 runs the brand check on every launch, but its pages write the term in lower case | 1 |
| `config_unpublish_no_approval` | taking a page down no longer needs an approval token | a config gate below the skill's approval rule; W3 reads the key on every takedown, but the orchestrator asks a person anyway | 1 |
| `benign_brand_skill_prose_reworded` | the brand-governance skill's prose is reworded, procedure and rules untouched | a wording change on one of the AEM-style agents | 0 |
| `benign_routing_guidance_reordered` | three bullets of the routing skill's guidance move to the top | a prompt edit on the skill every request reads | 0 |

A 0 means that no test reveals the change under that model, a fact about the model rather than a bug in the testbed
(§4). RESEARCH_PLAN §4.3 gives the criteria a change must meet to be in the set.

### Batches

A batch applies several catalog changes to one copy, as a nightly run or a pull request does (`BATCHES` in
`mutation/catalog.py`, listed after the 43 by `traceeval mutations`). Its members edit disjoint files, so their
edits compose (`tests/test_mutation_and_selection.py` checks it), and it is a regression when any member is one.
The 43 are recorded by default, a batch on request (`traceeval mutants --only <batch>`); `traceeval check <batch>`
checks it live and prints, after the verdict, the components it blames.

| batch | what it bundles | revealing tests (Gemma) |
|---|---|---|
| `batch_nightly` | a day's merges: six regressions across tools, harness, skills, an agent definition and a service, plus two harmless edits | 28 |
| `batch_publishing_pr` | one pull request on the publishing path: the skill drops its link validation, the link check lets external URLs through, taking a page down needs no approval token | 9 |
| `batch_benign` | all nine benign changes at once | 1: two of the prompt edits, harmless alone, change the orchestrator's answer together |

RESEARCH_PLAN §5.6 has what the strategies make of them, [results/gemma7/batches.md](results/gemma7/batches.md) the
full tables, and [results/gemma7/batch_sweep.md](results/gemma7/batch_sweep.md) twenty more batches of two to eight
changes drawn at random by `scripts/batch_sweep.py`.

## 7. How to extend

- **Property**: add an entry to `catalog/properties.yaml` (id, category, description, `checked_by`, `mandatory`,
  `threshold`, `sources`) before a test uses it; the loader rejects an unknown property and `pytest` fails if a
  property has no test. [AEM_ALIGNMENT.md](AEM_ALIGNMENT.md) §3.4 explains the fields. Or let a model draft the
  catalog from the requirements and tag the tests: `traceeval properties draft`, then edit
  `catalog/properties.draft.yaml` with `properties.draft.md` beside it, then `traceeval properties apply`; entries
  already in the catalog keep what a person wrote unless `--fresh`.
- **Test**: add a YAML entry. `expect` takes `route_to`, `state` (`[path, op, value]` with `==`, `!=`, `len`,
  `contains`, `in`, `>=`, `<=`, `absent`, `exists`), `tools_required`, `tools_forbidden`, `tools_not_attempted`,
  `tool_attempts`, `tool_results` (`[tool, path, op, value]` on the tool's last successful result), `audit`,
  `response_contains`, `response_excludes`, `max_steps`, `termination`, `tool_errors`, `agents_in_order` and
  `tools_in_order`.
  - `agents_in_order` lists the agents the delegations must reach in that order, `tools_in_order` the tools whose
    successful calls must come in that order; anything may come in between.
  - `response_contains` is for facts the answer must report (a job id, a path, which link is broken), not for
    wording; a list item is a set of alternatives; case, typographic hyphens, spaces and quotes are ignored. A run
    that ends with an answer must not end with an empty one (the `answered` check).
  - `fixture_patch` sets dotted paths in this run's copy of the starting data (`sut/fixtures/base.json`) before the
    run; the approver's answer lives there, so `fixture_patch: {approvals.decision: refuse}` makes the approver
    refuse. `fault_profile` names one of the three profiles in [CONTENTOPS.md](CONTENTOPS.md).
  - `pytest` checks, on Gemma's recorded answers, that the whole catalog passes on the baseline apart from Gemma's
    known mistakes, so record the new case's answers (§8).
- **Workflow**: a test that runs a multi-agent workflow end to end names it (`workflow: W2`); the id must be in
  `catalog/workflows.yaml`, which lists each workflow's chain of specialists, so add the entry there first. The
  coverage report counts the workflow as covered once a test names it and a recorded run delegates to exactly its
  agents, in order.
- **Settings**: a case runs with the defaults of `sut/config/runtime.yaml` unless it sets its own by dotted key,
  `config: {publishing.allow_scheduling: false}`. A value other than the default is a coverage component of its own
  (`config:publishing.allow_scheduling=false`), and the report lists the on/off settings no case runs at their
  other value. `traceeval run --set key=value` overrides both.
- **Feature**: a capability users see goes into `catalog/features.yaml` with the tools that carry it out and the
  other components it is made of (`skill:`, `agent:`, `config:`, `code:<file>` or `code:<file>::<function>`). A
  test covers it by calling one of its tools, a change affects it by touching a tool or a part, and `pytest` checks
  that every part exists in the app.
- **Tool errors**: a tool error the test intends (a refusal, a missing page, an injected outage) must be listed,
  for example `tool_errors: {unpublish_page: approval_required}`. Any other error fails the test as
  `tool_error:<tool>` unless a later call of the same tool succeeded; a crash in tool or service code (any
  exception other than a `ToolError`) fails it as `crash:<tool>`. Both are classified `TOOL_ERROR`.
  `tool_errors: "*"` allows any error, and a scenario added by a spec in `specs/` ([SDD_GUIDE.md](SDD_GUIDE.md))
  that writes its own `expect` gets it by default.
- **Change**: add a `Mutation(...)` to the table in `mutation/catalog.py`, with `replace`, `delete_line`,
  `delete_block` or `append` edits. Anchors are literal text, so reformatting `sut/` breaks them and the operators
  raise. A regression must be revealed by at least one test, a benign change by none.
- **Strategy**: in `selection/strategies.py`, subclass `Strategy` (`selection/base.py`), decorate the class with
  `@register` and implement `order(ctx)`, a prioritized list (tests left out are not selected); adaptive strategies
  implement `run(ctx, oracle)`. Use only `ctx.change`, `ctx.catalog`, the baseline facts in `ctx.history` and the
  other changes' outcomes (`ctx.train_variants`). Add the name to `CORE` to include it in the default comparison.
- **Model backends, recorded answers, the judge**: [EXPERIMENT.md](EXPERIMENT.md) §3 and §5.

## 8. Gotchas

- A run the environment broke is `INFRA_INVALID` ([EXPERIMENT.md](EXPERIMENT.md) §1): `traceeval check` retries
  such a run once and otherwise stops without a verdict.
- A change to anything a prompt is built from (a skill, an agent, a config value, a tool, a case) makes the replay
  miss (`INFRA_INVALID` with `CacheMiss`); record the missing answers again ([EXPERIMENT.md](EXPERIMENT.md) §5).
- `runs/` is git-ignored and large; to keep a run, copy its `results/` into `docs/results/`
  ([EXPERIMENT.md](EXPERIMENT.md) §5).
