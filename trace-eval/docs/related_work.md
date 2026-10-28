# Related work and positioning

*Literature survey compiled 2026-10-06 (arXiv / ACM / IEEE / GitHub). Items marked **[unverified]** were found by search but could not be fetched; **[from memory]** marks standard references not re-fetched. Treat every entry as a pointer to re-check before citing in a paper.*

## 1. Test selection / prioritization for LLM applications and agents

**CASPER — Change-Aware Slice Prioritization for Efficient Regression Testing of LLM-based Systems.** Muse, Briand, Lu, Gallaba (U. Ottawa / Huawei Canada), arXiv 2608.00378, Aug 2026. *The closest prior work.* Partitions a regression suite into "slices" that are (a) semantically coherent in a behavioral-signal feature space and (b) performance-consistent (mostly pass or mostly fail). Signals are 10 domain-specific features mined from agent execution logs on the baseline V0 (file-level recall, trajectory entropy deviation, plan compliance, test failure rate, …). After a change it runs only representative instances per slice on V1, re-extracts signals, scores change impact with a failure-prediction model trained on V0, and ranks slices by aggregated predicted-impact delta. Evaluated on LLM-agent issue resolution under model-change and prompt-change scenarios across budget levels; baselines are GMM/HDBSCAN (slicing) and random (ranking). **Reusable:** the slice abstraction, trace-derived behavioral signals, the "budget levels" protocol. **What it does not do:** it is not diff-aware (no mapping from *what* changed — skill/prompt/harness — to tests), reports no APFD-style metric, uses no mutation/fault-injected ground truth, has a single application domain, and has no stopping rule.

**(Why) Is My Prompt Getting Worse? Rethinking Regression Testing for Evolving LLM APIs.** Ma, Yang, Kästner (CMU), arXiv 2311.11123. Case study on silent LLM API updates; identifies three obstacles for classic regression testing — no crisp oracle, prompt brittleness, nondeterminism — and recommends slicing suites.

**ReCatcher.** Abbassi et al., arXiv 2507.19390, 2025. Regression-testing framework comparing two code-generation LLMs under fine-tuning/merging/new-release updates. No selection; evidence that model updates cause measurable regressions.

**Test Before You Deploy: Governing Updates in the LLM Supply Chain.** Chishti, Oyinloye, Li, arXiv 2604.27789, 2026. Contracts + risk-category suites + compatibility gates; targeted risk-area tests catch regressions aggregate metrics miss.

**When Generic Prompt Improvements Hurt.** Commey, arXiv 2601.22025, 2026. "Minimum viable evaluation suite"; prompt edits as regression risks.

**Submodular Evaluation Subset Selection in Automatic Prompt Optimization (SESS).** Nian et al., arXiv 2601.03493, 2026. Eval-subset choice as monotone submodular maximization; greedy with guarantee. **Reusable:** the formulation adapts directly to "select a subset maximizing expected regression detection under budget".

**Evaluation-Driven Development and Operations of LLM Agents (EDDOps).** Xia et al. (CSIRO Data61), arXiv 2411.13768. Lifecycle framing in which our selector is the offline gate fed by online traces.

**GBV-PD — Evolution-Aware Regression Test Prioritization of ML-Enabled Systems Using Gradient-Based Behavior Vectors.** Cho, Shin, Ko, arXiv 2606.28037, 2026. Each test is a PCA projection of its loss gradient under the old model; the parameter update is projected on the same basis to predict per-test loss change without running the new model. White-box (needs gradients and parameter deltas) → **not applicable to API-hosted LLMs or prompt/skill/harness changes**, but the nearest "change vector → test ranking" analogue; cite it.

Also: Pan et al., "Test case selection and prioritization using ML: an SLR", arXiv 2106.13891 (EMSE 2022).

## 2. Efficient evaluation and benchmark-subset selection

- **tinyBenchmarks.** Polo et al., arXiv 2402.14992, ICML 2024. IRT-calibrated ~100-item subsets reproduce full-benchmark scores. Transfers: IRT item parameters as per-test features; but calibration assumes many models, we have many *versions* of one system.
- **Anchor Points.** Vivek et al., arXiv 2309.08638, EACL 2024. Representative examples via confidence-pattern clustering (CASPER reuses the idea).
- **Efficient Benchmarking of Language Models (Flash-HELM).** Perlitz et al., arXiv 2308.11696, NAACL 2024. "Decision impact on reliability" — report decision stability, not only score error.
- **metabench.** Kipnis et al., arXiv 2407.12844. Sparse IRT-selected subset of six benchmarks.
- **Lifelong Benchmarks: Sort & Search.** Prabhu et al., arXiv 2402.19472. Amortized evaluation across many versions.
- **ATLAS — Adaptive Testing for LLM Evaluation.** Li et al., arXiv 2511.04689 (rev. 2026). Computerized adaptive testing: IRT + Fisher-information item selection, ≤90% fewer items. Transfers: sequential information-gain selection as a budget-aware stopping template.
- **Efficient Benchmarking of AI Agents.** Ndzomga, arXiv 2603.23749, 2026. Mid-range-difficulty filter (pass rate in [0.3, 0.7]) on Terminal-Bench 2.0 and HAL benchmarks: 44–70% fewer tasks with rank fidelity ρ≈0.91. Strongest existing baseline for cheap agent-eval subsets, but optimizes *model ranking*, not regression detection after a change.
- **Risk-Aware Adaptive Evaluation.** Maji & Chowdhury (Georgia Tech), arXiv 2609.38914, Sep 2026. Contextual Thompson sampling over τ-bench airline scenarios with impact weights; at 6% of corpus recovers 86% of oracle impact-weighted failure discovery. **Direct competitor for the run-allocation step** (but change-blind and needs impact scores) → use as a baseline.
- **Efficient Evaluation of LLM Performance with Statistical Guarantees (FAQ).** Wu, Nair, Candès, arXiv 2601.20251, 2026. Finite-population active querying with valid frequentist CIs. Transfers: anytime-valid confidence under adaptive selection — what a budget-aware stopping rule needs.
- **[unverified]** Sequential Bayesian Evaluation of LLM Behavior (arXiv 2511.10661); Active Evaluation Acquisition (2410.05952); Tailored Benchmarks (2502.13576); winner's-curse correction for adaptive benchmarking (2605.05973); SparseEval (2602.07909).

## 3. Mutation testing / fault injection for LLM apps, prompts, agents

**Terminology flag:** no paper found defines *mutation operators for prompts, skills or harness code* as regression ground truth. "Prompt mutation testing" searches return LLM-assisted mutation testing of *code* (MuTAP, arXiv 2308.16557; LLMorpheus, arXiv 2404.09952). **SABER** (Cuadron et al., arXiv 2512.07850, ICLR 2026) is *not* mutation testing: "mutating steps" means environment-modifying actions; it shows deviations in such steps cut success odds by up to 92–96% on τ-bench and releases **τ-Bench Verified** (cleaned annotations — useful as SUT).

Fault-injection work usable as ground-truth generators or contrast:

- **AgentChaos.** Tan et al., arXiv 2608.06790, ASE 2026. Non-intrusive HTTP-layer injection into LLM responses (crash/omission/value faults on content and tool-call fields); verifies the fault actually triggered. Reusable: trigger verification, fault taxonomy.
- **llmmas-otel.** Seyedghorban et al. (TU Delft / JetBrains), arXiv 2608.24271, 2026. OpenTelemetry tracing + rule-targeted fault injection at A2A / tool / LLM boundaries (delay, drop, truncate, timeout, rate_limit, malformed_response). Reusable: "injection points = trace boundaries".
- **AgentChaosBench / When Agentic Executions Fail.** Zhang et al. (U. Toronto), arXiv 2608.14680, 2026. 10 fault types, 275 traces with paired fault-free references.
- **When Tools Fail (ToolMaze).** Zhu et al., arXiv 2606.05806, 2026. Tool-perturbation taxonomy, Perturbation Recovery Rate.
- **ReliabilityBench.** Gupta, arXiv 2601.06112, 2026. Reliability surface R(k, ε, λ): pass^k, prompt-perturbation intensity, fault intensity (timeouts, rate limits, partial responses, schema drift); action metamorphic relations.
- **GameDevBench.** Chi et al. (CMU), arXiv 2602.11103, 2026. 333 Godot tasks with deterministic unit tests; failure analysis is qualitative, not a formal taxonomy.
- **SkillsBench.** Li et al., arXiv 2602.12670, 2026. 87 tasks / 8 domains, deterministic verifiers; curated skills +16.6 pp; small skill bundles beat exhaustive ones. The paired no-skill/with-skill protocol is the natural *skill-change* subject. A "skill-induced failure taxonomy" was **not** verified in it.
- Prompt-perturbation operator sources **[unverified details]:** PromptBench/PromptRobust (Zhu et al. 2023), "Benchmarking Prompt Sensitivity in LLMs" (arXiv 2502.06065).

## 4. Classic regression-testing foundations **[from memory unless noted]**

- Yoo & Harman, "Regression testing minimization, selection and prioritization: a survey", STVR 22(2), 2012.
- Rothermel & Harrold, "A safe, efficient regression test selection technique", TOSEM 6(2), 1997.
- Rothermel, Untch, Chu, Harrold, "Prioritizing test cases for regression testing", ICSM 1999 / TSE 27(10), 2001 — APFD, total/additional greedy.
- Elbaum, Malishevsky, Rothermel, "Incorporating varying test costs and fault severities into TCP", ICSE 2001 (APFD_c); Malishevsky et al., "Cost-cognizant test case prioritization", ICSM 2006.
- Saha, Zhang, Khurshid, Perry, "An IR approach for regression test prioritization based on program changes" (REPiR), ICSE 2015.
- Spieker, Gotlieb, Marijan, Mossige, "RL for automatic TCP and selection in CI" (RETECS), ISSTA 2017.
- Memon et al., "Taming Google-scale continuous testing", ICSE-SEIP 2017. Machalica et al., "Predictive test selection", ICSE-SEIP 2019 (arXiv 1810.05286) [verified].
- Fallahzadeh & Rigby, "The impact of flaky tests on historical test prioritization on Chrome", ICSE-SEIP 2022 [verified].
- Pan, Ghaleb, Briand, "LTM: Scalable and black-box similarity-based test suite minimization based on language models", IEEE TSE 50(11), 2024 (arXiv 2304.01397) [verified].
- Elbaum, Rothermel, Penix, "Techniques for improving regression testing in CI development environments", FSE 2014.

## 5. Agent benchmarks with executable environments and deterministic verification

- **τ-bench** (Yao et al., Sierra; arXiv 2406.12045): DB end-state vs. goal state; introduces pass^k.
- **τ²-bench** (Barres et al.; arXiv 2506.07982): dual-control telecom domain, compositional verifiable task generator. Repo now branded τ³-bench (voice + knowledge domains); see `docs/tau2_integration.md`.
- **AppWorld** (Trivedi et al.; arXiv 2407.18901, ACL 2024): 9 apps, 457 APIs, 750 tasks; state-based unit tests that also flag collateral damage.
- **SkillsBench** (above): deterministic verifiers; paired skill/no-skill design.
- **Terminal-Bench** (Merrill et al.; arXiv 2601.11868, ICLR 2026): 89 containerized tasks; harness at tbench.ai ("Harbor" not verified).
- **AgentDojo** (Debenedetti et al., ETH; arXiv 2406.13352): 97 tasks, 629 security cases; deterministic utility + security checks.
- **ToolSandbox** (Lu et al., Apple; arXiv 2408.04682): stateful tools, milestone/minefield evaluation, user simulator.
- **WorkArena** (Drouin et al., ServiceNow; arXiv 2403.07718, ICML 2024).

## 6. Agent reliability / nondeterminism statistics

- **pass^k** (τ-bench): P(all k trials succeed).
- **ReliabilityBench** (above); **Beyond pass@1: A Reliability Science Framework for Long-Horizon LLM Agents** (Khanal, Tao, Zhou; arXiv 2603.29231, 2026): Reliability Decay Curve, Variance Amplification Factor.
- **Adding Error Bars to Evals** (Miller, Anthropic; arXiv 2411.00640, 2024): CLT SEs, clustered SEs, paired comparisons, power analysis → paired per-test V0/V1 comparison and power-based run budgeting.
- **On Randomness in Agentic Evals** (Bjarnason, Silva, Monperrus, KTH; arXiv 2602.07150, 2026): single-run pass@1 varies 2.2–6.0 pp; SD > 1.5 pp even at temperature 0.
- **When Agents Disagree With Themselves** (Mehta; arXiv 2602.11619, 2026): behavioral consistency as uncertainty signal → trace-divergence features as flakiness predictors.
- **FAQ** (above) for anytime-valid CIs. **[unverified]** arXiv 2511.10661, 2608.22659.

## 7. Observability standards

- **OpenTelemetry GenAI semantic conventions** (`semantic-conventions-genai`, `gen-ai-agent-spans.md`): operations `create_agent`, `invoke_agent`, `execute_tool`, …; attributes `gen_ai.operation.name`, `gen_ai.provider.name`, `gen_ai.agent.{name,id,version}`, `gen_ai.request.model`, `gen_ai.usage.{input,output}_tokens`, `gen_ai.tool.name`, `error.type`. Status: **Development** (not stable). `gen_ai.agent.version` is a natural hook for change identity.
- **OpenInference** (Arize): span kinds LLM/CHAIN/TOOL/RETRIEVER/AGENT, OTel-compatible.
- Research using traces: llmmas-otel (OTel), AgentChaosBench (Langfuse), **TRAIL** (Deshpande et al., Patronus; arXiv 2505.08638). None uses traces for *test selection*.

## Gap analysis

1. **Diff-to-test impact mapping is absent.** CASPER is change-aware only via post-change behavioral drift; GBV-PD needs gradients. No work maps a concrete edit (skill file, prompt, tool schema, harness code, config) to the tests whose traces touched the changed component — the agent analogue of coverage-/IR-based RTS. Trace spans (`execute_tool`, skill loads, config reads) are an untapped coverage proxy.
2. **Cost model is token/time, not test count.** Agent tests have 10–100× cost variance; cost-cognizant APFD_c with token/latency costs and budget-aware stopping has not been applied to agent evals.
3. **Nondeterminism-aware selection.** Allocating *runs* and *tests* jointly under a budget with anytime-valid stopping is open. Risk-Aware Adaptive Evaluation does bandit run allocation but is change-blind.
4. **No mutation-based ground truth.** Existing injectors perturb runtime (LLM responses, tool latency); none mutates the *artifacts under change* (skills/prompts/harness/config) to seed regressions for measuring a selector's detection rate. Key methodological contribution and key credibility risk (reviewers will ask whether mutants resemble real regressions — pair with real version histories).
5. **Multi-SUT evaluation.** CASPER has one domain; τ²-bench, AppWorld, SkillsBench, Terminal-Bench, AgentDojo offer deterministic verifiers for cross-domain validation.

## Closest competitors (ranked)

1. **CASPER (2608.00378)** — same problem, same community. Differentiate on diff-awareness, cost model, stopping, mutation ground truth, multi-SUT.
2. **Risk-Aware Adaptive Evaluation (2609.38914)** — budgeted adaptive allocation on τ-bench; make it a baseline.
3. **Efficient Benchmarking of AI Agents (2603.23749)** — mid-range-difficulty subset baseline.
4. **GBV-PD (2606.28037)** — reviewers will ask why not applicable (black-box LLMs).
5. **ATLAS / tinyBenchmarks** — IRT adaptive selection baselines.
6. **SESS (2601.03493)** — submodular eval-subset selection.
7. **AgentChaos / llmmas-otel** — fault injection + OTel; distinguish artifact mutation from runtime fault injection.
8. **On Randomness in Agentic Evals (2602.07150)** — statistical framing of multi-run budgets.

## Venues and framing

- **ICSE / FSE / ASE / ISSTA:** regression test selection & prioritization for LLM-based systems — trace-coverage RTS, APFD_c with token cost, mutation analysis as ground truth, RQ-driven evaluation vs. CASPER/random/mid-range/IRT. ASE is a natural fit (AgentChaos appeared there); ISSTA favours the mutation/oracle angle.
- **ICST / ISSRE:** adequacy of mutants, flakiness-aware statistics, reliability (pass^k, stopping rules).
- **NeurIPS D&B / EMNLP:** a benchmark + protocol ("RegressionBench": seeded skill/prompt/harness mutants across τ²/AppWorld/SkillsBench with cost-bounded detection metrics) plus a released trace dataset.

## References

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
39. OpenTelemetry GenAI semantic conventions — agent spans. https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-agent-spans.md
40. OpenInference specification. https://github.com/Arize-ai/openinference/blob/main/spec/semantic_conventions.md
41. Machalica et al. Predictive Test Selection. ICSE-SEIP 2019. https://arxiv.org/abs/1810.05286
42. Fallahzadeh, Rigby. Flaky tests and historical TCP on Chrome. ICSE-SEIP 2022. https://ieeexplore.ieee.org/document/9793941
43. Pan, Ghaleb, Briand. LTM. IEEE TSE 2024. https://arxiv.org/abs/2304.01397
44. Pan et al. TCS/TCP using ML: an SLR. arXiv 2106.13891. https://arxiv.org/abs/2106.13891
