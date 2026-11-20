# Related work and positioning

Work related to TRACE-Eval, grouped by topic, from surveys of arXiv, ACM, IEEE and GitHub in October and November
2026. Each entry says what the work does and how it relates to this project. Entries marked *not yet read* were
found by search, but their full text has not been checked; they should be read before they are cited. The entries
of §8, on replaying recorded answers, were read at their sources unless marked *metadata only*.

## 1. Test selection / prioritization for LLM applications and agents

- **CASPER: Change-Aware Slice Prioritization for Efficient Regression Testing of LLM-based Systems.** Muse,
  Briand, Lu, Gallaba (U. Ottawa / Huawei Canada), arXiv 2608.00378, Aug 2026. The closest prior work. It
  partitions a regression suite into slices that are semantically coherent in a feature space of behavioural
  signals and consistent in performance (mostly pass or mostly fail). The signals are 10 domain-specific features
  mined from agent execution logs on the baseline V0, such as file-level recall, trajectory entropy deviation,
  plan compliance and test failure rate; the slices are found by a multi-objective search (NSGA-II). After a
  change, it runs only representative instances of each slice on V1, extracts the signals again, and scores the
  impact of the change with a failure-prediction model trained on V0. Slices are ranked by a predicted category
  first (regression, improvement, unchanged), then by predicted impact inside the category. It is evaluated on
  LLM-agent issue resolution, under model changes and prompt changes, across budget levels, against GMM/HDBSCAN
  (slicing) and random (ranking) baselines. It is adapted as the `casper_slices` strategy
  (`traceeval/selection/adapted.py`): slices from behavioural signals of the baseline traces, two representatives
  per slice, the slices ranked by how much a failure model's prediction rose on the representatives' signals.
  CASPER is not diff-aware: it does not map what
  changed in a skill, prompt or harness to tests. It also reports no APFD-style metric, has no ground truth from
  mutations or injected faults, covers a single application domain and has no stopping rule. Its strength is the
  case this testbed does not cover: a change with no diff to map, such as a model upgrade, where only the logs of
  the last full run exist (RESEARCH_PLAN §5.6 says where it fits beside the change-aware strategies).
- **(Why) Is My Prompt Getting Worse? Rethinking Regression Testing for Evolving LLM APIs.** Ma, Yang, Kästner
  (CMU), arXiv 2311.11123. A case study of silent updates to LLM APIs. It identifies three obstacles to classic
  regression testing (no crisp oracle, brittle prompts, nondeterminism) and recommends slicing the suites.
- **ReCatcher.** Abbassi et al., arXiv 2507.19390, 2025. A regression-testing framework that compares two
  code-generation LLMs across updates by fine-tuning, merging or a new release. It does no selection, but it shows
  that model updates cause measurable regressions.
- **Test Before You Deploy: Governing Updates in the LLM Supply Chain.** Chishti, Oyinloye, Li, arXiv
  2604.27789, 2026. Governs updates with contracts, suites per risk category and compatibility gates. Tests
  targeted at a risk area catch regressions that aggregate metrics miss.
- **When Generic Prompt Improvements Hurt.** Commey, arXiv 2601.22025, 2026. Proposes a minimum viable evaluation
  suite and treats prompt edits as regression risks.
- **Submodular Evaluation Subset Selection in Automatic Prompt Optimization (SESS).** Nian et al., arXiv
  2601.03493, 2026. Chooses the evaluation subset by monotone submodular maximization, with a greedy algorithm and
  its guarantee. The formulation adapts directly to selecting the subset that maximizes expected regression
  detection under a budget.
- **Evaluation-Driven Development and Operations of LLM Agents (EDDOps).** Xia et al. (CSIRO Data61), arXiv
  2411.13768. A lifecycle framing for agents, in which our selector is the offline gate fed by online traces.
- **GBV-PD: Evolution-Aware Regression Test Prioritization of ML-Enabled Systems Using Gradient-Based Behavior
  Vectors.** Cho, Shin, Ko, arXiv 2606.28037, 2026. Represents each test by a PCA projection of its loss gradient
  under the old model, and projects the parameter update on the same basis to predict each test's change in loss
  without running the new model. The method is white-box: it needs gradients and parameter deltas, so it does not
  apply to LLMs hosted behind an API or to changes in prompts, skills or the harness. It is still the nearest
  analogue of ranking tests from a change vector, and a paper should cite it.
- **Test case selection and prioritization using ML: an SLR.** Pan et al., arXiv 2106.13891, EMSE 2022. A
  systematic literature review of machine-learning approaches to test selection and prioritization.

## 2. Efficient evaluation and benchmark-subset selection

- **tinyBenchmarks.** Polo et al., arXiv 2402.14992, ICML 2024. Subsets of ~100 items, calibrated with item
  response theory (IRT), reproduce full-benchmark scores. IRT item parameters could serve as per-test features,
  but the calibration assumes many models, while we have many versions of one system.
- **Anchor Points.** Vivek et al., arXiv 2309.08638, EACL 2024. Picks representative examples by clustering their
  confidence patterns; CASPER reuses the idea.
- **Efficient Benchmarking of Language Models (Flash-HELM).** Perlitz et al., arXiv 2308.11696, NAACL 2024.
  Introduces "decision impact on reliability": a reduced benchmark should report how stable its decisions are,
  and not only the error in scores.
- **metabench.** Kipnis et al., arXiv 2407.12844. A sparse subset of six benchmarks, selected with IRT.
- **Lifelong Benchmarks: Sort & Search.** Prabhu et al., arXiv 2402.19472. Amortizes evaluation across many
  model versions.
- **ATLAS: Adaptive Testing for LLM Evaluation.** Li et al., arXiv 2511.04689. Computerized adaptive testing with
  IRT and item selection by Fisher information, using up to 90% fewer items. Its sequential selection by
  information gain is a template for budget-aware stopping.
- **Efficient Benchmarking of AI Agents.** Ndzomga, arXiv 2603.23749, 2026. Keeps the tasks of mid-range difficulty
  (pass rate in [0.3, 0.7]) on Terminal-Bench 2.0 and the HAL benchmarks, which removes 44% to 70% of the tasks
  with rank fidelity $\rho \approx 0.91$. It is the strongest existing baseline for cheap subsets of agent evals,
  but it optimizes the ranking of models and not the detection of regressions after a change.
- **Risk-Aware Adaptive Evaluation.** Maji & Chowdhury (Georgia Tech), arXiv 2609.38914, Sep 2026. Contextual
  Thompson sampling over $\tau$-bench airline scenarios with impact weights. With 6% of the corpus it recovers 86%
  of the impact-weighted failure discovery of an oracle. It competes directly with our allocation of runs, although
  it ignores the change and depends on impact scores. It is adapted as the `risk_aware_ts` strategy
  (`traceeval/selection/adapted.py`), with a test's risk level as its impact score.
- **Efficient Evaluation of LLM Performance with Statistical Guarantees (FAQ).** Wu, Nair, Candès, arXiv
  2601.20251, 2026. Active querying over a finite population with valid frequentist confidence intervals. Its
  anytime-valid confidence under adaptive selection is what a budget-aware stopping rule needs.
- *Not yet read:* Sequential Bayesian Evaluation of LLM Behavior (arXiv 2511.10661); Active Evaluation
  Acquisition (2410.05952); Tailored Benchmarks (2502.13576); a winner's-curse correction for adaptive
  benchmarking (2605.05973); SparseEval (2602.07909).

## 3. Mutation testing / fault injection for LLM apps, prompts, agents

Mutation operators on agent artefacts now exist in three works, none of which uses them to compare test
selection:

- **Mutation Testing for Multi-Agent Workflows.** Kahani, Bagherzadeh, arXiv 2611.09895, 2026 (no venue yet).
  Fourteen operators in four families (delegation, allowed tool, restriction, agent or instruction) on a workflow
  manifest; 1,084 mutants of ten workflows, three live runs per test with a majority. To bound cost, a mutant runs
  only on the tests structurally incident to its changed element: a static selection per change. Their earlier
  preprint, "Testing agentic workflows with structural coverage criteria" (arXiv 2605.26521), defines coverage
  over a typed coordination graph and is not mutation testing.
- **AgentAssay.** Bhardwaj, arXiv 2603.02601, 2026 (a technical report, not peer reviewed). Three-valued verdicts
  from sequential tests, behavioural fingerprints, and twelve mutation operators (prompt, tool, model, context).
  Its "trace-first offline analysis" checks coverage and contracts on stored traces; detecting a regression
  still needs new runs. It overlaps the sequential test this project plans for repeated runs.
- **Chronicle** (§8) evaluates its replayed regression tests on 192 mutants.
- **AdaT²** (Lin, Yu, Xu, Zhang, Briand, Muñoz, arXiv 2610.10141, 2026) is test generation, not mutation testing:
  boundary tests for conversational agents from policy statements and transformation instructions chosen by a
  bandit. Mutation appears in its evaluation only, as 16 seeded "policy flip" faults.

Searches for prompt mutation testing otherwise return LLM-assisted mutation testing of code (MuTAP, arXiv
2308.16557; LLMorpheus, arXiv 2404.09952). SABER (Cuadron et al., arXiv 2512.07850, ICLR 2026) is not mutation
testing either: its "mutating steps" are actions that modify the environment. It shows that deviations in such
steps cut the odds of success by up to 92% to 96% on $\tau$-bench, and it releases $\tau$-Bench Verified, with
cleaned annotations, which is usable as a SUT.

Fault-injection work that can generate a ground truth or serve as a contrast:

- **AgentChaos.** Tan et al., arXiv 2608.06790, ASE 2026. Injects faults into LLM responses at the HTTP layer,
  without touching the application: crash, omission and value faults on content and tool-call fields. It verifies
  that each fault actually triggered. Its trigger verification and fault taxonomy are reusable.
- **llmmas-otel.** Seyedghorban et al. (TU Delft / JetBrains), arXiv 2608.24271, 2026. Combines OpenTelemetry
  tracing with rule-targeted fault injection at the A2A, tool and LLM boundaries (delay, drop, truncate, timeout,
  rate_limit, malformed_response). Its use of trace boundaries as injection points is reusable.
- **AgentChaosBench / When Agentic Executions Fail.** Zhang et al. (U. Toronto), arXiv 2608.14680, 2026. 10 fault
  types and 275 traces, each paired with a fault-free reference.
- **When Tools Fail (ToolMaze).** Zhu et al., arXiv 2606.05806, 2026. A taxonomy of tool perturbations and a
  Perturbation Recovery Rate.
- **ReliabilityBench.** Gupta, arXiv 2601.06112, 2026. A reliability surface $R(k, \varepsilon, \lambda)$ over
  $\mathrm{pass}^k$, the intensity of prompt perturbations and the intensity of faults (timeouts, rate limits,
  partial responses, schema drift), with metamorphic relations over actions.
- **GameDevBench.** Chi et al. (CMU), arXiv 2602.11103, 2026. 333 Godot tasks with deterministic unit tests. Its
  failure analysis is qualitative and gives no formal taxonomy.
- **SkillsBench.** Li et al., arXiv 2602.12670, 2026. 87 tasks in 8 domains with deterministic verifiers. Curated
  skills add 16.6 pp, and small bundles of skills beat exhaustive ones. Its paired protocol, with and without a
  skill, is the natural subject for studying skill changes.
- *Not yet read in detail:* sources of prompt-perturbation operators, PromptBench/PromptRobust (Zhu et al. 2023)
  and "Benchmarking Prompt Sensitivity in LLMs" (arXiv 2502.06065).

## 4. Classic regression-testing foundations

- Yoo & Harman, "Regression testing minimization, selection and prioritization: a survey", STVR 22(2), 2012.
- Rothermel & Harrold, "A safe, efficient regression test selection technique", TOSEM 6(2), 1997.
- Rothermel, Untch, Chu, Harrold, "Prioritizing test cases for regression testing", ICSM 1999 / TSE 27(10), 2001.
  APFD, and the total and additional greedy orderings.
- Elbaum, Malishevsky, Rothermel, "Incorporating varying test costs and fault severities into TCP", ICSE 2001
  ($\mathrm{APFD}_c$); Malishevsky, Ruthruff, Rothermel, Elbaum, "Cost-cognizant test case prioritization",
  technical report TR-UNL-CSE-2006-0004, University of Nebraska–Lincoln, 2006.
- Saha, Zhang, Khurshid, Perry, "An IR approach for regression test prioritization based on program changes"
  (REPiR), ICSE 2015.
- Spieker, Gotlieb, Marijan, Mossige, "RL for automatic TCP and selection in CI" (RETECS), ISSTA 2017.
- Memon et al., "Taming Google-scale continuous testing", ICSE-SEIP 2017.
- Machalica et al., "Predictive test selection", ICSE-SEIP 2019 (arXiv 1810.05286).
- Pan, Ghaleb, Briand, "LTM: Scalable and black-box similarity-based test suite minimization based on language
  models", IEEE TSE 50(11), 2024 (arXiv 2304.01397).
- Elbaum, Rothermel, Penix, "Techniques for improving regression testing in CI development environments",
  FSE 2014.
- Gligoric, Eloussi, Marinov, "Practical regression test selection with dynamic file dependencies" (Ekstazi),
  ISSTA 2015. Records the files each test class uses, with checksums, and re-runs a class only when one changed.
  The same idea as replay-first, dependencies observed at run time and compared by content, at file granularity;
  in an agent app most tests read the same prompt and skill files, so file checksums select nearly everything.
- Bazel's test result caching (`--cache_test_results`, user manual): a test is re-run only if it or a declared
  dependency changed. A digest of declared inputs decides, with nothing run; its hermeticity assumption plays the
  role of replay-first's condition on the model.
- Wang, Lian, Marinov, Xu, "Test selection for unified regression testing" (uRTS), ICSE 2023. One selection
  algorithm for code changes, configuration changes and both, built on Ekstazi and Ctest. The closest classic
  precedent for selection across code and non-code artefacts; it instruments each kind of artefact, where a
  replay sees any artefact through its effect on a request.
- Mirarab, Tahvildari, "A prioritization approach for software test cases based on Bayesian networks", FASE
  2007. A probabilistic order from source changes, fault-proneness and coverage: a precedent for the adaptive
  method's kind of model.
- Gonzalez-Sanchez, Abreu, Gross, van Gemund, "Spectrum-based sequential diagnosis" (SEQUOIA), AAAI 2011. Picks
  the next test to reduce the entropy over Bayesian fault candidates: the precedent for choosing a test by
  expected information gain. Its goal is locating a fault after failures, which matters here for the blame in a
  batch. Abreu, Zoeteweij, van Gemund, "Spectrum-based multiple fault localization" (Barinel), ASE 2009, gives
  the posterior over faulty components, with components that fail only sometimes.

## 5. Agent benchmarks with executable environments and deterministic verification

- **$\tau$-bench.** Yao et al. (Sierra), arXiv 2406.12045. Compares the database end state with the goal state, and
  introduces $\mathrm{pass}^k$.
- **$\tau^2$-bench.** Barres et al., arXiv 2506.07982. Adds a dual-control telecom domain and a compositional
  generator of verifiable tasks.
- **AppWorld.** Trivedi et al., arXiv 2407.18901, ACL 2024. 9 apps, 457 APIs and 750 tasks, checked by
  state-based unit tests that also flag collateral damage.
- **SkillsBench** (§3). Deterministic verifiers, and a paired design with and without skills.
- **Terminal-Bench.** Merrill et al., arXiv 2601.11868, ICLR 2026. 89 containerized tasks, with its harness at
  tbench.ai.
- **AgentDojo.** Debenedetti et al. (ETH), arXiv 2406.13352. 97 tasks and 629 security cases, with deterministic
  checks of utility and security.
- **ToolSandbox.** Lu et al. (Apple), arXiv 2408.04682. Stateful tools, evaluation by milestones and minefields,
  and a user played by an LLM.
- **WorkArena.** Drouin et al. (ServiceNow), arXiv 2403.07718, ICML 2024. Knowledge-work tasks on the ServiceNow
  platform, for web agents.

## 6. Agent reliability / nondeterminism statistics

- **$\mathrm{pass}^k$** ($\tau$-bench). The probability that all $k$ trials succeed.
- **ReliabilityBench** (§3).
- **Beyond pass@1: A Reliability Science Framework for Long-Horizon LLM Agents.** Khanal, Tao, Zhou, arXiv
  2603.29231, 2026. Defines a Reliability Decay Curve and a Variance Amplification Factor.
- **Adding Error Bars to Evals.** Miller (Anthropic), arXiv 2411.00640, 2024. Standard errors from the central
  limit theorem, clustered standard errors, paired comparisons and power analysis. It supports the paired
  per-test comparison of V0 and V1 behind our majority-vote ground truth.
- **On Randomness in Agentic Evals.** Bjarnason, Silva, Monperrus (KTH), arXiv 2602.07150, 2026. Single-run pass@1
  varies by 2.2 to 6.0 pp, and the standard deviation stays above 1.5 pp even at temperature 0.
- **When Agents Disagree With Themselves.** Mehta, arXiv 2602.11619, 2026. Uses behavioural consistency as a
  signal of uncertainty.
- **FAQ** (§2), for anytime-valid confidence intervals.
- **Understanding and Mitigating Numerical Sources of Nondeterminism in LLM Inference.** Yuan et al., NeurIPS
  2025, arXiv 2506.09501. Under greedy decoding, the batch size, the number of GPUs or the GPU type change the
  output, through non-associative floating-point arithmetic at limited precision. It explains why about 2% of the
  requests of a recording are answered otherwise when sent again, and why the condition of replay-first has to be
  measured per serving setup. Measured here (`RESEARCH_PLAN.md` §5.2): the batch and the server's prefix cache
  account for all of it, and with neither every request gets its recorded answer again, across a restart too,
  under Gemma and under Qwen.
- **Non-Determinism of "Deterministic" LLM Settings.** Atil et al., arXiv 2408.04667 (Eval4NLP 2025). Identical
  output strings are rarer than identical parsed answers: the same gap between answers and outcomes as in the
  recording.
- **Defeating Nondeterminism in LLM Inference.** He, 2025 (blog). A thousand completions of one prompt at
  temperature 0 gave 80 distinct outputs; batch-invariant kernels gave one, at 1.6 to 2.1 times the time. vLLM's
  documentation says the same of its default mode; neither model of this testbed can be served batch-invariant.
- **The Replay Gap.** Gonuguntla, arXiv 2608.08239, 2026. Replaying a logged trajectory with another model's
  outputs substituted is open-loop: most later actions change. Replay-first is not open-loop: it stops trusting
  the recording at the first request the recording lacks.
- **Conformal Risk Control** (Angelopoulos, Bates, Fisch, Lei, Schuster, ICLR 2024) and **Learn then Test**
  (Angelopoulos, Bates, Candès, Jordan, Lei, Annals of Applied Statistics, 2025). A threshold calibrated on
  held-out data controls the expected value of a loss. Both fit a stop threshold over the diverged tests, and
  both assume the calibration changes are exchangeable with the next one.
- *Not yet read:* arXiv 2511.10661 (§2) and arXiv 2608.22659.

## 7. Observability standards

- **OpenTelemetry GenAI semantic conventions** (`semantic-conventions-genai`, `gen-ai-agent-spans.md`). Define the
  operations `create_agent`, `invoke_agent`, `execute_tool` and others, and the attributes `gen_ai.operation.name`,
  `gen_ai.provider.name`, `gen_ai.agent.{name,id,version}`, `gen_ai.request.model`,
  `gen_ai.usage.{input,output}_tokens`, `gen_ai.tool.name` and `error.type`. Their status is Development, not
  stable. The attribute `gen_ai.agent.version` is a natural hook for identifying a change.
- **OpenInference** (Arize). Span kinds LLM, CHAIN, TOOL, RETRIEVER and AGENT, compatible with OpenTelemetry.
- Research that uses traces: llmmas-otel (OpenTelemetry), AgentChaosBench (Langfuse) and **TRAIL** (Deshpande et
  al., Patronus, arXiv 2505.08638). None of them uses traces to select tests.

## 8. Replaying recorded answers

Replay-first (RESEARCH_PLAN §3.3) re-runs every test on the changed app with the model's calls answered from the
answers recorded on the original app. The mechanism has precedents, in classic testing and for LLM agents.

Classic precedents:

- **Automatic Test Factoring for Java.** Saff, Artzi, Perkins, Ernst, ASE 2005. The closest. It records the calls
  between the code under test and an expensive environment during a system test and replays them from a
  transcript. The factored test passes, fails, or throws a `ReplayException` when the sequence of calls or their
  arguments differ from the recording; the full system must then be run. These are replay-first's three
  outcomes, with the model as the environment. It differs in what follows: the fallback re-runs the whole test,
  the exception is a nuisance and not a signal, and nothing selects or orders the tests that threw.
- **Transparent Mutable Replay** (Dora). Viennot, Nair, Nieh, ASPLOS 2013. Replays a recording on a modified
  program and lets the session go live where the two diverge: the precedent for reusing the prefix of a run.
- **Efficient Patch-Based Auditing for Web Application Vulnerabilities** (POIROT). Kim, Chandra, Zeldovich, OSDI
  2012. Re-executes logged requests on patched code with their recorded I/O; a query the log has no result for
  flags the request. The divergence criterion, used for auditing. Its "memoized re-execution" reuses
  intermediate results across requests and is not a cache of test results.
- **Intrusion Recovery Using Selective Re-execution** (Retro). Kim, Wang, Zeldovich, Kaashoek, OSDI 2010. Skips
  re-executing an action whose inputs are equivalent to those of the original execution.
- Record/replay tests in industry: recorded traffic replayed before submit, re-recorded when a request no longer
  matches ("Larger testing", *Software Engineering at Google*, ch. 14); recorded event histories replayed against
  changed workflow code (Temporal's replay tests).
- *Metadata only:* capture and replay for unit tests (Orso and Kennedy, WODA 2005; Joshi and Orso, ICSM 2007;
  Elbaum, Chin, Dwyer, Jorde, IEEE TSE 2009); Mokhov, Mitchell, Peyton Jones, "Build systems à la carte", ICFP
  2018, under which replay-first reads as a build with dynamic dependencies and early cutoff.

For LLM applications and agents:

- **Chronicle: Cut-Point Replay for Regression Testing of LLM Agents.** Chawla, Koul, arXiv 2609.20625, 2026. The
  closest published work. It records each crossing of a developer-annotated boundary (model call, tool call,
  routing decision) and replays it, the k-th crossing getting the k-th recorded envelope; the developer chooses
  which crossings come from the record and which run live with new code. It matches by position, not by the
  content of the request, so it cannot tell that a change reached the model; a count mismatch raises and the
  fixture is re-recorded. It selects no tests, and its benchmark uses simulated model boundaries.
- **An "inference replay" design** in an open-source agent project (a design document, 2026). Recorded answers
  are served to later eval runs that send the same request, and a run pays for inference only from its first
  request that matches no recording. This is exact-match replay with reuse of the prefix. Every case still runs:
  there is no selection, order or stop.
- **Exact-match caches in evaluation frameworks** (promptfoo, Inspect AI, DSPy, a recording proxy in another
  open-source project). With such a cache on, re-running the whole suite after a change pays only for the changed
  requests. That is the baseline replay-first has to beat: on this testbed it costs at most 21% of the suite's
  tokens per change (RESEARCH_PLAN §5.2). None of them returns "replayed" or "diverged" per test, or orders or
  stops over the diverged tests.
- **Cassette tooling** (VCR.py, LangChain's and LangSmith's test caches, session recording in agent tools).
  A request the cassette lacks is a failure to fix or a reason to re-record. VCR.py does not match the request
  body by default, so a stock cassette answers a changed prompt with the old response.
- **AgentCheck** (Mazumder, Lia, arXiv 2607.11098, 2026) replays tool responses and goes live after the agent
  diverges, to hold everything but an injected fault fixed; model calls stay live. **agrepl** (Mudasiru, arXiv
  2607.16200, 2026) replays all external interactions for debugging.
- Selection for agent benchmarks that does not read the change: trajectory-aware subset selection (Ayyad et al.,
  arXiv 2609.24928, 2026) and a study of an evolving agent in production (She, Lin, arXiv 2609.21267, 2026), which
  states that changes to an agent do not directly identify the affected benchmark questions.

What we found no source for, and what replay-first therefore adds:

- the replay read as a classification of the whole suite, before any model call, into tests whose outcome is
  known and tests the change reaches;
- selection, ordering and stopping applied to the reached tests only, compared with test-selection baselines on
  seeded and generated changes;
- the condition measured at three levels (request, run, outcome), with an empty change as the reference.

## Gap analysis

1. **Little work maps a change to the tests it impacts.** CASPER is change-aware only through the drift in
   behaviour after a change, and GBV-PD needs gradients. Kahani and Bagherzadeh run a mutant on the tests
   structurally incident to its changed element, a static rule on a workflow manifest. No work maps a concrete
   edit (skill file, prompt, tool schema, harness code, config) to the tests whose traces touched the changed
   component, or to the tests whose requests to the model it changes (§8).
2. **Cost is measured in tokens and time, not in tests.** The cost of agent tests varies by a factor of 10 to 100.
   Cost-cognizant $\mathrm{APFD}_c$ with token or latency costs, and budget-aware stopping, have not been applied
   to agent evals.
3. **Selection that accounts for nondeterminism.** Allocating runs and tests jointly under a budget, with
   anytime-valid stopping, is an open problem. Risk-Aware Adaptive Evaluation allocates runs with a bandit but
   ignores the change.
4. **Mutation-based ground truth exists, but not for test selection.** Injectors perturb the runtime (LLM
   responses, tool latency); three works mutate agent artefacts (§3), to measure the adequacy of a test suite.
   None seeds regressions to measure a selector's detection rate. Reviewers will ask whether mutants resemble
   real regressions, so the hand-written and the generated changes should be paired with real version histories.
5. **Evaluation on several systems.** CASPER covers one domain. $\tau^2$-bench, AppWorld, SkillsBench,
   Terminal-Bench and AgentDojo offer deterministic verifiers for validation across domains.

## Closest competitors (ranked)

1. **Test factoring** (ASE 2005) and **Chronicle** (2609.20625). The replay mechanism, in classic testing and
   for agents. We differ in using the replay to select tests over a suite, in matching by the content of the
   request, in what runs after a divergence, and in measuring the condition (§8).
2. **An exact-match cache in front of the model.** Not a paper: what evaluation frameworks already do. It is the
   cost baseline for replay-first.
3. **CASPER** (2608.00378). The same problem in the same community. We differ in diff-awareness, the cost model,
   stopping, the mutation-based ground truth and evaluation on several systems. Adapted as
   `casper_slices`.
4. **Risk-Aware Adaptive Evaluation** (2609.38914). Adaptive allocation under a budget on $\tau$-bench; adapted
   as `risk_aware_ts`.
5. **Kahani and Bagherzadeh** (2611.09895). Mutation operators on agent workflows, with a static selection of
   tests per mutant.
6. **Efficient Benchmarking of AI Agents** (2603.23749). A baseline that keeps tasks of mid-range difficulty.
7. **GBV-PD** (2606.28037). Reviewers will ask why it does not apply here: the LLMs are black boxes.
8. **ATLAS / tinyBenchmarks.** Baselines for adaptive selection with IRT.
9. **SESS** (2601.03493). Submodular selection of evaluation subsets.
10. **AgentChaos / llmmas-otel.** Fault injection with OpenTelemetry tracing. We mutate the artifacts under
    change, while they inject faults at run time.
11. **On Randomness in Agentic Evals** (2602.07150). A statistical framing of budgets spread over several runs.

What the paper should not claim:

- that it is the first to replay recorded model answers on a changed agent, or the first to pay for a test only
  after its divergence;
- that the replay is an exact oracle: it is exact relative to the recorded answers, for one model and one
  serving setup;
- the token saving alone as the contribution: the cache baseline has most of it;
- "replay" without saying which: open-loop replay, a bandit's offline replay and experience replay are other
  things.

## Venues and framing

See RESEARCH_PLAN §7. ASE is a natural fit (AgentChaos appeared there); ISSTA favours the mutation and oracle
angle.

## References

Full bibliographic entries for the works the project builds on, with what each is used for, are in
[REFERENCES.md](REFERENCES.md).

1. Muse, Briand, Lu, Gallaba. CASPER. arXiv 2608.00378, 2026. https://arxiv.org/abs/2608.00378
2. Ma, Yang, Kästner. (Why) Is My Prompt Getting Worse? arXiv 2311.11123. https://arxiv.org/abs/2311.11123
3. Abbassi et al. ReCatcher. arXiv 2507.19390. https://arxiv.org/abs/2507.19390
4. Chishti, Oyinloye, Li. Test Before You Deploy. arXiv 2604.27789. https://arxiv.org/abs/2604.27789
5. Commey. When Generic Prompt Improvements Hurt. arXiv 2601.22025. https://arxiv.org/abs/2601.22025
6. Nian et al. SESS. arXiv 2601.03493. https://arxiv.org/abs/2601.03493
7. Xia et al. EDDOps. arXiv 2411.13768. https://arxiv.org/abs/2411.13768
8. Cho, Shin, Ko. GBV-PD. arXiv 2606.28037. https://arxiv.org/abs/2606.28037
9. Polo et al. tinyBenchmarks. arXiv 2402.14992, ICML 2024. https://arxiv.org/abs/2402.14992
10. Vivek et al. Anchor Points. arXiv 2309.08638, EACL 2024. https://arxiv.org/abs/2309.08638
11. Perlitz et al. Efficient Benchmarking. arXiv 2308.11696, NAACL 2024. https://arxiv.org/abs/2308.11696
12. Kipnis et al. metabench. arXiv 2407.12844. https://arxiv.org/abs/2407.12844
13. Prabhu et al. Lifelong Benchmarks. arXiv 2402.19472. https://arxiv.org/abs/2402.19472
14. Li et al. ATLAS. arXiv 2511.04689. https://arxiv.org/abs/2511.04689
15. Ndzomga. Efficient Benchmarking of AI Agents. arXiv 2603.23749. https://arxiv.org/abs/2603.23749
16. Maji, Chowdhury. Risk-Aware Adaptive Evaluation. arXiv 2609.38914. https://arxiv.org/abs/2609.38914
17. Wu, Nair, Candès. FAQ. arXiv 2601.20251. https://arxiv.org/abs/2601.20251
18. Cuadron et al. SABER. arXiv 2512.07850, ICLR 2026. https://arxiv.org/abs/2512.07850
19. Tan et al. AgentChaos. arXiv 2608.06790, ASE 2026. https://arxiv.org/abs/2608.06790
20. Seyedghorban et al. llmmas-otel. arXiv 2608.24271. https://arxiv.org/abs/2608.24271
21. Zhang et al. AgentChaosBench. arXiv 2608.14680. https://arxiv.org/abs/2608.14680
22. Zhu et al. ToolMaze. arXiv 2606.05806. https://arxiv.org/abs/2606.05806
23. Gupta. ReliabilityBench. arXiv 2601.06112. https://arxiv.org/abs/2601.06112
24. Chi et al. GameDevBench. arXiv 2602.11103. https://arxiv.org/abs/2602.11103
25. Li et al. SkillsBench. arXiv 2602.12670. https://arxiv.org/abs/2602.12670
26. Dakhel et al. MuTAP. arXiv 2308.16557. https://arxiv.org/abs/2308.16557
27. Yao et al. $\tau$-bench. arXiv 2406.12045. https://arxiv.org/abs/2406.12045
28. Barres et al. $\tau^2$-Bench. arXiv 2506.07982. https://arxiv.org/abs/2506.07982
29. Trivedi et al. AppWorld. arXiv 2407.18901, ACL 2024. https://arxiv.org/abs/2407.18901
30. Merrill et al. Terminal-Bench. arXiv 2601.11868, ICLR 2026. https://arxiv.org/abs/2601.11868
31. Debenedetti et al. AgentDojo. arXiv 2406.13352. https://arxiv.org/abs/2406.13352
32. Lu et al. ToolSandbox. arXiv 2408.04682. https://arxiv.org/abs/2408.04682
33. Drouin et al. WorkArena. arXiv 2403.07718, ICML 2024. https://arxiv.org/abs/2403.07718
34. Khanal, Tao, Zhou. Beyond pass@1. arXiv 2603.29231. https://arxiv.org/abs/2603.29231
35. Miller. Adding Error Bars to Evals. arXiv 2411.00640. https://arxiv.org/abs/2411.00640
36. Bjarnason, Silva, Monperrus. On Randomness in Agentic Evals. arXiv 2602.07150. https://arxiv.org/abs/2602.07150
37. Mehta. When Agents Disagree With Themselves. arXiv 2602.11619. https://arxiv.org/abs/2602.11619
38. Deshpande et al. TRAIL. arXiv 2505.08638. https://arxiv.org/abs/2505.08638
39. OpenTelemetry GenAI semantic conventions: agent spans. https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-agent-spans.md
40. OpenInference specification. https://github.com/Arize-ai/openinference/blob/main/spec/semantic_conventions.md
41. Machalica et al. Predictive Test Selection. ICSE-SEIP 2019. https://arxiv.org/abs/1810.05286
42. Pan, Ghaleb, Briand. LTM. IEEE TSE 2024. https://arxiv.org/abs/2304.01397
43. Pan et al. TCS/TCP using ML: an SLR. arXiv 2106.13891. https://arxiv.org/abs/2106.13891
44. Saff, Artzi, Perkins, Ernst. Automatic Test Factoring for Java. ASE 2005. https://homes.cs.washington.edu/~mernst/pubs/test-factoring-ase2005.pdf
45. Viennot, Nair, Nieh. Transparent Mutable Replay for Multicore Debugging and Patch Validation. ASPLOS 2013. https://www.cs.columbia.edu/~nieh/pubs/asplos2013_dora.pdf
46. Kim, Chandra, Zeldovich. Efficient Patch-Based Auditing for Web Application Vulnerabilities. OSDI 2012. https://www.usenix.org/conference/osdi12/technical-sessions/presentation/kim
47. Kim, Wang, Zeldovich, Kaashoek. Intrusion Recovery Using Selective Re-execution. OSDI 2010. https://www.usenix.org/events/osdi10/tech/full_papers/Kim.pdf
48. Chawla, Koul. Chronicle: Cut-Point Replay for Regression Testing of LLM Agents. arXiv 2609.20625. https://arxiv.org/abs/2609.20625
49. Gligoric, Eloussi, Marinov. Practical Regression Test Selection with Dynamic File Dependencies. ISSTA 2015. https://users.ece.utexas.edu/~gligoric/papers/GligoricETAL15Ekstazi.pdf
50. Wang, Lian, Marinov, Xu. Test Selection for Unified Regression Testing. ICSE 2023. https://doi.org/10.1109/ICSE48619.2023.00145
51. Mirarab, Tahvildari. A Prioritization Approach for Software Test Cases Based on Bayesian Networks. FASE 2007. https://doi.org/10.1007/978-3-540-71289-3_22
52. Gonzalez-Sanchez, Abreu, Gross, van Gemund. Spectrum-Based Sequential Diagnosis. AAAI 2011. https://doi.org/10.1609/aaai.v25i1.7844
53. Abreu, Zoeteweij, van Gemund. Spectrum-Based Multiple Fault Localization. ASE 2009. https://doi.org/10.1109/ASE.2009.25
54. Kahani, Bagherzadeh. Mutation Testing for Multi-Agent Workflows. arXiv 2611.09895. https://arxiv.org/abs/2611.09895
55. Bhardwaj. AgentAssay. arXiv 2603.02601. https://arxiv.org/abs/2603.02601
56. Lin, Yu, Xu, Zhang, Briand, Muñoz. AdaT². arXiv 2610.10141. https://arxiv.org/abs/2610.10141
57. Yuan et al. Understanding and Mitigating Numerical Sources of Nondeterminism in LLM Inference. NeurIPS 2025. https://arxiv.org/abs/2506.09501
58. Atil et al. Non-Determinism of "Deterministic" LLM Settings. arXiv 2408.04667. https://arxiv.org/abs/2408.04667
59. He. Defeating Nondeterminism in LLM Inference. 2025. https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/
60. Gonuguntla. The Replay Gap. arXiv 2608.08239. https://arxiv.org/abs/2608.08239
61. Angelopoulos, Bates, Fisch, Lei, Schuster. Conformal Risk Control. ICLR 2024. https://arxiv.org/abs/2208.02814
62. Angelopoulos, Bates, Candès, Jordan, Lei. Learn then Test. Annals of Applied Statistics, 2025. https://arxiv.org/abs/2110.01052
63. Mazumder, Lia. AgentCheck. arXiv 2607.11098. https://arxiv.org/abs/2607.11098
64. Ayyad, Wang, Shin, Zou, Adams. Trajectory-Aware Benchmark Subset Selection. arXiv 2609.24928. https://arxiv.org/abs/2609.24928
65. She, Lin. Efficient Benchmarking in Production. arXiv 2609.21267. https://arxiv.org/abs/2609.21267
