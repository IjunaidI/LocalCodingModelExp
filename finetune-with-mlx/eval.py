"""Run the evaluation questions against a model and log the run.

By default each answer is also scored for Relevance and Completeness using
DeepEval with a local Ollama judge model (gemma2:2b). The Ollama server must
be running locally (`ollama serve`) and the judge model already pulled.

Usage:
    python eval.py                          # base model, with scoring
    python eval.py --adapter adapters_v4    # fine-tuned, with scoring
    python eval.py --no-score               # skip DeepEval scoring (faster)
    python eval.py --judge-model llama3.1:8b  # use a different Ollama judge
"""
import argparse
import json
import platform
import statistics
import sys
import warnings
from datetime import datetime
from importlib.metadata import version
from pathlib import Path

import mlx.core as mx
from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler

warnings.filterwarnings("ignore")  # silence deepeval pydantic deprecation noise

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


def build_scorers(judge_model: str):
    """Return (relevancy, completeness) DeepEval metrics backed by a local Ollama judge."""
    from deepeval.models import OllamaModel
    from deepeval.metrics import AnswerRelevancyMetric, GEval
    from deepeval.test_case import LLMTestCaseParams

    judge = OllamaModel(model=judge_model, temperature=0.0)
    relevancy = AnswerRelevancyMetric(model=judge, async_mode=False, verbose_mode=False)
    completeness = GEval(
        name="Completeness",
        criteria=(
            "Determine whether the actual output fully addresses the input question "
            "without omitting key information. A complete answer covers the main aspects "
            "of what was asked; an incomplete answer leaves obvious gaps."
        ),
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
        model=judge,
        async_mode=False,
        verbose_mode=False,
    )
    return relevancy, completeness


def score_qa(question: str, answer: str, relevancy, completeness) -> dict:
    """Run both metrics and return scores + reasons. Failures are caught and recorded."""
    from deepeval.test_case import LLMTestCase

    tc = LLMTestCase(input=question, actual_output=answer)
    result = {}
    for name, metric in [("relevance", relevancy), ("completeness", completeness)]:
        try:
            metric.measure(tc)
            result[name] = {"score": float(metric.score), "reason": (metric.reason or "").strip()}
        except Exception as e:
            result[name] = {"score": None, "reason": f"scoring failed: {type(e).__name__}: {e}"}
    return result


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
        "scoring": {
            "enabled": not args.no_score,
            "framework": "deepeval" if not args.no_score else None,
            "judge_backend": "ollama" if not args.no_score else None,
            "judge_model": args.judge_model if not args.no_score else None,
            "metrics": ["AnswerRelevancyMetric", "GEval(Completeness)"] if not args.no_score else [],
        },
        "environment": {
            "python": sys.version.split()[0],
            "platform": f"{platform.system()} {platform.machine()}",
            "mlx_lm_version": version("mlx-lm"),
            "mlx_version": version("mlx"),
            "deepeval_version": version("deepeval") if not args.no_score else None,
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


def fmt_score(s) -> str:
    return f"{s:.2f}" if isinstance(s, float) else "n/a"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", default=None, help="Path to LoRA adapter dir")
    parser.add_argument("--max-tokens", type=int, default=150)
    parser.add_argument("--temperature", type=float, default=0.0, help="0 = greedy")
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--log", default=None, help="Override log file path")
    parser.add_argument("--no-score", action="store_true", help="Skip DeepEval scoring")
    parser.add_argument(
        "--judge-model",
        default="gemma2:2b",
        help="Ollama model used as DeepEval judge (must be pulled locally)",
    )
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

    relevancy = completeness = None
    if not args.no_score:
        print(f"Setting up DeepEval scorers (judge: ollama/{args.judge_model})")
        relevancy, completeness = build_scorers(args.judge_model)

    per_bucket_scores: dict[str, dict[str, list[float]]] = {}

    for bucket, questions in QUESTIONS.items():
        header = f"\n## {bucket}\n\n"
        print(f"\n{'=' * 70}\n{bucket}\n{'=' * 70}")
        append_log(log_path, header)
        per_bucket_scores[bucket] = {"relevance": [], "completeness": []}

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

            if not args.no_score:
                scores = score_qa(q, response, relevancy, completeness)
                rel = scores["relevance"]
                comp = scores["completeness"]
                block += (
                    f"**Scores** — relevance: `{fmt_score(rel['score'])}`, "
                    f"completeness: `{fmt_score(comp['score'])}`\n\n"
                    f"_Relevance reason:_ {rel['reason']}\n\n"
                    f"_Completeness reason:_ {comp['reason']}\n\n"
                )
                print(
                    f"\nQ{i}: {q}\nA: {response}\n"
                    f"   relevance={fmt_score(rel['score'])} completeness={fmt_score(comp['score'])}"
                )
                if isinstance(rel["score"], float):
                    per_bucket_scores[bucket]["relevance"].append(rel["score"])
                if isinstance(comp["score"], float):
                    per_bucket_scores[bucket]["completeness"].append(comp["score"])
            else:
                print(f"\nQ{i}: {q}\nA: {response}")

            append_log(log_path, block)

    if not args.no_score:
        append_log(log_path, "\n## Summary — mean scores per bucket\n\n")
        append_log(log_path, "| Bucket | mean relevance | mean completeness | n |\n")
        append_log(log_path, "|---|---|---|---|\n")
        print("\n" + "=" * 70 + "\nSummary — mean scores per bucket\n" + "=" * 70)
        for bucket, sc in per_bucket_scores.items():
            rel_mean = statistics.mean(sc["relevance"]) if sc["relevance"] else float("nan")
            comp_mean = statistics.mean(sc["completeness"]) if sc["completeness"] else float("nan")
            n = max(len(sc["relevance"]), len(sc["completeness"]))
            append_log(
                log_path,
                f"| {bucket} | {rel_mean:.2f} | {comp_mean:.2f} | {n} |\n",
            )
            print(f"{bucket}: relevance={rel_mean:.2f}  completeness={comp_mean:.2f}  n={n}")

    print(f"\nLog saved: {log_path}")


if __name__ == "__main__":
    main()
