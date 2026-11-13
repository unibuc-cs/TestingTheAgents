# References

The works the project builds on or cites, with full bibliographic details and what each one is used for. The survey
of related work, one entry per paper with its positioning, is [related_work.md](related_work.md). The LaTeX draft
of the paper (`docs/paper/`) cites the same works from `docs/paper/refs.bib`.

## Metrics

- Rothermel, G., Untch, R. H., Chu, C., Harrold, M. J. *Prioritizing test cases for regression testing.* IEEE
  Transactions on Software Engineering 27(10): 929–948, 2001. doi:10.1109/32.962562. Conference version: *Test
  case prioritization: an empirical study*, ICSM 1999, pp. 179–188.
  Defines APFD, the average percentage of faults detected by an order of the suite
  (`experiment/metrics.py::apfd`; [USER_GUIDE.md](USER_GUIDE.md) §4 gives the formula and how to read it).
- Elbaum, S., Malishevsky, A. G., Rothermel, G. *Incorporating varying test costs and fault severities into test
  case prioritization.* ICSE 2001, pp. 329–338. doi:10.1109/ICSE.2001.919106. Defines $\mathrm{APFD}_c$, the
  cost-cognizant form of APFD, which weighs each fault by its severity and each test by its cost
  (`experiment/metrics.py::apfdc`). The report's section 4 gives both.
- Elbaum, S., Malishevsky, A. G., Rothermel, G. *Test case prioritization: a family of empirical studies.* IEEE
  Transactions on Software Engineering 28(2): 159–182, 2002. doi:10.1109/32.988497.
  The empirical protocol for comparing prioritization techniques: many orders, many faulty versions, APFD.
- Malishevsky, A. G., Ruthruff, J. R., Rothermel, G., Elbaum, S. *Cost-cognizant test case prioritization.*
  Technical report TR-UNL-CSE-2006-0004, University of Nebraska–Lincoln, 2006. Prioritization with estimated costs
  and severities, and the argument for reading $\mathrm{APFD}_c$ rather than APFD when costs differ by an order of
  magnitude, as tokens do here.

## Regression test selection and prioritization

- Rothermel, G., Harrold, M. J. *A safe, efficient regression test selection technique.* ACM Transactions on
  Software Engineering and Methodology 6(2): 173–210, 1997. doi:10.1145/248233.248262.
  Safe selection on control-flow graphs; the `declared` and `observed` strategies are its analogue on metadata and
  on traces.
- Yoo, S., Harman, M. *Regression testing minimization, selection and prioritization: a survey.* Software Testing,
  Verification and Reliability 22(2): 67–120, 2012. doi:10.1002/stvr.430.
  The vocabulary of the three sub-problems ([RESEARCH_PLAN.md](RESEARCH_PLAN.md) §1).
- Saha, R. K., Zhang, L., Khurshid, S., Perry, D. E. *An information retrieval approach for regression test
  prioritization based on program changes.* ICSE 2015, pp. 268–279. doi:10.1109/ICSE.2015.47.
  REPiR: the diff as a query against the tests. The `ir_tfidf` strategy, and the text factor of the method.
- Elbaum, S., Rothermel, G., Penix, J. *Techniques for improving regression testing in continuous integration
  development environments.* FSE 2014, pp. 235–245. doi:10.1145/2635868.2635910.
  Selection and prioritization from failure history and time windows in continuous integration.
- Spieker, H., Gotlieb, A., Marijan, D., Mossige, M. *Reinforcement learning for automatic test case
  prioritization and selection in continuous integration.* ISSTA 2017, pp. 12–22. doi:10.1145/3092703.3092709.
  RETECS: an order learned online from outcomes.
- Memon, A., Gao, Z., Nguyen, B., Dhanda, S., Nickell, E., Siemborski, R., Micco, J. *Taming Google-scale
  continuous testing.* ICSE-SEIP 2017, pp. 233–242. doi:10.1109/ICSE-SEIP.2017.16.
  Failure history as the main signal at scale.
- Machalica, M., Samylkin, A., Porth, M., Chandra, S. *Predictive test selection.* ICSE-SEIP 2019, pp. 91–100.
  doi:10.1109/ICSE-SEIP.2019.00018. arXiv 1810.05286.
  A learned model over change and test features; the optional `history_ml` baseline.
- Pan, R., Ghaleb, T. A., Briand, L. C. *LTM: scalable and black-box similarity-based test suite minimization
  based on language models.* IEEE Transactions on Software Engineering 50(11), 2024. arXiv 2304.01397.
  Diversity-based ordering; the optional `observed_diverse` baseline.

## The two published methods reproduced as baselines

- Muse, B. A., Briand, L., Lu, Y., Gallaba, K. *CASPER: change-aware slice prioritization for efficient regression
  testing of LLM-based systems.* arXiv 2608.00378, August 2026. https://arxiv.org/abs/2608.00378
  Reproduced as `casper_slices` (`selection/reproduced.py`): slices from behavioural signals of the baseline logs,
  representatives of every slice run on the changed system, slices ranked by the drift of their outcomes.
- Maji, P., Chowdhury, S. G. *Risk-aware adaptive evaluation: finding high-impact failures under limited budgets.*
  arXiv 2609.38914, September 2026; NeurIPS 2026 workshop on the evaluation of interactive agents.
  https://arxiv.org/abs/2609.38914
  Reproduced as `risk_aware_ts`: contextual Thompson sampling over the tests, with a test's risk as its impact.

## Ingredients of the methods

- Lindley, D. V. *On a measure of the information provided by an experiment.* Annals of Mathematical Statistics
  27(4): 986–1005, 1956.
  Expected information gain, the quantity the adaptive method maximises per token when it picks the next test.
- Thompson, W. R. *On the likelihood that one unknown probability exceeds another in view of the evidence of two
  samples.* Biometrika 25(3–4): 285–294, 1933. Chapelle, O., Li, L. *An empirical evaluation of Thompson
  sampling.* NeurIPS 2011.
  Thompson sampling, the policy of the risk-aware bandit.
- Lloyd, S. P. *Least squares quantization in PCM.* IEEE Transactions on Information Theory 28(2): 129–137, 1982.
  The k-means iteration that cuts the suite into slices in the reproduction of CASPER.
- DeMillo, R. A., Lipton, R. J., Sayward, F. G. *Hints on test data selection: help for the practicing
  programmer.* IEEE Computer 11(4): 34–41, 1978. Jia, Y., Harman, M. *An analysis and survey of the development
  of mutation testing.* IEEE Transactions on Software Engineering 37(5): 649–678, 2011.
  Mutation analysis, the origin of the controlled changes that give the ground truth.

## Agent evaluation

- Yao, S., Shinn, N., Razavi, P., Narasimhan, K. *$\tau$-bench: a benchmark for tool-agent-user interaction in
  real-world domains.* arXiv 2406.12045, 2024. Barres, V., et al. *$\tau^2$-bench: evaluating conversational agents
  in a dual-control environment.* arXiv 2506.07982, 2025. State-based verification and $\mathrm{pass}^k$;
  tau2-bench is the planned second system under test.
- Ma, W., Yang, C., Kästner, C. *(Why) is my prompt getting worse? Rethinking regression testing for evolving LLM
  APIs.* CAIN 2024; arXiv 2311.11123.
  The obstacles to regression testing LLM applications: no crisp oracle, brittle prompts, nondeterminism.
- Miller, E. *Adding error bars to evals: a statistical approach to language model evaluations.* arXiv
  2411.00640, 2024. Bjarnason, B. H., Silva, A., Monperrus, M. *On randomness in agentic evals.* arXiv
  2602.07150, 2026.
  Run-to-run variation of agent evaluations: the reason the ground truth is a majority over repetitions, and the
  reason Qwen's and gpt-oss's recordings are reported as a finding rather than as results.
- OpenTelemetry. *Semantic conventions for generative AI: agent spans.*
  https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-agent-spans.md
  The span model of the trace export (`tracing/otel.py`).
