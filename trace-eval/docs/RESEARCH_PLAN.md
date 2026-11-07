# TRACE-Eval — Research and implementation plan

**Change-aware, cost-bounded selection, prioritization and stopping of tests and evals for LLM agent systems**

Ciprian Păduraru · University of Bucharest · working document, 6 October 2026 · status: prototype v0.1 running, first results in `docs/results/exp1/report.md`

---

## TL;DR

- **Problem.** After a change to an agent system, decide which tests and eval items to run, in what order, and
  when to stop, under a token budget and without missing regressions.
- **Method.** Map the diff to components (code lines and functions, skill procedures, agent fields, config keys)
  and match them to tests through the dependencies observed in traces. Rank tests by expected information per
  token in a Bayesian model whose sensitivities are calibrated from history, and stop when the probability of a
  regression is low. The method is `adaptive_bayes`; six baselines run alongside it.
- **Testbed.** A small multi-agent app (`traceeval/sut`) with 136 tests and 38 controlled changes applied as file
  edits (6 of them benign). Full-suite runs give the ground truth, and strategies are compared by offline replay.
- **Results so far (simulated agent).** Hand-written dependencies catch 66% of regressions. Trace-based selection
  catches 91% within a budget of 20% of the full-suite tokens. The adaptive method catches 84% while spending
  5–7% of those tokens, and never calls a benign change a regression. Under 5% agent flakiness it still never does,
  while the other strategies see at least one failure the change did not cause in 18–65% of replays. TF-IDF over the diff is a strong baseline (84%
  at 5%). Change sets hold code only, so the results are the same whether or not the code is commented.
- **Next.** Calibrate sensitivities per test rather than per kind, fold the IR signal into the model, run the LLM
  backend on the DGX, then move to tau2-bench as the external system under test. Paper: ASE/ISSTA/ICST framing.

---

## 0. What this document is

This plan merges five earlier inputs into one research design and one runnable testbed: the requirements captured from the July 2026 discussion with Georgiana (Adobe, AEM agent platform), the state-of-the-art report with APFD/APFD_c and reliability metrics, the OpenTelemetry-based prioritization sketch, the TRACE-Eval/Pi handoff, and the local Muse Glimmer/vLLM setup notes. Where the inputs disagreed, the decisions below say which way we went and why. The research problem is kept general (any agent platform built from skills, prompts, tools, harness code and configuration); AEM is the motivating instance, not a dependency.

**Decisions taken in this iteration**

| Topic | Decision | Reason |
|---|---|---|
| System under test (SUT) | A purpose-built mini content-operations platform ("ContentOps": pages, assets, publishing, SEO, translation, governance, rollback) is the primary SUT. tau2-bench, with the local vLLM model as both agent and user simulator, is the second SUT (designed, not yet implemented; see `docs/tau2_integration.md`). | The primary SUT gives a free, deterministic simulated mode to develop and evaluate selection methods now, a multi-agent structure with shared components built in on purpose (the hard case Georgiana described), and full control over mutations. tau2-bench adds external validity with a real LLM. |
| Agent runtime | Pure Python harness with an OpenAI-compatible LLM backend; Pi is not used in the prototype. | Shortest path. The harness code must itself be mutable and instrumentable (coverage contexts). A Pi adapter remains possible later. |
| Observability | Own trace recorder with an OpenTelemetry-compatible event model (agent/skill/tool/config/llm spans) rather than Phoenix/OpenInference as a dependency. | No services in the loop; an OTel exporter is a small addition. |
| Oracles | Deterministic (final state, tool trajectories, audit log, response substrings); an LLM judge only for explicitly marked answer-quality properties, executed after deterministic checks pass, simulated in the free mode. | Regression tracking must not depend on judge noise (docx report §"LLM-as-a-judge bottleneck"). |
| Ground truth | Mutation analysis: 38 controlled changes, benign ones included, applied as file edits. The selectors see only the diff. | Needed to measure detection rate against a known answer, and to measure wasted budget. |
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

c(t) = agent tokens (prompt + completion over all LLM calls in the delegation chain) + judge tokens (only when a judge runs). Latency is recorded alongside. In simulated mode, tokens are synthesised from the prompt material the agent actually "reads" (agent prompt + skills + request/context + growing history). This gives a realistic ~10× spread (0.9k–9k tokens per case), and multi-agent runs cost more. Real-LLM runs use the API usage fields.

### 2.4 Outcome model

A test run is PASS / TOOL_ERROR (a tool crashed, or failed in a way the case does not allow) / AGENT_FAILURE / HARNESS_ERROR (INFRA_INVALID is reserved for environment faults). Only pass/fail enters the ground truth. With K repetitions per variant, the ground truth "t reveals Δ" is a *majority flip*: baseline pass rate ≥ 0.5 and variant pass rate < 0.5. Flakiness f(t) = 1 − baseline pass rate is a direct input to the selectors.

---

## 3. Methods (strategies implemented in `traceeval/selection/`)

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
| `adaptive_bayes` | **proposed** | everything above + sequential inference | yes | yes |

### 3.1 The proposed method: adaptive Bayesian selection with budget-aware stopping

*Hypotheses.* Each changed component c is "broken" with prior π_c by kind (code/skill/config/agent ≈ 0.45–0.5, prompt wording/prose ≈ 0.12–0.15). The posterior is kept exactly over all 2^k subsets B (k ≤ 8 components).

*Likelihood.* P(t fails | B) = 1 − (1 − f_t) ∏_{c∈B} (1 − s_tc). The sensitivity s_tc of test t to component c is
s_tc = r_kind(c) · freq_t(c) · tilt_t, where

- r_kind is the empirical reveal ratio learned from the other recorded changes: the fraction of statically impacted tests that actually revealed a change of that kind. Kinds separate, for example, "executed the changed line" from "executed only the changed function", and agent fields are calibrated per field. This encodes "coverage does not imply detection" with measured numbers instead of hand-set constants.
- freq_t(c) is how often t exercised c in its baseline runs.
- tilt_t ∈ [0.5, 2.0] combines the lexical relevance of the change text (code only, never comments) to the test's own text (name, request, expectations) with a bonus when the author declared the dependency. It is a proxy for "the test's oracle plausibly observes the changed behaviour".

*Policy.* The next test is the argmax over t of (expected information gain about B, tilted by risk) / c(t). After a pass, the sensitivities of tests with the same behaviour signature (agents, tools, fault profile, dataset) are discounted (×0.35), because near-duplicate tests are correlated evidence, not independent draws. Flaky tests may be re-run once.

*Stopping.* The method stops "clean" when P(any component broken | evidence) < ε_clean (0.05), and stops "regression" when a failure has been observed and P(any broken) > 1 − ε_detect. Otherwise it runs until the budget is exhausted or no test is informative. A failure that does not reach 1 − ε_detect on its own is confirmed first: the same test runs once more before any other, because flakiness rarely fails a test twice in a row and a broken component does. Selection, prioritization and stopping all come from the same model.

### 3.2 Why these baselines

They cover the design space of the literature: classic RTS/TCP on declared coverage (Rothermel), IR-based TCP (Saha 2015), cost-cognizant TCP (Elbaum 2001), predictive test selection (Machalica 2019) and diversity-based ordering (Pan/Briand LTM). CASPER (2026) and Risk-Aware Adaptive Evaluation (2026) are the closest external competitors (`docs/related_work.md`). Reproducing them on the testbed is a phase-3 task.

---

## 4. Evaluation environment (the testbed)

### 4.1 System under test — ContentOps

`traceeval/sut` contains eight agents (orchestrator, authoring, publishing, assets, seo, translation, governance, maintenance), ten skills, 24 tools over deterministic services (repository with versions, workflow with reviews/scheduling, links, governance with consent and approval tokens, translation, SEO), a harness (configuration with instrumented reads, skill loader with a procedure DSL, keyword router, retry helper with idempotency keys, dispatcher with tool enablement + approval gate + fault injection, runtime loop with delegation and a step budget) and `config/runtime.yaml`.

The structure is deliberate, so that selection is hard and defence-in-depth questions can be discussed. Some components are shared and have a wide blast radius: `governance-checks` and `link-validation` are included by several skills, `check_permission` is available to every specialist agent and `get_page` to all but the governance agent, and the retry helper wraps every tool call. Others are narrow: the approval gate matters to one test. Some policies are enforced only in skills (publish permission), others also in tools (approval tokens).

Skills are executable by both backends. A `SKILL.md` has front matter, prose for the LLM, and a `## Procedure` YAML block that the simulated agent executes and the LLM reads as numbered steps (included skills written out in place, settings shown with their current values). A mutation of the procedure therefore changes both backends' behaviour at the same place. Prose-only mutations affect only the LLM and are flagged `#prose`.

### 4.2 Eval catalog

72 scenario tests (publishing 21, authoring 14, assets/SEO 16, translation/governance/maintenance/orchestration 21) and two dataset-style evals (40 routing items, prompt → expected delegation, run in route-only mode; 24 intent items, prompt → expected tool invocation). Each case defines an agent entry point, request, context slots, fixture (+ optional patch), fault profile (`healthy`, `transient_once:<tool>`, `ack_timeout_once:<tool>`, `permanent_down:<tool>`), risk (critical/high/medium/low → severity 4/3/2/1), properties (functional, routing, trajectory, safety_*, resilience_*, efficiency, answer_quality), declared dependencies, expectations (state assertions, required/forbidden tools, attempt counts, audit counts, response substrings, step limits, termination) and, for two cases, a judge rubric.

### 4.3 Controlled changes (38)

| Category | Count | Examples |
|---|---|---|
| code (tool adapters, services, harness) | 9 | argument-mapping bug in `set_page_metadata`; retry drops idempotency keys; retry disabled; approval gate bypass; external links treated as reachable; shared `get_page` reports the wrong review flag; edits keep approvals; `set_page_metadata` crashes when no keywords are given; link validation crashes on an unknown external URL |
| runtime | 3 | termination six steps early; delegation depth zero (breaks most of the suite); the delegated answer cut to 40 characters |
| skill | 9 | publishing skill drops link validation / permission check; authoring drops metadata; translation hard-codes en-US; rollback drops its permission check (the service still refuses); rollback restores the latest version; shared link-validation tolerates broken assets; governance drops the consent check; SEO drops the title-length guard |
| prompt / agent definition | 2 | SEO loses a tool; governance loses `check_consent` |
| configuration | 7 | validate_links disabled; review not required; step budget 5; retries 0; title limit 20; default agent changed; unpublish removed from the approval list |
| combined | 1 | keyword-count rule in code + very low limit in config (each alone harmless) |
| benign | 7 | prose reflow; comment/docstring edit (AST-equivalent); local-variable renames; config comments/ordering; new unused tool; orchestrator prompt wording; translation intents re-ordered |

This is the set as revised for real models (phase 4 in `docs/EXPERIMENT.md`): two changes that only the
simulator could see were replaced, one became benign, and the skill changes also edit the prose that
repeated the removed step. The simulated results in §5 used the earlier set.

The report checks a sanity property of the testbed: every regression-inducing change is revealed by ≥ 1 test, and no benign change is revealed by any test. Revealing-set sizes range from 1 to 109 tests.

### 4.4 Protocol and metrics

1. `baseline`: full suite × K with coverage contexts, giving observed dependencies, cost and flakiness.
2. `mutants`: for each change, copy the SUT, apply the edit, extract the change set and run the full suite × K, giving the fault matrix.
3. `evaluate`: for every (change, strategy, budget ∈ {2,5,10,20,30,50,100}% of full-suite tokens, seed), the strategy selects from the baseline facts and the change set only. Each execution is answered from the recorded runs of that variant (a random repetition supplies the outcome and cost). Adaptive strategies interact sequentially.
4. Metrics: detection (≥ 1 revealing test executed and failed), recall of revealing tests, tokens actually spent, cost to first detection, false alarms, safety recall, stop reason and stop correctness; APFD and APFD_c of the complete prioritized order; selection recall and selected-subset cost.

---

## 5. First results (simulated backend, `runs/exp1`: 136 cases × 3 reps baseline, 38 variants × 3 reps, 10 replay seeds; 483k tokens per full-suite run)

Re-run on 2026-11-04 with the tool-error oracle (tests also fail on unexpected tool errors and on tool crashes, classified TOOL_ERROR: 225 of the 807 failing variant runs) and two crash mutations, each revealed by one new test. The stricter oracle alone adds revealing tests to four changes (both retry changes 4→8, `config_disable_validate_links` 32→42, `skill_governance_drop_consent` 4→5).

Re-run again with code-only change sets (§2.1), so comments, docstrings, blank lines and formatting no longer reach any strategy. The SUT has since been commented throughout, and the replays are identical with and without those comments (23,310 of 23,310 rows). In the previous run, which still read the few comments the code then had, comments decided the outcome of two changes for the adaptive method. The trailing comment on the config line of `config_max_tool_calls_5` ("hard step budget per request (all agents in the delegation chain)") shared a word with all 136 tests, so every passing test counted as evidence and the change was never found. It is now found from the 20% budget. In the other direction, the comment on the changed line of `code_router_phrase_weight` ("multi-word trigger matched as a phrase") was its only lexical link to the routing tests, and without it the change is no longer found. IR/TF-IDF loses 3–6 points at the 2–10% budgets.

Re-run on 2026-11-06 after the `rollback_page` service started checking the `rollback` permission itself, with a new mutation that drops the rollback skill's own check (`skill_rollback_drop_permission_check`). Because the service still refuses, the data stays safe and the mistake shows only in behaviour: MNT-03 sees a forbidden call to `rollback_page` and an undeclared `permission_denied` error. It is the counterpart of `skill_publish_drop_permission_check`, where nothing below the skill stops the write. Its one revealing test is declared, so every strategy except `full` and `random` finds it at the 2% budget, and the averages below move by about a point because the set has one more easy regression. A control run of the previous code in the same environment reproduces the archived report exactly.

Re-run again on 2026-11-06 after the adaptive method started confirming failures (§3.1). Before that, a single failure could leave P(any broken) just under 1 − ε_detect, and the passes that followed wore it down: under the model, each passing test that covers the component says "had the component been broken, I would probably have failed too". The method then ran on to the end of its budget. On `skill_rollback_drop_permission_check`, MNT-03's failure left P = 0.980 and the method went on to spend 93% of the suite. Re-running MNT-03 raises P to 0.9996, and the method stops there. Detection is unchanged at every budget in both conditions. Tokens spent on regressions at full budget fall from 29% to 7% of the suite (from 28% to 8% under flakiness). The "regression" verdict on regressions rises from 940 to 1550 of the 2240 replays, and still no benign change gets one.

Detection rate of regression-inducing changes (32) vs. nominal budget, and tokens actually spent:

| strategy | 5% | 10% | 20% | 50% | 100% | spent @20% | spent @100% | waste on benign @100% |
|---|---|---|---|---|---|---|---|---|
| full (catalog order) | 0.12 | 0.28 | 0.50 | 0.75 | 1.00 | 0.20 | 0.97 | 1.00 |
| random | 0.22 | 0.38 | 0.56 | 0.82 | 1.00 | 0.20 | 0.97 | 0.99 |
| declared | 0.56 | 0.66 | 0.66 | 0.66 | 0.66 | 0.06 | 0.09 | 0.09 |
| ir_tfidf | 0.84 | 0.94 | 0.97 | 1.00 | 1.00 | 0.20 | 0.97 | 0.99 |
| observed | 0.66 | 0.78 | 0.91 | 0.97 | 1.00 | 0.16 | 0.46 | 0.22 |
| cost_aware | 0.66 | 0.78 | 0.91 | 0.97 | 1.00 | 0.20 | 0.97 | 0.99 |
| adaptive_bayes | 0.69 | 0.81 | 0.84 | 0.84 | 0.84 | 0.05 | 0.07 | 0.34 |

Two optional baselines (`observed_diverse` and `history_ml`, run with `--strategies all`) stay within ±0.16 of `observed` at every budget. APFD / APFD_c of the full prioritized order: full 0.67/0.57, random 0.49/0.50, declared 0.81/0.76 (selection recall 0.52), ir_tfidf 0.81/0.83, observed 0.82/0.85 (selection recall 1.00 at 49% of the suite cost), observed_diverse 0.83/0.80, cost_aware 0.82/0.85, history_ml 0.81/0.83, adaptive_bayes 0.81/0.79. Cost to first detection: declared 0.024, adaptive 0.025, ir 0.026, cost_aware 0.044, observed 0.045, random 0.144 of the full suite.

**Reading.**
- *RQ1/RQ2.* Declared metadata caps detection at 66% because shared skills reached through `include`, harness code (retry, dispatcher, runtime loop) and configuration keys are not declared. Observed dependencies recover full selection recall and reach 91% detection within a 20% budget. This gap is the main argument for trace-informed selection.
- *RQ3.* Informed strategies raise APFD_c from 0.50 (random) to 0.76–0.85; cost-aware ranking gives the best APFD_c.
- *RQ4.* Only the adaptive method returns budget: it detects 84% for 5–7% of the cost and spends 34% on benign changes. On a regression it usually stops at the first confirmed failure, with a "regression" verdict in 1550 of the 2240 replays. Of the 241 replays on the six benign changes that were not budget-limited, it stopped "clean" in 90, had nothing to test in 140 (the two comment- and format-only changes leave an empty change set) and found "nothing informative left" in 11. It raised no false regression alarm in any replay. The two crash mutations (one revealing test each) are found from 2% (metadata crash) and from 10% (links-service crash, which `declared` never finds). In all five changes it never detects (router phrase weight, termination off-by-six, translation-intent reorder, authoring metadata step, shared link-validation asset rule), one to three tests among dozens of covering ones reveal the change. The calibrated sensitivities and the near-duplicate discount make the posterior clear before those tests are reached. This is the limit of coverage-based evidence; learned sensitivities at test level and a stronger IR term (§7) are meant to address it. A behaviour-preserving edit inside a widely used function (`benign_code_rename_locals`) is declared clean only at full budget, after 82% of the suite (64% while its diff still carried comment words, which raised the lexical tilt of the covering tests). With calibrated sensitivities, the model rightly does not take a few passing covering tests as proof that such an edit is harmless, and below full budget the budget cap decides.
- *IR.* IR/TF-IDF over the diff is the strongest prioritizer on this testbed (84% at 5%, 94% at 10%). Test names, requests and declared tool names share vocabulary with the edited artefacts: skill procedures mention tool names, and config keys appear in diffs. Agent test suites are unusually "textual", which makes IR a strong baseline and a signal to fold into the Bayesian model more strongly than the current lexical tilt does. Whether this holds on tau2-bench (policy text vs. task descriptions) is one of the first external-validity questions.

**Nondeterministic condition** (`runs/exp2_flaky`: simulated agent with a 5% slot-slip rate, 5 reps per variant, 21 of 136 tests flaky at baseline; slips are seeded per test and repetition, so the run is reproducible). The majority-flip ground truth stays clean (sanity check OK), and detection stays close to the deterministic condition: within ±3 points at every budget for full, random, declared, ir and observed, within −8/+3 for cost_aware and within −7/+4 for the optional baselines (observed 0.66/0.75/0.92 at 5/10/20%; ir 0.84/0.94/0.97). The adaptive method does as well or better here from 5% up (0.72/0.84/0.84, and 0.88 from 30%) because it misses different changes: `code_get_page_review_flag`, `code_router_phrase_weight`, `code_termination_off_by_six` and `skill_linkval_ignore_assets`. The strategy families differ in how they handle failures the change did not cause (a failing test outside the change's revealing set, counted over all changes and every budget). Strategies without an outcome model see at least one such failure in 42–65% of replays (cost_aware 0.65, history_ml 0.65, random 0.59, full 0.58, ir 0.52, observed 0.42; declared, which runs few tests, 0.18), and in practice each one is a false "regression" alert. The Bayesian selector carries each test's baseline flakiness in its likelihood and re-runs a failing test before believing it. It sees such a failure in 3% of replays (8% on the benign changes alone, where it runs longest) and never stops with a "regression" verdict on a benign change (0 of 420). This measures the nondeterminism concern raised in the requirements document.

---

## 6. Second system under test and the real-LLM mode

- **ContentOps + LLM backend** (implemented, tested against a scripted client): set `TRACEEVAL_LLM_BASE_URL/API_KEY/MODEL` to the local vLLM endpoint (Muse Glimmer 30B per the setup notes) and run `traceeval baseline/mutants --backend llm`. Expected cost per case: 2–8k tokens × delegation. A 38-variant × 3-rep recording is ≈ 136 × 39 × 3 ≈ 15.9k runs, or ≈ 60–100M tokens: free on the DGX, and several hours of wall-clock time with batching. Start with 10 variants.
- **tau2-bench** (verified facts and adapter design in `docs/tau2_integration.md`): airline domain first (50 tasks, DB + communicate reward, no NL judge), agent and user simulator on the local vLLM via `--agent-llm openai/<model> --agent-llm-args '{"api_base": ..., "api_key": "EMPTY"}'` (and the same for `--user-llm`), `TAU2_DATA_DIR` pointed at a mutated copy of `data/` for policy mutations, a mutated checkout for tool-code mutations, change sets from `git diff`, outcomes/tokens parsed from `results.json` into the same history format. The replay evaluator and all strategies then run unchanged. Expect large per-simulation token counts (tens of thousands) and pass^k well below 1, which is the nondeterministic regime the method must handle.

---

## 7. Roadmap

| Phase | Deliverable | Status |
|---|---|---|
| 1. Testbed | SUT, catalog, tracing, mutations, change sets, record/replay, metrics, report, CLI, tests | done (v0.1) |
| 2. Methods | baselines + cost-aware + predictive + adaptive Bayesian selector with stopping | done (v0.1); tune ε, priors, discount; add a mandatory-safety policy wrapper |
| 3. Method improvements | (a) test-level learned sensitivities (per test × component-kind reveal history) instead of kind-level; (b) IR relevance inside the Bayesian likelihood; (c) joint allocation of repetitions for flaky tests (sequential testing with anytime-valid stopping, FAQ-style); (d) CASPER-style slices and the Risk-Aware Adaptive Evaluation bandit as reproduced baselines | next |
| 4. Real LLM | ContentOps with local vLLM: baseline + 10–15 variants × 3 reps; compare the simulated and LLM fault matrices (does the simulated backend predict which tests reveal a change?) | next, needs the DGX |
| 5. External SUT | tau2-bench airline adapter; 12 mutations (6 policy, 4 tool-code, 2 benign); same evaluation | after phase 4 |
| 6. Scale/robustness | more mutations (mutation operators generated systematically: step deletion/swap/condition negation in procedures, argument swaps in adapters, config boundary values), equivalent-mutant analysis, sensitivity to K and to budget definitions (time vs. tokens), ablations of each model ingredient | with the paper |
| 7. Paper | see §8 | drafting can start from this document and the report |

Immediate next steps, in order: implement the mandatory-safety wrapper and test-level sensitivity learning; run the LLM-backend baseline once on the DGX for the whole catalog. Comparing its cost and fault matrix with the simulated mode gives the first answer to "is the simulation realistic?".

---

## 8. Paper plan

**Working title.** TRACE-Eval: change-aware, cost-bounded regression test selection for LLM agent systems.

**Abstract (draft).** Agent platforms ship dozens of agents assembled from skills, prompts, tools, harness code and configuration, and verify them with tests and statistical evals whose cost is dominated by tokens. After a change, teams either re-run everything or guess. We formulate selection, prioritization and budget-aware stopping of agent tests as one problem and propose a method that (i) extracts a change set from the diff at the granularity of code lines, skill procedures, agent-definition fields and configuration keys, (ii) maps it to tests through dependencies *observed* in execution traces rather than declared metadata, (iii) ranks tests by expected information per token in a Bayesian model whose sensitivities are calibrated from history, and (iv) stops when the posterior probability of a regression is low. We evaluate on a testbed with a working multi-agent application, 136 tests/eval items, and 38 controlled changes with mutation-based ground truth, with a simulated agent that follows the skills; runs with LLM-driven agents are planned. Trace-informed selection recovers the 34% of regressions invisible to declared dependencies. The adaptive method detects 84% of regressions for 5–7% of the full-suite tokens and returns most of the budget on benign changes.

**Outline.** 1 Introduction (motivation from AEM-scale platforms; nightly batch + PR use; three sub-problems) · 2 Background and related work (RTS/TCP; efficient LLM evaluation; agent benchmarks; fault injection; CASPER as closest work) · 3 Problem formulation and models (§1–2) · 4 Method (§3.1) · 5 Testbed (§4) · 6 Evaluation (RQ1–RQ4 + ablations + LLM/tau2 external validity) · 7 Threats to validity (synthetic mutants vs. real regressions; simulated agent realism; single primary domain; calibration leakage controlled by leave-one-change-out; textual testbed favouring IR) · 8 Conclusion.

**Venues.** ASE / ISSTA / ICST (SE framing: RTS/TCP for LLM-based systems, mutation-based ground truth, APFD_c). Alternative: NeurIPS D&B / EMNLP with the testbed as the headline ("a benchmark for regression test selection in agent systems").

---

## 9. Questions still to settle with Georgiana

1. Change identification: is the diff available per PR/nightly batch, and does the platform keep skill/prompt/config under version control together with harness code? (The change-set extractor assumes files in one tree.)
2. Dependency registry: is there a mapping agent → skills/tools/config, and are traces (tool calls, skills loaded, config reads) retained for the nightly runs? (Observed dependencies need ≥ 1 baseline run per test with tracing.)
3. Eval datasets: can items be run individually and attributed costs? (Our dataset items are selectable units; the routing dataset is run in route-only mode.)
4. Oracles: which properties are deterministic vs. judged; which are release blockers (safety set)?
5. Budgets: tokens, time or both; per PR vs. nightly; is a partial run with an explicit "clean with probability p" statement acceptable to the team (this is what the stopping rule outputs)?
6. Nondeterminism: how many repetitions per test are run today; is pass^k reported?

---

*Repository: `trace-eval/` (README for commands). Inputs synthesized: Agent_Test_Prioritization_Requirements.md; Agent Test Prioritization Prototype.docx; agent_test_prioritization_summary.md; TRACE-Eval_Pi_Harness_Handoff.md; muse-glimmer-local-setup-and-agent-workflows.md.*
