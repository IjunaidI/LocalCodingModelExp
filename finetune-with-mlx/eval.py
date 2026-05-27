"""Run the evaluation questions against a model and log the run.

Usage:
    python eval.py                          # base model, auto-named log
    python eval.py --adapter adapters/      # after fine-tuning
    python eval.py --log logs/custom.md     # custom log path
"""
import argparse
import json
import platform
import sys
from datetime import datetime
from importlib.metadata import version
from pathlib import Path

import mlx.core as mx
from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler

BASE_MODEL = "mlx-community/SmolLM2-135M-Instruct"

QUESTIONS = {
    "1. In-distribution": [
        "What is MLX?",
        "When was MLX released?",
        "What hardware does MLX run on?",
        "How does memory work in MLX?",
        "What is lazy evaluation in MLX?",
        "What is mlx-lm?",
        "Does MLX support LoRA?",
        "How do I install MLX?",
        "What is mlx-community?",
        "How big is the smallest SmolLM2 model?",
    ],
    "2. Paraphrased / generalization": [
        "I'm new to Apple's ML stack — what library should I look at?",
        "Who is behind MLX?",
        "Will MLX work on my gaming PC?",
        "If I'm coming from PyTorch, does MLX feel familiar?",
        "Why is MLX efficient on M-series chips compared to other frameworks?",
        "Does an MLX computation happen the moment I call an operation?",
        "What's the equivalent of torch.autograd.grad in MLX?",
        "What package would I pip install to chat with Llama on my Mac?",
        "What's the cheap way to fine-tune a language model with MLX?",
        "Where on GitHub can I read the MLX source?",
    ],
    "3. Out-of-distribution (hallucination check)": [
        "What is TensorFlow?",
        "Who is the CEO of Anthropic?",
        "Write me a Python function that reverses a string.",
        "What is the capital of France?",
        "Does MLX support distributed training across multiple Macs?",
        "What is the largest model size mlx-lm can run on a 16GB M2?",
        "Explain backpropagation.",
        "What is the price of an M4 Mac mini?",
    ],
}


def collect_params(args: argparse.Namespace, model_path: str) -> dict:
    return {
        "timestamp_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "model": model_path,
        "adapter": args.adapter,
        "run_label": "base" if args.adapter is None else "fine-tuned",
        "sampling": {
            "max_tokens": args.max_tokens,
            "temperature": args.temperature,
            "top_p": args.top_p,
            "seed": args.seed,
        },
        "environment": {
            "python": sys.version.split()[0],
            "platform": f"{platform.system()} {platform.machine()}",
            "mlx_lm_version": version("mlx-lm"),
            "mlx_version": version("mlx"),
        },
    }


def write_log_header(log_path: Path, params: dict) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w") as f:
        f.write(f"# Eval Run — {params['run_label']} — {params['timestamp_utc']}\n\n")
        f.write("## Parameters\n\n")
        f.write("```json\n")
        f.write(json.dumps(params, indent=2))
        f.write("\n```\n\n")


def append_log(log_path: Path, text: str) -> None:
    with log_path.open("a") as f:
        f.write(text)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", default=None, help="Path to LoRA adapter dir")
    parser.add_argument("--max-tokens", type=int, default=150)
    parser.add_argument("--temperature", type=float, default=0.0, help="0 = greedy")
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--log", default=None, help="Override log file path")
    args = parser.parse_args()

    mx.random.seed(args.seed)

    params = collect_params(args, BASE_MODEL)
    if args.log:
        log_path = Path(args.log)
    else:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        log_path = Path("logs") / f"eval_{params['run_label']}_{ts}.md"

    write_log_header(log_path, params)
    print(f"Logging to {log_path}")
    print(f"Loading {BASE_MODEL}" + (f" with adapter {args.adapter}" if args.adapter else ""))

    model, tokenizer = load(BASE_MODEL, adapter_path=args.adapter)
    sampler = make_sampler(temp=args.temperature, top_p=args.top_p)

    for bucket, questions in QUESTIONS.items():
        header = f"\n## {bucket}\n\n"
        print(f"\n{'=' * 70}\n{bucket}\n{'=' * 70}")
        append_log(log_path, header)

        for i, q in enumerate(questions, 1):
            chat_prompt = tokenizer.apply_chat_template(
                [{"role": "user", "content": q}],
                tokenize=False,
                add_generation_prompt=True,
            )
            response = generate(
                model,
                tokenizer,
                prompt=chat_prompt,
                max_tokens=args.max_tokens,
                sampler=sampler,
                verbose=False,
            ).strip()

            block = f"### Q{i}. {q}\n\n{response}\n\n"
            print(f"\nQ{i}: {q}\nA: {response}")
            append_log(log_path, block)

    print(f"\nLog saved: {log_path}")


if __name__ == "__main__":
    main()
