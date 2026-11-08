# TRACE-Eval

**Question.** After a change to an LLM agent system (a skill, a prompt, harness code, a config key), which
tests should run, in what order, and when can we stop? The aim is to spend fewer tokens and less time and
still catch regressions.

**What this repo is.** A testbed for that question. It contains a small working multi-agent app whose agents
are played by a real model (Gemma 4 E4B or Qwen3.8-27B), 168 tests, 33 controlled changes with known effects, and
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
traceeval experiment --backend vllm --workdir runs/gemma4 --reps 3    # ~30 min
# -> runs/gemma4/results/report.md  (tables + 3 figures)
scripts/gpu_remote.sh down
```

**The prototype.** `traceeval check` checks one change live. The proposed method picks a test, the test runs on
the changed app with the real model, the outcome decides what runs next, and it stops with a verdict:

```bash
traceeval check code_retry_drop_idempotency --history runs/gemma4 --budget 0.2      # a change from the catalog
traceeval check path/to/my-copy-of-sut --history runs/qwen4 --backend llm           # your own edit, with Qwen
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
3. **Changes** are the 33 entries in [`traceeval/mutation/catalog.py`](traceeval/mutation/catalog.py), applied as edits to a copy of the app's files. Running the
   full suite on each gives the ground truth: which tests reveal which change.
4. **Strategies** in `traceeval/selection/` pick tests under a token budget. They see the diff of the code (without comments),
   the baseline traces (which agents, skills, tools, config keys and code lines each test touched), the test
   catalog and the outcomes of the other changes, but never the outcome of the change being evaluated.
   [`strategies.py`](traceeval/selection/strategies.py) holds the baselines, [`adaptive_bayes.py`](traceeval/selection/adaptive_bayes.py) the method (with two variants that compare text measures, `adaptive_bayes_tfidf` and `adaptive_bayes_notext`, and one without its mandatory-coverage rule, `adaptive_bayes_nomandatory`).
5. **The report** shows how many changes each strategy catches for how many tokens, how much it spends on
   harmless changes, whether the adaptive one stops at the right moment, and the coverage of the suite and of each
   change.

Main results, with Gemma and with Qwen3.8-27B playing the agents (three repetitions per test; recorded on the app as
it was before the multi-agent workflows, with 136 tests, and recorded again once they are complete): hand-written
dependencies catch 62–71% of regressions. Trace-based selection catches 88–90% within a budget of 20% of the
full-suite tokens. The adaptive method catches 81–83% while spending 5% of those tokens. Under Gemma it never calls a change that breaks nothing a regression; under Qwen it does in 8% of the replays
of benign changes, when a test that passed all three times on the original app failed once in three runs
on the changed copy (Qwen's answers are not perfectly repeatable on a busy server).
Gemma misses five of the 26 regressions, because it ignores the guards they touch either way; Qwen misses two.
See the [Gemma](docs/results/gemma4/report.md) and [Qwen](docs/results/qwen4/report.md) reports and
[docs/EXPERIMENT.md](docs/EXPERIMENT.md).

## Features asked for by Adobe's AEM team

The AEM team listed what they lack today and want in the prototype (requirements and follow-up questions, summed
up in [docs/AEM_ALIGNMENT.md](docs/AEM_ALIGNMENT.md) with the plan and status):

| feature | status |
|---|---|
| **Catalog of properties** with categories, how each is checked, mandatory flags and thresholds ([`properties.yaml`](traceeval/catalog/properties.yaml)); reports give pass rates against thresholds and the share of affected properties each strategy covered | done |
| **Drafting the catalog with a model** from the requirements only (skills' rules, agents, config guards, specs), within fixed limits, for people to edit (`traceeval properties draft`, then `apply`) | done; the Qwen run comes with the GPU work |
| **Coverage** from several angles: of the suite per dimension (agents, skills, tools, config, properties, execution paths, risk; declared and observed, with what no test covers), and of each change (changed components exercised, affected properties checked), in the report and in `traceeval check` | done; workflows join with them |
| **Mandatory properties in the method**: a check that found no regression does not end before every mandatory property the change may affect has a test | done (step 5 of `adaptive_bayes`) |
| Test selection, prioritization and stopping under a token budget | done (`adaptive_bayes`, `traceeval check`) |
| Per-test metadata: agents, skills, tools, config, risk, cost, history (declared and observed) | done |
| Trace assertions: final state, required and forbidden tools, attempts, audit, step limit, agent order, tool order | done |
| Workflows: one prompt that runs 2–5 agents: the orchestrator plans, passes each step its instruction and the ids of earlier steps, asks a person before publishing, scheduling or taking pages down, and stops at a failed step | planning, hand-offs and approvals done; W1 (campaign launch, five agents) and W3 (legal takedown) done; W2, W4–W6 planned |
| New agents modelled on AEM's: brand governance, data insights, site optimization, and asset search in the assets agent | done |
| OpenTelemetry export of traces, with plans and routing decisions as events | planned |

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
