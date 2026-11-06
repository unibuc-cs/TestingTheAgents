# TRACE-Eval

**Question.** After a change to an LLM agent system (a skill, a prompt, harness code, a config key), which
tests should run, in what order, and when can we stop? The aim is to spend fewer tokens and less time and
still catch regressions.

**What this repo is.** A testbed for that question that needs no LLM. It contains a small working
multi-agent app, 136 tests, 38 controlled changes with known effects, and 7 selection strategies, which are
compared by replaying recorded runs. One of them, `adaptive_bayes`, is the proposed method.

## Run it (5 minutes, no API keys)

```bash
pip install -e ".[dev]"
pytest -q                                                   # ~60 s
traceeval experiment --workdir runs/exp1 --reps 3 --seeds 10
# -> runs/exp1/results/report.md  (tables + 3 figures)
```

## What is in it

1. **Tests** live in [`traceeval/catalog/`](traceeval/catalog/) (YAML). Each has a request, a context, and deterministic checks on the
   final state, the tool calls and the response.
2. **The app under test** ("ContentOps", described in [docs/CONTENTOPS.md](docs/CONTENTOPS.md)) lives in [`traceeval/sut/`](traceeval/sut/): [agents](traceeval/sut/agents/) defined in YAML, [skills](traceeval/sut/skills/) ([example `SKILL.md`](traceeval/sut/skills/publishing-workflow/SKILL.md), each with
   a machine-readable procedure), [tools](traceeval/sut/tools/) and a [config file](traceeval/sut/config/runtime.yaml). A *simulated* agent follows the skills, so runs
   cost nothing. An *LLM* backend can replace it (`--backend llm`, OpenAI-compatible endpoint).
3. **Changes** are the 38 entries in [`traceeval/mutation/catalog.py`](traceeval/mutation/catalog.py), applied as edits to a copy of the app's files. Running the
   full suite on each gives the ground truth: which tests reveal which change.
4. **Strategies** in `traceeval/selection/` pick tests under a token budget. They see the diff of the code (without comments),
   the baseline traces (which agents, skills, tools, config keys and code lines each test touched), the test
   catalog and the outcomes of the other changes, but never the outcome of the change being evaluated.
   [`strategies.py`](traceeval/selection/strategies.py) holds the baselines, [`adaptive_bayes.py`](traceeval/selection/adaptive_bayes.py) the method.
5. **The report** shows how many changes each strategy catches for how many tokens, how much it spends on
   harmless changes, and whether the adaptive one stops at the right moment.

Main results from `runs/exp1`: hand-written dependencies catch 66% of regressions. Trace-based selection
catches 91% within a budget of 20% of the full-suite tokens. The adaptive method catches 84% while spending
5–7% of those tokens, and never calls a benign change a regression. See the [experiment 1 report](docs/results/exp1/report.md) and the [flaky-agent condition](docs/results/exp2_flaky/report.md).

## Spec-driven development on the same testbed

`traceeval sdd` checks 25 pull requests against five change requests written as
machine-checkable specs ([`traceeval/specs/`](traceeval/specs/), with clauses picked from a
[catalog of templates](traceeval/spec/catalog.yaml)). Two of the pull requests are the unchanged code, which
the specs check as it stands; the others change one to four files. It writes an evidence report: which clause failed, the
counterexample or the misplaced code, the assurance rung reached and the one required (example-tested …
proven), and what a coding agent had to read and run. `traceeval sdd draft` has a model draft a spec from a
prose request, for a person to confirm. Start with [docs/SDD_GUIDE.md](docs/SDD_GUIDE.md) if you are new to
it, or with [docs/SDD_DEMO.md](docs/SDD_DEMO.md) for the results. The report is in
[docs/sdd/report.md](docs/sdd/report.md).

## Further reading

- [docs/STUDY_GUIDE.md](docs/STUDY_GUIDE.md): the whole repository in diagrams, with the focus on the SDD layer, and a 2–3 hour reading plan.
- [docs/USER_GUIDE.md](docs/USER_GUIDE.md): how the pieces fit, how to read the report, how to add a test, a change or a strategy.
- [docs/RESEARCH_PLAN.md](docs/RESEARCH_PLAN.md): the research framing (RQs, method, results, roadmap, paper plan), opening with a TL;DR.
- [docs/related_work.md](docs/related_work.md), [docs/tau2_integration.md](docs/tau2_integration.md): literature positioning, and tau2-bench as a second system under test.
- [CLAUDE.md](CLAUDE.md): conventions for coding agents working in the repo.

Status: prototype v0.1. The simulated backend is fully reproducible. The LLM backend has been tested only
against a scripted client. The tau2-bench adapter is designed but not implemented.
