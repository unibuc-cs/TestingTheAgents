# TRACE-Eval

After a change to an LLM agent system (a skill, a prompt, harness code, a config key), which tests should run, in
what order, and when can we stop? The aim is to spend fewer tokens and less time and still catch regressions.

This repository is a testbed for that question. It contains a small, working multi-agent app whose agents are
played by a real model (Gemma 4 E4B or Qwen3.8-27B), 180 tests, 43 controlled changes with known effects, and 7
selection strategies. The strategies are compared by replaying recorded runs. One of them, `adaptive_bayes`, is the
method this project proposes, and `traceeval check` runs it live on one change.

## Run it

The tests and the spec-driven development (SDD) demo replay Gemma's recorded answers, stored in
[`tests/cassettes/`](tests/cassettes/), so they need no GPU and no API key:

```bash
pip install -e ".[dev]"
pytest -q                                                   # one to two minutes
traceeval sdd --workdir runs/sdd                            # spec-driven development demo
```

Recording an experiment needs the model, served either from the GPU server (see
[docs/EXPERIMENT.md](docs/EXPERIMENT.md)) or from a local GPU with `--backend hf`. `--backend vllm` runs Gemma and
`--backend llm` runs Qwen.

```bash
scripts/gpu_remote.sh up gemma
traceeval experiment --backend vllm --workdir runs/gemma5 --reps 3    # about an hour
# -> runs/gemma5/results/report.md  (tables + 3 figures)
scripts/gpu_remote.sh down
```

The prototype, `traceeval check`, checks one change live. The proposed method picks a test, and the test runs on
the changed app with the real model. The outcome decides what runs next, and the check ends with a verdict.

```bash
traceeval check skill_routing_drop_approval --history runs/gemma5 --budget 0.2      # a change from the catalog
traceeval check path/to/my-copy-of-sut --history runs/qwen5 --backend llm           # your own edit, with Qwen
```

`--history` points to an experiment recorded with the same model and the same version of the app. It tells the
method what each test costs and which code it runs.

## What is in it

1. Tests live in [`traceeval/catalog/`](traceeval/catalog/) as YAML. Each has a request, a context, and
   deterministic checks on the final state, the tool calls and the response. Two of them also have their answer
   judged by a model against a rubric. The judge is Gemma or Qwen, set with `TRACEEVAL_JUDGE`, and by default it
   is the model playing the agents.
2. The app under test, ContentOps, lives in [`traceeval/sut/`](traceeval/sut/) and is described in
   [docs/CONTENTOPS.md](docs/CONTENTOPS.md). It has [agents](traceeval/sut/agents/) defined in YAML,
   [skills](traceeval/sut/skills/) that each carry a machine-readable procedure
   ([example `SKILL.md`](traceeval/sut/skills/publishing-workflow/SKILL.md)), [tools](traceeval/sut/tools/) and a
   [config file](traceeval/sut/config/runtime.yaml). Gemma 4 E4B plays the agents, locally, on a GPU server, or
   from its recorded answers. `--backend llm` plays them with Qwen3.8-27B on the GPU server, or with any other
   OpenAI-compatible endpoint.
3. Changes are the 43 entries in [`traceeval/mutation/catalog.py`](traceeval/mutation/catalog.py), each applied as
   an edit to a copy of the app's files. Running the full suite on each change gives the ground truth: which tests
   reveal which change.
4. Strategies in `traceeval/selection/` pick tests under a token budget. They see the diff of the code without
   comments, the baseline traces (which agents, skills, tools, config keys and code lines each test touched on the
   unchanged app), the test catalog and the outcomes of the other changes. They never see the outcome of the
   change being evaluated. [`strategies.py`](traceeval/selection/strategies.py) holds the baselines,
   [`reproduced.py`](traceeval/selection/reproduced.py) two published methods reproduced as baselines (CASPER's
   slices and Risk-Aware Adaptive Evaluation's bandit, neither of which looks at the diff) and
   [`adaptive_bayes.py`](traceeval/selection/adaptive_bayes.py) the proposed method. The same file holds two
   variants that compare text measures, `adaptive_bayes_tfidf` and `adaptive_bayes_notext`, and one variant
   without the mandatory-coverage rule, `adaptive_bayes_nomandatory`.
5. The report shows, for each strategy, how many changes it catches for how many tokens and how much time, how
   many of the changes that break a safety property it catches, how much it spends on harmless changes, and
   whether the adaptive one stops at the right moment. It also gives the coverage of the suite and of each change.

## Main results

These results come from a recording in which Gemma 4 E4B played the agents of the current app (176 tests, 43
changes, three repetitions per test; the other four, WF2-03 and the three cases with settings of their own, came
later). Of the 34 regressions, 29 are revealed by at least one test. Gemma ignores the other five either way: it
behaves the same with or without the change. No benign change, one meant to break nothing, fails a test. The table
gives the share of those 29 that each strategy detects with a nominal budget of 20% of the full-suite tokens, and
what it actually spends:

| strategy | detected | tokens spent | time spent |
|---|---|---|---|
| `declared`: hand-written dependencies | 61% | 6.8% | 6.9% |
| `observed`: dependencies seen in traces | 86% | 15% | 15% |
| `ir_tfidf`: text similarity to the diff | 92% | 20% | 20% |
| `casper_slices`: CASPER's slices, reproduced | 50% | 20% | 22% |
| `risk_aware_ts`: Risk-Aware Adaptive Evaluation, reproduced | 59% | 20% | 21% |
| `adaptive_bayes`: the proposed method | 79% | 2.9% | 3.1% |

The adaptive method is the only one that leaves budget unspent. It stops as soon as it is confident, and it never
calls a change that breaks nothing a regression. Its misses are mostly narrow regressions, revealed by one to
five tests, where it concludes too early that nothing broke. Of the 21 changes that break a safety property, it
catches 86%. The two reproduced methods look at the traces and the outcomes but not at the diff, and sit between
random (52%) and the change-aware strategies. The full numbers are in the
[Gemma report](docs/results/gemma5/report.md).

Qwen3.8-27B's recording of the same app is not a clean ground truth. It records every benign change as revealed by
two to five tests, for two reasons. Six tests answer differently when run 64 at a time over three servers than when
run one at a time: the two it judges itself, the one at the 60-character boundary and three long workflows. And
some of its answers vary from run to run even under identical conditions. gpt-oss-120b, a third model, varies even
more, and five repetitions instead of three do not settle its vote. The models are used as they are served, so
these recordings are reported as a finding rather than as results ([EXPERIMENT.md](docs/EXPERIMENT.md) §7).

## Features asked for by Adobe's AEM team

The AEM team listed what they lack today and want in the prototype. Their requirements and follow-up questions
are summed up in [docs/AEM_ALIGNMENT.md](docs/AEM_ALIGNMENT.md), together with the plan and its status.

| feature | status |
|---|---|
| Catalog of properties, each with a category, how it is checked, a mandatory flag and a threshold ([`properties.yaml`](traceeval/catalog/properties.yaml)). Reports give pass rates against the thresholds and the share of affected properties each strategy covered | done |
| Drafting the catalog with a model, from the requirements only (skills' rules, agents, config guards, specs) and within fixed limits, for people to edit: `traceeval properties draft`, then `apply` | done; Qwen's draft is in [`docs/properties/draft_qwen/`](docs/properties/draft_qwen/) |
| Coverage from several angles, in the report and in `traceeval check`. For the suite: each dimension (agents, features, skills, tools, tool error paths, config, setting values, properties, workflows, execution paths, risk), declared and observed, with what no test covers, and per agent, skill, tool and feature the tests that declare it and the tests that invoke it (`traceeval coverage`). For each change: the changed components exercised, the affected properties checked, the affected workflows run, the affected features reached and the refusals in the changed code reached | done |
| Mandatory properties in the method: while the budget allows, a run that has found no regression does not end until every mandatory property the change may affect has been tested | done (`adaptive_bayes`) |
| Test selection, prioritization and stopping under a token budget | done (`adaptive_bayes`, `traceeval check`) |
| Per-test metadata: agents, skills, tools, config, workflow, risk, cost, history (declared and observed) | done |
| Trace assertions: final state, required and forbidden tools, attempts, audit, step limit, agent order, tool order | done |
| Workflows, where one prompt runs 2–5 agents. The orchestrator plans, passes each step its instruction and the ids of earlier steps, asks a person before publishing, scheduling or taking pages down, and stops at a failed step | done: six workflows of two to five agents (campaign launch, site optimization, legal takedown, localized price update, rollback of a broken release, privacy request), each with a variant where a step must stop |
| Agents modelled on AEM's: brand governance, data insights, site optimization, and asset search in the assets agent | done |
| Environment failures kept apart. A run broken by the model server or the network is marked `INFRA_INVALID` and left out of pass rates and replays, so it never counts against the agent. `traceeval check` stops instead of giving a verdict | done |
| OpenTelemetry export of traces (`traceeval run --otel`), with the plan, the routing decisions and the approvals as span events | done |

## Spec-driven development on the same testbed

`traceeval sdd` checks 25 pull requests against five change requests written as machine-checkable specs, kept in
[`traceeval/specs/`](traceeval/specs/). Each spec is built from clauses picked from a
[catalog of templates](traceeval/spec/catalog.yaml). Two of the pull requests are the unchanged code, which the
specs check as it stands. The others change one to four files. The command writes an evidence report: which
clause failed, the counterexample or the misplaced code, the level of assurance reached and the level required
(from example-tested up to proven), and what a coding agent had to read and run. `traceeval sdd draft` has a
model draft a spec from a prose request, for a person to confirm.

Start with [docs/SDD_GUIDE.md](docs/SDD_GUIDE.md) if you are new to spec-driven development, or with
[docs/SDD_DEMO.md](docs/SDD_DEMO.md) for the results. The report is in [docs/sdd/report.md](docs/sdd/report.md).

## Further reading

- [docs/DEMO.md](docs/DEMO.md): the 20-minute walkthrough for the AEM team, with the commands and what each shows.
- [docs/EXPERIMENT.md](docs/EXPERIMENT.md): the experiment with Gemma 4 E4B and Qwen3.8-27B. Where the models run, the GPU server script, the recorded answers and the commands to type.
- [docs/STUDY_GUIDE.md](docs/STUDY_GUIDE.md): the whole repository in diagrams, focused on the SDD layer, with a 2–3 hour reading plan.
- [docs/USER_GUIDE.md](docs/USER_GUIDE.md): how the pieces fit, how to read the report, how to add a test, a change or a strategy.
- [docs/RESEARCH_PLAN.md](docs/RESEARCH_PLAN.md): the research framing, opening with a short summary. It covers the research questions, method, results, roadmap and paper plan.
- [docs/related_work.md](docs/related_work.md): how this work relates to the literature.
- [CLAUDE.md](CLAUDE.md): conventions for coding agents working in the repo.

Status: prototype v0.1. The agents and the judge run on real models only. Running OpenAI's models through the
`llm` backend is on hold until API tokens are available. An adapter that adds tau2-bench, a public agent
benchmark, as a second system under test is planned ([docs/RESEARCH_PLAN.md](docs/RESEARCH_PLAN.md) §6).
