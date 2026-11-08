# Running the experiment with a real model

This page explains how the experiment runs the agents on real models (Gemma 4 E4B, and Qwen3.8-27B as a
second model). It covers where the models run, how the GPU server is wired in, and what to type. If you
feel lost, read sections 1 and 4 first; the rest you can look up when you need it.

The diagrams are Mermaid; GitHub and PyCharm (with the Mermaid plugin) draw them.

## 1. The idea in two minutes

The research question is simple to say: someone changes an LLM agent system (a skill, a prompt, a line of
harness code, a config value). Which tests should we run, and when can we stop, so that we still catch the
change if it broke something, without paying for the whole test suite every time?

To study that, the repo has four things:

- **An app with agents.** "ContentOps" is a small content platform with an orchestrator and specialist
  agents (publishing, authoring, SEO, assets, ...). Each agent follows a skill (a `SKILL.md` with a
  step-by-step procedure) and calls tools. The app's data (pages, users, reviews) lives in memory, so a test
  can't damage anything, and the harness can inject faults such as a tool that fails once.
  See [CONTENTOPS.md](CONTENTOPS.md).
- **Tests.** 136 cases in [`traceeval/catalog/tests/`](../traceeval/catalog/tests/). Each gives a request
  ("Please publish the welcome page") and checks the outcome: was the page published, which tools were
  called, which facts the answer reports.
- **Changes.** 33 controlled edits in [`traceeval/mutation/catalog.py`](../traceeval/mutation/catalog.py),
  each labelled *regression* (it should break something) or *benign* (it should not). Example:
  `config_seo_title_20` lowers the SEO title limit from 60 to 20 characters.
- **Selection strategies.** In [`traceeval/selection/`](../traceeval/selection/), they decide which tests
  to run for a given change.

We run every test on the original app and on every changed copy three times, and record what happened;
the majority of the three decides. That gives the ground truth: which tests fail under which change. After that, comparing the strategies costs
nothing. We replay the recordings: "strategy X would have run these tests, so it would (or would not) have
caught this change, for this many tokens".

```mermaid
flowchart LR
    T["Test catalog"] --> B["Run every test<br/>on the original app"]
    M["Controlled changes"] --> V["Changed copies<br/>of the app"]
    V --> R["Run every test<br/>on each copy"]
    B --> H[("Recordings<br/>runs/NAME/history")]
    R --> H
    H --> G["Ground truth:<br/>which test reveals which change"]
    G --> S["Replay the strategies<br/>on the recordings"]
    S --> P["Report<br/>runs/NAME/results/report.md"]
```

**Where the models come in.** Each agent's decisions come from a real model: Gemma 4 E4B, a small open model
from Google, or Qwen3.8-27B. Recording costs GPU time, which is why we use the GPU server (section 4);
replaying recorded answers is free (section 5).

## 2. What happens when one test runs

Take PUB-01, "Please publish the welcome page", from user `bob` for page `p4`.

```mermaid
sequenceDiagram
    participant X as Test runner
    participant O as Orchestrator agent
    participant G as Gemma
    participant P as Publishing agent
    participant D as Dispatcher and in-memory app
    X->>O: request and context
    O->>G: system prompt, request, tools
    G-->>O: call route_to_agent publishing
    O->>P: same request, one level down
    loop until Gemma answers without a tool call
        P->>G: conversation so far
        G-->>P: next tool call
        P->>D: get_page, check_permission, validate_links, publish_page
        D-->>P: tool result, faults injected if the test asks
    end
    P-->>O: final message
    O-->>X: final message and trace
    X->>X: checks on state, tool calls, answer
```

1. The **runner** ([`experiment/runner.py`](../traceeval/experiment/runner.py)) starts the case through the
   **executor** ([`experiment/executor.py`](../traceeval/experiment/executor.py)), which builds a fresh app
   from the fixtures.
2. The **runtime** ([`sut/harness/runtime.py`](../traceeval/sut/harness/runtime.py)) runs the orchestrator.
   At every step it asks the agent's backend "what next?". With a model backend
   ([`backends/llm_openai.py`](../traceeval/sut/harness/backends/llm_openai.py)), that is one model call.
3. Gemma picks `route_to_agent(publishing)`. The runtime then runs the publishing agent the same way: model
   call, tool call, result, model call again, until Gemma answers in plain text.
4. Every tool call goes through the **dispatcher**
   ([`sut/harness/dispatcher.py`](../traceeval/sut/harness/dispatcher.py)), which checks permissions,
   retries transient failures, injects the faults the test asks for, and records everything in the trace.
5. The **scorers** ([`scoring/scorers.py`](../traceeval/scoring/scorers.py)) check the result against the
   case's `expect` block. For PUB-01: routed to publishing, page `p4` is now `published`, the required tools
   were called, `request_review` was not, one `publish_page` in the audit log, and the answer is not empty.

### What Gemma sees

The system prompt of an agent is its own prompt, its tools, and its skill. The skill's procedure is written
out as numbered plain steps, with included skills expanded in place and every config value shown
([`render_procedure`](../traceeval/sut/harness/skills.py)). This is the start of what the publishing agent
reads:

```text
1. Call `get_page` with page_id=<page_id>. Its result is called `fetch`.
2. If the intent is `unpublish`: action = "unpublish".
...
7. Call `validate_links` with page_id=<page_id>. Go on only if broken_count == 0; otherwise stop and
   answer: "Found {broken_count} broken link(s) on {page_id}: {the link of each entry in broken}. Fix them first."
8. If publishing.require_review (true) and fetch.review_approved is false: call `request_review` with
   page_id=<page_id>. Then stop and answer: "Page {page_id} needs an approved review ..."
```

The procedure is the skill's own statement of the workflow, so a change to it changes what the model is told
to do.

### What Gemma writes

Gemma has its own syntax for tool calls. A real answer from the model log:

```text
<|tool_call>call:check_permission{action:<|"|>attach<|"|>,user_id:<|"|>alice<|"|>}<tool_call|>
```

The tokenizer's own parser turns that into `check_permission(action="attach", user_id="alice")`. We don't
parse it by hand.

## 3. Where the models run

Two models play the agents. **Gemma 4 E4B** (Google, small) is the default. **Qwen3.8-27B** (Alibaba,
August 2026, about six times bigger) is the second model, so we can check that results hold for more than one
model. The `--backend` option picks who plays the agents:

| backend | what it is | when to use it |
|---|---|---|
| `hf` (default) | Gemma in this Python process, on your local GPU (RTX 4090), one call at a time | a quick look at one case, no server needed |
| `vllm` | Gemma served by vLLM on the GPU server (GPU0), reached through an SSH tunnel; many calls at once | recording experiments with Gemma |
| `llm` | an OpenAI-compatible endpoint: by default Qwen on the GPU server (GPU1), or the one named by `TRACEEVAL_LLM_BASE_URL` and `TRACEEVAL_LLM_MODEL` | recording experiments with Qwen; later OpenAI's `gpt-6-luna` (phase 1) |
| `replay` | Gemma's recorded answers, no model (`tests/cassettes/gemma.jsonl`, or the file named by `TRACEEVAL_CACHE`) | the test suite and the SDD demo; running a recorded experiment again |

The two models are wired in slightly differently:

- **Gemma (`hf`, `vllm`):** we build the prompt on your machine with Gemma's chat template and send it as token
  ids. The answer comes back as raw text and we parse it on your machine
  ([`traceeval/llm/chat.py`](../traceeval/llm/chat.py)). The only difference between `hf` and `vllm` is who
  does the arithmetic, so a test gets the same prompt and the same parsing on either engine.
- **Qwen (`llm`):** the ordinary chat API. vLLM applies Qwen's chat template and turns Qwen's tool-call syntax
  into structured calls on the server, so there is no Qwen-specific code in the repo. Qwen's "thinking" mode
  is turned off on the server, so it answers directly, as Gemma does.

The two cases with a rubric (SEO-07, PUB-20) are also judged by a model once their fixed checks pass. By
default the judge is the model playing the agents; `TRACEEVAL_JUDGE=gemma` or `qwen` picks one. Gemma's verdicts
are recorded and replayed with its other answers; Qwen is always asked on its server.

This is the path of one model call when both models are running:

```mermaid
flowchart LR
    subgraph PC["Your PC"]
        A["Agent backend<br/>llm_openai.py"]
        A -->|"--backend vllm"| C["chat.py<br/>Gemma template, then parsing"]
        A -->|"--backend llm"| Q["OpenAI client<br/>chat API"]
        C --> L1["localhost:18100"]
        Q --> L2["localhost:18101"]
    end
    subgraph SRV["GPU server fmi0@10.23.13.53"]
        V1["vLLM server: Gemma"] --> G0["GPU0"]
        V2["vLLM server: Qwen<br/>template and tool parsing"] --> G1["GPU1"]
        GX["GPU2: someone else's job<br/>never touched"]
    end
    L1 -->|SSH tunnel| V1
    L2 -->|SSH tunnel| V2
```

Each vLLM server only listens on the server's own localhost, so nobody on the network can reach it. Your PC
gets in through an SSH tunnel per model, which uses the same key you use to log in.

**Is it reproducible?** Decoding is greedy (temperature 0), so the same prompt gives the same answer. On vLLM
this is *nearly* exact rather than bit-exact: the batch a request lands in can change the floating-point
arithmetic slightly, and once in a while that flips a token, and with it the rest of the run. We saw this
with Qwen when 32 cases ran at once: a test failed under a change that couldn't have affected it (section 7).
That's why a ground truth should come from several repetitions (`--reps 3`, majority vote), not one.

## 4. The GPU server, step by step

Everything goes through one script, [`scripts/gpu_remote.sh`](../scripts/gpu_remote.sh). Run it from the
repo root in Git Bash (or any bash). It knows two models, called presets:

| preset | model | GPU | port | run with |
|---|---|---|---|---|
| `gemma` (the default) | `google/gemma-4-E4B-it` | 0 | 18100 | `--backend vllm` |
| `qwen` | `Qwen/Qwen3.8-27B-FP8` (8-bit weights, about 30 GB) | 1 | 18101 | `--backend llm` |

Different GPUs and ports mean both can run at the same time, each with its own experiment.

### What lives where

| where | what |
|---|---|
| server `~/traceeval-vllm/.venv` | a Python 3.12 environment with vLLM 0.31.0, kept apart from anything else on the server |
| server `~/traceeval-vllm/gemma.log`, `qwen.log` | each server's log: start-up, errors, request counts |
| server `~/traceeval-vllm/gemma.pid`, `qwen.pid` | each server's process id, so `down` can stop it |
| server `~/.cache/huggingface/` | the model weights (both already downloaded) |
| your PC `~/.traceeval-vllm-tunnel-gemma.pid`, `...-qwen.pid` | each tunnel's process id, so `down` can close it |

### Once (already done)

```bash
scripts/gpu_remote.sh setup     # creates ~/traceeval-vllm/.venv on the server, installs vLLM, checks the models
```

### Every working session

```bash
scripts/gpu_remote.sh up gemma  # start Gemma on GPU0, open its tunnel, wait until it answers
scripts/gpu_remote.sh up qwen   # the same for Qwen on GPU1
scripts/gpu_remote.sh status    # GPU memory, and for each model: server, tunnel, endpoint

# Gemma
traceeval run --test PUB-01 --backend vllm                              # one case, to check
traceeval experiment --backend vllm --workdir runs/gemma2 --reps 3      # the whole recording
traceeval check code_retry_drop_idempotency --history runs/gemma3       # one change, live (section 5)

# Qwen (in another terminal, at the same time if you like)
traceeval run --test PUB-01 --backend llm
traceeval experiment --backend llm --workdir runs/qwen2 --reps 3
traceeval check code_retry_drop_idempotency --history runs/qwen3 --backend llm

scripts/gpu_remote.sh down      # stop both servers and close the tunnels: frees the GPUs
scripts/gpu_remote.sh down qwen # or just one of them
```

Qwen is the slow one. When Gemma isn't needed, `TRACEEVAL_GPUS=0,1 scripts/gpu_remote.sh up qwen` puts a copy
of Qwen on each GPU; then run the changes with `--workers 64`. vLLM shares the requests between the copies.

`up` does four things:

1. It checks whether that model's server is already running (via its pid file). If not, it starts
   `vllm serve` on the server, detached from the SSH session, so it keeps running when the script exits.
2. It opens that model's SSH tunnel in the background, unless one is already open.
3. It polls the endpoint until it answers. That takes a few minutes while vLLM loads the model and compiles
   its kernels.
4. If the server dies while starting, it prints the last lines of the server log and exits.

You can run `up` as often as you like: it reuses a running server and an open tunnel.

**Please run `down` when you're done.** The server is shared, and vLLM keeps most of each GPU's memory
reserved while it runs, even when idle.

### More GPUs: the SLURM cluster, and several servers in one run

Two more H100s are available through the university's SLURM cluster (login
`ciprian.paduraru@hpc-ctrl01.acc-ub.local`). Its GPU node, `hpc-nodegpu01`, is the same machine as fmi0: it has 8
H100s, and SLURM hands out 4 of them. The same script drives it with `TRACEEVAL_SITE=hpc`:

```bash
TRACEEVAL_SITE=hpc scripts/gpu_remote.sh up qwen     # a SLURM job for 2 GPUs (8 hours at most), tunnel on port 18111
TRACEEVAL_SITE=hpc scripts/gpu_remote.sh status      # our jobs, and which endpoints answer
TRACEEVAL_SITE=hpc scripts/gpu_remote.sh down        # cancel the jobs, close the tunnels
```

`up` submits a job that serves the model on the GPU node's own localhost, waits until SLURM starts it, and opens
the tunnel through the controller. The first job also creates the vLLM environment in your cluster home and
downloads the model, so it takes longer. The job checks its GPUs first and stops if one is already in use:
SLURM doesn't see processes started outside it (another user's server, or one started on fmi0) and may hand out
their GPUs anyway. That happened on the first try, so check `TRACEEVAL_SITE=hpc scripts/gpu_remote.sh status`
and, if needed, ask the cluster's admin which GPUs are free.

To use both sites in one run, list both servers, separated by commas. Each request goes to the next server in
turn (`traceeval/llm/chat.py::Servers`); decoding is greedy, so which server answers doesn't matter:

```bash
export TRACEEVAL_LLM_BASE_URL=http://127.0.0.1:18101/v1,http://127.0.0.1:18111/v1   # Qwen on fmi0 and on the cluster
traceeval experiment --backend llm --workdir runs/qwen3 --reps 3 --workers 64
```

For Gemma the variable is `TRACEEVAL_VLLM_URL` (ports 18100 and 18110).

### Settings

All optional, as environment variables:

| variable | default | meaning |
|---|---|---|
| `TRACEEVAL_SITE` | `fmi0` | `fmi0` (the shared server) or `hpc` (the SLURM cluster) |
| `TRACEEVAL_GPU_HOST` | `fmi0@10.23.13.53` (hpc: `ciprian.paduraru@hpc-ctrl01.acc-ub.local`) | the SSH login (key-based, no password prompt) |
| `TRACEEVAL_GPUS` | the preset's GPU (hpc: 2) | which GPUs; one copy of the model on each. `TRACEEVAL_GPUS=0,1 scripts/gpu_remote.sh up gemma` puts Gemma on both GPUs when Qwen isn't needed. On hpc, how many GPUs to ask SLURM for |
| `TRACEEVAL_VLLM_PORT` | the preset's port (hpc: plus 10) | the port, the same on both ends of the tunnel |
| `TRACEEVAL_HF_MODEL` | `google/gemma-4-E4B-it` | the `gemma` preset's model; `--backend hf` and `vllm` read it too |
| `TRACEEVAL_VLLM_URL` | `http://127.0.0.1:18100/v1` | where `--backend vllm` sends Gemma's calls; several servers separated by commas |
| `TRACEEVAL_LLM_BASE_URL`, `TRACEEVAL_LLM_MODEL` | `http://127.0.0.1:18101/v1`, `Qwen/Qwen3.8-27B-FP8` | where `--backend llm` sends its calls (several servers separated by commas), and the model name the servers know |
| `TRACEEVAL_JUDGE` | the agents' model | `gemma` or `qwen`: the model that judges the cases with a rubric |

To add a third model, add a preset to the `case` in `preset()` at the top of the script: model, GPU, port,
and any vLLM flags it needs.

### When something goes wrong

| symptom | what to do |
|---|---|
| `endpoint ... does not answer` but the server is running (often after the PC slept) | the tunnel died: `scripts/gpu_remote.sh down NAME` then `up NAME` |
| `up` says "the server stopped" | read the log lines it prints, or `scripts/gpu_remote.sh logs NAME` |
| log shows `nvcc ... Unknown option '--compress-mode=size'` or `NVCC version must be at least 12.9` | a vLLM component tried to compile kernels with the server's old CUDA compiler (12.0). The script turns off the two that did (`VLLM_USE_FLASHINFER_SAMPLER=0`, `VLLM_USE_DEEP_GEMM=0`); a new one needs the same treatment |
| log shows `max_num_seqs ... exceeds available Mamba cache blocks` | the model can't keep state for that many requests at once: lower `--max-num-seqs` in the script |
| log shows "out of memory" | another job took GPU memory: check `status`, pick other GPUs with `TRACEEVAL_GPUS`, or lower `--gpu-memory-utilization` in the script |
| the tunnel fails with "address already in use" | something on your PC uses the port: set `TRACEEVAL_VLLM_PORT` to another one (use the same value for `up`, the runs and `down`) |
| SSH asks for a password | the script needs key login: `ssh-copy-id fmi0@10.23.13.53` once |

## 5. Running an experiment

```bash
traceeval experiment --backend vllm --workdir runs/gemma2 --reps 3
```

This runs four steps: `baseline`, `mutants`, `evaluate` and `report`. You can also run them one at a time
with the same options.

- **`baseline`** runs every test on the original app, one test at a time. It records code coverage per test,
  and coverage can only follow one test at a time in a process.
- **`mutants`** makes a changed copy of the app for each change (in `runs/gemma2/variants/`) and runs every
  test on it, 32 tests at a time (`--workers`), because the vLLM server handles many requests at once.
  With the local `hf` engine it stays at 1.
- **`evaluate`** replays the strategies on the recordings; it makes no model calls.
- **`report`** writes `runs/gemma2/results/report.md`. Its first section is the sanity check: every
  regression must be revealed by at least one test, and no benign change by any.

`--reps 1` is good for a first look. For a ground truth you'll rely on, use `--reps 3`: greedy decoding on
vLLM is not perfectly repeatable (section 3), and the majority vote over the repetitions takes care of that.

What ends up in the work folder (git-ignored; copy `results/` into `docs/results/` to keep a run):

| path | what |
|---|---|
| `history/*.jsonl` | one line per test run: outcome, failed checks, tokens, the trace, observed dependencies (large: it includes line coverage) |
| `variants/` | the changed copies of the app |
| `results/report.md`, `results/*.csv` | the report and the raw replay tables |

**Seeing what the model did.** Set `TRACEEVAL_MODEL_LOG` to a file and every model call is appended to it as
one JSON line: which agent, the last message it got, Gemma's raw answer, tokens and seconds.

```bash
TRACEEVAL_MODEL_LOG=runs/gemma2/model_calls.jsonl traceeval run --test PUB-02 --backend vllm
```

### Checking one change live (the prototype)

`traceeval check` is what a developer would run before merging: the proposed method on one change, with the
tests run live by the model instead of looked up in a recording
([`traceeval/experiment/check.py`](../traceeval/experiment/check.py)).

```bash
traceeval check code_retry_drop_idempotency --history runs/gemma3 --budget 0.2    # a change from the catalog
traceeval check my-sut-copy --history runs/qwen3 --backend llm                    # a changed copy of traceeval/sut
```

The method picks the most informative test for its cost, the test runs on the changed app, and its outcome
decides what runs next. The check stops at the first test that passed on the original app and fails now (a
regression), when the method is sure nothing broke, or when the budget is spent. It prints each test as
it runs, then the verdict (`REGRESSION`, `no regression`, `no regression found within the budget`, or `no failure within the budget`), the
tokens spent and the method's probability that the change broke something.

`--history` gives the method what it knows beforehand: each test's cost and the code it runs on the original
app, and how the other changes showed up in the tests. Record it with the same model, and again whenever the
app's code changes, since code is matched by line number: `traceeval experiment --reps 1` is enough. A changed
copy of the app is compared with `traceeval/sut`, so copy that folder before editing it.

### Recorded answers: running without a model

Every answer Gemma gives can be recorded, keyed by exactly what it was sent
([`traceeval/llm/cache.py`](../traceeval/llm/cache.py)). Decoding is greedy and the app has no clock and no
randomness, so a run that starts from recorded answers sends the same prompts again and replays exactly.

- **`--backend replay`** answers only from recorded answers, with no model and no GPU. The test suite and
  `traceeval sdd` do this by default, from `tests/cassettes/gemma.jsonl`.
- **`TRACEEVAL_CACHE=<file>`** with `--backend hf` or `vllm` answers what the file has, asks Gemma for the rest
  and adds those answers to the file. Running the same experiment again then costs nothing.
- **When the app changes a prompt** (a skill, an agent definition, a config value, a tool result), the recorded
  answer no longer matches, and a replay fails with `CacheMiss`. Start Gemma, run `TRACEEVAL_BACKEND=vllm pytest
  -q` (it replays what it can and records the rest) and commit the cassette. To drop answers nothing asks for
  any more, delete the file first and record everything again.

```bash
scripts/gpu_remote.sh up gemma
TRACEEVAL_BACKEND=vllm pytest -q            # records into tests/cassettes/gemma.jsonl what the tests lack
TRACEEVAL_CACHE=tests/cassettes/gemma.jsonl traceeval sdd --backend vllm --workers 32   # the SDD demo, faster
scripts/gpu_remote.sh down
```

## 6. What we changed to make Gemma work, and why

The first full run of Gemma on the original app passed 92 of 136 tests, and most failures were not about
the app at all:

- **Gemma called step names as tools.** The skills' procedures were shown to it as raw YAML (`say:`,
  `include: governance-checks`), and it tried to call `say` and `governance-checks`. Now the procedure is
  written out as numbered sentences, with included skills expanded and config values filled in.
- **Tool results were in the wrong place.** Gemma was trained with each tool result attached to the model
  turn that asked for it, not as a separate message. [`chat.py`](../traceeval/llm/chat.py) now converts the
  conversation to that form.
- **Tests checked wording.** Checks like "the answer contains *broken*" fail a model that says "invalid"
  instead. We dropped the 33 wording checks. A test now checks a phrase only when it is a fact the answer
  has to report: a job id, a URL, which link is broken.
- **Empty answers.** Sometimes Gemma ends without a word. The backend now asks once ("Reply to the user
  now..."), and a new check, `answered`, fails a run that still ends with an empty answer.

After these, the original app passed 131 of 136. Phase 4 (section 7) added three more fixes:

- **The answer after an empty reply.** At a failed link check Gemma stopped without a word, and the reminder
  made it summarise without saying which link. The reminder now asks for the answer the step prepared, so
  PUB-02 and PUB-03 pass.
- **Conditions spelled out.** `If <request_review>:` became `If <request_review> is given and true:` (Gemma
  read the first one as an order), `not fetch.review_approved` became `fetch.review_approved is false`, and
  `len(<seo_title>) > ...` became `<seo_title> has more than ... characters`.
- **The default agent.** The orchestrator is now told where to send a request that no specialist owns
  (`routing.default_agent`). Without it, Qwen answered "Hello there" itself.

Now the original app passes 133 of 136 under Gemma and 135 of 136 under Qwen. What is left are real model
mistakes, which clearer wording did not fix:

| case | model | what goes wrong |
|---|---|---|
| PUB-10 | Gemma | it requests the review, as it should, and then schedules the page anyway |
| AUT-04 | Gemma | after an edit it requests a review nobody asked for |
| SEO-02 | Gemma | it applies an 83-character title over the 60-character limit |
| SEO-05 | Qwen | it counts the 60-character title as 61 and refuses it |

Since a model judges the two rubric cases (phase 6), Qwen also fails SEO-07 when it judges its own answer:
"Updated SEO metadata on p1; SEO score is now 100" does not say that the keywords were applied, which the rubric
asks for. Gemma, judging the same kind of answer, lets it pass. The rubric stays strict on purpose.

Gemma acts on guards that come from a tool's answer (a denied permission, a broken link), but not on guards
it has to work out for itself (a review flag, a length).

## 7. Where we are

| phase | what | status |
|---|---|---|
| 0 | measure Gemma on the original app; make prompts and checks fit a real model | done |
| — | GPU server: `scripts/gpu_remote.sh`, `--backend vllm`, parallel runs | done |
| — | first full recording with Gemma (`runs/gemma1`, below) | done |
| — | second model: Qwen3.8-27B on GPU1, next to Gemma on GPU0 (`runs/qwen1`, below) | done |
| 1 | a cache of model answers (`traceeval/llm/cache.py`, section 5); an OpenAI backend (`gpt-6-luna`) | cache done; OpenAI waits for API tokens |
| 2 | tokens and latency from the model servers' own counts | done |
| 3 | pytest replays recorded model answers ("cassettes", `tests/cassettes/`), so tests need no GPU | done |
| 4 | re-derive the ground truth under both models, with three repetitions (`runs/gemma2`, `runs/qwen2`, below) | done |
| 5 | the SDD demo on Gemma ([SDD_DEMO.md](SDD_DEMO.md)); the experiment's results are `runs/gemma2` and `runs/qwen2` (`docs/results/`) | done |
| 6 | real models only: the rubric cases judged by Gemma or Qwen instead of a word match; the prototype `traceeval check` (section 5) | done |

The next two subsections are the first recordings, from before phase 4 (old changes, one repetition). The
phase 4 recordings come after them.

### The first full recording with Gemma

`traceeval experiment --backend vllm --workdir runs/gemma1 --reps 1` took about ten minutes: a few for the
baseline (one test at a time), about six for the 38 changes, and half a minute for the replay. Here is what it
found:

- **Original app:** 131 of 136 pass, the same five failures as in section 6.
- **Benign changes:** none of the six breaks a test. That is what we want.
- **Regressions:** 20 of 32 are caught by at least one test, and **12 are caught by none**. The report's sanity
  line therefore says VIOLATED. That's expected: the 38 changes were designed before a real model played the
  agents, and phase 4 exists to re-derive the ground truth under the model.

The 12 misses fall into three groups, and each needs a different fix:

| why no test catches it | changes | what it means |
|---|---|---|
| **A model doesn't use what changed.** Keyword weights, trigger lists, intent order and the default agent were inputs of a keyword router the app no longer has; Gemma routes by reading the agents' descriptions | `code_router_phrase_weight`, `prompt_publishing_triggers_removed`, `prompt_translation_intents_reordered`, `config_default_agent_publishing` | under a real model these are benign: relabel them, or replace them with changes a model does depend on |
| **Gemma does the step anyway.** The procedure step was removed, but the skill's prose or the agent's prompt still asks for it (permission check, consent check, review), or Gemma ignores the guard either way (it applies an SEO title over the limit whatever the limit is) | `skill_publish_drop_permission_check`, `skill_rollback_drop_permission_check`, `skill_governance_drop_consent`, `config_require_review_false`, `config_seo_title_20` | a real finding: the model is more robust (or more careless) than the procedure. To make them regressions again, the change must also remove the instruction from the prose |
| **The only test that would catch it already fails on the original app** | `code_edit_keeps_review` (AUT-04), `skill_seo_drop_length_guard` (SEO-02), `skill_linkval_ignore_assets` (PUB-03; its other test, AUT-03, passes because Gemma does the step anyway) | a test that is red on the baseline can't reveal anything: fix the model's mistake (clearer skill wording) or add a test that passes on the baseline |

On the 20 regressions that are caught, the strategies line up as follows:

- **20% of the full-suite tokens:** trace-based selection (`observed`) and `ir_tfidf` catch 90%.
- **Hand-written dependencies:** `declared` catches 60%.
- **Adaptive method:** `adaptive_bayes` catches 85% while spending about 7%.

Treat these numbers as preliminary. They come from one repetition and from a ground truth that phase 4
still has to fix. The report is `runs/gemma1/results/report.md`.

### The same experiment with Qwen

`traceeval experiment --backend llm --workdir runs/qwen1 --reps 1`, with Qwen on GPU1, took about an hour:
ten minutes for the baseline and 45 for the changes. Qwen takes about three seconds per case where Gemma
takes one, and it slows down more when 32 cases run at once.

- **Original app:** 134 of 136 pass. In SEO-05 Qwen counts the 60-character title as 61 and refuses it
  (models are bad at counting characters). In AST-07, after the attach fails as expected, it looks the
  missing asset up, and the test doesn't allow that second error. That one is arguably the test being too
  strict.
- **Regressions:** 23 of 32 caught, against 20 for Gemma.
- **Benign changes:** one of them, a rewording of the orchestrator's prompt, fails two tests. One of the two
  (PUB-07) can't be caused by the change: the failing step is in the publishing agent, whose prompt doesn't
  include the orchestrator's. It's run-to-run noise (see "Is it reproducible?" in section 3).

The two models miss different regressions:

| | changes | why |
|---|---|---|
| **both miss** | the four router changes; `skill_publish_drop_permission_check`, `skill_governance_drop_consent`, `skill_seo_drop_length_guard` | the router changes don't matter to a model; for the skill changes, both models do the step anyway because the skill's prose still asks for it |
| **only Gemma misses** | `code_edit_keeps_review`, `config_require_review_false`, `config_seo_title_20`, `skill_linkval_ignore_assets`, `skill_rollback_drop_permission_check` | Gemma's own baseline failures hide some of them, and Gemma ignores some guards whatever their setting; Qwen follows the config values |
| **only Qwen misses** | `skill_publish_drop_link_validation`, `combined_seo_keyword_limit` | Qwen validates links even when the step is gone. In SEO-07 Qwen reports the new score (70) but adds that it "dropped from 100", which satisfies the fact check "100": that check is too weak and should look at the score itself |

Strategies on the regressions Qwen does catch, at 20% of the full-suite tokens:

- `ir_tfidf` catches 92%, `observed` 83% and `declared` 50%.
- `adaptive_bayes` catches 88% while spending about 9%.

The ranking is the same as under Gemma.

**What this means for phase 4:** the four router changes are benign under any model, and three skill changes
are masked by the skills' prose under both models. Both groups need relabelling or redesigning. The rest
depends on the model, which is exactly why a second model is useful. Qwen also needs `--reps 3`, so that a
majority vote filters out the noise.

### Phase 4: a ground truth for real models

The two recordings above showed that some of the 38 changes, and a few tests, did not fit a real model.
Phase 4 fixed them and then recorded both models again, this time with three repetitions per test.

**What changed**

- **The app's prompts:** the three fixes at the end of section 6 (the reply reminder, conditions spelled out,
  the default agent).
- **Two tests:** AST-07 now lets the model look the missing asset up (`get_asset: not_found` is allowed).
  SEO-07 checks the score in the last SEO report (a new kind of check, `tool_results`) rather than only
  looking for "100" in the answer.
- **The changes:** still 38, now 31 regressions and 7 benign. Five were dropped later as redundant
  ([USER_GUIDE.md](USER_GUIDE.md) §6); the results below are for the remaining 33 (26 regressions).

| before | now | why |
|---|---|---|
| `code_router_phrase_weight` | `code_delegation_truncates_answer`: the orchestrator gets only the first 40 characters of the specialist's answer | a model doesn't use the keyword weights |
| `prompt_publishing_triggers_removed` | `prompt_governance_consent_tool_removed`: the governance agent loses `check_consent` | a model routes by the agents' descriptions and the routing skill, not by the trigger list |
| `prompt_translation_intents_reordered` (regression) | `benign_translation_intents_reordered` | a model picks the intent from the request, not from the order of a list |
| `config_default_agent_publishing` | unchanged | the orchestrator is now told the default agent, so a model depends on it too |
| `skill_publish_drop_permission_check`, `skill_rollback_drop_permission_check` | also remove the sentence in the prose, and the shared permission skill from the agent | with only the procedure step gone, both models still checked the permission |
| `skill_governance_drop_consent`, `skill_seo_drop_length_guard`, `skill_linkval_ignore_assets` | also change the prose | the prose still asked for the step |

**Results**

`runs/gemma2` took about half an hour. `runs/qwen2` took about an hour and a half: the baseline on GPU1,
then the changes on a copy of Qwen on each GPU (`TRACEEVAL_GPUS=0,1`, `--workers 64`), once Gemma was done.

| | Gemma 4 E4B | Qwen3.8-27B |
|---|---|---|
| original app | 133 of 136 pass | 135 of 136 pass |
| regressions caught | 21 of 26 | 26 of 26 |
| benign changes that fail a test | none | none |
| sanity line of the report | VIOLATED (the five below) | OK |

Qwen catches every regression, so the changes and the tests are now sound for a model that follows its
instructions. Gemma misses five, for one reason: it doesn't act on a guard it has to work out for itself, so it
behaves the same (wrongly) with or without the change.

| change | why Gemma can't see it |
|---|---|
| `config_require_review_false`, `code_edit_keeps_review` | Gemma schedules a page without an approved review anyway (PUB-10), and requests a review nobody asked for after an edit (AUT-04) |
| `config_seo_title_20`, `skill_seo_drop_length_guard` | Gemma applies an over-long title whatever the limit (SEO-02) |
| `skill_linkval_ignore_assets` | Gemma stops at a broken asset reference even when the skill says it doesn't block |

We keep them as they are. The ground truth belongs to a model, and a change that a model can't see is a fact
about that model, not a bug in the testbed.

**Repetitions.** Under Gemma, no test gave different verdicts in its three repetitions on the original app, and
three tests did so once each on a changed copy. Under Qwen, SEO-05 (the 60-character boundary) flips on ten
changes and a handful of tests flip once. The majority vote absorbs all of it.

**Strategies at 20% of the full-suite tokens**, on the regressions each model reveals:

| strategy | Gemma | Qwen |
|---|---|---|
| `declared` (hand-written dependencies) | 71% | 65% |
| `observed` (dependencies from traces) | 90% | 85% |
| `ir_tfidf` (text similarity to the diff) | 90% | 88% |
| `adaptive_bayes` (spending) | 76% (5%) | 65% (6%) |

- **The main claim holds under real models.** Hand-written dependencies stay at 65–71%, and traces recover most
  of the rest.
- **The adaptive method is weaker under Qwen.** On regressions that only one or two tests reveal, it stops with
  "clean" before reaching them (185 of 910 replays). Each test's own record is now part of the method (see
  USER_GUIDE.md §5); the text-similarity signal inside the model is the next planned improvement.
- **Tests that are red on the original app cost the other strategies dearly.** Gemma's three failing tests fail
  on every changed copy, so a strategy that runs one of them sees a failure the change did not cause. On the
  changes that no test reveals, `full` sees such a failure in 71% of replays and `ir_tfidf` in 58% under Gemma
  (56% and 16% under Qwen). `adaptive_bayes` discounts a test by its failures on the original app and gives no
  "regression" verdict on any of these changes.

## 8. Where to look in the code

| file | role |
|---|---|
| [`scripts/gpu_remote.sh`](../scripts/gpu_remote.sh) | start, check and stop the model server on the GPU server |
| [`traceeval/llm/chat.py`](../traceeval/llm/chat.py) | the model client: prompt, engines (`hf`, `vllm`), parsing, log; the `llm` backend's client; several servers in turn (`Servers`); which model judges (`judge_client`) |
| [`traceeval/llm/cache.py`](../traceeval/llm/cache.py) | recorded answers: the cache in front of a model, and `replay` without one |
| [`traceeval/sut/harness/backends/llm_openai.py`](../traceeval/sut/harness/backends/llm_openai.py) | one agent's conversation with the model: system prompt, tool calls, results |
| [`traceeval/sut/harness/skills.py`](../traceeval/sut/harness/skills.py) | skills, and `render_procedure`, which writes a procedure as plain steps |
| [`traceeval/sut/harness/runtime.py`](../traceeval/sut/harness/runtime.py) | the agent loop and delegation |
| [`traceeval/experiment/runner.py`](../traceeval/experiment/runner.py) | runs the suite on the original app and on each change, sequentially or in parallel |
| [`traceeval/scoring/scorers.py`](../traceeval/scoring/scorers.py) | the checks, and the model judge (`judge_answer`) |
| [`traceeval/experiment/check.py`](../traceeval/experiment/check.py) | the prototype: one change checked live with the proposed method |
| [`traceeval/cli.py`](../traceeval/cli.py) | the `traceeval` command |

For the rest of the repository (strategies, report, SDD), see [USER_GUIDE.md](USER_GUIDE.md) and
[STUDY_GUIDE.md](STUDY_GUIDE.md).
