# TRACE-Eval — Research and implementation plan

**Change-aware, cost-bounded selection, prioritization and stopping of tests and evals for LLM agent systems**

Ciprian Păduraru · University of Bucharest · working document, 6 October 2026 · status: prototype v0.1 running, first results in `runs/exp1/results/report.md`

---

## TL;DR (read this, skip the rest unless you need detail)

- **Problem.** After a change to an agent system, pick which tests/eval items to run, in what order, and when
  to stop, under a token budget, without missing regressions.
- **Method.** Map the diff to components (code lines/functions, skill procedures, agent fields, config keys);
  match them to tests through dependencies *observed in traces*; rank tests by expected information per token in
  a Bayesian model whose sensitivities are calibrated from history; stop when the probability of a regression is
  low. Implemented as `adaptive_bayes`; six baselines next to it.
- **Testbed.** A small real multi-agent app (`traceeval/sut`), 134 tests, 35 controlled changes applied as real
  edits (6 benign), full-suite runs as ground truth, offline replay to compare strategies.
- **Results so far (simulated agent).** Hand-written dependencies catch 66% of regressions; trace-based selection
  catches 90% for 20% of the full-suite tokens; the adaptive method catches 86% for 11–26% and stops correctly on
  benign changes; under 5% agent flakiness it never raises a false regression while the others do in 40–69% of
  replays. TF-IDF over the diff is a surprisingly strong baseline (93% at 5%).
- **Next.** Calibrate sensitivities per test (not per kind), fold the IR signal into the model, run the LLM backend
  on the DGX, then tau2-bench as the external system under test. Paper: ASE/ISSTA/ICST framing.

---

## 0. What this document is

This plan consolidates five earlier inputs — the requirements captured from the July 2026 discussion with Georgiana (Adobe, AEM agent platform), the state-of-the-art report with APFD/APFD_c and reliability metrics, the OpenTelemetry-based prioritization sketch, the TRACE-Eval/Pi handoff, and the local Muse Glimmer/vLLM setup notes — into one research design and one runnable testbed. Where the inputs disagreed, the decisions below say which way we went and why. The research problem is kept general (any agent platform built from skills, prompts, tools, harness code and configuration); AEM is the motivating instance, not a dependency.

**Decisions taken in this iteration**

| Topic | Decision | Reason |
|---|---|---|
| System under test (SUT) | A purpose-built mini content-operations platform ("ContentOps": pages, assets, publishing, SEO, translation, governance, rollback) is the primary SUT; **tau2-bench with the local vLLM model as agent *and* user simulator is the second SUT** (designed, not yet implemented; see `docs/tau2_integration.md`). | The primary SUT gives a free, deterministic simulated mode to develop and evaluate selection methods today, a planted multi-agent structure with shared components (the non-trivial case Georgiana described), and full control over mutations. tau2-bench adds external validity with a real LLM. |
| Agent runtime | Pure Python harness with an OpenAI-compatible LLM backend; Pi is not used in the prototype. | Shortest path; the harness code must itself be mutable and instrumentable (coverage contexts). A Pi adapter remains possible later. |
| Observability | Own trace recorder with an OpenTelemetry-compatible event model (agent/skill/tool/config/llm spans) rather than Phoenix/OpenInference as a dependency. | Keeps the loop free of services; exporting to OTel is a thin addition. |
| Oracles | Deterministic (final state, tool trajectories, audit log, response substrings); an LLM judge only for explicitly marked answer-quality properties, executed after deterministic checks pass, simulated in the free mode. | Regression tracking must not depend on judge noise (docx report §"LLM-as-a-judge bottleneck"). |
| Ground truth | Mutation analysis: 35 controlled changes applied as real file edits; the selectors only ever see the diff. Benign changes included. | Required to measure detection rate honestly and to measure wasted budget. |
| Evaluation | Record-then-replay: run the full suite once per variant, evaluate all strategies offline. | Decouples method development (thousands of replays) from execution cost (one recording per variant). |

---

## 1. Problem statement and research questions

A change set Δ (edits to skill files, prompts/agent definitions, harness or tool code, configuration) arrives at an agent platform with a suite T of tests and eval-dataset items, each with a cost c(t) (tokens, time). We must choose a subset S ⊆ T and an order, possibly adaptively, under a budget B, such that regressions introduced by Δ are detected with high probability, at low cost, and such that the procedure stops when further evidence is not worth its price.

Three sub-problems (from the requirements document) are kept separate throughout: **selection** (which), **prioritization** (in which order), **budget-aware stopping** (when to stop). The research questions are those of the requirements document, made measurable:

- **RQ1 (selection)** Can we identify the tests relevant to a change? *Metric: selection recall of the revealing tests and cost of the selected subset, declared vs. observed dependencies.*
- **RQ2 (traces)** Do execution traces improve selection beyond static/declared dependency information? *Metric: RQ1 and RQ3 metrics for `declared` vs. `observed*`.*
- **RQ3 (prioritization)** Can we order tests to detect regressions earlier? *Metric: APFD, cost-cognizant APFD_c, cost to first detection.*
- **RQ4 (budget)** Can we reduce time and tokens while retaining acceptable detection and coverage? *Metric: detection rate vs. budget curves, tokens actually spent, waste on benign changes, stopping accuracy.*

**Claimed contribution.** A change-aware, trace-informed, cost-bounded method for selecting agent tests with a principled stopping rule, plus a reproducible testbed (SUT + mutation catalogue + metrics) for evaluating such methods. The method, not the testbed, is the contribution (requirements §11); the testbed is what makes the method testable.

---

## 2. Models underlying the method

### 2.1 Change model (what a diff becomes)

The extractor (`traceeval/mutation/changeset.py`) turns a diff into *components* with the same identifiers used for dependencies:

| Component | Example | Granularity notes |
|---|---|---|
| `code:<file>::<function>` + `line:<file>:<n>` | `code:harness/retry.py::with_retry`, `line:harness/retry.py:26` | AST-normalised function comparison (docstrings ignored); changed baseline lines; an insertion anchors to its neighbours. |
| `tool:<name>` | `tool:set_page_metadata` | When a changed function is a registered tool adapter. |
| `skill:<name>#procedure` / `#prose` / `#meta` | `skill:link-validation#procedure` | The machine-readable procedure block vs. instruction prose vs. front matter. |
| `agent:<name>.<field>` | `agent:publishing.triggers`, `agent:seo.tools` | Order-sensitive comparison (intent order matters). |
| `config:<dotted.key>` | `config:runtime.retries` | Effective value changes only. |
| non-semantic edits | `code:…#text`, `config:…#comments` | Flagged `semantic=False`: comments/docstrings/whitespace, YAML comments/ordering. |

### 2.2 Dependency model (declared · observed · required)

- **Declared**: the metadata a test author wrote (`declared:` block in the catalog) — deliberately incomplete, as in practice (shared skills reached through `include`, harness code and most configuration keys are not declared).
- **Observed**: from baseline traces — agents started, agent-definition fields consulted by the orchestrator, skills loaded (with version/digest), tools called (with status and attempts), configuration keys read, executed code functions and lines (coverage.py dynamic contexts, one context per test and repetition).
- **Required**: properties/risk that must always be evaluated (safety tests are marked by `safety_*` properties; a mandatory-set policy is a one-line addition to any strategy).

### 2.3 Cost model

c(t) = agent tokens (prompt + completion over all LLM calls in the delegation chain) + judge tokens (only when a judge runs) ; latency is recorded alongside. In simulated mode tokens are synthesised from the prompt material actually "read" (agent prompt + skills + request/context + growing history), giving a realistic ~10× spread (0.9k–9k tokens per case) and multi-agent runs costing more. Real-LLM runs use the API usage fields.

### 2.4 Outcome model

A test run is PASS / AGENT_FAILURE / HARNESS_ERROR (INFRA_INVALID reserved for environment faults). With K repetitions per variant, the ground truth "t reveals Δ" is a *majority flip*: baseline pass rate ≥ 0.5 and variant pass rate < 0.5. Flakiness f(t) = 1 − baseline pass rate is a first-class input to the selectors.

---

## 3. Methods (strategies implemented in `traceeval/selection/strategies.py`)

| Strategy | Family | Uses | Selects? | Stops? |
|---|---|---|---|---|
| `full` | reference | — | no | no |
| `random` | baseline | seed | no | no |
| `declared` | change-based (classic RTS on metadata) | declared deps, risk | yes | n/a |
| `ir_tfidf` | IR-based TCP (REPiR-style) | diff text vs. test text | no (ranks all) | no |
| `observed` | trace-informed RTS | observed deps incl. executed lines, risk, cost | yes | n/a |
| `observed_diverse` | observed + "additional" greedy breadth | + behaviour signatures | yes | n/a |
| `cost_aware` | handoff formula Risk × ChangeAffinity × FailureHistory / ExpectedTokens | observed deps, flakiness, cost | ranks all (affected first) | no |
| `history_ml` | predictive test selection (Machalica et al.) | logistic model over affinity/cost/risk features trained on other changes (leave-one-change-out) | ranks all | no |
| `adaptive_bayes` | **proposed** | everything above + sequential inference | yes | **yes** |

### 3.1 The proposed method: adaptive Bayesian selection with budget-aware stopping

*Hypotheses.* Each semantic changed component c is "broken" with prior π_c by kind (code/skill/config/agent ≈ 0.45–0.5, prompt wording/prose ≈ 0.12–0.15, provably benign edits 0.02). The posterior is kept exactly over all 2^k subsets B (k ≤ 8 components).

*Likelihood.* P(t fails | B) = 1 − (1 − f_t) ∏_{c∈B} (1 − s_tc). The sensitivity s_tc of test t to component c is
s_tc = r_kind(c) · freq_t(c) · tilt_t, where

- r_kind is the **empirical reveal ratio** learned from the other recorded changes (fraction of statically impacted tests that actually revealed a change of that kind; e.g. "executed the changed line" vs. "executed the changed function only"; agent fields are calibrated per field) — this encodes "coverage does not imply detection" with measured numbers instead of hand-set constants;
- freq_t(c) is how often t exercised c in its baseline runs;
- tilt_t ∈ [0.5, 2.0] combines the lexical relevance of the change text to the test's own text (name, request, expectations) and a bonus when the author declared the dependency — a proxy for "the test's oracle plausibly observes the changed behaviour".

*Policy.* Next test = argmax over t of (expected information gain about B, tilted by risk) / c(t). After a **pass**, the sensitivities of tests sharing the same behaviour signature (agents, tools, fault profile, dataset) are discounted (×0.35): near-duplicate tests are correlated evidence, not independent draws. Flaky tests may be re-run once.

*Stopping.* Stop "clean" when P(any component broken | evidence) < ε_clean (0.05); stop "regression" when a failure has been observed and P(any broken) > 1 − ε_detect; otherwise until the budget is exhausted or no test is informative. Selection, prioritization and stopping fall out of the same model.

### 3.2 Why these baselines

They span the design space the literature covers: classic RTS/TCP on declared coverage (Rothermel), IR-based TCP (Saha 2015), cost-cognizant TCP (Elbaum 2001), predictive test selection (Machalica 2019), and diversity-based ordering (Pan/Briand LTM). CASPER (2026) and Risk-Aware Adaptive Evaluation (2026) are the closest external competitors (`docs/related_work.md`); reproducing them on the testbed is a phase-3 task.

---

## 4. Evaluation environment (the testbed)

### 4.1 System under test — ContentOps

`traceeval/sut`: eight agents (orchestrator, authoring, publishing, assets, seo, translation, governance, maintenance), ten skills, 22 tools over deterministic services (repository with versions, workflow with reviews/scheduling, links, governance with consent and approval tokens, translation, SEO), a harness (configuration with instrumented reads, skill loader with a procedure DSL, keyword router, retry helper with idempotency keys, dispatcher with tool enablement + approval gate + fault injection, runtime loop with delegation and a step budget) and `config/runtime.yaml`.

Deliberate structure: shared components with wide blast radius (`governance-checks` and `link-validation` are included by several skills; `get_page` and `check_permission` are used by every agent; the retry helper wraps every tool call), narrow components (the approval gate matters to one test), policies enforced only in skills (publish permission) vs. also in tools (approval tokens) — so that selection is non-trivial and defence-in-depth questions can be discussed.

**Skills are executable by both backends.** A `SKILL.md` has front matter, prose for the LLM, and a `## Procedure` YAML block the simulated agent executes and the LLM reads verbatim. A mutation of the procedure therefore changes both backends' behaviour at the same place; prose-only mutations affect only the LLM (and are flagged `#prose`).

### 4.2 Eval catalog

70 scenario tests (publishing 20, authoring 14, assets/SEO 15, translation/governance/maintenance/orchestration 21) and two dataset-style evals (40 routing items, prompt → expected delegation, run in route-only mode; 24 intent items, prompt → expected tool invocation). Each case: agent entry point, request, context slots, fixture (+ optional patch), fault profile (`healthy`, `transient_once:<tool>`, `ack_timeout_once:<tool>`, `permanent_down:<tool>`), risk (critical/high/medium/low → severity 4/3/2/1), properties (functional, routing, trajectory, safety_*, resilience_*, efficiency, answer_quality), declared dependencies, expectations (state assertions, required/forbidden tools, attempt counts, audit counts, response substrings, step limits, termination) and, for two cases, a judge rubric.

### 4.3 Controlled changes (35)

| Category | Count | Examples |
|---|---|---|
| code (tool adapters, services, harness) | 8 | argument-mapping bug in `set_page_metadata`; retry drops idempotency keys; retry disabled; approval gate bypass; external links treated as reachable; phrase triggers lose weight; shared `get_page` reports the wrong review flag; edits keep approvals |
| runtime | 2 | termination six steps early; delegation depth zero (catastrophic) |
| skill | 8 | publishing skill drops link validation / permission check; authoring drops metadata; translation hard-codes en-US; rollback restores the latest version; **shared** link-validation tolerates broken assets; governance drops the consent check; SEO drops the title-length guard |
| prompt / agent definition | 3 | publishing loses its "take down" triggers; SEO loses a tool; translation intents re-ordered (order-sensitive YAML) |
| configuration | 7 | validate_links disabled; review not required; step budget 5; retries 0; title limit 20; default agent changed; unpublish removed from the approval list |
| combined | 1 | keyword-count rule in code + very low limit in config (each alone harmless) |
| benign | 6 | prose reflow; comment/docstring edit (AST-equivalent); local-variable renames; config comments/ordering; new unused tool; orchestrator prompt wording |

Testbed sanity property (checked by the report): every regression-inducing change is revealed by ≥ 1 test; no benign change is revealed by any test. Revealing-set sizes range from 1 to 107 tests.

### 4.4 Protocol and metrics

1. `baseline`: full suite × K with coverage contexts → observed dependencies, cost, flakiness.
2. `mutants`: per change: copy SUT, apply edit, extract change set, full suite × K → fault matrix.
3. `evaluate`: for every (change, strategy, budget ∈ {2,5,10,20,30,50,100}% of full-suite tokens, seed): the strategy selects from baseline facts + change set only; executions are answered from the recorded runs of that variant (random repetition → outcome and cost). Adaptive strategies interact sequentially.
4. Metrics: detection (≥ 1 revealing test executed and failed), recall of revealing tests, tokens actually spent, cost to first detection, false alarms, safety recall, stop reason and stop correctness; APFD and APFD_c of the complete prioritized order; selection recall and selected-subset cost.

---

## 5. First results (simulated backend, `runs/exp1`: 134 cases × 3 reps baseline, 35 variants × 3 reps, 10 replay seeds; 472k tokens per full-suite run)

Detection rate of regression-inducing changes (29) vs. nominal budget, and tokens actually spent:

| strategy | 5% | 10% | 20% | 50% | 100% | spent @20% | spent @100% | waste on benign @100% |
|---|---|---|---|---|---|---|---|---|
| full (catalog order) | 0.14 | 0.31 | 0.52 | 0.79 | 1.00 | 0.20 | 0.97 | 1.00 |
| random | 0.21 | 0.34 | 0.54 | 0.83 | 1.00 | 0.20 | 0.97 | 1.00 |
| declared | 0.59 | 0.62 | 0.62 | 0.66 | **0.66** | 0.06 | 0.09 | 0.09 |
| ir_tfidf | 0.93 | 0.97 | 0.97 | 1.00 | 1.00 | 0.20 | 0.97 | 0.99 |
| observed | 0.62 | 0.69 | 0.90 | 0.97 | 1.00 | 0.16 | 0.49 | 0.22 |
| cost_aware | 0.66 | 0.69 | 0.90 | 0.97 | 1.00 | 0.20 | 0.97 | 0.99 |
| adaptive_bayes | 0.62 | 0.83 | 0.86 | 0.86 | 0.86 | **0.11** | **0.26** | **0.36** |

Two optional baselines (`observed_diverse`, `history_ml`; `--strategies all`) land between `observed` and `cost_aware` on every metric. APFD / APFD_c of the full prioritized order: full 0.68/0.58, random 0.54/0.54, declared 0.81/0.77 (selection recall 0.53), ir_tfidf 0.83/0.83, observed 0.80/0.83 (selection recall 1.00 at 52% of the suite cost), observed_diverse 0.82/0.79, cost_aware 0.81/0.84, history_ml 0.79/0.81, adaptive_bayes 0.81/0.79. Cost to first detection: declared 0.02, ir 0.02, adaptive 0.03, observed/cost_aware 0.05, random 0.15 of the full suite.

**Reading.**
- *RQ1/RQ2.* Declared metadata caps detection at 66% because shared skills reached through `include`, harness code (retry, dispatcher, runtime loop) and configuration keys are not declared; observed dependencies recover full selection recall and reach 90% detection at 20% of the cost. This is the central quantitative argument for trace-informed selection.
- *RQ3.* All informed strategies roughly double random's APFD_c; cost-aware ranking gives the best APFD_c.
- *RQ4.* Only the adaptive method returns budget: 86% detection for 11–26% of the cost, 36% on benign changes. On the six benign changes it stopped "clean" in 220 and "nothing informative left" in 20 of the 240 replays that were not budget-limited, and it raised **no false regression alarm** in any replay. The four changes it never detects (termination off-by-six, translation-intent reorder, authoring metadata step, shared link-validation asset rule) are all cases where one to three tests among dozens of covering ones reveal the change: the calibrated sensitivities and the near-duplicate discount make the posterior clear before those tests are reached — the honest limit of coverage-based evidence, to be addressed by learned sensitivities at test level and a stronger IR term (§7). Conversely, a behaviour-preserving edit inside a widely used function (`benign_code_rename_locals`) is never declared clean: with calibrated sensitivities the model (correctly) does not believe that passing covering tests prove such an edit harmless, and the budget cap decides.
- *A finding to take seriously:* IR/TF-IDF over the diff is the strongest prioritizer on this testbed (93% at 5%). Test names, requests and declared tool names share vocabulary with the edited artefacts (skill procedures mention tool names; config keys appear in diffs). Agent test suites are unusually "textual", which makes IR a serious baseline — and a signal to fold into the Bayesian model more strongly than the current lexical tilt. Whether this holds on tau2-bench (policy text vs. task descriptions) is one of the first external-validity questions.

**Nondeterministic condition** (`runs/exp2_flaky`: simulated agent with a 5% slot-slip rate, 5 reps per variant, 19 of 134 tests flaky at baseline). The majority-flip ground truth stays clean (sanity check OK), detection curves are within ±4 points of the deterministic condition for every strategy (adaptive 0.69/0.83/0.86 at 5/10/20%; observed 0.62/0.69/0.90; ir 0.90/0.97/0.97), and the difference between families shows where it matters: strategies without an outcome model observe at least one spurious failure in 40–69% of replays (full 0.69, cost_aware 0.61, history_ml 0.58, random 0.52, ir 0.44, observed 0.40) — in practice a false "regression" alert each time — whereas the Bayesian selector, which carries each test's baseline flakiness in its likelihood and re-runs flaky tests once, observes one in 8% of replays and **never stops with a "regression" verdict on a benign change** (0 of 420). This is the nondeterminism argument of the requirements document made quantitative.

---

## 6. Second system under test and the real-LLM mode

- **ContentOps + LLM backend** (implemented, tested against a scripted client): set `TRACEEVAL_LLM_BASE_URL/API_KEY/MODEL` to the local vLLM endpoint (Muse Glimmer 30B per the setup notes) and run `traceeval baseline/mutants --backend llm`. Expected cost per case: 2–8k tokens × delegation; a 35-variant × 3-rep recording is ≈ 134 × 36 × 3 ≈ 14.5k runs ≈ 60–100M tokens — free on the DGX, several hours of wall-clock with batching. Start with 10 variants.
- **tau2-bench** (verified facts and adapter design in `docs/tau2_integration.md`): airline domain first (50 tasks, DB + communicate reward, no NL judge), agent and user simulator on the local vLLM via `--agent-llm openai/<model> --agent-llm-args '{"api_base": ..., "api_key": "EMPTY"}'` (and the same for `--user-llm`), `TAU2_DATA_DIR` pointed at a mutated copy of `data/` for policy mutations, a mutated checkout for tool-code mutations, change sets from `git diff`, outcomes/tokens parsed from `results.json` into the same history format. The replay evaluator and all strategies then run unchanged. Expect large per-simulation token counts (tens of thousands) and pass^k well below 1 — exactly the nondeterministic regime the method must handle.

---

## 7. Roadmap

| Phase | Deliverable | Status |
|---|---|---|
| 1. Testbed | SUT, catalog, tracing, mutations, change sets, record/replay, metrics, report, CLI, tests | **done (v0.1)** |
| 2. Methods | baselines + cost-aware + predictive + adaptive Bayesian selector with stopping | **done (v0.1)**; tune ε, priors, discount; add a mandatory-safety policy wrapper |
| 3. Method improvements | (a) test-level learned sensitivities (per test × component-kind reveal history) instead of kind-level; (b) IR relevance inside the Bayesian likelihood; (c) joint allocation of repetitions for flaky tests (sequential testing with anytime-valid stopping, FAQ-style); (d) CASPER-style slices and the Risk-Aware Adaptive Evaluation bandit as reproduced baselines | next |
| 4. Real LLM | ContentOps with local vLLM: baseline + 10–15 variants × 3 reps; compare the simulated and LLM fault matrices (does the simulated backend predict which tests reveal a change?) | next, needs the DGX |
| 5. External SUT | tau2-bench airline adapter; 12 mutations (6 policy, 4 tool-code, 2 benign); same evaluation | after phase 4 |
| 6. Scale/robustness | more mutations (mutation operators generated systematically: step deletion/swap/condition negation in procedures, argument swaps in adapters, config boundary values), equivalent-mutant analysis, sensitivity to K and to budget definitions (time vs. tokens), ablations of each model ingredient | with the paper |
| 7. Paper | see §8 | drafting can start from this document and the report |

Immediate next steps (in order): run `runs/exp2_flaky`'s report and compare; implement the mandatory-safety wrapper and the test-level sensitivity learning; run the LLM-backend baseline on the DGX for the whole catalog once (cost + fault-matrix comparison with the simulated mode is the first "is the simulation realistic?" result).

---

## 8. Paper plan

**Working title.** TRACE-Eval: change-aware, cost-bounded regression test selection for LLM agent systems.

**Abstract (draft).** Agent platforms ship dozens of agents assembled from skills, prompts, tools, harness code and configuration, and verify them with tests and statistical evals whose cost is dominated by tokens. After a change, teams either re-run everything or guess. We formulate selection, prioritization and budget-aware stopping of agent tests as one problem and propose a method that (i) extracts a change set from the diff at the granularity of code lines, skill procedures, agent-definition fields and configuration keys, (ii) maps it to tests through dependencies *observed* in execution traces rather than declared metadata, (iii) ranks tests by expected information per token in a Bayesian model whose sensitivities are calibrated from history, and (iv) stops when the posterior probability of a regression is low. We evaluate on a testbed with a real multi-agent application, 134 tests/eval items, and 35 controlled changes with mutation-based ground truth, under simulated and LLM-driven agents. Trace-informed selection recovers the 34% of regressions invisible to declared dependencies; the adaptive method detects 86% of regressions for 11–26% of the full-suite tokens and returns most of the budget on benign changes.

**Outline.** 1 Introduction (motivation from AEM-scale platforms; nightly batch + PR use; three sub-problems) · 2 Background and related work (RTS/TCP; efficient LLM evaluation; agent benchmarks; fault injection; CASPER as closest work) · 3 Problem formulation and models (§1–2) · 4 Method (§3.1) · 5 Testbed (§4) · 6 Evaluation (RQ1–RQ4 + ablations + LLM/tau2 external validity) · 7 Threats to validity (synthetic mutants vs. real regressions; simulated agent realism; single primary domain; calibration leakage controlled by leave-one-change-out; textual testbed favouring IR) · 8 Conclusion.

**Venues.** ASE / ISSTA / ICST (SE framing: RTS/TCP for LLM-based systems, mutation-based ground truth, APFD_c). Alternative: NeurIPS D&B / EMNLP with the testbed as the headline ("a benchmark for regression test selection in agent systems").

---

## 9. Questions still to settle with Georgiana (made concrete)

1. Change identification: is the diff available per PR/nightly batch, and does the platform keep skill/prompt/config under version control together with harness code? (The change-set extractor assumes files in one tree.)
2. Dependency registry: is there a mapping agent → skills/tools/config, and are traces (tool calls, skills loaded, config reads) retained for the nightly runs? (Observed dependencies need ≥ 1 baseline run per test with tracing.)
3. Eval datasets: can items be run individually and attributed costs? (Our dataset items are selectable units; the routing dataset is run in route-only mode.)
4. Oracles: which properties are deterministic vs. judged; which are release blockers (safety set)?
5. Budgets: tokens, time or both; per PR vs. nightly; is a partial run with an explicit "clean with probability p" statement acceptable to the team (this is what the stopping rule outputs)?
6. Nondeterminism: how many repetitions per test are run today; is pass^k reported?

---

*Repository: `trace-eval/` (README for commands). Inputs synthesized: Agent_Test_Prioritization_Requirements.md; Agent Test Prioritization Prototype.docx; agent_test_prioritization_summary.md; TRACE-Eval_Pi_Harness_Handoff.md; muse-glimmer-local-setup-and-agent-workflows.md.*
