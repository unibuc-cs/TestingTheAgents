#!/usr/bin/env bash
# Serve the agents' models with vLLM on the GPU server, and reach them through SSH tunnels.
#
#   scripts/gpu_remote.sh setup               once: create the vLLM environment on the server
#   scripts/gpu_remote.sh up [MODEL]          start MODEL on its GPU and open its tunnel (waits until ready)
#   scripts/gpu_remote.sh status              servers, GPU use, and which endpoints answer
#   scripts/gpu_remote.sh logs [MODEL]        follow a server's log
#   scripts/gpu_remote.sh down [MODEL]        stop a server and close its tunnel (default: all of them)
#
# MODEL is a preset (default: gemma). The two presets use different GPUs and ports, so both can run at once:
#   gemma  google/gemma-4-E4B-it  GPU 0  port 18100  then: traceeval ... --backend vllm
#   qwen   Qwen/Qwen3.8-27B-FP8   GPU 1  port 18101  then: traceeval ... --backend llm
#
# A server listens only on the server's own localhost; this machine reaches it through its tunnel, at
# http://127.0.0.1:PORT/v1. Environment variables override a preset for one call:
#   TRACEEVAL_SITE       [fmi0]  where the GPUs are: fmi0 (the shared server) or hpc (the SLURM cluster, below)
#   TRACEEVAL_GPU_HOST   [fmi0@10.23.13.53]  SSH login on the server (key-based)
#   TRACEEVAL_GPUS       GPUs to use, one copy of the model per GPU (e.g. TRACEEVAL_GPUS=0,1 for gemma alone);
#                        the server is shared: only GPUs 0 and 1 are ours, never list GPU 2. On hpc: how many
#   TRACEEVAL_VLLM_PORT  port on both ends of the tunnel
#   TRACEEVAL_HF_MODEL   the gemma preset's model (the vllm backend reads the same variable)
#   TRACEEVAL_VLLM_ENV   extra settings for the server, e.g. "VLLM_BATCH_INVARIANT=1" (greedy answers that do not
#                        depend on how requests are batched together)
#
# TRACEEVAL_SITE=hpc runs the same commands on the SLURM cluster (login ciprian.paduraru@hpc-ctrl01.acc-ub.local).
# 'up' submits a job for 2 GPUs (at most 8 hours, SLURM's limit) whose server listens on the GPU node's localhost,
# and opens the tunnel through the controller; 'down' cancels the job. The first job also creates the vLLM
# environment and downloads the model. The ports are the presets' plus 10 (gemma 18110, qwen 18111), so both
# sites can serve at once; list both URLs, comma-separated, in TRACEEVAL_VLLM_URL (gemma) or
# TRACEEVAL_LLM_BASE_URL (qwen), and a run sends its requests to the servers in turn.
set -euo pipefail

SITE=${TRACEEVAL_SITE:-fmi0}
case "$SITE" in
  fmi0) HOST=${TRACEEVAL_GPU_HOST:-fmi0@10.23.13.53} ;;
  hpc) HOST=${TRACEEVAL_GPU_HOST:-ciprian.paduraru@hpc-ctrl01.acc-ub.local} ;;
  *) echo "unknown site '$SITE' (fmi0 or hpc)"; exit 2 ;;
esac
VERSION=0.31.0  # the vLLM release setup installs
RDIR=traceeval-vllm  # folder in the server home: environment, and per model its log and pid
PRESETS="gemma qwen"

# Sets the variables of one preset: model, GPUs, port, extra vLLM flags, and where its pid and log live.
preset() {
  NAME=$1
  case "$NAME" in
    gemma)  # we build Gemma's prompts and parse its answers ourselves (traceeval/llm/chat.py)
      MODEL=${TRACEEVAL_HF_MODEL:-google/gemma-4-E4B-it}; GPUS=0; PORT=18100; EXTRA="" ;;
    qwen)  # vLLM applies Qwen's chat template and parses its tool calls; thinking and images are off
      MODEL=Qwen/Qwen3.8-27B-FP8; GPUS=1; PORT=18101
      EXTRA="--enable-auto-tool-choice --tool-call-parser qwen3_coder --reasoning-parser qwen3"
      EXTRA="$EXTRA --default-chat-template-kwargs '{\"enable_thinking\": false}'"
      EXTRA="$EXTRA --limit-mm-per-prompt '{\"image\": 0, \"video\": 0}'" ;;
    *) echo "unknown model '$NAME' (one of: $PRESETS)"; exit 2 ;;
  esac
  SUFFIX=""
  if [ "$SITE" = hpc ]; then GPUS=2; PORT=$((PORT + 10)); SUFFIX="-hpc"; fi  # on hpc SLURM picks the GPUs
  GPUS=${TRACEEVAL_GPUS:-$GPUS}
  PORT=${TRACEEVAL_VLLM_PORT:-$PORT}
  COPIES=$(awk -F, '{print NF}' <<<"$GPUS")  # one copy of the model per GPU in the list
  if [ "$SITE" = hpc ]; then COPIES=$GPUS; fi
  URL="http://127.0.0.1:$PORT/v1"
  PIDF="$RDIR/$NAME.pid"  # on the server, relative to the home folder
  LOG="$RDIR/$NAME.log"
  JOB="traceeval-$NAME"  # the SLURM job's name on hpc
  TUNNEL_PID="$HOME/.traceeval-vllm-tunnel-$NAME$SUFFIX.pid"  # the local tunnel process, for 'down'
}

remote() { ssh -o BatchMode=yes -o ConnectTimeout=10 "$HOST" "$@"; }

server_alive() {
  if [ "$SITE" = hpc ]; then
    remote "squeue -h -u \$USER -n $JOB | grep -q ."
  else
    remote "[ -f ~/$PIDF ] && kill -0 \$(cat ~/$PIDF) 2>/dev/null"
  fi
}

# The FlashInfer sampler and DeepGEMM (FP8 matrix kernels) are off: both compile their kernels at start-up with
# the system nvcc, which on fmi0 is too old; vLLM's own sampler and its precompiled FP8 kernels need no compiling.
# At most 128 requests at once: a run sends a few dozen, and vLLM's default (1024) needs more per-request state
# than a hybrid model such as Qwen3.8 has room for.
SERVE_ENV="VLLM_USE_FLASHINFER_SAMPLER=0 VLLM_USE_DEEP_GEMM=0 ${TRACEEVAL_VLLM_ENV:-}"
serve_cmd() {
  echo ".venv/bin/vllm serve $MODEL --host 127.0.0.1 --port $PORT --data-parallel-size $COPIES \
    --max-model-len 32768 --max-num-seqs 128 --enable-prefix-caching --gpu-memory-utilization 0.85 --seed 0 $EXTRA"
}

# On hpc: submit the job that serves the model. It stops at once on a GPU that is already in use (SLURM does not
# see processes started outside it), creates the vLLM environment the first time, and serves until cancelled.
start_hpc() {
  remote "mkdir -p ~/$RDIR && cd ~/$RDIR && sbatch --job-name=$JOB --partition=gpu --gres=gpu:$COPIES \
    --cpus-per-task=$((8 * COPIES)) --mem=$((64 * COPIES))G --time=08:00:00 --output=$NAME.log" <<EOF
#!/bin/bash
if nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '\$1 > 1000 {busy = 1} END {exit !busy}'; then
  echo "A GPU given to this job is already in use by a process outside SLURM; stopping."; nvidia-smi; exit 1
fi
cd ~/$RDIR
[ -x .venv/bin/vllm ] || { python3 -m venv .venv && .venv/bin/pip install -q 'vllm==$VERSION'; }
$SERVE_ENV $(serve_cmd)
EOF
}

# On hpc the tunnel needs the GPU node, known once SLURM has started the job.
wait_for_node() {
  echo -n "$NAME: waiting for SLURM to start the job"
  for _ in $(seq 1 120); do
    NODE=$(remote "squeue -h -u \$USER -n $JOB -t RUNNING -o %N")
    if [ -n "$NODE" ]; then
      echo " on $NODE."
      return 0
    fi
    if ! server_alive; then
      echo " the job ended. Last lines of ~/$LOG:"
      remote "tail -n 30 ~/$LOG"
      return 1
    fi
    echo -n "."
    sleep 5
  done
  echo " not started after 10 minutes; 'squeue' on the controller shows why."
  return 1
}

tunnel_alive() { [ -f "$TUNNEL_PID" ] && kill -0 "$(cat "$TUNNEL_PID")" 2>/dev/null; }

server_ready() { curl -sf --max-time 5 "$URL/models" >/dev/null 2>&1; }

cmd_setup() {
  if [ "$SITE" = hpc ]; then
    echo "Nothing to do on hpc: the first job creates ~/$RDIR/.venv and downloads the model."
    return 0
  fi
  echo "Creating ~/$RDIR/.venv on $HOST with vllm==$VERSION ..."
  remote "set -e
    mkdir -p ~/$RDIR && cd ~/$RDIR
    UV=\$(command -v uv || echo ~/.local/bin/uv)
    [ -x .venv/bin/python ] || \$UV venv --python 3.12 .venv
    \$UV pip install --python .venv/bin/python 'vllm==$VERSION'
    .venv/bin/python -c 'import vllm, torch; print(\"vllm\", vllm.__version__, \"torch\", torch.__version__)'"
  for name in $PRESETS; do
    preset "$name"
    if remote "ls ~/.cache/huggingface/hub/models--${MODEL//\//--}/snapshots/*/config.json >/dev/null 2>&1"; then
      echo "$name: $MODEL is in the Hugging Face cache"
    else
      echo "$name: $MODEL is NOT in the cache; download it once on the server: ~/$RDIR/.venv/bin/hf download $MODEL"
    fi
  done
}

cmd_up() {
  preset "${1:-gemma}"
  if server_alive; then
    echo "$NAME: already running on $SITE."
  elif [ "$SITE" = hpc ]; then
    echo "$NAME: submitting a job for $MODEL on $GPUS GPUs of the cluster, port $PORT ..."
    start_hpc
  else
    echo "$NAME: starting $MODEL on $HOST, GPUs $GPUS, port $PORT ..."
    # setsid gives the server its own process group, so that 'down' stops it together with its workers.
    remote "cd ~/$RDIR || exit 1
      CUDA_VISIBLE_DEVICES=$GPUS HF_HUB_OFFLINE=1 $SERVE_ENV setsid nohup $(serve_cmd) > $NAME.log 2>&1 < /dev/null &
      echo \$! > $NAME.pid"
  fi
  # Through the controller to the GPU node on hpc; straight to the server on fmi0.
  local target=$HOST jump=""
  if [ "$SITE" = hpc ]; then
    wait_for_node || return 1
    target="${HOST%@*}@$NODE"
    jump="-J $HOST"
  fi
  if tunnel_alive; then
    echo "$NAME: tunnel already open (pid $(cat "$TUNNEL_PID"))."
  else
    # The tunnel runs in the background with no terminal attached, so it outlives this script.
    # shellcheck disable=SC2086  # $jump is empty or two words
    ssh -N -o BatchMode=yes -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 $jump \
      -L "$PORT:127.0.0.1:$PORT" "$target" </dev/null >/dev/null 2>&1 &
    echo $! >"$TUNNEL_PID"
    disown || true
    echo "$NAME: tunnel open, $URL (pid $(cat "$TUNNEL_PID"))."
  fi
  # The first job on hpc also installs vLLM and downloads the model: allow it half an hour.
  local tries=120
  if [ "$SITE" = hpc ]; then tries=360; fi
  echo -n "$NAME: waiting for the server"
  for _ in $(seq 1 "$tries"); do
    if server_ready; then
      echo " ready."
      return 0
    fi
    if ! server_alive; then
      echo " the server stopped. Last lines of ~/$LOG:"
      remote "tail -n 30 ~/$LOG"
      return 1
    fi
    echo -n "."
    sleep 5
  done
  echo " not ready after $((tries / 12)) minutes; see: scripts/gpu_remote.sh logs $NAME"
  return 1
}

cmd_status() {
  if [ "$SITE" = hpc ]; then  # the controller has no GPUs: show our jobs instead
    remote "squeue -u \$USER -o '%.10i %.18j %.9T %.10M %.12N %b'"
  else
    remote "nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv,noheader"
  fi
  for name in $PRESETS; do
    preset "$name"
    local server tunnel endpoint
    if server_alive; then server="running"; else server="stopped"; fi
    if tunnel_alive; then tunnel="open"; else tunnel="closed"; fi
    if server_ready; then endpoint="answers"; else endpoint="does not answer"; fi
    echo "$name ($MODEL): server $server, tunnel $tunnel, $URL $endpoint"
  done
}

cmd_logs() {
  preset "${1:-gemma}"
  remote "tail -n 50 -f ~/$LOG"
}

cmd_down() {
  for name in ${1:-$PRESETS}; do
    preset "$name"
    if [ "$SITE" = hpc ]; then
      remote "if squeue -h -u \$USER -n $JOB | grep -q .; then scancel -u \$USER -n $JOB; echo '$NAME: job cancelled'; fi"
    else
      remote "if [ -f ~/$PIDF ]; then kill -TERM -- -\$(cat ~/$PIDF) 2>/dev/null || true;
        rm -f ~/$PIDF; echo '$NAME: server stopped'; fi"
    fi
    if [ -f "$TUNNEL_PID" ]; then
      kill "$(cat "$TUNNEL_PID")" 2>/dev/null || true
      rm -f "$TUNNEL_PID"
      echo "$NAME: tunnel closed"
    fi
  done
}

case "${1:-}" in
  setup) cmd_setup ;;
  up) cmd_up "${2:-}" ;;
  status) cmd_status ;;
  logs) cmd_logs "${2:-}" ;;
  down) cmd_down "${2:-}" ;;
  *) sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; exit 2 ;;
esac
