import argparse
import time
from statistics import mean

from tensorrt_llm import LLM, SamplingParams


def run_inference(args: argparse.Namespace) -> None:
    prompts = args.prompts
    sampling_params = SamplingParams(
        temperature=args.temperature,
        top_p=args.top_p,
        max_tokens=args.max_tokens,
    )

    llm = LLM(model=args.model, tensor_parallel_size=args.tensor_parallel_size)

    latencies = []
    for i in range(args.iterations):
        t0 = time.perf_counter()
        outputs = list(llm.generate(prompts, sampling_params))
        latencies.append(time.perf_counter() - t0)
        if args.print_outputs:
            print(f"--- iteration {i + 1} ---")
            for out in outputs:
                text = out.outputs[0].text if out.outputs else ""
                print(f"Prompt: {out.prompt!r}\nCompletion: {text!r}\n")

    print("=== Summary ===")
    print(f"model={args.model}")
    print(f"batch_size={len(prompts)}")
    print(f"iterations={args.iterations}")
    print(f"avg_latency_s={mean(latencies):.4f}")
    print(f"p50_latency_s={sorted(latencies)[len(latencies)//2]:.4f}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="TensorRT-LLM Python LLM API pipeline")
    p.add_argument("--model", required=True, help="HF model id or local model/checkpoint path")
    p.add_argument("--prompts", nargs="+", default=["Hello, my name is", "The capital of France is"])
    p.add_argument("--iterations", type=int, default=5)
    p.add_argument("--temperature", type=float, default=0.8)
    p.add_argument("--top-p", type=float, default=0.95)
    p.add_argument("--max-tokens", type=int, default=64)
    p.add_argument("--tensor-parallel-size", type=int, default=1)
    p.add_argument("--print-outputs", action="store_true")
    return p.parse_args()


if __name__ == "__main__":
    run_inference(parse_args())
