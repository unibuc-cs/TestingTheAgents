# TRACE-Eval

After a change to an LLM agent system (a skill, a prompt, the agent runtime, a config key), which tests should run,
in what order, and when can we stop? The aim is to spend fewer tokens and less time and still catch regressions.

This repository is a testbed for that question: a small, working multi-agent application whose agents are played by
a model, a catalog of tests, changes written by hand and changes generated from the app, and eleven selection
strategies. Its answer is *replay first*: a change is replayed against the answers the model gave the current app,
and a test whose requests to the model do not change needs no model at all. A strategy then orders the tests the
change reaches, and a threshold set on past changes says when to stop. Everything is compared offline, on recorded
runs, and `traceeval check` checks one change live.

## The pieces, and how they fit

```mermaid
flowchart LR
    subgraph once["recorded once, with the model"]
        C["test catalog"] --> B["every test on the<br/>current app, traced"]
        M["controlled changes"] --> V["changed copies<br/>of the app"]
        V --> R["every test on<br/>each changed copy"]
    end
    B --> F["per test: dependencies,<br/>cost, pass rate"]
    B --> K["cassette: the answers<br/>the model gave"]
    R --> G["ground truth: which test<br/>reveals which change"]
    V --> D["change set: the diff<br/>as components"]
    K --> Y["replay-first: the tests<br/>the change reaches"]
    V --> Y
    F --> S["a strategy picks tests<br/>under a token budget"]
    D --> S
    Y --> S
    S --> E["evaluation: look up the<br/>recorded outcome"]
    G --> E
    E --> P["report: detection, cost,<br/>coverage, verdicts"]
```

- **The application**, ContentOps, lives in [`traceeval/sut/`](traceeval/sut/): an orchestrator and ten specialist
  agents defined in YAML, skills that each carry a machine-readable procedure, tools over deterministic services,
  and one config file. The agents are played by a model: Gemma 4 E4B by default, Qwen3.8-27B or gpt-oss-120b
  through an OpenAI-compatible endpoint. [docs/CONTENTOPS.md](docs/CONTENTOPS.md) describes it.
- **The tests** live in [`traceeval/catalog/`](traceeval/catalog/) as YAML. Each has a request, a context and
  checks on the final state, the tool calls and the answer. Each test names the properties it checks, ids from a
  catalog of properties ([`properties.yaml`](traceeval/catalog/properties.yaml)): behavioural requirements such as
  "a page is never published with broken links", some of them release blockers.
- **A traced run** of every test on the current app records, per test, the components it touched (agents, skills,
  tools, config keys, code lines), its cost in tokens and its pass rate. These are its observed dependencies, as
  opposed to the declared ones its author wrote.
- **The changes** are the entries of [`traceeval/mutation/catalog.py`](traceeval/mutation/catalog.py), each applied
  as an edit to a copy of the app. The diff becomes a change set: the components it touches, in the same
  identifiers the traces use. Running the whole suite on each changed copy gives the ground truth: a test *reveals*
  a change when it passes on the current app and fails on the changed copy, by majority over the repetitions. A
  change is a regression when at least one test reveals it. Three batches by hand, and twenty drawn at random,
  bundle two to nine changes, as a nightly run does; the check then also names the components it blames
  ([docs/RESEARCH_PLAN.md](docs/RESEARCH_PLAN.md) §5.6). A generator
  ([`traceeval/mutation/generator.py`](traceeval/mutation/generator.py)) makes 692 more changes mechanically, one
  per place an edit of its kind applies to; they have no label, and the recording says which a test reveals.
- **Replay-first** ([`traceeval/experiment/replay_first.py`](traceeval/experiment/replay_first.py)): the recording
  keeps every answer the model gave the current app. Run on a changed copy with those answers, a test either
  replays to the end, and its outcome there is known for no tokens, or diverges at the first request the current
  app never made, and needs the model from there on. A strategy then orders the diverged tests only.
- **The strategies** in [`traceeval/selection/`](traceeval/selection/) pick tests under a token budget from the
  change set, the traces, the costs and the pass rates, and from the outcomes of the other recorded changes. They
  never see the outcome of the change under evaluation. Eight are baselines, two are methods from the literature
  adapted to the testbed (CASPER and Risk-Aware Adaptive Evaluation, neither of which reads the diff;
  [docs/REFERENCES.md](docs/REFERENCES.md)), and `adaptive_bayes` is ours: an order that also stops. All are run
  the same way: a test the model already fails on the current app is not run, and a run ends at its first
  failure.
- **The report** compares the strategies: the regressions caught for the tokens and the time spent, with intervals
  over the changes, the changes that break a safety property, what is spent on the changes no test reveals, the
  verdict each run ends with, the coverage of the suite and of each change, and the same strategies replay-first.

## How replay-first works

The recording keeps only the model's answers, each under the exact request that got it: the prompt, every message
so far with its tool results, the tools offered, the decoding settings. On a changed copy every test runs with the
model's calls answered from those answers, and everything else runs as the copy has it: the harness, the tools, the
services and the test's checks.

| the change alters | what the replay sees | the test |
|---|---|---|
| what an agent is sent up front: its prompt, skills, tools and their descriptions | the first request of the agent's conversation is new | diverges there, and goes to the model |
| what a tool returns: its code, a service, the starting data | a tool result differs, and with it the next request | diverges there, and goes to the model |
| only state the model never reads | every request is one the original app made; the checks see the new state | replays to its outcome: a failure if the change broke it |
| nothing the test's run touches | every request is one the original app made | replays to its recorded outcome |

The replayed outcome is the live one under two conditions: the model as served gives the same request the same
answer (R), and the app's code is deterministic given the answers (D). The empty change measures R for a model and
its server. D holds here by construction, and the original app replayed against its own answers checks it
([docs/RESEARCH_PLAN.md](docs/RESEARCH_PLAN.md) §3.3, [the paper](docs/paper/main.tex) §4). This is not the prompt
caching of model providers, which reuses part of the computation and still calls the model: a request the
recording holds makes no call at all.

What it is for:

- a change that no test can tell from the original app is settled without the model, and so is one that a replayed
  test fails;
- a strategy orders only the tests the change reaches, each with a cost known in advance: at most its tokens after
  the divergence point;
- once all of those pass, the clean verdict leaves nothing the change reaches untested;
- for a batch of changes, a failing test's suspects are the members whose own replay reaches it, found for free.

## Run it

The test suite (`pytest`) and the spec-driven development (SDD) demo replay Gemma's recorded answers, stored in
[`tests/cassettes/`](tests/cassettes/), so they need no GPU and no API key:

```bash
pip install -e ".[dev]"
pytest -q                                                   # one to two minutes
traceeval sdd --workdir runs/sdd                            # spec-driven development demo
```

uv is configured to copy packages rather than hardlink them, avoiding Windows cloud-storage hardlink errors.

Recording an experiment needs a model, used as it is served: Gemma on the GPU server (`--backend vllm`), or Qwen,
gpt-oss or any other OpenAI-compatible endpoint (`--backend llm`). [docs/EXPERIMENT.md](docs/EXPERIMENT.md) §3 says
where each model runs.

```bash
scripts/gpu_remote.sh up gemma
traceeval experiment --backend vllm --workdir runs/gemma8 --reps 5    # about two hours
# -> runs/gemma8/results/report.md  (tables + 4 figures)
scripts/gpu_remote.sh down
```

The prototype, `traceeval check`, checks one change live. It replays the change first, in seconds and without the
model. Then our method picks a test among those that diverge, the test runs live on the changed app, the outcome
decides what runs next, and the check ends with a verdict. `--floor` adds the coverage floor before a clean
verdict, and for a batch a failing test is followed by its suspects among the members.

```bash
traceeval check skill_routing_drop_approval --history runs/gemma8 --budget 0.2      # a change from the catalog
traceeval check path/to/my-copy-of-sut --history runs/gemma8                        # your own edit
traceeval check skill_seo_drop_length_guard --history runs/gemma8_gen --miss-rate 0.1   # clean at a miss rate
traceeval check skill_seo_drop_length_guard --history runs/gemma8_gen --miss-rate 0.1 --floor   # and covered
```

`--history` points to an experiment recorded with the same model and the same version of the app. It holds the
answers the model gave that app, what each test costs and which code it runs
([docs/EXPERIMENT.md](docs/EXPERIMENT.md) §5).

## Main results

From Gemma's recordings of the current app: 180 tests, 43 hand-written changes and 691 of the 692 changes
generated from the app, five repetitions each ([docs/RESEARCH_PLAN.md](docs/RESEARCH_PLAN.md) §5.7 to §5.9).

| per change, on the 43 hand-written changes | tokens, share of the full suite | regressions found |
|---|---|---|
| an order of the whole suite, stopped at the first failure | 16% to 47% | 98% to 100% |
| the whole suite through a cache of the model's answers | 13.5% | all |
| replay first: an order of the reached tests, stopped at the first failure | 5% to 7% | 98% to 99% |
| replay first, stopped early by `adaptive_bayes` | 1.7% | 93% |

- **The replay settles a fifth of the changes without a model**, in seconds: no test diverges, or a test replays
  to a failure. The other changes reach 40 of the 180 tests on average and 12 to 15 at the median; an edit to a
  prompt every request reads reaches 153.
- **What replays is the outcome, not every model call.** 2% to 3% of the requests sent again get another answer,
  and no test ends otherwise. The other answers come from two settings of the server, many tests at a time and its
  prefix cache. One test at a time and without the cache, Gemma and Qwen give every request its recorded answer
  again, across a restart of the server too; Gemma's suite then takes ten times as long.
- **The cache is the baseline.** Replaying recorded answers is an old idea (test factoring, 2005), and a cache
  already saves most of the tokens ([docs/related_work.md](docs/related_work.md) §8). What the replay adds is
  knowing, before any model call, which tests a change reaches: a regression then costs 2% to 3% of the suite
  instead of 12%. A change that breaks nothing still costs every test it reaches, 12% to 14%.
- **Stopping with a miss rate you choose.** A threshold set on past changes, one per group of changes, keeps the
  share of regressions called clean at its target, also on changes unlike the past ones. On the 25 hand-written
  regressions the replay leaves open, `adaptive_bayes` misses none at a 10% target, for 15% of the suite instead
  of 37%. One threshold for all changes is cheaper, but it misses 87% of the regressions among edits to prompts
  and prose.
- **A coverage floor under the threshold.** Before a clean verdict, the cheapest reached tests that cover every
  changed component and affected mandatory property run too: every clean verdict then covers what the change
  touches, for a few tenths of a point of the suite, and a few more regressions are caught. A fixed minimal set
  of 15 tests covers as much and misses 13 of the 25 regressions: covering is not catching.
- **Live**, `traceeval check --miss-rate 0.1 --confirm` finds all 28 regressions and raises no false alarm, for
  2.8% of the suite per check, and it says what its threshold rests on.
- **The same holds** on 342 generated changes the strategies never learned from, and for a second model: with
  Qwen, recorded one test at a time, every order of the reached tests finds all 32 of its regressions for 4% to 5%
  of the suite.
- **Without the replay**, reading the change pays: an order by the traces, by the diff's text or by a model trained
  on the other changes finds 86% to 93% of the regressions within a 20% budget, hand-written dependencies 61%, and
  the two adapted methods stay at a random order's level. `adaptive_bayes` finds the most at a 5% budget.

The full numbers, with intervals over the changes, are in the reports of the recordings
([hand-written](docs/results/gemma8/report.md), [generated](docs/results/gemma8_gen/report.md),
[Qwen](docs/results/qwen8/report.md)), and the take-aways in [RESEARCH_PLAN.md](docs/RESEARCH_PLAN.md) §5.5. What
follows from them is the plan in [TODO.md](TODO.md).

**Batches** of two to nine changes, as a nightly run sees them: the replay stays exact, and live checks find 19
of the 20 batches a test reveals, with no false alarm. When a test fails, the members whose own replay reaches it
are the suspects, for no tokens: they always held the member that fails it alone, two members of six on average,
and halving them finds that member in under one run of the test instead of two and a half
([docs/RESEARCH_PLAN.md](docs/RESEARCH_PLAN.md) §5.6). The recordings of Qwen and gpt-oss made many tests at once
are not clean ground truths: their answers vary with the batch ([docs/RESEARCH_PLAN.md](docs/RESEARCH_PLAN.md)
§5.4).

## Built for the Adobe Team

The Adobe Team, who work on Adobe Experience Manager (AEM), Adobe's content management system, listed what they
lack today and want in the prototype, and the testbed has it:

- a catalog of properties, some of them release blockers;
- coverage of the suite and of each change;
- workflows of two to five agents with plans and approvals;
- budgets with early stopping;
- OpenTelemetry export of the traces.

[docs/AEM_ALIGNMENT.md](docs/AEM_ALIGNMENT.md) checks each requirement in its §2, with the Adobe Team's answers,
and its §4 has the next steps.

## Spec-driven development on the same testbed

`traceeval sdd` checks 25 pull requests against five change requests written as machine-checkable specs
([`traceeval/specs/`](traceeval/specs/)) and writes an evidence report: which clause failed and with what
counterexample, and the level of assurance reached, from example-tested up to proven. `traceeval sdd draft` has a
model draft a spec from a prose request, for a person to confirm. [docs/SDD_GUIDE.md](docs/SDD_GUIDE.md) explains
the layer and [docs/SDD_DEMO.md](docs/SDD_DEMO.md) has the results.

## How to read the documentation

[docs/README.md](docs/README.md) lists the documents by what you want to do and gives the reading order; each
document uses only what the ones before it define.
