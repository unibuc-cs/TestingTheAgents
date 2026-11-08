# TRACE-Eval — Research and implementation plan

**Change-aware, cost-bounded selection, prioritization and stopping of tests and evals for LLM agent systems**

Ciprian Păduraru · University of Bucharest · working document, 6 October 2026, updated 8 November 2026 · status: prototype v0.1 running on real models, results in `docs/results/gemma2/report.md` and `docs/results/qwen2/report.md`

---

## TL;DR

- **Problem.** After a change to an agent system, decide which tests and eval items to run, in what order, and
  when to stop, under a token budget and without missing regressions.
- **Method.** Map the diff to components (code lines and functions, skill procedures, agent fields, config keys)
  and match them to tests through the dependencies observed in traces. Rank tests by expected information per
  token in a Bayesian model whose sensitivities are calibrated from history, and stop when the probability of a
  regression is low. The method is `adaptive_bayes`; six baselines run alongside it.
- **Testbed.** A small multi-agent app (`traceeval/sut`) whose agents are played by a real model (Gemma 4 E4B, and
  Qwen3.8-27B as a second model), 136 tests and 33 controlled changes applied as file edits (7 of them benign).
  Full-suite runs with three repetitions give the ground truth, and strategies are compared by offline replay.
- **Results so far (§5.1).** Hand-written dependencies catch 65–71% of regressions. Trace-based selection catches
  85–90% within a budget of 20% of the full-suite tokens. The adaptive method catches 65–76% while spending 5–6% of
  those tokens, and never calls a change that breaks nothing a regression, even though Gemma fails three tests on
  the original app and the other strategies take those failures for regressions. TF-IDF over the diff is a strong
  baseline (73–81% at 5%). Change sets hold code only, so the results are the same whether or not the code is
  commented.
- **Next.** Fold the IR signal into the model (the adaptive method still stops too early on regressions that one
  or two tests reveal, mostly under Qwen), re-record the ground truth on the current app, then move to
  tau2-bench as the external system under test. Real models only, decoded greedily. Paper: ASE/ISSTA/ICST framing.

---

## 0. What this document is

This plan merges five earlier inputs into one research design and one runnable testbed: the requirements captured from the July 2026 discussion with Georgiana (Adobe, AEM agent platform), the state-of-the-art report with APFD/APFD_c and reliability metrics, the OpenTelemetry-based prioritization sketch, the TRACE-Eval/Pi handoff, and the local Muse Glimmer/vLLM setup notes. Where the inputs disagreed, the decisions below say which way we went and why. The research problem is kept general (any agent platform built from skills, prompts, tools, harness code and configuration); AEM is the motivating instance, not a dependency.

**Decisions taken in this iteration**

| Topic | Decision | Reason |
|---|---|---|
| System under test (SUT) | A purpose-built mini content-operations platform ("ContentOps": pages, assets, publishing, SEO, translation, governance, rollback) is the primary SUT. tau2-bench, with the local vLLM model playing both the agent and the user, is the second SUT (designed, not yet implemented; see `docs/tau2_integration.md`). | The primary SUT gives a multi-agent structure with shared components built in on purpose (the hard case Georgiana described) and full control over mutations. Its agents run on a local model, and recorded answers make reruns free and exact. tau2-bench adds external validity. |
| Agent runtime | Pure Python harness with an OpenAI-compatible LLM backend; Pi is not used in the prototype. | Shortest path. The harness code must itself be mutable and instrumentable (coverage contexts). A Pi adapter remains possible later. |
| Observability | Own trace recorder with an OpenTelemetry-compatible event model (agent/skill/tool/config/llm spans) rather than Phoenix/OpenInference as a dependency. | No services in the loop; an OTel exporter is a small addition. |
| Oracles | Deterministic (final state, tool trajectories, audit log, response substrings); an LLM judge only for explicitly marked answer-quality properties, executed after deterministic checks pass, by Gemma or Qwen against the case's rubric (the recordings in §5.1 still used a check of the required facts in its place). | Regression tracking must not depend on judge noise (docx report §"LLM-as-a-judge bottleneck"). |
| Ground truth | Mutation analysis: 33 controlled changes, benign ones included, applied as file edits. The selectors see only the diff. | Needed to measure detection rate against a known answer, and to measure wasted budget. |
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
| `agent:<name>.<field>` | `agent:publishing.triggers`, `agent:seo.tools` | Order-sensitive comparison (intent order matters). |
| `config:<dotted.key>` | `config:runtime.retries` | Effective value changes only. |
| comments and formatting | — | Left out: comments, docstrings, blank lines, YAML comments and the order of config mappings add no component, file or diff line, so no selector or probability depends on them. The selectors read the diff of the code alone. |

### 2.2 Dependency model (declared · observed · required)

- **Declared**: the metadata a test author wrote (`declared:` block in the catalog). It is incomplete on purpose, as in practice: shared skills reached through `include`, harness code and most configuration keys are not declared.
- **Observed**: from baseline traces: agents started, agent-definition fields consulted by the orchestrator, skills loaded (with version/digest), tools called (with status and attempts), configuration keys read, executed code functions and lines (coverage.py dynamic contexts, one context per test and repetition).
- **Required**: properties/risk that must always be evaluated (safety tests are marked by `safety_*` properties; a mandatory-set policy is a one-line addition to any strategy).

### 2.3 Cost model

c(t) = agent tokens (prompt + completion over all LLM calls in the delegation chain) + judge tokens (only when a judge runs). Latency is recorded alongside. Tokens come from the model server's usage fields, so a case that delegates, retries or reads long skills costs more. A full-suite run costs about 0.96M tokens under Gemma and 1.08M under Qwen.

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

The two optional baselines run only with `--strategies all`; the results in §5 compare the other seven.

### 3.1 The proposed method: adaptive Bayesian selection with budget-aware stopping

*Hypotheses.* Each changed component c is "broken" with prior π_c by kind (code/skill/config/agent ≈ 0.45–0.5, prompt wording/prose ≈ 0.12–0.15). The posterior is kept exactly over all 2^k subsets B (k ≤ 8 components).

*Likelihood.* P(t fails | B) = 1 − (1 − f_t) ∏_{c∈B} (1 − s_tc). The sensitivity s_tc of test t to component c is
s_tc = r_kind(c) · lift_t,kind(c) · freq_t(c) · tilt_t, where

- r_kind is the empirical reveal ratio learned from the other recorded changes: the fraction of statically impacted tests that actually revealed a change of that kind. Kinds separate, for example, "executed the changed line" from "executed only the changed function", and agent fields are calibrated per field. This encodes "coverage does not imply detection" with measured numbers instead of hand-set constants.
- lift_t,k = (O_tk + m) / (E_tk + m) is the test's own record on the earlier changes of kind k that impacted it: O_tk is how many of them it revealed, E_tk how many an average impacted test would have revealed (the sum of those changes' reveal rates), and m = 2 pads a short record. A test that ran many changed functions and never caught anything gets a lift below 1; one that caught changes most impacted tests missed gets a lift above 1. Comparing with E rather than counting catches matters: a change that breaks a large part of the suite (link validation turned off everywhere: 40 tests) says little about each test it breaks. Like r_kind, the records are recomputed from the recordings at every run, without the change under evaluation, so they grow as more changes are recorded (`docs/USER_GUIDE.md` §5).
- freq_t(c) is how often t exercised c in its baseline runs.
- tilt_t ∈ [0.5, 2.0] combines the lexical relevance of the change text (code only, never comments) to the test's own text (name, request, expectations) with a bonus when the author declared the dependency. It is a proxy for "the test's oracle plausibly observes the changed behaviour".

*Policy.* The next test is the argmax over t of (expected information gain about B, tilted by risk) / c(t). After a pass, the sensitivities of tests with the same behaviour signature (agents, tools, fault profile, dataset) are discounted (×0.35), because near-duplicate tests are correlated evidence, not independent draws. Each test runs at most once: the models decode greedily, so a rerun gives the same answer.

*Stopping.* The method stops "regression" at the first failure of a test that passed on the original app: the models decode greedily, so that failure shows a changed behaviour, which is what the ground truth calls revealing. It stops "clean" when P(any component broken | evidence) < ε_clean (0.05). Otherwise it runs until the budget is exhausted or no test is informative. Selection, prioritization and stopping all come from the same model.

### 3.2 Why these baselines

They cover the design space of the literature: classic RTS/TCP on declared coverage (Rothermel), IR-based TCP (Saha 2015), cost-cognizant TCP (Elbaum 2001), predictive test selection (Machalica 2019) and diversity-based ordering (Pan/Briand LTM). CASPER (2026) and Risk-Aware Adaptive Evaluation (2026) are the closest external competitors (`docs/related_work.md`). Reproducing them on the testbed is a phase-3 task.

---

## 4. Evaluation environment (the testbed)

### 4.1 System under test — ContentOps

`traceeval/sut` contains eight agents (orchestrator, authoring, publishing, assets, seo, translation, governance, maintenance), ten skills, 24 tools over deterministic services (repository with versions, workflow with reviews/scheduling, links, governance with consent and approval tokens, translation, SEO), a harness (configuration with instrumented reads, skill loader with a procedure DSL, retry helper with idempotency keys, dispatcher with tool enablement + approval gate + fault injection, runtime loop with delegation and a step budget) and `config/runtime.yaml`.

The structure is deliberate, so that selection is hard and defence-in-depth questions can be discussed. Some components are shared and have a wide blast radius: `governance-checks` and `link-validation` are included by several skills, `check_permission` is available to every specialist agent and `get_page` to all but the governance agent, and the retry helper wraps every tool call. Others are narrow: the approval gate matters to one test. Some policies are enforced only in skills (publish permission), others also in tools (approval tokens).

A `SKILL.md` has front matter, prose, and a `## Procedure` YAML block that the model reads as numbered steps (included skills written out in place, settings shown with their current values). Mutations of the prose and of the procedure are separate components (`#prose`, `#procedure`).

### 4.2 Eval catalog

72 scenario tests (publishing 21, authoring 14, assets/SEO 16, translation/governance/maintenance/orchestration 21) and two dataset-style evals (40 routing items, prompt → expected delegation, run in route-only mode; 24 intent items, prompt → expected tool invocation). Each case defines an agent entry point, request, context slots, fixture (+ optional patch), fault profile (`healthy`, `transient_once:<tool>`, `ack_timeout_once:<tool>`, `permanent_down:<tool>`), risk (critical/high/medium/low → severity 4/3/2/1), properties (functional, routing, trajectory, safety_*, resilience_*, efficiency, answer_quality), declared dependencies, expectations (state assertions, required/forbidden tools, attempt counts, audit counts, response substrings, step limits, termination) and, for two cases, a judge rubric.

### 4.3 Controlled changes (33)

| Category | Count | Examples |
|---|---|---|
| code (tool adapters, services, harness) | 6 | argument-mapping bug in `set_page_metadata`; retry drops idempotency keys; approval gate bypass; external links treated as reachable; shared `get_page` reports the wrong review flag; edits keep approvals |
| runtime | 2 | termination six steps early; the delegated answer cut to 40 characters |
| skill | 9 | publishing skill drops link validation / permission check; authoring drops metadata; translation hard-codes en-US; rollback drops its permission check (the service still refuses); rollback restores the latest version; shared link-validation tolerates broken assets; governance drops the consent check; SEO drops the title-length guard |
| prompt / agent definition | 2 | SEO loses a tool; governance loses `check_consent` |
| configuration | 6 | validate_links disabled; review not required; step budget 5; retries 0; title limit 20; default agent changed |
| combined | 1 | keyword-count rule in code + very low limit in config (each alone harmless) |
| benign | 7 | prose reflow; comment/docstring edit (AST-equivalent); local-variable renames; config comments/ordering; new unused tool; orchestrator prompt wording; translation intents re-ordered |

This is the set as revised for real models (phase 4 in `docs/EXPERIMENT.md`): two changes that a model does
not depend on (keyword-router weights and triggers) were replaced, one became benign, and the skill changes
also edit the prose that repeated the removed step. Five more were dropped afterwards: two exact twins of other
changes (retries disabled in code, approval removed in config), two crashes that only exercised the crash
classification, and delegation depth zero, which broke four tests in five and so told nothing about selection.
The results in §5 use the remaining 33; `docs/USER_GUIDE.md` §6 explains each change and why it is in the set.

The report checks a sanity property of the testbed: every regression-inducing change is revealed by ≥ 1 test, and no benign change is revealed by any test. It holds under Qwen. Under Gemma five regressions are revealed by no test, for reasons that belong to the model (§5.1).

### 4.4 Protocol and metrics

1. `baseline`: full suite × K with coverage contexts, giving observed dependencies, cost and pass rates.
2. `mutants`: for each change, copy the SUT, apply the edit, extract the change set and run the full suite × K, giving the fault matrix.
3. `evaluate`: for every (change, strategy, budget ∈ {2,5,10,20,30,50,100}% of full-suite tokens, seed), the strategy selects from the baseline facts and the change set only. Each execution is answered from the recorded runs of that variant (a random repetition supplies the outcome and cost). Adaptive strategies interact sequentially.
4. Metrics: detection (≥ 1 revealing test executed and failed), recall of revealing tests, tokens actually spent, cost to first detection, false alarms, safety recall, stop reason and stop correctness; APFD and APFD_c of the complete prioritized order; selection recall and selected-subset cost.

---

## 5. Results

### 5.1 Gemma and Qwen (`runs/gemma2`, `runs/qwen2`: 136 cases × 3 reps baseline, 33 variants × 3 reps, 5 replay seeds)

The agents are played by Gemma 4 E4B and by Qwen3.8-27B, served with vLLM on a GPU server
(`docs/EXPERIMENT.md`, phase 4). The ground truth belongs to the model:

- **Original app:** 133 of 136 tests pass under Gemma, 135 of 136 under Qwen. The failures are model mistakes
  that clearer wording did not fix (Gemma schedules a page without an approved review, requests a review nobody
  asked for, and applies an over-long SEO title; Qwen counts a 60-character title as 61).
- **Regressions:** Qwen reveals all 26. Gemma reveals 21: it does not act on guards it has to work out for itself
  (a review flag, a length), so it behaves the same, wrongly, with or without the five changes to those guards.
- **Benign changes:** none of the seven fails a test under either model.

Detection of the regressions each model reveals (21 under Gemma, 26 under Qwen), vs. nominal budget, and tokens
actually spent. Each cell is Gemma / Qwen:

| strategy | 5% | 10% | 20% | 50% | 100% | spent @20% | spent @100% | waste on benign @100% |
|---|---|---|---|---|---|---|---|---|
| full (catalog order) | 0.10 / 0.08 | 0.19 / 0.19 | 0.48 / 0.50 | 0.71 / 0.77 | 1.00 / 1.00 | 0.20 / 0.20 | 0.98 / 0.99 | 1.00 / 1.00 |
| random | 0.18 / 0.15 | 0.33 / 0.33 | 0.54 / 0.52 | 0.81 / 0.78 | 1.00 / 1.00 | 0.20 / 0.20 | 0.98 / 0.99 | 0.99 / 0.99 |
| declared | 0.71 / 0.58 | 0.71 / 0.65 | 0.71 / 0.65 | 0.71 / 0.65 | 0.71 / 0.65 | 0.08 / 0.07 | 0.10 / 0.09 | 0.07 / 0.11 |
| ir_tfidf | 0.81 / 0.73 | 0.81 / 0.81 | 0.90 / 0.88 | 1.00 / 1.00 | 1.00 / 1.00 | 0.20 / 0.20 | 0.98 / 0.99 | 0.99 / 0.99 |
| observed | 0.52 / 0.54 | 0.62 / 0.65 | 0.90 / 0.85 | 0.95 / 0.96 | 1.00 / 1.00 | 0.15 / 0.15 | 0.46 / 0.43 | 0.23 / 0.20 |
| cost_aware | 0.52 / 0.54 | 0.62 / 0.65 | 0.86 / 0.85 | 0.95 / 0.96 | 1.00 / 1.00 | 0.20 / 0.20 | 0.98 / 0.99 | 0.99 / 0.99 |
| adaptive_bayes | 0.62 / 0.46 | 0.76 / 0.58 | 0.76 / 0.65 | 0.81 / 0.69 | 0.86 / 0.73 | 0.05 / 0.06 | 0.07 / 0.08 | 0.37 / 0.25 |

APFD_c of the full prioritized order (Gemma / Qwen): random 0.47/0.44, full 0.55/0.58, adaptive 0.78/0.76,
ir_tfidf 0.79/0.80, cost_aware 0.81/0.83, observed 0.82/0.83 (selection recall 1.00 at about half of the suite
cost), declared 0.83/0.80 (selection recall 0.63/0.52). Cost to first detection: declared 0.02, ir 0.03–0.04,
adaptive 0.04, observed 0.06, cost_aware 0.06–0.07, random 0.15–0.17 of the full suite.

**Reading.**
- *RQ1/RQ2.* Declared metadata caps detection at 71% (Gemma) and 65% (Qwen), because shared skills reached through
  `include`, harness code and most configuration keys are not declared. Observed dependencies recover full
  selection recall and reach 85–90% within a 20% budget. The main argument for trace-informed selection holds
  under real models.
- *RQ3.* Informed strategies raise APFD_c from about 0.45 (random) to 0.76–0.83; declared ranks well but selects
  only part of the revealing tests (selection recall 0.52–0.63), observed and cost-aware ranking select them all.
- *RQ4.* The adaptive method again is the only one that returns budget: 76% (Gemma) and 65% (Qwen) detection for
  5–6% of the tokens, 7–8% at full budget. It stops at the first failure of a test that passed on the original
  app, and each test's own record (§3.1) brings the revealing test forward (on the earlier set of 38 changes it
  found regressions 3–15% sooner than kind-level sensitivities). It is weaker under Qwen because Qwen reveals
  more regressions that only one or two tests catch, and on those the method stops "clean" before reaching them
  (185 of 910 replays on regressions). The IR term inside the model (§7) is meant to address it.
- *Red tests on the original app.* Gemma's three failing tests fail on every changed copy too, so a strategy that
  runs one of them sees a failure the change did not cause. On the changes that no test reveals, `full` sees such
  a failure in 71% of replays and `ir_tfidf` in 58% under Gemma (56% and 16% under Qwen). The adaptive method
  discounts a test by its failures on the original app and gives no "regression" verdict on any change that no
  test reveals (0 of 665 replays).
- *IR.* TF-IDF over the diff is still the strongest prioritizer at small budgets (81%/73% at 5%).

---

## 6. Models, the prototype, and a second system under test

- **ContentOps on real models** (done, `docs/EXPERIMENT.md`): Gemma 4 E4B (`--backend vllm`, or `hf` on a local
  GPU) and Qwen3.8-27B (`--backend llm`, or any other OpenAI-compatible endpoint) run on the GPU server: two GPUs
  directly, plus two through SLURM on the same machine (`TRACEEVAL_SITE=hpc`), and one run can spread its requests
  over several servers. A 33-variant × 3-rep recording is about 13.9k runs: about half an hour under Gemma and an
  hour and a half under Qwen. Every answer can be recorded (`traceeval/llm/cache.py`), so a rerun costs nothing and the test suite
  replays Gemma's answers without a GPU. An OpenAI backend is planned once API tokens are available.
- **The prototype** (`traceeval check`, `docs/EXPERIMENT.md` §5): the adaptive method on one change, live.
  Each test it picks runs on the changed app with the real model, and the outcome decides what runs next;
  it stops with a verdict and its probability that the change broke something. A recording made with the
  same model supplies the baseline traces, the costs and the other changes to calibrate from.
- **tau2-bench** (verified facts and adapter design in `docs/tau2_integration.md`): airline domain first (50 tasks, DB + communicate reward, no NL judge), the agent and the user both played by the local vLLM model, via `--agent-llm openai/<model> --agent-llm-args '{"api_base": ..., "api_key": "EMPTY"}'` (and the same for `--user-llm`), `TAU2_DATA_DIR` pointed at a mutated copy of `data/` for policy mutations, a mutated checkout for tool-code mutations, change sets from `git diff`, outcomes/tokens parsed from `results.json` into the same history format. The replay evaluator and all strategies then run unchanged. Expect large token counts per task (tens of thousands).

---

## 7. Roadmap

| Phase | Deliverable | Status |
|---|---|---|
| 1. Testbed | SUT, catalog, tracing, mutations, change sets, record/replay, metrics, report, CLI, tests | done (v0.1) |
| 2. Methods | baselines + cost-aware + predictive + adaptive Bayesian selector with stopping | done (v0.1); tune ε, priors, discount; add a mandatory-safety policy wrapper |
| 3. Method improvements | (a) test-level learned sensitivities (per test × component-kind reveal history) instead of kind-level; (b) IR relevance inside the Bayesian likelihood; (c) CASPER-style slices and the Risk-Aware Adaptive Evaluation bandit as reproduced baselines | (a) done; (b), (c) next |
| 4. Real LLM | ContentOps on real models (local vLLM): all variants × 3 reps under two models | done: Gemma and Qwen (`docs/EXPERIMENT.md`) |
| 5. External SUT | tau2-bench airline adapter; 12 mutations (6 policy, 4 tool-code, 2 benign); same evaluation | after 3(b) |
| 6. Scale/robustness | more mutations (mutation operators generated systematically: step deletion/swap/condition negation in procedures, argument swaps in adapters, config boundary values), equivalent-mutant analysis, sensitivity to K and to budget definitions (time vs. tokens), ablations of each model ingredient | with the paper |
| 7. Paper | see §8 | drafting can start from this document and the report |

Phase 4 showed that a model's own mistakes and blind spots shape the ground truth: which changes a test reveals depends on the model (`docs/EXPERIMENT.md`, phase 4).

The prototype (`traceeval check`, §6) ran live on four changes under each model, from recordings of the current app (`runs/gemma3`, `runs/qwen3`, one repetition). It caught a skill regression with its first test, called a harmless prompt rewording clean, and found nothing for a hand edit that no test covers. The weak case was the retry change: the method first spent on cheap tests that merely call the changed function, and ran out of budget undecided. That led to item 3(a), each test's own record, together with stopping at the first failure of a test that passed on the original app. Replayed on the same recordings, the retry change now ends "regression" after 17 tests (8.9% of the suite) under Gemma and 11 (5.9%) under Qwen. The new recordings also show that the ground truth moves with the app and the judge: under Qwen, three regressions revealed in `runs/qwen2` are not revealed on the current app, one because the strict model judge now fails SEO-07 on the original app.

Immediate next steps, in order: the IR signal inside the likelihood (the adaptive method's misses under Qwen); re-recording the ground truth with three repetitions on the current app with the model judge, before the paper; the mandatory-safety wrapper; the OpenAI backend once API tokens are available.

---

## 8. Paper plan

**Working title.** TRACE-Eval: change-aware, cost-bounded regression test selection for LLM agent systems.

**Abstract (draft).** Agent platforms ship dozens of agents assembled from skills, prompts, tools, harness code and configuration, and verify them with tests and statistical evals whose cost is dominated by tokens. After a change, teams either re-run everything or guess. We formulate selection, prioritization and budget-aware stopping of agent tests as one problem and propose a method that (i) extracts a change set from the diff at the granularity of code lines, skill procedures, agent-definition fields and configuration keys, (ii) maps it to tests through dependencies *observed* in execution traces rather than declared metadata, (iii) ranks tests by expected information per token in a Bayesian model whose sensitivities are calibrated from history, and (iv) stops when the posterior probability of a regression is low. We evaluate on a testbed with a working multi-agent application whose agents are played by two open models (a small and a mid-size one), 136 tests/eval items, and 33 controlled changes with a mutation-based ground truth derived per model. Declared dependencies miss 29–35% of the regressions; trace-informed selection finds 85–90% of them within 20% of the full-suite tokens. The adaptive method detects 65–76% for 5–6% of the tokens, returns most of the budget on benign changes, and, unlike the other strategies, does not mistake the tests the model already fails for regressions.

**Outline.** 1 Introduction (motivation from AEM-scale platforms; nightly batch + PR use; three sub-problems) · 2 Background and related work (RTS/TCP; efficient LLM evaluation; agent benchmarks; fault injection; CASPER as closest work) · 3 Problem formulation and models (§1–2) · 4 Method (§3.1) · 5 Testbed (§4) · 6 Evaluation (RQ1–RQ4 + ablations + LLM/tau2 external validity) · 7 Threats to validity (synthetic mutants vs. real regressions; two models, greedy decoding, and a ground truth that depends on the model; single primary domain; calibration leakage controlled by leave-one-change-out; textual testbed favouring IR) · 8 Conclusion.

**Venues.** ASE / ISSTA / ICST (SE framing: RTS/TCP for LLM-based systems, mutation-based ground truth, APFD_c). Alternative: NeurIPS D&B / EMNLP with the testbed as the headline ("a benchmark for regression test selection in agent systems").

---

## 9. Questions still to settle with Georgiana

1. Change identification: is the diff available per PR/nightly batch, and does the platform keep skill/prompt/config under version control together with harness code? (The change-set extractor assumes files in one tree.)
2. Dependency registry: is there a mapping agent → skills/tools/config, and are traces (tool calls, skills loaded, config reads) retained for the nightly runs? (Observed dependencies need ≥ 1 baseline run per test with tracing.)
3. Eval datasets: can items be run individually and attributed costs? (Our dataset items are selectable units; the routing dataset is run in route-only mode.)
4. Oracles: which properties are deterministic vs. judged; which are release blockers (safety set)?
5. Budgets: tokens, time or both; per PR vs. nightly; is a partial run with an explicit "clean with probability p" statement acceptable to the team (this is what the stopping rule outputs)?

---

*Repository: `trace-eval/` (README for commands). Inputs synthesized: Agent_Test_Prioritization_Requirements.md; Agent Test Prioritization Prototype.docx; agent_test_prioritization_summary.md; TRACE-Eval_Pi_Harness_Handoff.md; muse-glimmer-local-setup-and-agent-workflows.md.*
