# Batch-invariant decoding

vLLM's batch-invariant mode (`VLLM_BATCH_INVARIANT=1`) makes greedy answers independent of how requests are batched
together, which would make a recording of the changed copies, many tests at a time, repeat the baseline's runs
exactly. Gemma 4 E4B started in that mode on one H100 (`TRACEEVAL_VLLM_ENV=VLLM_BATCH_INVARIANT=1
scripts/gpu_remote.sh up gemma`, vLLM 0.31.0) does not start, so nothing is recorded in it. The server log, in
order (process ids and times left out):

```text
INFO [config.py:259] Gemma4 model has heterogeneous head dimensions {'sliding_attention': 256, 'full_attention': 512}. Using FA4 for all layers to avoid mixed FA3/FA4 penalty.
WARNING [fa_utils.py:172] Cannot use FA version 4 with batch invariance, defaulting to FA version 2.
INFO [cuda.py:526] Using FLASH_ATTN attention backend out of potential backends: ['FLASH_ATTN', 'TRITON_ATTN', 'FLEX_ATTENTION'].
INFO [flash_attn.py:1167] Using FlashAttention version 2
...
ERROR [core.py:1433] EngineCore failed to start.
...
ERROR [core.py:1433]     cudagraph_memory_estimate = self.model_runner.profile_cudagraph_memory()
...
ERROR [core.py:1433]     measured = int(runner.capture_model(profile_only=True))
...
ERROR [core.py:1433] RuntimeError: mha_varlen_fwd, /workspace/.deps/vllm-flash-attn-src/csrc/flash_attn/flash_api.cpp:658, FlashAttention forward only supports head dimension at most 256
...
RuntimeError: Engine core initialization failed. See root cause above. Failed core proc(s): {}
```

Gemma 4's sliding-window attention layers have heads of 256 dimensions and its full-attention layers heads of 512.
vLLM serves both with FlashAttention 4; batch invariance rules version 4 out, so vLLM falls back to FlashAttention
2, which takes heads of at most 256 dimensions. The model loads and compiles, and the first forward pass through a
full-attention layer, while vLLM captures its CUDA graphs to measure their memory, fails. Serving with one of the
other two attention backends the log lists (`TRITON_ATTN`, `FLEX_ATTENTION`) was not tried.

So Gemma 4 E4B, like Qwen3.8, whose linear-attention layers the mode refuses (`docs/RESEARCH_PLAN.md` §5.4), cannot
be served batch-invariant with this vLLM, and whether its outcomes and token counts would then repeat the
baseline's stays open. Gemma is served as for every other recording. Its noise floor under that setup is zero: over
fifteen repetitions of the empty change in batches, no test flips against the baseline and no test's runs disagree
(`docs/results/gemma7/noise_floor.md`).
