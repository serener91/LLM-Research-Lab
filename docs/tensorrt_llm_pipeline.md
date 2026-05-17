# TensorRT-LLM Inference Optimization Pipeline (CLI + Python API)

## 1) Version pinning (as of 2026-05-17)

- **Latest stable release**: `v1.2.1`.
- **Latest overall** on docs quick-start examples uses `1.3.0rc*` images (release candidates / pre-release line).
- Production recommendation: pin stable for baseline, test RC separately via canary.

## 2) End-to-end optimization process

1. Start with `trtllm-serve` quick validation on a smaller model.
2. For production, tune engine/model serving limits (batch/sequence/KV cache).
3. Measure throughput and latency (`trtllm-bench`, app-level metrics).
4. Iterate on precision, batch, parallelism, and prompt length distributions.

## 3) CLI workflow

Use `scripts/cli_pipeline.sh` for build/serve/benchmark stages.

- `build`: `trtllm-build`
- `serve`: `trtllm-serve`
- `bench`: `trtllm-bench`

## 4) Python backend (actual LLM API)

Use `src/python_pipeline.py`, which directly uses TensorRT-LLM Python API:

- Imports `LLM` and `SamplingParams` from `tensorrt_llm`.
- Creates `LLM(model=...)` instance.
- Calls `llm.generate(prompts, sampling_params)` for batched generation.
- Reports basic latency summary for repeated iterations.

Example:

```bash
python3 src/python_pipeline.py \
  --model TinyLlama/TinyLlama-1.1B-Chat-v1.0 \
  --prompts "Hello, my name is" "The future of AI is" \
  --iterations 10 --max-tokens 64 --print-outputs
```

## 5) Docker packaging

- `docker/Dockerfile.cli`: CLI pipeline image.
- `docker/Dockerfile.python`: Python API runner image.
- Pinned base image: `nvcr.io/nvidia/tensorrt-llm/release:1.2.1`.

## 6) Docker Compose

`docker-compose.yml` provides:
- `trtllm-cli`: CLI flow.
- `trtllm-python`: Python LLM API flow.

## 7) Production hardening checklist

- Pin model revision + tokenizer artifacts.
- Persist engine/timing cache to mounted volume.
- Export service metrics and set health probes.
- Use representative prompt/completion distributions for perf tests.
- Validate upgrades in canary before moving stable tag.
