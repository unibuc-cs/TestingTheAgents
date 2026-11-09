# TRACE-Eval

**Question.** After a change to an LLM agent system (a skill, a prompt, harness code, a config key), which
tests should run, in what order, and when can we stop? The aim is to spend fewer tokens and less time and
still catch regressions.

**What this repo is.** A testbed for that question. It contains a small working multi-agent app whose agents
are played by a real model (Gemma 4 E4B or Qwen3.8-27B), 177 tests, 43 controlled changes with known effects, and
7 selection strategies, which are compared by replaying recorded runs. One of them, `adaptive_bayes`, is the
proposed method; `traceeval check` runs it live on one change.

## Run it

The tests and the SDD demo replay Gemma's recorded answers ([`tests/cassettes/`](tests/cassettes/)), so they need
no GPU and no API key:

```bash
pip install -e ".[dev]"
pytest -q                                                   # one to two minutes
traceeval sdd --workdir runs/sdd                            # spec-driven development demo
```

Recording an experiment needs the model: on the GPU server (see [docs/EXPERIMENT.md](docs/EXPERIMENT.md)), or
on a local GPU with `--backend hf`. `--backend vllm` is Gemma, `--backend llm` is Qwen.

```bash
scripts/gpu_remote.sh up gemma
traceeval experiment --backend vllm --workdir runs/gemma5 --reps 3    # about an hour
# -> runs/gemma5/results/report.md  (tables + 3 figures)
scripts/gpu_remote.sh down
```

**The prototype.** `traceeval check` checks one change live. The proposed method picks a test, the test runs on
the changed app with the real model, the outcome decides what runs next, and it stops with a verdict:

```bash
traceeval check skill_routing_drop_approval --history runs/gemma5 --budget 0.2      # a change from the catalog
traceeval check path/to/my-copy-of-sut --history runs/qwen5 --backend llm           # your own edit, with Qwen
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
3. **Changes** are the 43 entries in [`traceeval/mutation/catalog.py`](traceeval/mutation/catalog.py), applied as edits to a copy of the app's files. Running the
   full suite on each gives the ground truth: which tests reveal which change.
4. **Strategies** in `traceeval/selection/` pick tests under a token budget. They see the diff of the code (without comments),
   the baseline traces (which agents, skills, tools, config keys and code lines each test touched), the test
   catalog and the outcomes of the other changes, but never the outcome of the change being evaluated.
   [`strategies.py`](traceeval/selection/strategies.py) holds the baselines, [`adaptive_bayes.py`](traceeval/selection/adaptive_bayes.py) the method (with two variants that compare text measures, `adaptive_bayes_tfidf` and `adaptive_bayes_notext`, and one without its mandatory-coverage rule, `adaptive_bayes_nomandatory`).
5. **The report** shows how many changes each strategy catches for how many tokens and how much time, how many
   of the changes that break a safety property it catches, how much it spends on harmless changes, whether the adaptive one stops at the right moment, and the coverage of the suite and of each
   change.

## Main results

Gemma 4 E4B played the agents of the current app (176 tests, 43 changes, three repetitions per test; the Qwen
recording of the same app is under way). Of the 34 regressions, 29 are revealed by at least one test; the other
five are ones Gemma ignores either way, with or without the change. No benign change fails a test. The table gives
the share of those 29 that a strategy detects with a nominal budget of 20% of the full-suite tokens, and what it
actually spends:

| strategy | detected | tokens spent | time spent |
|---|---|---|---|
| `declared`: hand-written dependencies | 61% | 6.8% | 6.9% |
| `observed`: dependencies seen in traces | 86% | 15% | 15% |
| `ir_tfidf`: text similarity to the diff | 92% | 20% | 20% |
| `adaptive_bayes`: the proposed method | 79% | 2.9% | 3.1% |

The adaptive method is the only one that returns budget: it stops as soon as it is confident, and it never calls
a change that breaks nothing a regression. It misses mostly narrow regressions, revealed by one to five tests,
where it stops "clean" too early. Of the 21 changes that break a safety property it catches 86%. See the
[Gemma report](docs/results/gemma5/report.md).

## Features asked for by Adobe's AEM team

The AEM team listed what they lack today and want in the prototype (requirements and follow-up questions, summed
up in [docs/AEM_ALIGNMENT.md](docs/AEM_ALIGNMENT.md) with the plan and status):

| feature | status |
|---|---|
| **Catalog of properties** with categories, how each is checked, mandatory flags and thresholds ([`properties.yaml`](traceeval/catalog/properties.yaml)); reports give pass rates against thresholds and the share of affected properties each strategy covered | done |
| **Drafting the catalog with a model** from the requirements only (skills' rules, agents, config guards, specs), within fixed limits, for people to edit (`traceeval properties draft`, then `apply`) | done; Qwen's draft is in [`docs/properties/draft_qwen/`](docs/properties/draft_qwen/) |
| **Coverage** from several angles: of the suite per dimension (agents, skills, tools, config, properties, workflows, execution paths, risk; declared and observed, with what no test covers), and of each change (changed components exercised, affected properties checked, affected workflows run), in the report and in `traceeval check` | done |
| **Mandatory properties in the method**: a run that found no regression does not end before every mandatory property the change may affect has a test, while the budget allows | done (`adaptive_bayes`) |
| Test selection, prioritization and stopping under a token budget | done (`adaptive_bayes`, `traceeval check`) |
| Per-test metadata: agents, skills, tools, config, workflow, risk, cost, history (declared and observed) | done |
| Trace assertions: final state, required and forbidden tools, attempts, audit, step limit, agent order, tool order | done |
| Workflows: one prompt that runs 2–5 agents: the orchestrator plans, passes each step its instruction and the ids of earlier steps, asks a person before publishing, scheduling or taking pages down, and stops at a failed step | done: six workflows of two to five agents (campaign launch, site optimization, legal takedown, localized price update, rollback of a broken release, privacy request), each with a variant where a step must stop |
| New agents modelled on AEM's: brand governance, data insights, site optimization, and asset search in the assets agent | done |
| OpenTelemetry export of traces (`traceeval run --otel`), with the plan, the routing decisions and the approvals as span events | done |

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

- [docs/DEMO.md](docs/DEMO.md): the 20-minute walkthrough for the AEM team, with the commands and what each shows.
- [docs/EXPERIMENT.md](docs/EXPERIMENT.md): the experiment with real models (Gemma 4 E4B, Qwen3.8-27B): where they run, the GPU server script, recorded answers, what to type.
- [docs/STUDY_GUIDE.md](docs/STUDY_GUIDE.md): the whole repository in diagrams, with the focus on the SDD layer, and a 2–3 hour reading plan.
- [docs/USER_GUIDE.md](docs/USER_GUIDE.md): how the pieces fit, how to read the report, how to add a test, a change or a strategy.
- [docs/RESEARCH_PLAN.md](docs/RESEARCH_PLAN.md): the research framing (RQs, method, results, roadmap, paper plan), opening with a TL;DR.
- [docs/related_work.md](docs/related_work.md), [docs/tau2_integration.md](docs/tau2_integration.md): literature positioning, and tau2-bench as a second system under test.
- [CLAUDE.md](CLAUDE.md): conventions for coding agents working in the repo.

Status: prototype v0.1. The agents and the judge run on real models only. Running OpenAI's models through the
`llm` backend waits for API tokens. The tau2-bench adapter is designed but not implemented.
