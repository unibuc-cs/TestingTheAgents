# tau2-bench as the second system under test — verified facts and adapter design

*All facts in Part A were verified on 2026-10-05/06 against the live `main` branch of `sierra-research/tau2-bench` (raw.githubusercontent.com). Re-verify and pin a commit before running experiments. Items flagged "(LiteLLM convention)" come from LiteLLM's documented behaviour, not from tau2's own docs.*

The repository has moved on since the τ²-bench paper: `pyproject.toml` says `name = "tau2"`, `version = "1.0.1"`, the README is branded **τ³-bench** (voice + knowledge domains; "75+ task fixes" in `1.0.0`; a `banking_knowledge` grading change in `1.0.1`, dated 2026-07-15 in `CHANGELOG.md`).

## A1. Install, Python, keys, LiteLLM, local vLLM

- **Install:** `git clone https://github.com/sierra-research/tau2-bench && cd tau2-bench && uv sync` (core = text-mode airline/retail/telecom/mock). Extras: `--extra voice|knowledge|gym|dev|experiments`, `--all-extras`.
- **Python:** `requires-python = ">=3.12,<3.14"`; `.python-version` pins 3.12.
- **Not on PyPI** (`tau2` on PyPI is an unrelated package). Install from git; pin: `pip install git+https://github.com/sierra-research/tau2-bench@<tag-or-commit>`.
- **Console script:** `tau2 = "tau2.cli:main"`.
- **Keys:** `cp .env.example .env`; loaded by `load_dotenv()` in `src/tau2/utils/utils.py`.
- **Data dir env var:** `TAU2_DATA_DIR` — `DATA_DIR = Path(os.getenv("TAU2_DATA_DIR"))` else `<repo>/data`. Every domain resolves `policy.md`, `db.json`, `tasks.json` from it (e.g. `src/tau2/domains/retail/utils.py`: `RETAIL_DATA_DIR = DATA_DIR / "tau2" / "domains" / "retail"`). Results go under `DATA_DIR / "simulations"`.
- **LiteLLM call path:** `src/tau2/utils/llm_utils.py::generate(model, messages, tools, tool_choice, call_name, **kwargs)` → `litellm.completion(model=model, messages=..., tools=..., **kwargs)`; `litellm.drop_params = True`; `num_retries = 3`; an `httpx.Client(limits=httpx.Limits(max_keepalive_connections=5, max_connections=10))` — **10-connection cap** when raising `--max-concurrency`.
- **Pointing agent AND user simulator at local vLLM (verified mechanism):** `--agent-llm-args` / `--user-llm-args` are `json.loads`-parsed (`src/tau2/cli.py`) and flow into `TextRunConfig.llm_args_agent` / `llm_args_user` → `build_agent(...)` / `build_user(...)` (`src/tau2/runner/build.py`) → `generate(**kwargs)` → `litellm.completion(**kwargs)`. So `api_base` / `api_key` can be passed per role:

```bash
tau2 run --domain retail \
  --agent-llm openai/Muse-Glimmer-30B \
  --agent-llm-args '{"temperature":0.0,"api_base":"http://127.0.0.1:8000/v1","api_key":"EMPTY"}' \
  --user-llm  openai/Muse-Glimmer-30B \
  --user-llm-args  '{"temperature":0.0,"api_base":"http://127.0.0.1:8000/v1","api_key":"EMPTY"}' \
  --task-ids 0 1 2 --num-trials 3 --max-steps 60 --max-concurrency 4 --save-to my_run
```

  Model-name prefixes are LiteLLM's: `openai/<served-model-name>` + `api_base` (or env `OPENAI_API_BASE` / `OPENAI_API_KEY`), or `hosted_vllm/<model>` + `HOSTED_VLLM_API_BASE` (LiteLLM convention). Defaults: `DEFAULT_LLM_AGENT = DEFAULT_LLM_USER = "gpt-4.1-2025-04-14"`, temperature 0.0 (`src/tau2/config.py`). `make_run_name()` strips the provider prefix for the results dir name. `batch.py` warns that each trial modifies the agent seed if `"seed"` is in llm args.
- **Hidden third LLM:** `DEFAULT_LLM_NL_ASSERTIONS = "gpt-4.1-2025-04-14"` is the NL-assertion judge; no CLI flag. Under `EvaluationType.ALL` (default in `src/tau2/runner/batch.py`) NL assertions are judged when in the task's `reward_basis` — the case for **112/114 retail tasks**. For a fully local setup, change that constant (verify that `src/tau2/evaluator/evaluator_nl_assertions.py` consumes it) or restrict to airline (`["DB","COMMUNICATE"]`, no judge).

## A2. Repository layout, domains, task schema

- **Domain data:** `data/tau2/domains/<domain>/` with `tasks.json`, `split_tasks.json` (must contain a `base` split), `policy.md`, `db.json` or `db.toml`, optional `user_db.*`, `tasks_voice.json`. Telecom uses `db.toml`, `user_db.toml` and policies `main_policy.md` + `tech_support_manual.md` / `tech_support_workflow.md`.
- **Domain code:** `src/tau2/domains/<domain>/{data_model.py, tools.py, environment.py, utils.py}`. `tools.py` subclasses `ToolKitBase` with `@is_tool(ToolType.READ|WRITE|THINK|GENERIC)`; `environment.py` exposes `get_environment(db=None, solo_mode=False)`, `get_tasks(task_split_name="base")`, `get_tasks_split()`.
- **Registered domains** (`src/tau2/registry.py`): `mock`, `airline`, `retail`, `telecom`, `telecom-workflow`, `banking_knowledge`; task sets additionally `telecom_full`, `telecom_small`.
- **Task counts (live data):** retail 114 (`base` 114, `train` 74, `test` 40); airline 50 (`base` 50, `train` 30, `test` 20); telecom 2285 in file (`base` 114, `small` 20, `train` 74, `test` 40, `full` 2285); mock 10; banking_knowledge 97.
- **reward_basis distribution:** airline all `["DB","COMMUNICATE"]`; retail 112× `["DB","NL_ASSERTION"]`, 2× `["DB"]`; telecom 2253× `["ENV_ASSERTION"]`, 32× `["ENV_ASSERTION","ACTION"]`.
- **Task JSON schema** (`src/tau2/data_model/tasks.py`): `Task{id, description{purpose, relevant_policies, notes}, user_scenario{persona, instructions}, ticket, initial_state{initialization_data, initialization_actions, message_history}, evaluation_criteria{actions[Action{action_id, requestor, name, arguments, info, compare_args}], env_assertions[...], communicate_info[str], nl_assertions[str], reward_basis[RewardType]}, ...}`. Policy sizes: retail `policy.md` ≈1,158 words; airline ≈1,313 words.

## A3. Run CLI, agents, results, reward

- **CLI** (`docs/cli-reference.md`): `--domain`, `--agent` (default `llm_agent`), `--agent-llm`, `--agent-llm-args`, `--user` (default `user_simulator`), `--user-llm`, `--user-llm-args`, `--task-set-name`, `--task-split-name` (default `base`), `--task-ids` (nargs="+"), `--num-tasks`, `--num-trials` (1), `--max-steps` (200), `--max-errors` (10), `--timeout`, `--max-concurrency` (3), `--workers`, `--seed` (300), `--save-to`, `--log-level`, `--verbose-logs`, `--max-retries`, `--auto-resume`, `--auto-review`, …
- **Agents:** `llm_agent`; `llm_agent_gt` (`LLMGTAgent`: receives the expected actions — oracle plan); `llm_agent_solo` (`LLMSoloAgent`: no customer interaction; requires `task.ticket`; must pair with `--user dummy_user`). **Solo mode avoids the user simulator but only telecom and mock tasks have tickets**; retail raises `"Retail domain does not support solo mode"`.
- **Results:** `data/simulations/<run_name>/results.json`: `Results{timestamp, info{git_commit, num_trials, ...}, tasks[], simulations[SimulationRun], ...}`. `SimulationRun{id, task_id, timestamp, start_time, end_time, duration, termination_reason, agent_cost, user_cost, reward_info, messages[], trial, seed, ...}`; `RewardInfo{reward, db_check{db_match, db_reward}, env_assertions[], action_checks[], nl_assertions[], communicate_checks[], reward_basis, reward_breakdown}`.
- **Trials/seeds:** `random.seed(config.seed); seeds = [random.randint(0, 1000000) for _ in range(num_trials)]`; `--auto-resume` skips `(trial, task.id, seed)` already present.
- **Reward:** product of components in `reward_basis`. `DB`: replay `evaluation_criteria.actions` on a fresh gold env and compare `Environment.get_db_hash()`; `ENV_ASSERTION`; `COMMUNICATE` (substring); `NL_ASSERTION` (LLM judge); `ACTION`. **pass^k:** `src/tau2/metrics/agent_metrics.py::pass_hat_k(num_trials, success_count, k) = comb(success_count,k)/comb(num_trials,k)`; `is_successful(reward)` ⇔ `|reward − 1| ≤ 1e-6`; `INFRASTRUCTURE_ERROR` runs excluded.

## A4. Mock domain

`data/tau2/domains/mock/`: `policy.md` (5 rules), `db.json`, `tasks.json` (10 tasks), `user_db.json`, `policy_solo.md`. Tools: `create_task` (WRITE), `get_users` (READ), `update_task_status` (WRITE), `transfer_to_human_agents`, plus assertion helpers. No scripted agent in the registry, but `tests/test_domains/test_mock/test_tools_mock.py` drives tools with `ToolCall(...)` directly and `Environment.set_state(...)` replays trajectories — a CI smoke test can exercise env + evaluator with a hand-written `SimulationRun` and `evaluate_simulation(...)` without any LLM. A scripted agent would be a custom `HalfDuplexAgent` registered via `registry.register_agent_factory(create_my_agent, "my_agent")`.

## A5. Extensibility and Python API

- Policy/DB/tasks are read from `TAU2_DATA_DIR` at call time (`get_environment` reads `policy.md` per environment build), so **pointing `TAU2_DATA_DIR` at a mutated copy of `data/` overrides policy / db / tasks without code edits**; `tools.py` is Python in the installed package, so tool mutations need a mutated checkout (editable `uv sync`) or monkeypatching.
- **Programmatic API:** `from tau2.run import run_domain; from tau2.data_model.simulation import TextRunConfig; results = run_domain(TextRunConfig(domain="retail", agent="llm_agent", llm_agent=..., llm_args_agent={...}, llm_user=..., llm_args_user={...}, task_ids=[...], num_trials=N, max_steps=..., max_concurrency=..., seed=..., save_to="name"))`. Lower layers: `get_tasks(...)`, `run_single_task(config, task, seed=...)`, `build_orchestrator(...)` + `run_simulation(orch)`, `tau2.runner.run_tasks(config, tasks, save_path=..., evaluation_type=...)`. `Results.load(path)`.

## A6. Cost / latency fields

Per message (`src/tau2/data_model/message.py`): `timestamp`, `cost`, `usage = {"completion_tokens", "prompt_tokens"}`, `generation_time_seconds`, `turn_idx`, `tool_calls[ToolCall{id, name, arguments, requestor}]`; `ToolMessage{id, content, requestor, error, turn_idx, timestamp}`. Per simulation: `start_time`, `end_time`, `duration`, `agent_cost`, `user_cost`. Cost uses `litellm.completion_cost`; for unknown local model names it returns `0.0` → **for vLLM rely on `usage` tokens, not `cost`**. `--verbose-logs` writes per-call request/response JSON (`llm_debug/*.json`).

## Adapter design for TRACE-Eval (`traceeval/sut_adapters/tau2/`, phase 2)

1. **Materialise SUT:** clone at a pinned commit; `uv sync`; `cp -r data/ <workdir>/data_variant/`; `export TAU2_DATA_DIR=<workdir>/data_variant`. For tool mutations use a per-variant checkout (`git worktree add <workdir>/src_variant <commit>`) and run that worktree's `uv run tau2 ...`.
2. **Controlled mutations:** policy → edit `data_variant/tau2/domains/<d>/policy.md` (telecom: `main_policy.md` / `tech_support_manual.md`); tools → patch `src/tau2/domains/<d>/tools.py`; task/config → `tasks.json` / `split_tasks.json`; DB → `db.json` / `db.toml`. Our mutation catalogue format (`traceeval/mutation/`) is a list of textual patch operators with `expect_found` assertions, so the same mechanism applies.
3. **Change set:** unified diff between baseline and variant trees; map `policy.md` sections → tasks via `description.relevant_policies`; `tools.py` function names → tasks whose `evaluation_criteria.actions[].name` references them (declared) and, better, to tasks whose baseline traces called them (observed, from `messages[].tool_calls`); `db.*` keys → tasks whose `actions[].arguments` reference touched IDs. `coverage` dynamic contexts on `src/tau2/domains/<d>/tools.py` during the baseline run give an empirical function→task map (same mechanism as in the primary SUT).
4. **Execute:** `run_domain(TextRunConfig(domain, task_ids=selected, num_trials=N, llm_agent="openai/<m>", llm_args_agent={"temperature":0,"api_base":"http://127.0.0.1:8000/v1","api_key":"EMPTY"}, llm_user=..., llm_args_user={...}, max_steps=..., max_concurrency≤10, seed=S, save_to=f"{variant}_{hash}"))`; set `DEFAULT_LLM_NL_ASSERTIONS` to the local model for retail (or use airline to avoid the judge); `--auto-resume` for restarts.
5. **Parse into TRACE-Eval history records:** for each `results.simulations[i]`: `test_id=task_id`, `rep=trial`, `passed=is_successful(reward_info.reward)`, `reward_breakdown`, `tokens=Σ msg.usage` over agent messages (and separately user-simulator messages), `latency=duration`, `tool_calls=[(tc.name, tc.arguments, tool_msg.error)]`, `termination_reason`. pass^k with `pass_hat_k`.
6. **Token budget planning:** each agent turn re-sends policy (≈1.6–2k tokens) + tool schemas + full history, so prompt tokens grow roughly quadratically per simulation; expect on the order of 50k–200k prompt tokens per retail/airline simulation on the agent side plus a similar order for the user simulator (order-of-magnitude placeholder — calibrate from `usage` on the first local run). With a local vLLM this is free in money but sets wall-clock: e.g. 50 airline tasks × 20 mutations × 3 trials = 3,000 simulations.

**Recommended first tau2 experiment:** airline domain (no NL-assertion judge, 50 tasks, `["DB","COMMUNICATE"]` reward), local vLLM for agent and user, 3 trials, ~12 mutations (6 policy edits, 4 tool-code edits, 2 benign), baseline first to measure pass^k and flakiness; the TRACE-Eval replay evaluator then runs unchanged on the parsed history.

## Sources (fetched)

README.md, docs/getting-started.md, docs/cli-reference.md, docs/evaluation.md, CHANGELOG.md, pyproject.toml, .env.example, src/tau2/{config,cli,run,registry}.py, src/tau2/runner/{batch,build,helpers}.py, src/tau2/utils/{utils,llm_utils}.py, src/tau2/data_model/{simulation,message,tasks}.py, src/tau2/evaluator/evaluator.py, src/tau2/metrics/agent_metrics.py, src/tau2/agent/{llm_agent.py,README.md}, src/tau2/user/user_simulator.py, src/tau2/domains/README.md and domains/{mock,retail,airline,telecom}/{environment,utils,tools}.py, data/tau2/domains/{mock,retail,airline,telecom}/{tasks.json,split_tasks.json,policy.md}, tests/test_domains/test_mock/test_tools_mock.py, Makefile — all under https://github.com/sierra-research/tau2-bench (main, 2026-10-05).
