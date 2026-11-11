# By what you want to do

| you want to                                                                                                                                              | read |
|----------------------------------------------------------------------------------------------------------------------------------------------------------|---|
| understand the goals, the pieces and the main results                                                                                                    | [README](../README.md) |
| see the application the tests exercise: its users, agents, skills, tools and rules                                                                       | [CONTENTOPS.md](CONTENTOPS.md) |
| Adobe's platform, what Georgiana asked for, the features built for it, the next steps                                                                    | [AEM_ALIGNMENT.md](AEM_ALIGNMENT.md) |
| the research: the problem, the abstractions, the methods, the results, the take-aways, the roadmap                                                       | [RESEARCH_PLAN.md](RESEARCH_PLAN.md) |
| work in the repository: the vocabulary, how to read a report, how the method weighs a test, the controlled changes, how to add a test, a change or a strategy | [USER_GUIDE.md](USER_GUIDE.md) |
| record with a model: a local GPU server, the commands, recording and replay, what the recordings show, what the models get wrong                         | [EXPERIMENT.md](EXPERIMENT.md) |
| give or follow the demo for the AEM team, command by command                                                                                             | [DEMO.md](DEMO.md) |
| the full results of a recording: tables and figures                                                                                                      | [results/gemma7/report.md](results/gemma7/report.md), the results the README quotes; [results/qwen7/](results/qwen7/report.md) and [results/gptoss7/](results/gptoss7/report.md), the other two models |
| spec-driven development: what a spec is, how a pull request is judged against it, the assurance rungs                                                    | [SDD_GUIDE.md](SDD_GUIDE.md), then [SDD_DEMO.md](SDD_DEMO.md) for the results and [sdd/report.md](sdd/report.md) for the full report |
| read the code of the spec-driven development layer, with diagrams, in two to three hours                                                                 | [STUDY_GUIDE.md](STUDY_GUIDE.md) |
| the literature, the references and the paper                                                                                                             | [related_work.md](related_work.md), [REFERENCES.md](REFERENCES.md), `paper/main.tex` (build with `latexmk -pdf main`) |

## Reading order

Each document uses only what the ones before it define, so a first reading goes top to bottom. The spec-driven
development documents and the literature branch off the main line.

```mermaid
flowchart TD
    R["README<br/>the question, the pieces, the results"] --> A["CONTENTOPS.md<br/>the application under test"]
    A --> U["USER_GUIDE.md<br/>vocabulary, the report, the method's weights,<br/>the changes, how to extend"]
    U --> X["EXPERIMENT.md<br/>the models, a local GPU server, recording and replay"]
    X --> P["RESEARCH_PLAN.md<br/>problem, abstractions, methods, results,<br/>take-aways, roadmap"]
    P --> M["AEM_ALIGNMENT.md<br/>what the AEM team asked for,<br/>and the features built for it"]
    M --> D["DEMO.md<br/>the walkthrough for the AEM team"]
    X --> S["SDD_GUIDE.md, SDD_DEMO.md, STUDY_GUIDE.md<br/>spec-driven development, the add-on"]
    P --> W["related_work.md, REFERENCES.md, paper/<br/>the literature and the paper"]
```

## What else is in this folder

- `results/`: one folder per recording (`gemma7`, `qwen7`, `gptoss7`), each with the report and its three figures,
  and the follow-up experiments:
  - `gemma7/live_vs_replay.md`: the live check against the replay, change by change;
  - `gemma7/false_alarm_one_at_a_time.md`: the change behind the one live false alarm, recorded one test at a time;
  - `gemma7/noise_floor.md`: the empty change recorded fifteen times, against the number of runs;
  - `gemma7/batch_invariant.md`: why Gemma 4 cannot be served in vLLM's batch-invariant mode;
  - `gemma7/batches.md`: the three batches of changes, replayed and checked live;
  - `gemma7/batch_sweep.md`: twenty batches of two to eight changes drawn at random, replayed and checked live;
  - `gemma7/second_recording.md`: the whole experiment recorded a second time, on other GPUs, against
    `runs/gemma7`;
  - `qwen7/one_at_a_time.md`: Qwen's empty change recorded one test at a time, against its batched recording;
  - `qwen7/noise_floor.md`: the same change recorded fifteen times in batches, against the number of runs;
  - `gptoss7/one_at_a_time.md`: gpt-oss's empty change recorded one test at a time, against its baseline and its
    batched recording.
- `sdd/`: the spec-driven development report, its figures, and a spec drafted by Qwen from a change request, with
  its answer.
- `properties/draft_qwen/`: the catalog of properties as Qwen drafted it from the requirements, with the model's
  answers, so the draft can be replayed without a GPU.
- `diagrams/` and `figures/`: the Mermaid sources and the rendered images the guides use.
- `paper/`: the LaTeX paper, its bibliography and the overview figure.
