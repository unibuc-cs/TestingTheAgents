#!/usr/bin/env bash
# Serve the agents' model (Gemma 4 E4B) with vLLM on the GPU server, and reach it through an SSH tunnel.
#
#   scripts/gpu_remote.sh setup    once: create the vLLM environment on the server
#   scripts/gpu_remote.sh up       start the server on the chosen GPUs and open the tunnel (waits until ready)
#   scripts/gpu_remote.sh status   server process, GPU use, and whether the tunnel answers
#   scripts/gpu_remote.sh logs     follow the server log
#   scripts/gpu_remote.sh down     stop the server and close the tunnel
#
# Then run, e.g.:  traceeval mutants --backend vllm --workdir runs/x --reps 1
#
# The server listens only on the server's own localhost; this machine reaches it through the tunnel, at
# http://127.0.0.1:$PORT/v1 (what the vllm backend expects; override with TRACEEVAL_VLLM_URL).
# Settings, as environment variables [defaults]:
#   TRACEEVAL_GPU_HOST   [fmi0@10.23.13.53]       SSH login on the server (key-based)
#   TRACEEVAL_GPUS       [0,1]                     GPUs to use; one copy of the model per GPU
#   TRACEEVAL_VLLM_PORT  [18100]                   port on both ends of the tunnel
#   TRACEEVAL_HF_MODEL   [google/gemma-4-E4B-it]   must be in the server's Hugging Face cache
set -euo pipefail

HOST=${TRACEEVAL_GPU_HOST:-fmi0@10.23.13.53}
GPUS=${TRACEEVAL_GPUS:-0,1}
PORT=${TRACEEVAL_VLLM_PORT:-18100}
MODEL=${TRACEEVAL_HF_MODEL:-google/gemma-4-E4B-it}
VERSION=0.31.0                                     # the vLLM release setup installs
RDIR=traceeval-vllm                                # folder in the server home: environment, log, pid
TUNNEL_PID="$HOME/.traceeval-vllm-tunnel-$PORT.pid"  # the local tunnel process, for 'down'
COPIES=$(awk -F, '{print NF}' <<<"$GPUS")          # one copy of the model per GPU in the list
URL="http://127.0.0.1:$PORT/v1"

remote() { ssh -o BatchMode=yes -o ConnectTimeout=10 "$HOST" "$@"; }

tunnel_alive() { [ -f "$TUNNEL_PID" ] && kill -0 "$(cat "$TUNNEL_PID")" 2>/dev/null; }

server_ready() { curl -sf --max-time 5 "$URL/models" >/dev/null 2>&1; }

cmd_setup() {
  echo "Creating ~/$RDIR/.venv on $HOST with vllm==$VERSION ..."
  remote "set -e
    mkdir -p ~/$RDIR && cd ~/$RDIR
    UV=\$(command -v uv || echo ~/.local/bin/uv)
    [ -x .venv/bin/python ] || \$UV venv --python 3.12 .venv
    \$UV pip install --python .venv/bin/python 'vllm==$VERSION'
    .venv/bin/python -c 'import vllm, torch; print(\"vllm\", vllm.__version__, \"torch\", torch.__version__)'
    if ls ~/.cache/huggingface/hub/models--${MODEL//\//--}/snapshots/*/config.json >/dev/null 2>&1; then
      echo 'model: $MODEL is in the Hugging Face cache'
    else
      echo 'model: $MODEL is NOT in the cache; download it once on the server: hf download $MODEL'
    fi"
}

cmd_up() {
  if remote "[ -f ~/$RDIR/server.pid ] && kill -0 \$(cat ~/$RDIR/server.pid) 2>/dev/null"; then
    echo "Server already running on $HOST."
  else
    echo "Starting vLLM on $HOST, GPUs $GPUS ($COPIES copies of $MODEL) ..."
    # setsid gives the server its own process group, so that 'down' stops it together with its workers.
    # The FlashInfer sampler is off: it compiles its kernels at start-up with the system nvcc, which on this
    # server is too old; vLLM's own sampler needs no compiling.
    remote "cd ~/$RDIR || exit 1
      CUDA_VISIBLE_DEVICES=$GPUS HF_HUB_OFFLINE=1 VLLM_USE_FLASHINFER_SAMPLER=0 \
        setsid nohup .venv/bin/vllm serve $MODEL --host 127.0.0.1 --port $PORT \
        --data-parallel-size $COPIES --max-model-len 32768 --enable-prefix-caching \
        --gpu-memory-utilization 0.85 --seed 0 > server.log 2>&1 < /dev/null &
      echo \$! > server.pid"
  fi
  if tunnel_alive; then
    echo "Tunnel already open (pid $(cat "$TUNNEL_PID"))."
  else
    # The tunnel runs in the background with no terminal attached, so it outlives this script.
    ssh -N -o BatchMode=yes -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
      -L "$PORT:127.0.0.1:$PORT" "$HOST" </dev/null >/dev/null 2>&1 &
    echo $! >"$TUNNEL_PID"
    disown || true
    echo "Tunnel open: $URL (pid $(cat "$TUNNEL_PID"))."
  fi
  echo -n "Waiting for the server"
  for _ in $(seq 1 120); do
    if server_ready; then
      echo " ready."
      return 0
    fi
    if ! remote "kill -0 \$(cat ~/$RDIR/server.pid) 2>/dev/null"; then
      echo " the server stopped. Last lines of ~/$RDIR/server.log:"
      remote "tail -n 30 ~/$RDIR/server.log"
      return 1
    fi
    echo -n "."
    sleep 5
  done
  echo " not ready after 10 minutes; see: scripts/gpu_remote.sh logs"
  return 1
}

cmd_status() {
  remote "if [ -f ~/$RDIR/server.pid ] && kill -0 \$(cat ~/$RDIR/server.pid) 2>/dev/null; then
      echo \"server: running (pid \$(cat ~/$RDIR/server.pid))\"; else echo 'server: stopped'; fi
    nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv,noheader"
  if tunnel_alive; then echo "tunnel: open (pid $(cat "$TUNNEL_PID"))"; else echo "tunnel: closed"; fi
  if server_ready; then echo "endpoint: $URL answers"; else echo "endpoint: $URL does not answer"; fi
}

cmd_logs() { remote "tail -n 50 -f ~/$RDIR/server.log"; }

cmd_down() {
  remote "if [ -f ~/$RDIR/server.pid ]; then kill -TERM -- -\$(cat ~/$RDIR/server.pid) 2>/dev/null || true;
    rm -f ~/$RDIR/server.pid; echo 'server: stopped'; else echo 'server: not running'; fi"
  if [ -f "$TUNNEL_PID" ]; then
    kill "$(cat "$TUNNEL_PID")" 2>/dev/null || true
    rm -f "$TUNNEL_PID"
    echo "tunnel: closed"
  fi
}

case "${1:-}" in
  setup) cmd_setup ;;
  up) cmd_up ;;
  status) cmd_status ;;
  logs) cmd_logs ;;
  down) cmd_down ;;
  *) sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'; exit 2 ;;
esac
