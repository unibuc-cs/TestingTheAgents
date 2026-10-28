# TRACE-Eval

**Question.** After a change to an LLM agent system (a skill, a prompt, harness code, a config key), which
tests should run, in what order, and when can we stop — so that tokens and time drop but regressions are
still caught?

**What this repo is.** A testbed to answer that question without needing an LLM: a small but real
multi-agent app, 134 tests, 35 controlled changes with known effects, and 7 selection strategies compared
by replaying recorded runs. One of the strategies (`adaptive_bayes`) is the proposed method.

## Run it (5 minutes, no API keys)

```bash
pip install -e ".[dev]"
pytest -q                                                   # 22 tests, ~40 s
traceeval experiment --workdir runs/exp1 --reps 3 --seeds 10
# -> runs/exp1/results/report.md  (tables + 3 figures)
```

## The five things to know

1. **Tests** live in [`traceeval/catalog/`](traceeval/catalog/) (YAML). Each has a request, context, and deterministic checks on the
   final state / tool calls / response.
2. **The app under test** lives in [`traceeval/sut/`](traceeval/sut/): 8 agents defined in YAML, 10 skills ([example `SKILL.md`](traceeval/sut/skills/publishing-workflow/SKILL.md), each with
   a machine-readable procedure), 22 tools, a config file. A *simulated* agent follows the skills so runs are
   free; an *LLM* backend can replace it (`--backend llm`, OpenAI-compatible endpoint).
3. **Changes** are the 35 entries in [`traceeval/mutation/catalog.py`](traceeval/mutation/catalog.py), applied as real file edits. Running the
   full suite on each gives the ground truth: which tests reveal which change.
4. **Strategies** in `traceeval/selection/` see only the diff plus the baseline traces (which agents, skills,
   tools, config keys and code lines each test touched) and pick tests under a token budget.
   [`strategies.py`](traceeval/selection/strategies.py) = baselines, [`adaptive_bayes.py`](traceeval/selection/adaptive_bayes.py) = the method.
5. **The report** answers: how many changes does each strategy catch for how many tokens, how much does it
   waste on harmless changes, and does the adaptive one stop at the right moment.

Headline from `runs/exp1`: hand-written dependencies catch 66% of regressions; trace-based selection catches
90% for 20% of the full-suite tokens; the adaptive method catches 86% for 11–26% and stops correctly on
benign changes. ([experiment 1 report](docs/results/exp1/report.md), [flaky-agent condition](docs/results/exp2_flaky/report.md))

## Spec-driven development on the same testbed

`traceeval sdd` applies five change requests written as machine-checkable specs
([`traceeval/specs/`](traceeval/specs/)) to 24 pull requests (1–4 files each) and writes an evidence report: which
clause failed, the counterexample or the misplaced code, the assurance rung reached (example-tested …
proven), and what a coding agent had to read and run. Start with [docs/SDD_DEMO.md](docs/SDD_DEMO.md);
the report is in [docs/sdd/report.md](docs/sdd/report.md).

## Read more only if you need it

- [docs/STUDY_GUIDE.md](docs/STUDY_GUIDE.md) — the whole repository in diagrams, oriented towards the SDD layer; a 2–3 hour reading plan.
- [docs/USER_GUIDE.md](docs/USER_GUIDE.md) — how the pieces fit, how to read the report, how to add a test / change / strategy.
- [docs/RESEARCH_PLAN.md](docs/RESEARCH_PLAN.md) — the research framing (RQs, method, results, roadmap, paper plan). Starts with a TL;DR.
- [docs/related_work.md](docs/related_work.md), [docs/tau2_integration.md](docs/tau2_integration.md) — literature positioning; tau2-bench as a second system under test.
- [CLAUDE.md](CLAUDE.md) — conventions for coding agents working in the repo.

Status: prototype v0.1. Simulated backend fully reproducible; LLM backend tested against a scripted client
only; tau2-bench adapter designed, not implemented.
