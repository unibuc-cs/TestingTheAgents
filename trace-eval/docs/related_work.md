# Related work and positioning

Work related to TRACE-Eval, grouped by topic, from a survey of arXiv, ACM, IEEE and GitHub in October 2026. Each
entry says what the work does and how it relates to this project. Entries marked *not yet read* were found by
search, but their full text has not been checked; they should be read before they are cited.

## 1. Test selection / prioritization for LLM applications and agents

- **CASPER: Change-Aware Slice Prioritization for Efficient Regression Testing of LLM-based Systems.** Muse,
  Briand, Lu, Gallaba (U. Ottawa / Huawei Canada), arXiv 2608.00378, Aug 2026. The closest prior work. It
  partitions a regression suite into slices that are semantically coherent in a feature space of behavioural
  signals and consistent in performance (mostly pass or mostly fail). The signals are 10 domain-specific features
  mined from agent execution logs on the baseline V0, such as file-level recall, trajectory entropy deviation,
  plan compliance and test failure rate. After a change, it runs only representative instances of each slice on
  V1, extracts the signals again, scores the impact of the change with a failure-prediction model trained on V0,
  and ranks slices by the aggregated change in predicted impact. It is evaluated on LLM-agent issue resolution,
  under model changes and prompt changes, across budget levels, against GMM/HDBSCAN (slicing) and random (ranking)
  baselines. It is reproduced as the `casper_slices` strategy (`traceeval/selection/reproduced.py`): slices from
  behavioural signals of the baseline traces, two representatives per slice, the slices ranked by the shift in
  their failure rate. CASPER is not diff-aware: it does not map what changed in a skill, prompt or harness to
  tests. It also reports no APFD-style metric, has no ground truth from mutations or injected faults, covers a
  single application domain and has no stopping rule. Its strength is the case this testbed does not cover: a
  change with no diff to map, such as a model upgrade, where only the logs of the last full run exist
  (RESEARCH_PLAN §5.1 says where it fits beside the change-aware strategies).
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
- **Efficient Benchmarking of AI Agents.** Ndzomga, arXiv 2603.23749, 2026. Keeps the tasks of mid-range
  difficulty (pass rate in [0.3, 0.7]) on Terminal-Bench 2.0 and the HAL benchmarks, which removes 44–70% of the
  tasks with rank fidelity ρ≈0.91. It is the strongest existing baseline for cheap subsets of agent evals, but it
  optimizes the ranking of models and not the detection of regressions after a change.
- **Risk-Aware Adaptive Evaluation.** Maji & Chowdhury (Georgia Tech), arXiv 2609.38914, Sep 2026. Contextual
  Thompson sampling over τ-bench airline scenarios with impact weights. With 6% of the corpus it recovers 86% of
  the impact-weighted failure discovery of an oracle. It competes directly with our allocation of runs, although
  it ignores the change and depends on impact scores. It is reproduced as the `risk_aware_ts` strategy
  (`traceeval/selection/reproduced.py`), with a test's risk level as its impact score.
- **Efficient Evaluation of LLM Performance with Statistical Guarantees (FAQ).** Wu, Nair, Candès, arXiv
  2601.20251, 2026. Active querying over a finite population with valid frequentist confidence intervals. Its
  anytime-valid confidence under adaptive selection is what a budget-aware stopping rule needs.
- *Not yet read:* Sequential Bayesian Evaluation of LLM Behavior (arXiv 2511.10661); Active Evaluation
  Acquisition (2410.05952); Tailored Benchmarks (2502.13576); a winner's-curse correction for adaptive
  benchmarking (2605.05973); SparseEval (2602.07909).

## 3. Mutation testing / fault injection for LLM apps, prompts, agents

We found no paper that defines mutation operators for prompts, skills or harness code as a regression ground
truth. Searches for prompt mutation testing return LLM-assisted mutation testing of code (MuTAP, arXiv
2308.16557; LLMorpheus, arXiv 2404.09952). SABER (Cuadron et al., arXiv 2512.07850, ICLR 2026) is not mutation
testing either: its "mutating steps" are actions that modify the environment. It shows that deviations in such
steps cut the odds of success by up to 92–96% on τ-bench, and it releases τ-Bench Verified, with cleaned
annotations, which is usable as a SUT.

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
- **ReliabilityBench.** Gupta, arXiv 2601.06112, 2026. A reliability surface R(k, ε, λ) over pass^k, the
  intensity of prompt perturbations and the intensity of faults (timeouts, rate limits, partial responses, schema
  drift), with metamorphic relations over actions.
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
  (APFD_c); Malishevsky, Ruthruff, Rothermel, Elbaum, "Cost-cognizant test case prioritization", technical
  report TR-UNL-CSE-2006-0004, University of Nebraska–Lincoln, 2006.
- Saha, Zhang, Khurshid, Perry, "An IR approach for regression test prioritization based on program changes"
  (REPiR), ICSE 2015.
- Spieker, Gotlieb, Marijan, Mossige, "RL for automatic TCP and selection in CI" (RETECS), ISSTA 2017.
- Memon et al., "Taming Google-scale continuous testing", ICSE-SEIP 2017.
- Machalica et al., "Predictive test selection", ICSE-SEIP 2019 (arXiv 1810.05286).
- Pan, Ghaleb, Briand, "LTM: Scalable and black-box similarity-based test suite minimization based on language
  models", IEEE TSE 50(11), 2024 (arXiv 2304.01397).
- Elbaum, Rothermel, Penix, "Techniques for improving regression testing in CI development environments",
  FSE 2014.

## 5. Agent benchmarks with executable environments and deterministic verification

- **τ-bench.** Yao et al. (Sierra), arXiv 2406.12045. Compares the database end state with the goal state, and
  introduces pass^k.
- **τ²-bench.** Barres et al., arXiv 2506.07982. Adds a dual-control telecom domain and a compositional generator
  of verifiable tasks.
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

- **pass^k** (τ-bench). The probability that all k trials succeed.
- **ReliabilityBench** (§3).
- **Beyond pass@1: A Reliability Science Framework for Long-Horizon LLM Agents.** Khanal, Tao, Zhou, arXiv
  2603.29231, 2026. Defines a Reliability Decay Curve and a Variance Amplification Factor.
- **Adding Error Bars to Evals.** Miller (Anthropic), arXiv 2411.00640, 2024. Standard errors from the central
  limit theorem, clustered standard errors, paired comparisons and power analysis. It supports the paired
  per-test comparison of V0 and V1 behind our majority-vote ground truth.
- **On Randomness in Agentic Evals.** Bjarnason, Silva, Monperrus (KTH), arXiv 2602.07150, 2026. Single-run pass@1
  varies by 2.2–6.0 pp, and the standard deviation stays above 1.5 pp even at temperature 0.
- **When Agents Disagree With Themselves.** Mehta, arXiv 2602.11619, 2026. Uses behavioural consistency as a
  signal of uncertainty.
- **FAQ** (§2), for anytime-valid confidence intervals.
- *Not yet read:* arXiv 2511.10661 (§2) and arXiv 2608.22659.

## 7. Observability standards

- **OpenTelemetry GenAI semantic conventions** (`semantic-conventions-genai`, `gen-ai-agent-spans.md`). Define the
  operations `create_agent`, `invoke_agent`, `execute_tool`, … and the attributes `gen_ai.operation.name`,
  `gen_ai.provider.name`, `gen_ai.agent.{name,id,version}`, `gen_ai.request.model`,
  `gen_ai.usage.{input,output}_tokens`, `gen_ai.tool.name` and `error.type`. Their status is Development, not
  stable. The attribute `gen_ai.agent.version` is a natural hook for identifying a change.
- **OpenInference** (Arize). Span kinds LLM, CHAIN, TOOL, RETRIEVER and AGENT, compatible with OpenTelemetry.
- Research that uses traces: llmmas-otel (OpenTelemetry), AgentChaosBench (Langfuse) and **TRAIL** (Deshpande et
  al., Patronus, arXiv 2505.08638). None of them uses traces to select tests.

## Gap analysis

1. **No work maps a diff to the tests it impacts.** CASPER is change-aware only through the drift in behaviour
   after a change, and GBV-PD needs gradients. No work maps a concrete edit (skill file, prompt, tool schema,
   harness code, config) to the tests whose traces touched the changed component, which would be the agent
   analogue of coverage-based or IR-based RTS. Trace spans (`execute_tool`, skill loads, config reads) are an
   untapped proxy for coverage.
2. **Cost is measured in tokens and time, not in tests.** The cost of agent tests varies by a factor of 10–100.
   Cost-cognizant APFD_c with token or latency costs, and budget-aware stopping, have not been applied to agent
   evals.
3. **Selection that accounts for nondeterminism.** Allocating runs and tests jointly under a budget, with
   anytime-valid stopping, is an open problem. Risk-Aware Adaptive Evaluation allocates runs with a bandit but
   ignores the change.
4. **No mutation-based ground truth.** Existing injectors perturb the runtime (LLM responses, tool latency). None
   mutates the artifacts under change (skills, prompts, harness, config) to seed regressions and measure a
   selector's detection rate. This is the testbed's main methodological addition; the contribution itself is the
   method (RESEARCH_PLAN §1). It is also the testbed's main credibility risk: reviewers will ask whether mutants
   resemble real regressions, so the mutants should be paired with real version histories.
5. **Evaluation on several systems.** CASPER covers one domain. τ²-bench, AppWorld, SkillsBench, Terminal-Bench
   and AgentDojo offer deterministic verifiers for validation across domains.

## Closest competitors (ranked)

1. **CASPER** (2608.00378). The same problem in the same community. We differ in diff-awareness, the cost model,
   stopping, the mutation-based ground truth and evaluation on several systems. Reproduced as
   `casper_slices`.
2. **Risk-Aware Adaptive Evaluation** (2609.38914). Adaptive allocation under a budget on τ-bench; reproduced as
   `risk_aware_ts`.
3. **Efficient Benchmarking of AI Agents** (2603.23749). A baseline that keeps tasks of mid-range difficulty.
4. **GBV-PD** (2606.28037). Reviewers will ask why it does not apply here: the LLMs are black boxes.
5. **ATLAS / tinyBenchmarks.** Baselines for adaptive selection with IRT.
6. **SESS** (2601.03493). Submodular selection of evaluation subsets.
7. **AgentChaos / llmmas-otel.** Fault injection with OpenTelemetry tracing. We mutate the artifacts under change,
   while they inject faults at run time.
8. **On Randomness in Agentic Evals** (2602.07150). A statistical framing of budgets spread over several runs.

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
27. Yao et al. τ-bench. arXiv 2406.12045. https://arxiv.org/abs/2406.12045
28. Barres et al. τ²-Bench. arXiv 2506.07982. https://arxiv.org/abs/2506.07982
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
