# TRACE-Eval

**Question.** After a change to an LLM agent system (a skill, a prompt, harness code, a config key), which
tests should run, in what order, and when can we stop? The aim is to spend fewer tokens and less time and
still catch regressions.

**What this repo is.** A testbed for that question. It contains a small working multi-agent app whose agents
are played by a real model (Gemma 4 E4B or Qwen3.8-27B), 136 tests, 38 controlled changes with known effects, and
7 selection strategies, which are compared by replaying recorded runs. One of them, `adaptive_bayes`, is the
proposed method; `traceeval check` runs it live on one change.

## Run it

The tests and the SDD demo replay Gemma's recorded answers ([`tests/cassettes/`](tests/cassettes/)), so they need
no GPU and no API key:

```bash
pip install -e ".[dev]"
pytest -q                                                   # ~60 s
traceeval sdd --workdir runs/sdd                            # spec-driven development demo
```

Recording an experiment needs the model: on the GPU server (see [docs/EXPERIMENT.md](docs/EXPERIMENT.md)), or
on a local GPU with `--backend hf`. `--backend vllm` is Gemma, `--backend llm` is Qwen.

```bash
scripts/gpu_remote.sh up gemma
traceeval experiment --backend vllm --workdir runs/gemma3 --reps 3    # ~30 min
# -> runs/gemma3/results/report.md  (tables + 3 figures)
scripts/gpu_remote.sh down
```

**The prototype.** `traceeval check` checks one change live. The proposed method picks a test, the test runs on
the changed app with the real model, the outcome decides what runs next, and it stops with a verdict:

```bash
traceeval check code_retry_disabled --history runs/gemma3 --budget 0.2              # a change from the catalog
traceeval check path/to/my-copy-of-sut --history runs/qwen3 --backend llm           # your own edit, with Qwen
```

`--history` is an experiment recorded with the same model and the same version of the app; it tells the method
what each test costs and which code it runs.

## What is in it

1. **Tests** live in [`traceeval/catalog/`](traceeval/catalog/) (YAML). Each has a request, a context, and deterministic checks on the
   final state, the tool calls and the response. Two also have their answer judged by a model against a rubric
   (Gemma or Qwen, `TRACEEVAL_JUDGE`; by default the model playing the agents).
2. **The app under test** ("ContentOps", described in [docs/CONTENTOPS.md](docs/CONTENTOPS.md)) lives in [`traceeval/sut/`](traceeval/sut/): [agents](traceeval/sut/agents/) defined in YAML, [skills](traceeval/sut/skills/) ([example `SKILL.md`](traceeval/sut/skills/publishing-workflow/SKILL.md), each with
   a machine-readable procedure), [tools](traceeval/sut/tools/) and a [config file](traceeval/sut/config/runtime.yaml). Gemma 4 E4B plays the agents (locally, on a GPU
   server, or from its recorded answers); `--backend llm` plays them with Qwen3.8-27B on the GPU server, or with
   any other OpenAI-compatible endpoint.
3. **Changes** are the 38 entries in [`traceeval/mutation/catalog.py`](traceeval/mutation/catalog.py), applied as edits to a copy of the app's files. Running the
   full suite on each gives the ground truth: which tests reveal which change.
4. **Strategies** in `traceeval/selection/` pick tests under a token budget. They see the diff of the code (without comments),
   the baseline traces (which agents, skills, tools, config keys and code lines each test touched), the test
   catalog and the outcomes of the other changes, but never the outcome of the change being evaluated.
   [`strategies.py`](traceeval/selection/strategies.py) holds the baselines, [`adaptive_bayes.py`](traceeval/selection/adaptive_bayes.py) the method.
5. **The report** shows how many changes each strategy catches for how many tokens, how much it spends on
   harmless changes, and whether the adaptive one stops at the right moment.

Main results, with Gemma and with Qwen3.8-27B playing the agents (three repetitions per test): hand-written
dependencies catch 61–64% of regressions. Trace-based selection catches 84–92% within a budget of 20% of the
full-suite tokens. The adaptive method catches 65–80% while spending 5–6% of those tokens, and never calls a
change that breaks nothing a regression. Gemma misses six of the 31 regressions, because it ignores the guards
they touch either way; Qwen reveals all 31. See the [Gemma](docs/results/gemma2/report.md) and
[Qwen](docs/results/qwen2/report.md) reports and [docs/EXPERIMENT.md](docs/EXPERIMENT.md).

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

- [docs/EXPERIMENT.md](docs/EXPERIMENT.md): the experiment with real models (Gemma 4 E4B, Qwen3.8-27B): where they run, the GPU server script, recorded answers, what to type.
- [docs/STUDY_GUIDE.md](docs/STUDY_GUIDE.md): the whole repository in diagrams, with the focus on the SDD layer, and a 2–3 hour reading plan.
- [docs/USER_GUIDE.md](docs/USER_GUIDE.md): how the pieces fit, how to read the report, how to add a test, a change or a strategy.
- [docs/RESEARCH_PLAN.md](docs/RESEARCH_PLAN.md): the research framing (RQs, method, results, roadmap, paper plan), opening with a TL;DR.
- [docs/related_work.md](docs/related_work.md), [docs/tau2_integration.md](docs/tau2_integration.md): literature positioning, and tau2-bench as a second system under test.
- [CLAUDE.md](CLAUDE.md): conventions for coding agents working in the repo.

Status: prototype v0.1. The agents and the judge run on real models only: Gemma 4 E4B, locally or on the GPU
server, and Qwen3.8-27B through the `llm` backend ([docs/EXPERIMENT.md](docs/EXPERIMENT.md)). An OpenAI backend is
planned. The tau2-bench adapter is designed but not implemented.
