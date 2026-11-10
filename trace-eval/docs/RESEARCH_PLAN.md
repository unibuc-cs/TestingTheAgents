# TRACE-Eval: research and implementation plan

**Change-aware, cost-bounded selection, prioritization and stopping of tests and evals for LLM agent systems**

Ciprian Păduraru · University of Bucharest · working document, 9 November 2026 · status: prototype v0.1 running on
real models, results in `docs/results/gemma5/report.md`

---

## TL;DR

- **Problem.** After a change to an agent system, decide which tests and eval items to run, in what order, and
  when to stop, under a token budget and without missing regressions.
- **Method.** Map the diff to components (code lines and functions, skill procedures, agent fields, config keys)
  and match them to tests through the dependencies observed in traces. Rank tests by expected information per
  token in a Bayesian model whose sensitivities are calibrated from history, and stop when the probability of a
  regression is low. The method is `adaptive_bayes`; six baselines run alongside it.
- **Testbed.** A small multi-agent app (`traceeval/sut`) whose agents are played by a real model (Gemma 4 E4B, and
  Qwen3.8-27B as a second model), 180 tests (the recordings hold 176; four came later) and 43 controlled changes
  applied as file edits (9 of them benign). Full-suite runs with three repetitions give the ground truth, and
  strategies are compared by offline replay.
- **Results (§5, Gemma).** Hand-written dependencies catch 61% of the regressions. Trace-based selection catches
  86% within a budget of 20% of the full-suite tokens, and TF-IDF over the diff 92%. The adaptive method catches
  76% at a 5% budget and 79% at 20% while spending under 3% of the tokens, and 86% of the changes that break a
  safety property. Unlike the other strategies, it does not mistake the tests a model already fails for
  regressions, and it gives no false "regression" verdict on any change that no test reveals. Its weakness is
  narrow regressions, revealed by one to five tests, where it can stop with a "clean" verdict too early. A
  mandatory-coverage rule (§5.3) makes it test every mandatory property a change may affect before it calls the
  change clean, for under one extra test per change; on this app the rule also catches a regression the method
  alone misses. Change sets hold code only, so the results are the same whether or not the code is commented.
  Qwen's recording of the same app is not a clean ground truth, because some of its answers vary from run to run
  (§5.4).
- **Next.** The demo for the AEM team (`docs/AEM_ALIGNMENT.md` §4), then tau2-bench as the external system under
  test. Real models only, used as they are served and decoded greedily. The paper is framed for ASE, ISSTA or
  ICST.

---

## 0. What this document is

This plan merges five inputs into one research design and one runnable testbed: the requirements captured from
the July 2026 discussion with Georgiana (Adobe, AEM agent platform), the state-of-the-art report with APFD/APFD_c
and reliability metrics, the OpenTelemetry-based prioritization sketch, the TRACE-Eval/Pi handoff, and the local
Muse Glimmer/vLLM setup notes. Where the inputs disagreed, the decisions below say which way we went and why. The
research problem is kept general: any agent platform built from skills, prompts, tools, harness code and
configuration. AEM is the motivating instance, and the method does not depend on it.

**Design decisions**

| Topic | Decision | Reason |
|---|---|---|
| System under test (SUT) | A purpose-built mini content-operations platform ("ContentOps": pages, assets, publishing, SEO, translation, governance, rollback) is the primary SUT. tau2-bench, with the local vLLM model playing both the agent and the user, is the second SUT (designed, not yet implemented; see §6). | The primary SUT gives a multi-agent structure with shared components built in on purpose (the hard case Georgiana described) and full control over mutations. Its agents run on a local model, and recorded answers make reruns free and exact. tau2-bench adds external validity. |
| Agent runtime | A pure Python harness with an OpenAI-compatible LLM backend. Pi is not used in the prototype. | It is the shortest path, and the harness code must itself be mutable and instrumentable (coverage contexts). A Pi adapter remains possible later. |
| Observability | Our own trace recorder with an OpenTelemetry-compatible event model (agent, skill, tool, config and llm events) and an OTLP JSON exporter (`tracing/otel.py`), rather than Phoenix/OpenInference as a dependency. | No services in the loop, and the export needs no dependency. |
| Oracles | Deterministic checks (final state, tool trajectories, audit log, response substrings). An LLM judge (Gemma or Qwen, against the case's rubric) runs only for explicitly marked answer-quality properties, and only after the deterministic checks pass. | Regression tracking must not depend on judge noise (see "LLM-as-a-judge bottleneck" in the prototype report). |
| Ground truth | Mutation analysis: 43 controlled changes, benign ones included, applied as file edits. The selectors see only the diff. | Needed to measure the detection rate against a known answer, and to measure wasted budget. |
| Evaluation | Record, then replay: run the full suite once per variant, and evaluate all strategies offline. | Decouples method development (thousands of replays) from execution cost (one recording per variant). |

---

## 1. Problem statement and research questions

A change set Δ (edits to skill files, prompts or agent definitions, harness or tool code, configuration) arrives
at an agent platform with a suite T of tests and eval-dataset items, each with a cost c(t) in tokens and time. We
must choose a subset S ⊆ T and an order, possibly adaptively, under a budget B, so that the regressions Δ
introduces are detected with high probability and at low cost. The procedure should stop when more evidence is
not worth its price.

We keep the three sub-problems of the requirements document separate throughout: selection (which tests),
prioritization (in which order) and budget-aware stopping (when to stop). The research questions are those of the
requirements document, each with a metric:

- **RQ1 (selection)** Can we identify the tests relevant to a change? *Metric: selection recall of the revealing
  tests and cost of the selected subset, declared vs. observed dependencies.*
- **RQ2 (traces)** Do execution traces improve selection beyond static/declared dependency information? *Metric:
  RQ1 and RQ3 metrics for `declared` vs. `observed*`.*
- **RQ3 (prioritization)** Can we order tests to detect regressions earlier? *Metric: APFD, cost-cognizant
  APFD_c, cost to first detection.*
- **RQ4 (budget)** Can we reduce time and tokens while retaining acceptable detection and coverage? *Metric:
  detection rate vs. budget curves, tokens actually spent, waste on benign changes, stopping accuracy.*

**Claimed contribution.** A change-aware, trace-informed, cost-bounded method for selecting agent tests, with a
stopping rule based on the posterior probability of a regression, and a reproducible testbed (SUT, mutation
catalogue, metrics) for evaluating such methods. The contribution is the method (requirements §11); the testbed
is what makes it testable.

---

## 2. Models underlying the method

### 2.1 Change model (what a diff becomes)

The extractor (`traceeval/mutation/changeset.py`) turns a diff into *components* with the same identifiers used
for dependencies:

| Component | Example | Granularity notes |
|---|---|---|
| `code:<file>::<function>` + `line:<file>:<n>` | `code:harness/retry.py::with_retry`, `line:harness/retry.py:29` | AST-normalised function comparison (docstrings ignored); changed baseline code lines; an insertion anchors to the code lines around it. |
| `tool:<name>` | `tool:set_page_metadata` | When a changed function is a registered tool adapter. |
| `skill:<name>#procedure` / `#prose` / `#meta` | `skill:link-validation#procedure` | The machine-readable procedure block, the instruction prose, and the front matter. |
| `agent:<name>.<field>` | `agent:publishing.triggers`, `agent:seo.tools` | Order-sensitive comparison (intent order matters). A tool or skill list that only lost items names them (`removed: tool:check_consent`). |
| `config:<dotted.key>` | `config:runtime.retries` | Changes of the effective value only. |
| comments and formatting | — | Left out. Comments, docstrings, blank lines, YAML comments and the order of config mappings add no component, file or diff line, so no selector or probability depends on them. |

### 2.2 Dependency model (declared · observed · required)

- **Declared** dependencies are the metadata a test author wrote (the `declared:` block in the catalog). They are
  incomplete on purpose, as in practice: shared skills reached through `include`, harness code and most
  configuration keys are not declared.
- **Observed** dependencies come from the baseline traces: the agents started, the agent-definition fields the
  orchestrator consulted, the skills loaded (with version and digest), the tools called (with status and
  attempts), the configuration keys read, and the code functions and lines executed (coverage.py dynamic
  contexts, one context per test and repetition).
- **Required** dependencies are the properties and risks that must always be evaluated, which are the mandatory
  properties of the catalog of properties (the safety ones). The adaptive method tests every mandatory property a
  change may affect before it ends without a regression (step 5, §5.3).

### 2.3 Cost model

c(t) = agent tokens (prompt + completion over all LLM calls in the delegation chain) + judge tokens (only when a
judge runs). Latency is recorded alongside. Tokens come from the model server's usage fields, so a case that
delegates, retries or reads long skills costs more. A full-suite run of the 176 recorded tests costs about 2.0M
tokens under Gemma and 2.4M under Qwen.

### 2.4 Outcome model

A test run ends in one of five outcomes:

- PASS;
- TOOL_ERROR: a tool crashed, or failed in a way the case does not allow;
- AGENT_FAILURE;
- HARNESS_ERROR: the run itself raised;
- INFRA_INVALID: the environment broke the run, because the model server or the network did not answer, or a
  replay had no recorded answer.

An INFRA_INVALID run is left out, as if it had not been made. Of the other outcomes, only pass or fail enters the
ground truth. With K repetitions per variant, the ground truth "t reveals Δ" is a *majority flip*: the baseline
pass rate is ≥ 0.5 and the variant pass rate is < 0.5. A test that the model fails on the original app
(f(t) = 1 − baseline pass rate) cannot reveal anything, and f(t) is a direct input to the selectors.

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
| `casper_slices` | CASPER (Muse et al. 2026), reproduced | behavioural signals of the baseline traces, slices, the outcomes of two representatives per slice on the changed app | ranks slices (runs all) | no |
| `risk_aware_ts` | Risk-Aware Adaptive Evaluation (Maji & Chowdhury 2026), reproduced | a test's definition and the shape of its baseline runs as context, its risk as impact, the outcomes so far (Thompson sampling) | no (ranks all) | no |
| `adaptive_bayes` | **proposed** | everything above + sequential inference | yes | yes |

The two optional baselines run only with `--strategies all`; the results in §5 compare the other nine. Two
variants of the proposed method differ from it only in how text is compared (§5.2): `adaptive_bayes_tfidf` and
`adaptive_bayes_notext`. A third, `adaptive_bayes_nomandatory`, leaves out step 5 (§5.3).

### 3.1 The proposed method: adaptive Bayesian selection with budget-aware stopping

*Hypotheses.* Each changed component c is broken with a prior π_c that depends on its kind: ≈ 0.45–0.5 for code,
skill, config and agent components, ≈ 0.12–0.15 for prompt wording and prose. The posterior is kept exactly over
all 2^k subsets B of the changed components (k ≤ 8 components).

*Likelihood.* P(t fails | B) = 1 − (1 − f_t) ∏_{c∈B} (1 − s_tc). The sensitivity s_tc of test t to component c is
s_tc = r_kind(c) · lift_t,kind(c) · freq_t(c) · tilt_t, where

- r_kind is the empirical reveal ratio learned from the other recorded changes: the fraction of statically
  impacted tests that actually revealed a change of that kind. Kinds separate, for example, tests that executed
  the changed line from tests that executed only the changed function, and agent fields are calibrated per field.
  The ratio encodes the fact that coverage does not imply detection, with measured numbers instead of hand-set
  constants. A ratio learned from few changes is padded toward a default for its kind (m = 2 changes' worth, as
  below), so that one earlier change cannot make a whole kind look certain.
- lift_t,k = (O_tk + m) / (E_tk + m) is the test's own record on the earlier changes of kind k that impacted it.
  O_tk is how many of them it revealed, E_tk how many an average impacted test would have revealed (the sum of
  those changes' reveal rates), and m = 2 pads a short record. A test that ran many changed functions and never
  caught anything gets a lift below 1; one that caught changes most impacted tests missed gets a lift above 1.
  Comparing with E, instead of counting catches, matters because a change that breaks a large part of the suite
  (link validation turned off everywhere: 48 tests) says little about each test it breaks. Like r_kind, the
  records are recomputed from the recordings at every run, without the change under evaluation, so they grow as
  more changes are recorded (`docs/USER_GUIDE.md` §5).
- freq_t(c) is how often t exercised c in its baseline runs. For an agent's tool or skill list that only lost
  items, it is how often t used one of the removed items: losing `check_consent` can affect only the tests that
  call it, and not every test of the governance agent.
- tilt_t ∈ [0.5, 2.0] combines the lexical relevance of the change text (code only, never comments) to the test's
  own text (name, request, expectations) with a bonus when the author declared the dependency. It is a proxy for
  whether the test's oracle plausibly observes the changed behaviour. The relevance measure is an option
  (`text`): word overlap (the default), TF-IDF, or none (§5.2).

*Policy.* The next test is the argmax over t of (expected information gain about B, tilted by risk) / c(t). After a
pass, the sensitivities of tests with the same behaviour signature (agents, tools, fault profile, dataset) are
discounted (×0.35), because near-duplicate tests give correlated evidence rather than independent draws. Each test
runs at most once: the models decode greedily, so a rerun almost always gives the same answer (§5.4 measures where
it does not).

*Stopping.* The method stops with the verdict "regression" at the first failure of a test that passed on the
original app. The models decode greedily, so that failure shows a changed behaviour, which is what the ground
truth calls revealing. It stops with the verdict "clean" when P(any component broken | evidence) < ε_clean (0.05).
Otherwise it runs until the budget is exhausted or no test is informative. Selection, prioritization and stopping
all come from the same model.

*Mandatory coverage (step 5).* A coverage rule sits on top of the model. A run that found no regression then
tests every mandatory property the change may affect that is still untested, with the cheapest test that checks
it, while the budget allows (§5.3).

### 3.2 Why these baselines

They cover the design space of the literature: classic RTS/TCP on declared coverage (Rothermel), IR-based TCP
(Saha 2015), cost-cognizant TCP (Elbaum 2001), predictive test selection (Machalica 2019) and diversity-based
ordering (Pan/Briand LTM). CASPER (2026) and Risk-Aware Adaptive Evaluation (2026) are the closest external
competitors (`docs/related_work.md`), and both are reproduced on the testbed (`selection/reproduced.py`,
roadmap item 3(c)).

Neither looks at the diff. CASPER cuts the suite into slices of tests that behave alike on the original app
(k-means on ten behavioural signals of the baseline traces, with the baseline outcome as a heavier column), runs
two representatives of every slice on the changed app, and ranks the slices by the shift in their failure rate; it
has no stopping rule. Risk-Aware Adaptive Evaluation is a contextual Thompson-sampling bandit: a logistic
regression on the outcomes so far gives every test a failure probability, a Beta posterior per test mixes it with
the test's own outcome, and the test whose draw times its risk is highest runs next. It rewards any failure, so a
test the model already fails counts as a find. The module's docstrings say where the testbed forced an adaptation:
the replay oracle returns an outcome and a cost, not a trace, so CASPER's slices are scored by their failure rate
rather than by a model of the signals; the budget is in tokens; and each test runs once, because the models decode
greedily.

---

## 4. Evaluation environment (the testbed)

### 4.1 System under test: ContentOps

`traceeval/sut` contains:

- eleven agents: orchestrator, authoring, publishing, assets, seo, translation, governance, maintenance, and the
  brand, insights and optimizer agents, modelled on AEM's;
- thirteen skills;
- 32 tools over deterministic services: a repository with versions and asset search, a workflow service with
  reviews and scheduling, links, governance with consent, approval tokens and human approvals, translation, SEO,
  brand guidelines, analytics and a site audit;
- a harness: configuration with instrumented reads, a skill loader with a procedure DSL, a retry helper with
  idempotency keys, a dispatcher with tool enablement, an approval gate and fault injection, and a runtime loop
  with delegation and step budgets per agent and per request;
- `config/runtime.yaml`.

The orchestrator either delegates a request to one specialist or, for a request that needs several, plans the
steps (`make_plan`). It then delegates them one at a time, each with its own instruction and the ids of earlier
steps, and asks a person before publishing, scheduling or taking pages down (`request_approval`;
`docs/AEM_ALIGNMENT.md` §3.1-3.3).

The structure is deliberate, so that selection is hard and defence-in-depth questions can be discussed. Some
components are shared and have a wide blast radius: `governance-checks` and `link-validation` are included by
several skills, `check_permission` is available to eight of the ten specialists and `get_page` to six, and the
retry helper wraps every tool call. Others are narrow: the approval gate matters to one test. Some policies are
enforced only in skills (publish permission), others also in tools (approval tokens).

A `SKILL.md` has front matter, prose, and a `## Procedure` YAML block that the model reads as numbered steps,
with included skills written out in place and settings shown with their current values. Mutations of the prose
and of the procedure are separate components (`#prose`, `#procedure`).

### 4.2 Eval catalog

The catalog holds 103 scenario tests and two dataset-style evals:

- Scenario tests: publishing 23, authoring 14, assets/SEO 18, translation/governance/maintenance/orchestration 21,
  brand/insights/optimizer 12, and 15 workflow tests. The workflows are W1 campaign launch across five
  specialists, W2 site optimization across four, and W3 legal takedown, W4 localized price update, W5 rollback of
  a broken release and W6 privacy request across two or three. Each has variants where the plan must stop.
- Dataset-style evals: 50 routing items (prompt → expected delegation, run in route-only mode) and 24 intent
  items (prompt → expected tool invocation).

Each case defines:

- an agent entry point, a request, context slots and a fixture (with an optional patch);
- a fault profile: `healthy`, `transient_once:<tool>`, `ack_timeout_once:<tool>` or `permanent_down:<tool>`;
- a risk, critical/high/medium/low, mapped to severity 4/3/2/1;
- properties, ids from the catalog of properties such as `task_completion`, `correct_routing`,
  `workflow_completion`, `safety_*` and `resilience_*`;
- declared dependencies;
- expectations: state assertions, required and forbidden tools, attempt counts, audit counts, response
  substrings, step limits, termination, and agent and tool order;
- for the workflow tests, the workflow they run end to end (`traceeval/catalog/workflows.yaml` lists the six
  with their chains of specialists);
- for two cases, a judge rubric.

The catalog of properties (`traceeval/catalog/properties.yaml`) gives each property a category, the ways it is
checked, a mandatory flag (the safety properties are release blockers) and a threshold. A model can draft it from
the requirements (`docs/AEM_ALIGNMENT.md` §3.4). The report gives coverage over the requirements' dimensions,
declared and observed, for the suite (what no test covers) and for each change (§4.4 and §5.3 here, §3.5 in
`docs/AEM_ALIGNMENT.md`).

### 4.3 Controlled changes (43)

| Category | Count | Examples |
|---|---|---|
| code (tool adapters, services, harness) | 10 | argument-mapping bug in `set_page_metadata`; retry drops idempotency keys; approval gate bypass; external links treated as reachable; shared `get_page` reports the wrong review flag; edits keep approvals; the insights ranking sorted the wrong way; page search and the brand check case-sensitive; the site audit ignores alt text |
| runtime | 3 | termination six steps early; the delegated answer cut to 40 characters; a delegation drops the ids of earlier steps |
| skill | 11 | publishing skill drops link validation / permission check; authoring drops metadata; translation hard-codes en-US; rollback drops its permission check (the service still refuses); rollback restores the latest version; shared link-validation tolerates broken assets; governance drops the consent check; SEO drops the title-length guard; the routing skill stops asking for approval; the routing skill drops the brand gate |
| prompt / agent definition | 2 | SEO loses a tool; governance loses `check_consent` |
| configuration | 7 | validate_links disabled; review not required; step budget 5; retries 0; title limit 20; default agent changed; no approval needed to take a page down |
| combined | 1 | keyword-count rule in code + very low limit in config (each alone harmless) |
| benign | 9 | prose reflow; comment/docstring edit (AST-equivalent); local-variable renames; config comments/ordering; new unused tool; orchestrator prompt wording; translation intents re-ordered; brand skill prose reworded; routing guidance reordered |

The set is written for real models. A change has to touch an input a model acts on (keyword weights, trigger
lists and the order of an agent's intents are not such inputs), and a removed step has to go from both the
procedure and the prose, or the model does the step anyway. Candidates that told nothing about selection were
left out: exact twins of other changes, crashes that only exercised the crash classification, and a change that
broke most of the suite. Ten of the changes are aimed at the multi-agent workflows: the orchestrator's approval
and brand rules, the hand-off of ids between steps, the services behind the AEM-style agents, and two benign
ones. `docs/USER_GUIDE.md` §6 explains each of the 43 and why it is in the set.

The report checks a sanity property of the testbed: every regression-inducing change is revealed by ≥ 1 test, and
no benign change is revealed by any test. Under Gemma five regressions are revealed by no test, for reasons that
belong to the model (§5.1); under Qwen every regression is revealed, but so is every benign change (§5.4).

### 4.4 Protocol and metrics

1. `baseline`: full suite × K with coverage contexts, giving observed dependencies, cost and pass rates.
2. `mutants`: for each change, copy the SUT, apply the edit, extract the change set and run the full suite × K,
   giving the fault matrix.
3. `evaluate`: for every (change, strategy, budget ∈ {2,5,10,20,30,50,100}% of full-suite tokens, seed), the
   strategy selects from the baseline facts and the change set only. Each execution is answered from the
   recorded runs of that variant (a random repetition supplies the outcome and cost). Adaptive strategies
   interact sequentially.
4. Metrics:
   - change coverage, which needs no ground truth (`experiment/coverage.py`): the share of the changed components
     the executed tests exercised, the share of the properties the change may affect that they checked, whether
     every affected mandatory property got a test, and the shares of the affected workflows they ran, of the
     affected features they reached and of the refusals in the changed code they reached;
   - property coverage: of the properties a change breaks, those its selected tests exercise;
   - detection (≥ 1 revealing test executed and failed), recall of revealing tests, tokens actually spent, cost
     to first detection, false alarms, safety recall, stop reason and stop correctness;
   - APFD and APFD_c of the complete prioritized order;
   - selection recall and selected-subset cost.

---

## 5. Results

### 5.1 Gemma (`runs/gemma5`: 176 tests × 3 reps baseline, 43 changes × 3 reps, with the model judge, 5 replay seeds)

The agents are played by Gemma 4 E4B, served with vLLM on a GPU server (`docs/EXPERIMENT.md`). §5.4 covers
Qwen3.8-27B's recording of the same app. The ground truth belongs to the model:

- On the original app, 170 of 176 tests pass. The six failures are model mistakes that clearer wording did not
  fix (`docs/EXPERIMENT.md` §6). Gemma schedules a page without an approved review (PUB-10, and in the campaign
  launch WF1-01), requests a review nobody asked for (AUT-04), applies an over-long SEO title (SEO-02), goes on
  to publishing after a failed link check (WF5-02), and stops a whole plan after a refused export that the other
  steps do not depend on (WF6-02). Its three runs of each test always agreed.
- 29 of the 34 regressions are revealed. Gemma does not act on guards it has to work out for itself (a review
  flag, a length), and it stops at a broken asset reference even when the skill says the reference does not
  block. It therefore behaves the same, wrongly, with or without the five changes to those guards.
- None of the nine benign changes fails a test. Across all 43 changes, the three runs disagreed on only five
  (change, test) pairs, and the majority vote absorbs them.

Detection of the 29 regressions Gemma reveals, by nominal budget, and tokens actually spent:

| strategy | 5% | 10% | 20% | 50% | 100% | spent @20% | spent @100% | spent on benign @100% |
|---|---|---|---|---|---|---|---|---|
| full (catalog order) | 0.14 | 0.21 | 0.34 | 0.90 | 0.99 | 0.20 | 0.98 | 1.00 |
| random | 0.21 | 0.33 | 0.52 | 0.84 | 0.99 | 0.20 | 0.98 | 1.00 |
| declared | 0.55 | 0.55 | 0.61 | 0.61 | 0.61 | 0.07 | 0.10 | 0.13 |
| ir_tfidf | 0.70 | 0.71 | 0.92 | 0.99 | 0.99 | 0.20 | 0.98 | 0.99 |
| observed | 0.62 | 0.69 | 0.86 | 0.86 | 0.99 | 0.15 | 0.49 | 0.32 |
| cost_aware | 0.59 | 0.62 | 0.83 | 0.86 | 0.99 | 0.20 | 0.98 | 0.99 |
| casper_slices (CASPER, reproduced) | 0.28 | 0.43 | 0.50 | 0.88 | 0.99 | 0.20 | 0.98 | 1.00 |
| risk_aware_ts (Risk-Aware Adaptive Evaluation, reproduced) | 0.27 | 0.43 | 0.59 | 0.81 | 0.99 | 0.20 | 0.98 | 1.00 |
| adaptive_bayes | 0.76 | 0.79 | 0.79 | 0.83 | 0.83 | 0.03 | 0.03 | 0.20 |

APFD_c of the full prioritized order: random 0.53, casper_slices 0.54, full 0.57, risk_aware_ts 0.61, declared 0.76
(selection recall 0.53), ir_tfidf 0.77, cost_aware 0.78, observed 0.79 (selection recall 1.00 at half the suite's
cost), adaptive 0.81. Cost to first detection, as a fraction of the full suite: adaptive 0.017, declared 0.025,
ir_tfidf 0.04, observed 0.05, cost_aware 0.06, casper_slices 0.12, risk_aware_ts 0.13, random 0.14, full 0.19. Time
spent follows tokens closely (the report's section 2).

**Reading.**
- *RQ1/RQ2.* Declared metadata caps detection at 61%, because shared skills reached through `include`, harness
  code and most configuration keys are not declared. Observed dependencies recover full selection recall and
  reach 86% within a 20% budget. The main argument for trace-informed selection holds.
- *RQ3.* Informed strategies raise APFD_c from 0.53 (random) to 0.76–0.81. The adaptive method's order is the
  best, and it finds the first regression soonest.
- *RQ4.* The adaptive method is the only one that returns budget: it catches 76% of the regressions at a 5%
  budget and 79% at 20%, for under 3% of the tokens. Its ceiling is 83%. On narrow regressions, revealed by one
  to five tests, it can stop with a "clean" verdict before reaching them (145 of 1,015 replays of regressions).
  The changes it misses at a 20% budget are the delegation that drops the ids of earlier steps, the agent loop
  that stops six steps early, retries without idempotency keys, the routing skill without its brand gate, the
  authoring skill without its metadata step, and the combined change, which runs out of budget.
- *Critical regressions.* Of the 21 changes that break a safety property, the adaptive method catches 86% from a
  10% budget on, `observed` 81% and TF-IDF 98% at 20% (spending the whole 20%).
- *Red tests on the original app.* Gemma's six failing tests fail on every changed copy too, so a strategy that
  runs one sees a failure the change did not cause. On the 14 changes no test reveals, `full` sees such a failure
  in 71% of replays, `ir_tfidf` in 70% and `cost_aware` in 91%. The adaptive method discounts a test by its
  failures on the original app and gives no "regression" verdict on any of these changes (0 of 490 replays).
- *IR.* TF-IDF over the diff is the strongest selector at 20% (92%) but spends the whole budget. At 5% the
  adaptive method leads (76% against 70%).
- *The reproduced methods.* CASPER's slices and the risk-aware bandit do not look at the diff, and it shows: 50%
  and 59% of the regressions at a 20% budget, between random (52%) and the change-aware strategies (83–92%); an
  order no better than random's (APFD_c 0.54 and 0.61); and a first detection at 12–13% of the suite, where the
  change-aware strategies need 2–6%. The bandit's impact score is the test's risk, so it does better on the changes
  that break a safety property (73% at 20%, 94% at 50%). It rewards any failure, so it also runs Gemma's red tests
  early: on the changes no test reveals it sees a failure the change did not cause in 71% of its replays, CASPER's
  slices in 57%. Neither stops: both spend the whole budget on every change.

### 5.2 Text in the method: an option (roadmap 3(b))

The method's text signal (the tilt in §3.1) can be word overlap (the default), the TF-IDF similarity of the
`ir_tfidf` strategy (`adaptive_bayes_tfidf`), or nothing (`adaptive_bayes_notext`, an ablation). Detection, with
the tokens spent in parentheses, on the Gemma recording of §5.1 (5 seeds):

| budget | overlap (default) | TF-IDF | no text | `ir_tfidf` alone |
|---|---|---|---|---|
| 5% | 0.76 (2.1%) | 0.79 (2.0%) | 0.62 (2.4%) | 0.70 (5%) |
| 20% | 0.79 (2.9%) | 0.83 (2.4%) | 0.69 (3.5%) | 0.92 (20%) |
| 50% | 0.83 (2.9%) | 0.83 (2.4%) | 0.69 (4.5%) | 0.99 (50%) |

The TF-IDF variant also stops correctly most often (0.88 at 20%, against 0.86 for the default and 0.79 without
text), and no variant gives a "regression" verdict on a change no test reveals.

**Reading.** TF-IDF brings forward the one test that reveals a narrow change, and gains up to four points while
spending less. Without any text the method loses ten points, so text matters, but coverage and history carry
most of the result. The testbed is textual: tests, skills and config keys share vocabulary, which favours any
text measure (a threat noted in §8). The default stays word overlap until a second recording shows whether the
gain holds there too. Whether TF-IDF helps as much where tests and changes are worded differently is a question
for tau2-bench.

### 5.3 Coverage, and mandatory properties in the method

Coverage is a metric the AEM team asked for (`docs/AEM_ALIGNMENT.md` §3.5); the report's section 6 gives it for
the suite and for each change. On this app every agent, skill, setting, property and workflow has a test; one
tool, `get_asset`, has none. The declared metadata misses one skill and four settings that the traces show in use.

Change coverage needs no ground truth. Observed, cost-aware and TF-IDF selection and the adaptive method all
exercise 97% of the changed components at a 20% budget (one change touches code no test runs). The adaptive
method checks about half of the properties a change may affect (0.50, against 0.83 for `observed`), because it
stops at the first real failure or as soon as it is confident. That is the purpose of stopping, but it would also
let the method call a change clean with a mandatory property untested.

Step 5 of the method (on by default; `adaptive_bayes_nomandatory` is the ablation) closes that gap. A run that
found no regression does not end before every mandatory property the change may affect has a test, while the
budget allows. The test chosen is the cheapest one that checks the property and passes on the original app. At a
20% budget:

| recording | runs without a regression that tested every affected mandatory property, without / with the rule | extra tests per change | detection without / with the rule |
|---|---|---|---|
| gemma5 | 0.33 / 0.90 | 0.8 | 0.76 / 0.79 |

On this app the rule is also a detector. It catches `skill_publish_drop_link_validation`, which the method alone
calls clean: before ending, the method must test the mandatory property `safety_no_broken_publish`, and that test
fails. The rule never caused a false verdict. Below a 10% budget it often cannot afford the extra test.

### 5.4 Qwen and gpt-oss: why their recordings are not a ground truth

Qwen3.8-27B (`runs/qwen5`: the same protocol, on one GPU of the server and two SLURM GPUs) passes 171 of the 176
tests on the original app. It gets five of Gemma's six mistakes right and makes its own. In particular, where the
routing skill says to stop after a failed step, it re-plans, as Adobe's Agent Orchestrator does: it repairs the
page that failed the brand check, or has the broken link fixed, and goes on (`docs/EXPERIMENT.md` §6).

Its recording is not a clean ground truth. Every regression is revealed, but so is every benign change, by two to
five tests, including the no-op change whose change set is empty. Six tests (the two that Qwen judges itself, the
60-character boundary and three long workflows) answer differently when they run 64 at a time over three servers,
as the changed copies do, than when they run one at a time, as the baseline does. Qwen's three runs also disagreed
on 260 (change, test) pairs, against Gemma's five. The strategies' numbers on this recording are therefore not
results; its report stays in `docs/results/qwen5/` as a record of the effect. The two reproduced methods show the
effect once more: CASPER's slices appear to detect 87% of the changes at a 20% budget there, because two of their
twenty representatives, SEO-05 and WF4-02, are among the unstable tests and "reveal" 25 and 31 of the 43 changes.

Two remedies fall short. vLLM 0.31's batch-invariant mode, which makes greedy decoding exactly repeatable, does
not support Qwen3.8: the server refuses it for the model's linear-attention layers ("not supported for
GDN_ATTN"). Recording the baseline the way the changes are recorded is not enough either. With the no-op change,
recorded exactly like the others, as the reference, seven of the eight other benign changes still flip one to
five tests, so some of Qwen's answers vary from run to run even under identical conditions.

gpt-oss-120b, OpenAI's open-weights model, was recorded on the branch with re-planning (`docs/AEM_ALIGNMENT.md`
§4.1: 182 tests, 48 changes, three repetitions). Its answers vary even more: the no-op change appears to break four
tests, and every benign change two to seven. More repetitions would show whether a majority vote settles them
(roadmap, phase 6).

Qwen and gpt-oss are used as they are served, like Gemma. Their recordings stand as this finding, and the results
are Gemma's. The lesson for a pipeline is to measure how much the model's answers vary from run to run under the
serving setup the selection will run on, before trusting a ground truth or a stopping rule. The no-op change
measures exactly that.

---

## 6. Models, the prototype, and a second system under test

- **ContentOps on real models** (`docs/EXPERIMENT.md`). Gemma 4 E4B (`--backend vllm`, or `hf` on a local GPU) and
  Qwen3.8-27B (`--backend llm`, or any other OpenAI-compatible endpoint) run on the GPU server, which offers two
  GPUs directly and two more through SLURM on the same machine (`TRACEEVAL_SITE=hpc`). One run can spread its
  requests over several servers. A 43-variant × 3-rep recording of the 176 tests is about 23k runs (timings in
  `docs/EXPERIMENT.md` §7). Every answer can be recorded (`traceeval/llm/cache.py`), so a rerun costs nothing and
  the test suite replays Gemma's answers without a GPU. gpt-oss-120b, OpenAI's open-weights model, runs the same
  way over both of the server's GPUs (§5.4). A run with a model behind OpenAI's API waits for API tokens.
- **The prototype** (`traceeval check`, `docs/EXPERIMENT.md` §5) runs the adaptive method on one change, live.
  Each test it picks runs on the changed app with the real model, and the outcome decides what runs next. It
  stops with a verdict and its probability that the change broke something. A recording made with the same model
  supplies the baseline traces, the costs and the other changes to calibrate from.
- **tau2-bench** (designed, not yet implemented). The airline domain comes first: 50 tasks, with a reward
  computed from the database state and the agent's communication, and no model judge. The local model plays both
  the agent and the user, and the controlled changes mutate the policy and the tool code. The replay evaluator
  and the strategies run unchanged on the parsed history.

---

## 7. Roadmap

| Phase | Deliverable | Status |
|---|---|---|
| 1. Testbed | SUT, catalog, tracing, mutations, change sets, record/replay, metrics, report, CLI, tests | done (v0.1) |
| 2. Methods | baselines + cost-aware + predictive + adaptive Bayesian selector with stopping | done (v0.1), with the mandatory-coverage rule (§5.3); open: tuning ε, the priors and the discount |
| 3. Method improvements | (a) test-level learned sensitivities (per test × component-kind reveal history) instead of kind-level; (b) IR relevance inside the Bayesian likelihood; (c) CASPER-style slices and the Risk-Aware Adaptive Evaluation bandit as reproduced baselines | (a) done; (b) done as an option (§5.2); (c) done: `casper_slices` and `risk_aware_ts` (§5.1) |
| 4. Real LLM | ContentOps on real models (local vLLM): all variants × 3 reps under two models | done: Gemma (`runs/gemma5`); Qwen's recording of the same app (`runs/qwen5`) is spoiled by run-to-run variation and is not used for the results (§5.4); gpt-oss-120b, recorded on the re-planning branch, varies even more |
| 5. External SUT | tau2-bench airline adapter; 12 mutations (6 policy, 4 tool-code, 2 benign); same evaluation | after the demo for the AEM team |
| 6. Scale/robustness | more mutations (mutation operators generated systematically: step deletion/swap/condition negation in procedures, argument swaps in adapters, config boundary values), equivalent-mutant analysis, sensitivity to K and to budget definitions (time vs. tokens), ablations of each model ingredient, more repetitions for the models whose answers vary (§5.4) | with the paper |
| 7. Paper | see §8 | drafting can start from this document and the report |

A model's own mistakes and blind spots shape the ground truth: which changes a test reveals depends on the model
(`docs/EXPERIMENT.md` §6 and §7). Two parts of the method follow from this. Each test's own record (§3.1) is there
because kind-level sensitivities alone let the method spend on cheap tests that merely call a changed function.
Stopping at the first failure of a test that passed on the original app is there because a failure the model also
produces on the original app says nothing about the change.

The prototype includes these items from the AEM team's wish list (`docs/AEM_ALIGNMENT.md`, whose §4 is the dated
plan for the demo of 12 November 2026):

- the catalog of properties, drafted by a model from the requirements;
- coverage reports, with workflows as a coverage dimension, and the mandatory-coverage rule (§5.3);
- the orchestrator's planning mode (plans, hand-offs with ids, human approvals), three agents modelled on AEM's
  (brand, insights, optimizer) and asset search;
- six multi-agent workflows (campaign launch across five specialists, site optimization across four, legal
  takedown, localized price update, rollback of a broken release, privacy request), and trace assertions on agent
  and tool order;
- ten controlled changes aimed at the workflows;
- the OpenTelemetry export;
- environment failures kept apart (`INFRA_INVALID`);
- recordings of the app with both models.

After the demo come re-planning after a failed step, built on a branch and waiting for one product decision
(`docs/AEM_ALIGNMENT.md` §4.1), then tau2-bench, and a run with a model behind OpenAI's API once tokens are
available.

---

## 8. Paper plan

**Working title.** TRACE-Eval: change-aware, cost-bounded regression test selection for LLM agent systems.

**Abstract (draft).** Agent platforms ship dozens of agents assembled from skills, prompts, tools, harness code and
configuration, and verify them with tests and statistical evals whose cost is dominated by tokens. After a change,
teams either re-run everything or guess. We formulate selection, prioritization and budget-aware stopping of agent
tests as one problem and propose a method that (i) extracts a change set from the diff at the granularity of code
lines, skill procedures, agent-definition fields and configuration keys, (ii) maps it to tests through dependencies
*observed* in execution traces rather than declared metadata, (iii) ranks tests by expected information per token
in a Bayesian model whose sensitivities are calibrated from history, and (iv) stops when the posterior probability
of a regression is low. We evaluate on a testbed with 180 tests and eval items, 43 controlled changes with a
mutation-based ground truth derived per model, and a working multi-agent application, including multi-agent
workflows, whose agents are played by open models (a small one, and a mid-size one as a second). Declared
dependencies miss 39% of the regressions; trace-informed selection finds 86% of them within 20% of the full-suite
tokens. The two closest published methods, reproduced on the testbed, find 50% and 59%, because neither looks at
the change. The adaptive method detects 79% for 3% of the tokens and returns most of the budget on benign changes.
Unlike the other strategies, it does not mistake the tests the model already fails for regressions.

**Outline.**

1. Introduction: motivation from AEM-scale platforms; nightly batch and PR use; the three sub-problems.
2. Background and related work: RTS/TCP; efficient LLM evaluation; agent benchmarks; fault injection; CASPER as
   the closest work.
3. Problem formulation and models (§1–2).
4. Method (§3.1).
5. Testbed (§4).
6. Evaluation: RQ1–RQ4, ablations, and external validity with LLMs and tau2-bench.
7. Threats to validity: synthetic mutants vs. real regressions; three models, of which only the smallest gives a
   stable ground truth with three repetitions; greedy decoding, and a ground truth that depends on the model; a
   single primary domain; calibration leakage, controlled by leave-one-change-out; a textual testbed that favours
   IR.
8. Conclusion.

**Venues.** ASE, ISSTA or ICST, with a software-engineering framing: RTS/TCP for LLM-based systems, a
mutation-based ground truth, APFD_c. The alternative is NeurIPS D&B or EMNLP, with the testbed as the headline
("a benchmark for regression test selection in agent systems").

---

## 9. Questions still to settle with Georgiana

The follow-up questions with the AEM team (`docs/AEM_ALIGNMENT.md` §1) answered part of this list: nightly and
model-update runs, prompt → answer and prompt → tool-call datasets, the thresholds and mandatory properties
wanted, and budgets with early stopping.

1. Change identification. Is the diff available per PR or nightly batch, and does the platform keep skills,
   prompts and config under version control together with the harness code? The change-set extractor assumes
   files in one tree.
2. Dependency registry. Is there a mapping from agents to skills, tools and config, and are traces (tool calls,
   skills loaded, config reads) retained for the nightly runs? Observed dependencies need ≥ 1 baseline run per
   test with tracing.
3. Eval datasets. Can items be run individually and their costs attributed? Our dataset items are selectable
   units; the routing dataset is run in route-only mode.
4. Oracles. Which properties are deterministic and which are judged? Which are release blockers (the safety set)?
5. Budgets. Tokens, time or both; per PR or nightly? Is a partial run with an explicit "clean with probability p"
   statement acceptable to the team? This is what the stopping rule outputs.
6. Re-planning. Should a single publish request for a page with a broken link be repaired or refused? The
   re-planning branch waits for this answer (`docs/AEM_ALIGNMENT.md` §4.1).

---

*Repository: `trace-eval/` (the README lists the commands). Inputs synthesized:
Agent_Test_Prioritization_Requirements.md; Agent Test Prioritization Prototype.docx;
agent_test_prioritization_summary.md; TRACE-Eval_Pi_Harness_Handoff.md;
muse-glimmer-local-setup-and-agent-workflows.md.*
