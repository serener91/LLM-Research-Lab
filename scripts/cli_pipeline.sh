#!/usr/bin/env bash
set -euo pipefail

: "${MODEL_DIR:?Set MODEL_DIR}"
: "${ENGINE_DIR:?Set ENGINE_DIR}"
: "${TOKENIZER_DIR:?Set TOKENIZER_DIR}"

MAX_BATCH_SIZE="${MAX_BATCH_SIZE:-16}"
MAX_INPUT_LEN="${MAX_INPUT_LEN:-4096}"
MAX_SEQ_LEN="${MAX_SEQ_LEN:-8192}"
PORT="${PORT:-8000}"

STAGE="${1:-all}"

build_engine() {
  trtllm-build \
    --checkpoint_dir "${MODEL_DIR}" \
    --output_dir "${ENGINE_DIR}" \
    --max_batch_size "${MAX_BATCH_SIZE}" \
    --max_input_len "${MAX_INPUT_LEN}" \
    --max_seq_len "${MAX_SEQ_LEN}" \
    --paged_kv_cache enable
}

serve_engine() {
  trtllm-serve "${ENGINE_DIR}" \
    --backend tensorrt \
    --tokenizer "${TOKENIZER_DIR}" \
    --host 0.0.0.0 \
    --port "${PORT}"
}

bench_engine() {
  trtllm-bench throughput --engine_dir "${ENGINE_DIR}"
}

case "$STAGE" in
  build) build_engine ;;
  serve) serve_engine ;;
  bench) bench_engine ;;
  all)
    build_engine
    bench_engine
    serve_engine
    ;;
  *)
    echo "Unknown stage: $STAGE (use build|serve|bench|all)" >&2
    exit 1
    ;;
esac
