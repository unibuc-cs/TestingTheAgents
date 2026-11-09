# TRACE-Eval — Research and implementation plan

**Change-aware, cost-bounded selection, prioritization and stopping of tests and evals for LLM agent systems**

Ciprian Păduraru · University of Bucharest · working document, 6 October 2026, updated 9 November 2026 · status: prototype v0.1 running on real models, results in `docs/results/gemma5/report.md`

---

## TL;DR

- **Problem.** After a change to an agent system, decide which tests and eval items to run, in what order, and
  when to stop, under a token budget and without missing regressions.
- **Method.** Map the diff to components (code lines and functions, skill procedures, agent fields, config keys)
  and match them to tests through the dependencies observed in traces. Rank tests by expected information per
  token in a Bayesian model whose sensitivities are calibrated from history, and stop when the probability of a
  regression is low. The method is `adaptive_bayes`; six baselines run alongside it.
- **Testbed.** A small multi-agent app (`traceeval/sut`) whose agents are played by a real model (Gemma 4 E4B, and
  Qwen3.8-27B as a second model), 177 tests and 43 controlled changes applied as file edits (9 of them benign).
  Full-suite runs with three repetitions give the ground truth, and strategies are compared by offline replay.
- **Results (§5, Gemma on the current app).** Hand-written dependencies catch 61% of the regressions. Trace-based
  selection catches 86% within a budget of 20% of the full-suite tokens, TF-IDF over the diff 92%. The adaptive
  method catches 76% at a 5% budget and 79% at 20% while spending under 3% of the tokens, and 86% of the changes
  that break a safety property. Unlike the other strategies it does not take the tests a model already fails for
  regressions: no false "regression" verdict on any change no test reveals. Its weakness is narrow regressions,
  revealed by one to five tests, where it can stop "clean" too early. A mandatory-coverage rule (§5.3) makes it
  test every mandatory property a change may affect before it calls the change clean, for under one extra test per
  change, and on this app the rule also catches a regression the method alone misses. Change sets hold code only,
  so the results are the same whether or not the code is commented. Qwen's recording of the same app is not a
  clean ground truth: its answers change with how requests are batched (§5.4).
- **Next.** The demo for the AEM team (`docs/AEM_ALIGNMENT.md` §4); make Qwen's answers exactly repeatable (vLLM's batch-invariant mode), so that one run is proof again; then move
  to tau2-bench as the external system under test. Real models only, decoded greedily. Paper: ASE/ISSTA/ICST framing.

---

## 0. What this document is

This plan merges five earlier inputs into one research design and one runnable testbed: the requirements captured from the July 2026 discussion with Georgiana (Adobe, AEM agent platform), the state-of-the-art report with APFD/APFD_c and reliability metrics, the OpenTelemetry-based prioritization sketch, the TRACE-Eval/Pi handoff, and the local Muse Glimmer/vLLM setup notes. Where the inputs disagreed, the decisions below say which way we went and why. The research problem is kept general (any agent platform built from skills, prompts, tools, harness code and configuration); AEM is the motivating instance, not a dependency.

**Decisions taken in this iteration**

| Topic | Decision | Reason |
|---|---|---|
| System under test (SUT) | A purpose-built mini content-operations platform ("ContentOps": pages, assets, publishing, SEO, translation, governance, rollback) is the primary SUT. tau2-bench, with the local vLLM model playing both the agent and the user, is the second SUT (designed, not yet implemented; see `docs/tau2_integration.md`). | The primary SUT gives a multi-agent structure with shared components built in on purpose (the hard case Georgiana described) and full control over mutations. Its agents run on a local model, and recorded answers make reruns free and exact. tau2-bench adds external validity. |
| Agent runtime | Pure Python harness with an OpenAI-compatible LLM backend; Pi is not used in the prototype. | Shortest path. The harness code must itself be mutable and instrumentable (coverage contexts). A Pi adapter remains possible later. |
| Observability | Own trace recorder with an OpenTelemetry-compatible event model (agent/skill/tool/config/llm events) and an OTLP JSON exporter (`tracing/otel.py`), rather than Phoenix/OpenInference as a dependency. | No services in the loop; the export needs no dependency. |
| Oracles | Deterministic (final state, tool trajectories, audit log, response substrings); an LLM judge only for explicitly marked answer-quality properties, executed after deterministic checks pass, by Gemma or Qwen against the case's rubric. | Regression tracking must not depend on judge noise (docx report §"LLM-as-a-judge bottleneck"). |
| Ground truth | Mutation analysis: 43 controlled changes, benign ones included, applied as file edits. The selectors see only the diff. | Needed to measure detection rate against a known answer, and to measure wasted budget. |
| Evaluation | Record-then-replay: run the full suite once per variant, evaluate all strategies offline. | Decouples method development (thousands of replays) from execution cost (one recording per variant). |

---

## 1. Problem statement and research questions

A change set Δ (edits to skill files, prompts/agent definitions, harness or tool code, configuration) arrives at an agent platform with a suite T of tests and eval-dataset items, each with a cost c(t) (tokens, time). We must choose a subset S ⊆ T and an order, possibly adaptively, under a budget B, so that regressions introduced by Δ are detected with high probability and at low cost, and so that the procedure stops when more evidence is not worth its price.

We keep the three sub-problems of the requirements document separate throughout: selection (which tests), prioritization (in which order) and budget-aware stopping (when to stop). The research questions are those of the requirements document, each with a metric:

- **RQ1 (selection)** Can we identify the tests relevant to a change? *Metric: selection recall of the revealing tests and cost of the selected subset, declared vs. observed dependencies.*
- **RQ2 (traces)** Do execution traces improve selection beyond static/declared dependency information? *Metric: RQ1 and RQ3 metrics for `declared` vs. `observed*`.*
- **RQ3 (prioritization)** Can we order tests to detect regressions earlier? *Metric: APFD, cost-cognizant APFD_c, cost to first detection.*
- **RQ4 (budget)** Can we reduce time and tokens while retaining acceptable detection and coverage? *Metric: detection rate vs. budget curves, tokens actually spent, waste on benign changes, stopping accuracy.*

**Claimed contribution.** A change-aware, trace-informed, cost-bounded method for selecting agent tests, with a stopping rule based on the posterior probability of a regression, plus a reproducible testbed (SUT + mutation catalogue + metrics) for evaluating such methods. The method, not the testbed, is the contribution (requirements §11); the testbed is what makes the method testable.

---

## 2. Models underlying the method

### 2.1 Change model (what a diff becomes)

The extractor (`traceeval/mutation/changeset.py`) turns a diff into *components* with the same identifiers used for dependencies:

| Component | Example | Granularity notes |
|---|---|---|
| `code:<file>::<function>` + `line:<file>:<n>` | `code:harness/retry.py::with_retry`, `line:harness/retry.py:29` | AST-normalised function comparison (docstrings ignored); changed baseline code lines; an insertion anchors to the code lines around it. |
| `tool:<name>` | `tool:set_page_metadata` | When a changed function is a registered tool adapter. |
| `skill:<name>#procedure` / `#prose` / `#meta` | `skill:link-validation#procedure` | The machine-readable procedure block vs. instruction prose vs. front matter. |
| `agent:<name>.<field>` | `agent:publishing.triggers`, `agent:seo.tools` | Order-sensitive comparison (intent order matters). A tool or skill list that only lost items names them (`removed: tool:check_consent`). |
| `config:<dotted.key>` | `config:runtime.retries` | Effective value changes only. |
| comments and formatting | — | Left out: comments, docstrings, blank lines, YAML comments and the order of config mappings add no component, file or diff line, so no selector or probability depends on them. The selectors read the diff of the code alone. |

### 2.2 Dependency model (declared · observed · required)

- **Declared**: the metadata a test author wrote (`declared:` block in the catalog). It is incomplete on purpose, as in practice: shared skills reached through `include`, harness code and most configuration keys are not declared.
- **Observed**: from baseline traces: agents started, agent-definition fields consulted by the orchestrator, skills loaded (with version/digest), tools called (with status and attempts), configuration keys read, executed code functions and lines (coverage.py dynamic contexts, one context per test and repetition).
- **Required**: properties/risk that must always be evaluated: the mandatory properties of the catalog of properties (the safety ones). The adaptive method tests every mandatory property a change may affect before ending without a regression (step 5, §5.3).

### 2.3 Cost model

c(t) = agent tokens (prompt + completion over all LLM calls in the delegation chain) + judge tokens (only when a judge runs). Latency is recorded alongside. Tokens come from the model server's usage fields, so a case that delegates, retries or reads long skills costs more. A full-suite run of the 136-test app costs about 0.96M tokens under Gemma and 1.07M under Qwen.

### 2.4 Outcome model

A test run is PASS / TOOL_ERROR (a tool crashed, or failed in a way the case does not allow) / AGENT_FAILURE / HARNESS_ERROR (INFRA_INVALID is reserved for environment faults). Only pass/fail enters the ground truth. With K repetitions per variant, the ground truth "t reveals Δ" is a *majority flip*: baseline pass rate ≥ 0.5 and variant pass rate < 0.5. A test that the model fails on the original app (f(t) = 1 − baseline pass rate) cannot reveal anything; f(t) is a direct input to the selectors.

---

## 3. Methods (strategies implemented in `traceeval/selection/`)

| Strategy | Family | Uses | Selects? | Stops? |
|---|---|---|---|---|
| `full` | reference | — | no | no |
| `random` | baseline | seed | no | no |
| `declared` | change-based (classic RTS on metadata) | declared deps, risk | yes | n/a |
| `ir_tfidf` | IR-based TCP (REPiR-style) | diff text vs. test text | no (ranks all) | no |
| `observed` | trace-informed RTS | observed deps incl. executed lines, risk, cost | yes | n/a |
| `observed_diverse` (optional) | observed + "additional" greedy breadth | + behaviour signatures | yes | n/a |
| `cost_aware` | handoff formula Risk × ChangeAffinity × FailureHistory / ExpectedTokens | observed deps, baseline failures, cost | ranks all (affected first) | no |
| `history_ml` (optional) | predictive test selection (Machalica et al.) | logistic model over affinity/cost/risk features trained on other changes (leave-one-change-out) | ranks all | no |
| `adaptive_bayes` | **proposed** | everything above + sequential inference | yes | yes |

The two optional baselines run only with `--strategies all`; the results in §5 compare the other seven. Two
variants of the proposed method differ only in how text is compared (§5.2): `adaptive_bayes_tfidf` and
`adaptive_bayes_notext`; a third, `adaptive_bayes_nomandatory`, leaves out step 5 (§5.3).

### 3.1 The proposed method: adaptive Bayesian selection with budget-aware stopping

*Hypotheses.* Each changed component c is "broken" with prior π_c by kind (code/skill/config/agent ≈ 0.45–0.5, prompt wording/prose ≈ 0.12–0.15). The posterior is kept exactly over all 2^k subsets B (k ≤ 8 components).

*Likelihood.* P(t fails | B) = 1 − (1 − f_t) ∏_{c∈B} (1 − s_tc). The sensitivity s_tc of test t to component c is
s_tc = r_kind(c) · lift_t,kind(c) · freq_t(c) · tilt_t, where

- r_kind is the empirical reveal ratio learned from the other recorded changes: the fraction of statically impacted tests that actually revealed a change of that kind. Kinds separate, for example, "executed the changed line" from "executed only the changed function", and agent fields are calibrated per field. This encodes "coverage does not imply detection" with measured numbers instead of hand-set constants. A ratio learned from few changes is padded toward a default for its kind (m = 2 changes' worth, as below), so that one earlier change cannot make a whole kind look certain.
- lift_t,k = (O_tk + m) / (E_tk + m) is the test's own record on the earlier changes of kind k that impacted it: O_tk is how many of them it revealed, E_tk how many an average impacted test would have revealed (the sum of those changes' reveal rates), and m = 2 pads a short record. A test that ran many changed functions and never caught anything gets a lift below 1; one that caught changes most impacted tests missed gets a lift above 1. Comparing with E rather than counting catches matters: a change that breaks a large part of the suite (link validation turned off everywhere: 40 tests) says little about each test it breaks. Like r_kind, the records are recomputed from the recordings at every run, without the change under evaluation, so they grow as more changes are recorded (`docs/USER_GUIDE.md` §5).
- freq_t(c) is how often t exercised c in its baseline runs. For an agent's tool or skill list that only lost items, it is how often t used one of the removed items: losing `check_consent` can affect only the tests that call it, not every test of the governance agent.
- tilt_t ∈ [0.5, 2.0] combines the lexical relevance of the change text (code only, never comments) to the test's own text (name, request, expectations) with a bonus when the author declared the dependency. It is a proxy for "the test's oracle plausibly observes the changed behaviour". The relevance measure is an option (`text`): word overlap (the default), TF-IDF, or none (§5.2).

*Policy.* The next test is the argmax over t of (expected information gain about B, tilted by risk) / c(t). After a pass, the sensitivities of tests with the same behaviour signature (agents, tools, fault profile, dataset) are discounted (×0.35), because near-duplicate tests are correlated evidence, not independent draws. Each test runs at most once: the models decode greedily, so a rerun gives the same answer.

*Stopping.* The method stops "regression" at the first failure of a test that passed on the original app: the models decode greedily, so that failure shows a changed behaviour, which is what the ground truth calls revealing. It stops "clean" when P(any component broken | evidence) < ε_clean (0.05). Otherwise it runs until the budget is exhausted or no test is informative. Selection, prioritization and stopping all come from the same model; step 5 is a coverage rule on top of it: a run that found no regression then tests every mandatory property the change may affect that is still untested, with the cheapest test that checks it, while the budget allows (§5.3).

### 3.2 Why these baselines

They cover the design space of the literature: classic RTS/TCP on declared coverage (Rothermel), IR-based TCP (Saha 2015), cost-cognizant TCP (Elbaum 2001), predictive test selection (Machalica 2019) and diversity-based ordering (Pan/Briand LTM). CASPER (2026) and Risk-Aware Adaptive Evaluation (2026) are the closest external competitors (`docs/related_work.md`). Reproducing them on the testbed is roadmap item 3(c).

---

## 4. Evaluation environment (the testbed)

### 4.1 System under test — ContentOps

`traceeval/sut` contains eleven agents (orchestrator, authoring, publishing, assets, seo, translation, governance, maintenance, and, modelled on AEM's agents, brand, insights and optimizer), thirteen skills, 32 tools over deterministic services (repository with versions and asset search, workflow with reviews/scheduling, links, governance with consent, approval tokens and human approvals, translation, SEO, brand guidelines, analytics and a site audit), a harness (configuration with instrumented reads, skill loader with a procedure DSL, retry helper with idempotency keys, dispatcher with tool enablement + approval gate + fault injection, runtime loop with delegation, step budgets per agent and per request) and `config/runtime.yaml`. The orchestrator either delegates a request to one specialist or, for a request that needs several, plans the steps (`make_plan`), delegates them one at a time with their own instruction and the ids of earlier steps, and asks a person before publishing, scheduling or taking pages down (`request_approval`); `docs/AEM_ALIGNMENT.md` §3.1-3.3.

The structure is deliberate, so that selection is hard and defence-in-depth questions can be discussed. Some components are shared and have a wide blast radius: `governance-checks` and `link-validation` are included by several skills, `check_permission` is available to eight of the ten specialists and `get_page` to six, and the retry helper wraps every tool call. Others are narrow: the approval gate matters to one test. Some policies are enforced only in skills (publish permission), others also in tools (approval tokens).

A `SKILL.md` has front matter, prose, and a `## Procedure` YAML block that the model reads as numbered steps (included skills written out in place, settings shown with their current values). Mutations of the prose and of the procedure are separate components (`#prose`, `#procedure`).

### 4.2 Eval catalog

103 scenario tests (publishing 23, authoring 14, assets/SEO 18, translation/governance/maintenance/orchestration 21, brand/insights/optimizer 12, and 15 workflow tests: W1 campaign launch across five specialists, W2 site optimization across four, W3 legal takedown, W4 localized price update, W5 rollback of a broken release and W6 privacy request across two or three, each with variants where the plan must stop) and two dataset-style evals (50 routing items, prompt → expected delegation, run in route-only mode; 24 intent items, prompt → expected tool invocation). Each case defines an agent entry point, request, context slots, fixture (+ optional patch), fault profile (`healthy`, `transient_once:<tool>`, `ack_timeout_once:<tool>`, `permanent_down:<tool>`), risk (critical/high/medium/low → severity 4/3/2/1), properties (ids from the catalog of properties, e.g. `task_completion`, `correct_routing`, `workflow_completion`, `safety_*`, `resilience_*`), declared dependencies, expectations (state assertions, required/forbidden tools, attempt counts, audit counts, response substrings, step limits, termination, agent and tool order), for the workflow tests the workflow they run end to end (`traceeval/catalog/workflows.yaml` lists the six with their chains of specialists) and, for two cases, a judge rubric. The catalog of properties (`traceeval/catalog/properties.yaml`) gives each property a category, the ways it is checked, a mandatory flag (the safety properties are release blockers) and a threshold; a model can draft it from the requirements (`docs/AEM_ALIGNMENT.md` §3.4). Coverage over the requirements' dimensions, declared and observed, is reported for the suite (what no test covers) and for each change (§4.4, §5.3; §3.5 there).

### 4.3 Controlled changes (43)

| Category | Count | Examples |
|---|---|---|
| code (tool adapters, services, harness) | 10 | argument-mapping bug in `set_page_metadata`; retry drops idempotency keys; approval gate bypass; external links treated as reachable; shared `get_page` reports the wrong review flag; edits keep approvals; the insights ranking sorted the wrong way; page search and the brand check case-sensitive; the site audit ignores alt text |
| runtime | 3 | termination six steps early; the delegated answer cut to 40 characters; a delegation drops the ids of earlier steps |
| skill | 11 | publishing skill drops link validation / permission check; authoring drops metadata; translation hard-codes en-US; rollback drops its permission check (the service still refuses); rollback restores the latest version; shared link-validation tolerates broken assets; governance drops the consent check; SEO drops the title-length guard; the routing skill no longer asks for approval; the routing skill drops the brand gate |
| prompt / agent definition | 2 | SEO loses a tool; governance loses `check_consent` |
| configuration | 7 | validate_links disabled; review not required; step budget 5; retries 0; title limit 20; default agent changed; no approval needed to take a page down |
| combined | 1 | keyword-count rule in code + very low limit in config (each alone harmless) |
| benign | 9 | prose reflow; comment/docstring edit (AST-equivalent); local-variable renames; config comments/ordering; new unused tool; orchestrator prompt wording; translation intents re-ordered; brand skill prose reworded; routing guidance reordered |

The set is written for real models: a change has to touch an input a model acts on (keyword weights, trigger
lists and the order of an agent's intents are not), and a removed step has to go from the procedure and from the
prose, or the model does the step anyway. Candidates that told nothing about selection were left out: exact twins
of other changes, crashes that only exercised the crash classification, and a change that broke most of the
suite. Ten changes aimed at the multi-agent workflows (the orchestrator's approval and brand rules, the hand-off
of ids between steps, the services behind the AEM-style agents, two benign ones) joined on 9 November 2026.
`docs/USER_GUIDE.md` §6 explains each of the 43 and why it is in the set.

The report checks a sanity property of the testbed: every regression-inducing change is revealed by ≥ 1 test, and no benign change is revealed by any test. Under Gemma five regressions and under Qwen two are revealed by no test, for reasons that belong to the model (§5.1).

### 4.4 Protocol and metrics

1. `baseline`: full suite × K with coverage contexts, giving observed dependencies, cost and pass rates.
2. `mutants`: for each change, copy the SUT, apply the edit, extract the change set and run the full suite × K, giving the fault matrix.
3. `evaluate`: for every (change, strategy, budget ∈ {2,5,10,20,30,50,100}% of full-suite tokens, seed), the strategy selects from the baseline facts and the change set only. Each execution is answered from the recorded runs of that variant (a random repetition supplies the outcome and cost). Adaptive strategies interact sequentially.
4. Metrics: change coverage without the ground truth (the share of the changed components the executed tests exercised, the share of the properties the change may affect that they checked, whether every affected mandatory property got a test, the share of the affected workflows they ran; `experiment/coverage.py`), property coverage (of the properties a change breaks, those its selected tests exercise), detection (≥ 1 revealing test executed and failed), recall of revealing tests, tokens actually spent, cost to first detection, false alarms, safety recall, stop reason and stop correctness; APFD and APFD_c of the complete prioritized order; selection recall and selected-subset cost.

---

## 5. Results

### 5.1 Gemma on the current app (`runs/gemma5`: 176 tests × 3 reps baseline, 43 changes × 3 reps, with the model judge, 5 replay seeds)

The agents are played by Gemma 4 E4B, served with vLLM on a GPU server (`docs/EXPERIMENT.md`); Qwen3.8-27B's
recording of the same app is in §5.4. The ground truth belongs to the model:

- **Original app:** 170 of 176 tests pass. The six failures are model mistakes that clearer wording did not fix
  (`docs/EXPERIMENT.md` §6): Gemma schedules a page without an approved review (PUB-10, and in the campaign launch
  WF1-01), requests a review nobody asked for (AUT-04), applies an over-long SEO title (SEO-02), goes on to
  publishing after a failed link check (WF5-02) and stops a whole plan after a refused export that the other steps
  do not depend on (WF6-02). Its three runs of each test always agreed.
- **Regressions:** 29 of the 34 are revealed. Gemma does not act on guards it has to work out for itself (a review
  flag, a length), and stops at a broken asset reference even when the skill says it does not block, so it behaves
  the same, wrongly, with or without the five changes to those guards.
- **Benign changes:** none of the nine fails a test. Across all 43 changes, the three runs disagreed on only five
  (change, test) pairs; the majority vote absorbs them.

Detection of the 29 regressions Gemma reveals, by nominal budget, and tokens actually spent:

| strategy | 5% | 10% | 20% | 50% | 100% | spent @20% | spent @100% | spent on benign @100% |
|---|---|---|---|---|---|---|---|---|
| full (catalog order) | 0.14 | 0.21 | 0.34 | 0.90 | 0.99 | 0.20 | 0.98 | 1.00 |
| random | 0.21 | 0.33 | 0.52 | 0.84 | 0.99 | 0.20 | 0.98 | 1.00 |
| declared | 0.55 | 0.55 | 0.61 | 0.61 | 0.61 | 0.07 | 0.10 | 0.13 |
| ir_tfidf | 0.70 | 0.71 | 0.92 | 0.99 | 0.99 | 0.20 | 0.98 | 0.99 |
| observed | 0.62 | 0.69 | 0.86 | 0.86 | 0.99 | 0.15 | 0.49 | 0.32 |
| cost_aware | 0.59 | 0.62 | 0.83 | 0.86 | 0.99 | 0.20 | 0.98 | 0.99 |
| adaptive_bayes | 0.76 | 0.79 | 0.79 | 0.83 | 0.83 | 0.03 | 0.03 | 0.20 |

APFD_c of the full prioritized order: random 0.53, full 0.57, declared 0.76 (selection recall 0.53), ir_tfidf 0.77,
cost_aware 0.78, observed 0.79 (selection recall 1.00 at half the suite's cost), adaptive 0.81. Cost to first
detection: adaptive 0.017, declared 0.025, ir_tfidf 0.04, observed 0.05, cost_aware 0.06, random 0.14, full 0.19 of
the full suite. Time spent follows tokens closely (the report's section 2).

**Reading.**
- *RQ1/RQ2.* Declared metadata caps detection at 61%, because shared skills reached through `include`, harness code
  and most configuration keys are not declared. Observed dependencies recover full selection recall and reach 86%
  within a 20% budget. The main argument for trace-informed selection holds.
- *RQ3.* Informed strategies raise APFD_c from 0.53 (random) to 0.76–0.81; the adaptive method's order is the best,
  and it finds the first regression soonest.
- *RQ4.* The adaptive method is the only one that returns budget: 76% of the regressions at a 5% budget and 79% at
  20%, for under 3% of the tokens. Its ceiling is 83%: on narrow regressions, revealed by one to five tests, it can
  stop "clean" before reaching them (145 of 1,015 replays of regressions). The changes it misses at a 20% budget are
  the delegation that drops the ids of earlier steps, the agent loop that stops six steps early, retries without
  idempotency keys, the routing skill without its brand gate, the authoring skill without its metadata step, and the
  combined change, which runs out of budget.
- *Critical regressions.* Of the 21 changes that break a safety property, the adaptive method catches 86% from a 10%
  budget on, `observed` 81% and TF-IDF 98% at 20% (spending the whole 20%).
- *Red tests on the original app.* Gemma's six failing tests fail on every changed copy too, so a strategy that runs
  one sees a failure the change did not cause. On the 14 changes no test reveals, `full` sees such a failure in 71%
  of replays, `ir_tfidf` in 70% and `cost_aware` in 91%. The adaptive method discounts a test by its failures on the
  original app and gives no "regression" verdict on any of them (0 of 490 replays).
- *IR.* TF-IDF over the diff is the strongest selector at 20% (92%) but spends the whole budget; at 5% the adaptive
  method leads (76% against 70%).

### 5.2 Text in the method: an option (roadmap 3(b))

The method's text signal (the tilt in §3.1) can be word overlap (the default), the TF-IDF similarity of the
`ir_tfidf` strategy (`adaptive_bayes_tfidf`), or nothing (`adaptive_bayes_notext`, an ablation). Detected and spent
on the Gemma recording of §5.1 (5 seeds):

| budget | overlap (default) | TF-IDF | no text | `ir_tfidf` alone |
|---|---|---|---|---|
| 5% | 0.76 (2.1%) | 0.79 (2.0%) | 0.62 (2.4%) | 0.70 (5%) |
| 20% | 0.79 (2.9%) | 0.83 (2.4%) | 0.69 (3.5%) | 0.92 (20%) |
| 50% | 0.83 (2.9%) | 0.83 (2.4%) | 0.69 (4.5%) | 0.99 (50%) |

The TF-IDF variant also stops correctly most often (0.88 at 20%, against 0.86 for the default and 0.79 without
text), and no variant gives a "regression" verdict on a change no test reveals.

**Reading.** TF-IDF brings forward the one test that reveals a narrow change, and helps by up to four points for
less spending. Without any text the method loses ten points, so text matters, but coverage and history carry most
of the result. The testbed is textual: tests, skills and config keys share vocabulary, which favours any text
measure (a threat noted in §8). The default stays word overlap until a repeatable second model's recording shows
whether the gain holds there too (§5.4); whether TF-IDF helps as much where tests and changes are worded differently is a
question for tau2-bench.

### 5.3 Coverage, and mandatory properties in the method

Coverage is a metric the AEM team asked for (`docs/AEM_ALIGNMENT.md` §3.5); the report's section 6 gives it for the
suite and for each change. On the current app every agent, skill, setting, property and workflow has a test; one
tool, `get_asset`, has none. The declared metadata misses one skill and four settings that the traces show in use.

Change coverage needs no ground truth. Observed, cost-aware and TF-IDF selection and the adaptive method all
exercise 97% of the changed components at a 20% budget (one change touches code no test runs). The adaptive method
checks about half of the properties a change may affect (0.50, against 0.83 for `observed`), because it stops at
the first real failure or as soon as it is confident. That is the point of stopping, but it would also let the
method call a change clean with a mandatory property untested.

Step 5 of the method (on by default; `adaptive_bayes_nomandatory` is the ablation) closes that hole. A run that
found no regression does not end before every mandatory property the change may affect has a test, the cheapest
that checks it and passes on the original app, while the budget allows. At a 20% budget:

| recording | runs without a regression that tested every affected mandatory property, without / with the rule | extra tests per change | detection without / with the rule |
|---|---|---|---|
| gemma5 | 0.33 / 0.90 | 0.8 | 0.76 / 0.79 |

On this app the rule is also a detector: it catches `skill_publish_drop_link_validation`, which the method alone
calls clean. Before ending, the method must test the mandatory "no broken publish" property, and that test fails.
The rule never caused a false verdict. Below a 10% budget it often cannot afford the extra test.

### 5.4 Qwen on the current app: a finding, not a ground truth

Qwen3.8-27B (`runs/qwen5`, the same protocol on fmi0's GPU1 and two SLURM GPUs) passes 171 of the 176 tests on
the original app. It gets five of Gemma's six mistakes right and makes its own; in particular it re-plans after
a failed step (it repairs the page that failed the brand check, or has the broken link fixed, and goes on), as
Adobe's Agent Orchestrator does, where the routing skill says stop (`docs/EXPERIMENT.md` §6). Its recording is not
a clean ground truth, though: every regression is revealed, but so is every benign change, by two to five tests,
including the no-op change whose change set is empty. Six tests (the two Qwen judges itself, the 60-character
boundary and three long workflows) answer differently when run 64 at a time over three servers, as the changed
copies are, than one at a time, as the baseline is, and Qwen's three runs disagreed on 260 (change, test) pairs
against Gemma's five. The strategies' numbers on it are therefore not results. Its report is kept in
`docs/results/qwen5/` as a record of the effect; the remedy is exactly repeatable decoding (vLLM's batch-invariant
mode) for the next recording. The lesson for a pipeline: measure the suite's own flakiness under the serving setup
the selection will run on (the no-op change does exactly that) before trusting a ground truth or a stopping rule.

---

## 6. Models, the prototype, and a second system under test

- **ContentOps on real models** (done, `docs/EXPERIMENT.md`): Gemma 4 E4B (`--backend vllm`, or `hf` on a local
  GPU) and Qwen3.8-27B (`--backend llm`, or any other OpenAI-compatible endpoint) run on the GPU server: two GPUs
  directly, plus two through SLURM on the same machine (`TRACEEVAL_SITE=hpc`), and one run can spread its requests
  over several servers. A 43-variant × 3-rep recording of the 176 tests is about 23k runs (timings in
  `docs/EXPERIMENT.md` §7). Every answer can be recorded (`traceeval/llm/cache.py`), so a rerun costs nothing and
  the test suite replays Gemma's answers without a GPU. A run with an OpenAI model, through the `llm` backend,
  waits for API tokens.
- **The prototype** (`traceeval check`, `docs/EXPERIMENT.md` §5): the adaptive method on one change, live.
  Each test it picks runs on the changed app with the real model, and the outcome decides what runs next;
  it stops with a verdict and its probability that the change broke something. A recording made with the
  same model supplies the baseline traces, the costs and the other changes to calibrate from.
- **tau2-bench** (`docs/tau2_integration.md`): airline domain first (50 tasks, DB + communicate reward, no model judge), the agent and the user played by the local model, policy and tool-code mutations; the replay evaluator and the strategies run unchanged on the parsed history.

---

## 7. Roadmap

| Phase | Deliverable | Status |
|---|---|---|
| 1. Testbed | SUT, catalog, tracing, mutations, change sets, record/replay, metrics, report, CLI, tests | done (v0.1) |
| 2. Methods | baselines + cost-aware + predictive + adaptive Bayesian selector with stopping | done (v0.1), with the mandatory-coverage rule (§5.3); tune ε, priors, discount |
| 3. Method improvements | (a) test-level learned sensitivities (per test × component-kind reveal history) instead of kind-level; (b) IR relevance inside the Bayesian likelihood; (c) CASPER-style slices and the Risk-Aware Adaptive Evaluation bandit as reproduced baselines | (a) done; (b) done as an option (§5.2); (c) open |
| 4. Real LLM | ContentOps on real models (local vLLM): all variants × 3 reps under two models | done: Gemma on the current app (`runs/gemma5`); Qwen's recording of it (`runs/qwen5`) is spoiled by batching nondeterminism and is to be redone with repeatable decoding (§5.4) |
| 5. External SUT | tau2-bench airline adapter; 12 mutations (6 policy, 4 tool-code, 2 benign); same evaluation | after the AEM steps and repeatable decoding |
| 6. Scale/robustness | more mutations (mutation operators generated systematically: step deletion/swap/condition negation in procedures, argument swaps in adapters, config boundary values), equivalent-mutant analysis, sensitivity to K and to budget definitions (time vs. tokens), ablations of each model ingredient | with the paper |
| 7. Paper | see §8 | drafting can start from this document and the report |

A model's own mistakes and blind spots shape the ground truth: which changes a test reveals depends on the model (`docs/EXPERIMENT.md` §6 and §7). Two parts of the method come from that. Each test's own record (§3.1) exists because kind-level sensitivities let the method spend on cheap tests that merely call a changed function; stopping at the first failure of a test that passed on the original app exists because a failure the model also produces on the original app says nothing about the change.

The AEM team's wish list (`docs/AEM_ALIGNMENT.md`) is being implemented step by step; its §4 is the dated plan for the demo of 12 November 2026. Done: the catalog of properties, drafted by a model from the requirements; coverage reports with the mandatory-coverage rule (§5.3); the orchestrator's planning mode (plans, hand-offs with ids, human approvals), three agents modelled on AEM's (brand, insights, optimizer) and asset search, six multi-agent workflows (campaign launch across five specialists, site optimization across four, legal takedown, localized price update, rollback of a broken release, privacy request), and trace assertions on agent and tool order. Next, in order: the remaining workflows with controlled changes aimed at them, both ground truths recorded on the current app; then exactly repeatable decoding for Qwen (vLLM's batch-invariant mode), so that a one-off difference cannot pass for a regression; a run with an OpenAI model once API tokens are available; tau2-bench.

---

## 8. Paper plan

**Working title.** TRACE-Eval: change-aware, cost-bounded regression test selection for LLM agent systems.

**Abstract (draft).** Agent platforms ship dozens of agents assembled from skills, prompts, tools, harness code and configuration, and verify them with tests and statistical evals whose cost is dominated by tokens. After a change, teams either re-run everything or guess. We formulate selection, prioritization and budget-aware stopping of agent tests as one problem and propose a method that (i) extracts a change set from the diff at the granularity of code lines, skill procedures, agent-definition fields and configuration keys, (ii) maps it to tests through dependencies *observed* in execution traces rather than declared metadata, (iii) ranks tests by expected information per token in a Bayesian model whose sensitivities are calibrated from history, and (iv) stops when the posterior probability of a regression is low. We evaluate on a testbed with a working multi-agent application, including multi-agent workflows, whose agents are played by open models (a small one, and a mid-size one as a second), 177 tests and eval items, and 43 controlled changes with a mutation-based ground truth derived per model. Declared dependencies miss 39% of the regressions; trace-informed selection finds 86% of them within 20% of the full-suite tokens. The adaptive method detects 79% for 3% of the tokens, returns most of the budget on benign changes, and, unlike the other strategies, does not mistake the tests the model already fails for regressions.

**Outline.** 1 Introduction (motivation from AEM-scale platforms; nightly batch + PR use; three sub-problems) · 2 Background and related work (RTS/TCP; efficient LLM evaluation; agent benchmarks; fault injection; CASPER as closest work) · 3 Problem formulation and models (§1–2) · 4 Method (§3.1) · 5 Testbed (§4) · 6 Evaluation (RQ1–RQ4 + ablations + LLM/tau2 external validity) · 7 Threats to validity (synthetic mutants vs. real regressions; two models, greedy decoding, and a ground truth that depends on the model; single primary domain; calibration leakage controlled by leave-one-change-out; textual testbed favouring IR) · 8 Conclusion.

**Venues.** ASE / ISSTA / ICST (SE framing: RTS/TCP for LLM-based systems, mutation-based ground truth, APFD_c). Alternative: NeurIPS D&B / EMNLP with the testbed as the headline ("a benchmark for regression test selection in agent systems").

---

## 9. Questions still to settle with Georgiana

Partly answered by the follow-up questions with the AEM team (`docs/AEM_ALIGNMENT.md` §1): nightly and
model-update runs, prompt → answer and prompt → tool-call datasets, thresholds and mandatory properties wanted,
budgets with early stopping.

1. Change identification: is the diff available per PR/nightly batch, and does the platform keep skill/prompt/config under version control together with harness code? (The change-set extractor assumes files in one tree.)
2. Dependency registry: is there a mapping agent → skills/tools/config, and are traces (tool calls, skills loaded, config reads) retained for the nightly runs? (Observed dependencies need ≥ 1 baseline run per test with tracing.)
3. Eval datasets: can items be run individually and attributed costs? (Our dataset items are selectable units; the routing dataset is run in route-only mode.)
4. Oracles: which properties are deterministic vs. judged; which are release blockers (safety set)?
5. Budgets: tokens, time or both; per PR vs. nightly; is a partial run with an explicit "clean with probability p" statement acceptable to the team (this is what the stopping rule outputs)?

---

*Repository: `trace-eval/` (README for commands). Inputs synthesized: Agent_Test_Prioritization_Requirements.md; Agent Test Prioritization Prototype.docx; agent_test_prioritization_summary.md; TRACE-Eval_Pi_Harness_Handoff.md; muse-glimmer-local-setup-and-agent-workflows.md.*
