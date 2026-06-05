"""Show ONE held-out test case side by side:

    expected answer | fine-tuned model answer | relevance score | correctness score

Expected answers come from data/test.jsonl (the held-out split). Relevance is
reference-free (AnswerRelevancyMetric); correctness is reference-based GEval that
compares the model output against the expected answer. Judge = local Ollama gemma2:2b.

Usage:
    python side_by_side.py --adapter adapters_v5 --contains released
    python side_by_side.py --adapter adapters_v5 --index 0
"""
import argparse
import json
import textwrap
import warnings
from pathlib import Path

from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler

warnings.filterwarnings("ignore")
BASE_MODEL = "mlx-community/SmolLM2-135M-Instruct"


def pick_case(rows, contains, index):
    if contains:
        for r in rows:
            if contains.lower() in r["messages"][0]["content"].lower():
                return r
        raise SystemExit(f"No test question contains {contains!r}")
    return rows[index]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", default="adapters_v5")
    ap.add_argument("--contains", default=None, help="pick first test question containing this")
    ap.add_argument("--index", type=int, default=0)
    ap.add_argument("--judge-model", default="gemma2:2b")
    args = ap.parse_args()

    rows = [json.loads(l) for l in open(Path("data") / "test.jsonl")]
    case = pick_case(rows, args.contains, args.index)
    question = case["messages"][0]["content"]
    expected = case["messages"][1]["content"]

    sampler = make_sampler(temp=0.0, top_p=1.0)

    def run(adapter_path):
        model, tok = load(BASE_MODEL, adapter_path=adapter_path)
        prompt = tok.apply_chat_template(
            [{"role": "user", "content": question}], tokenize=False, add_generation_prompt=True
        )
        return generate(model, tok, prompt=prompt, max_tokens=150, sampler=sampler, verbose=False).strip()

    base_out = run(None)          # base model, no fine-tuning
    actual = run(args.adapter)    # fine-tuned

    from deepeval.models import OllamaModel
    from deepeval.metrics import AnswerRelevancyMetric, GEval
    from deepeval.test_case import LLMTestCase, LLMTestCaseParams

    judge = OllamaModel(model=args.judge_model, temperature=0.0)
    relevancy = AnswerRelevancyMetric(model=judge, async_mode=False, verbose_mode=False)
    correctness = GEval(
        name="Correctness",
        criteria=(
            "Compare the actual output to the expected output. Score high only if the "
            "actual output is factually correct and agrees with the expected answer on "
            "all key facts (names, dates, numbers). Penalize wrong or contradictory facts."
        ),
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.EXPECTED_OUTPUT,
        ],
        model=judge,
        async_mode=False,
        verbose_mode=False,
    )

    def score(metric, output):
        tc = LLMTestCase(input=question, actual_output=output, expected_output=expected)
        try:
            metric.measure(tc)
            return f"{metric.score:.2f}", (metric.reason or "").strip()
        except Exception as e:
            return "n/a", f"scoring failed: {type(e).__name__}: {e}"

    base_rel_s, base_rel_r = score(relevancy, base_out)
    base_cor_s, base_cor_r = score(correctness, base_out)
    ft_rel_s, ft_rel_r = score(relevancy, actual)
    ft_cor_s, ft_cor_r = score(correctness, actual)

    def block(text):
        return "\n".join("    " + l for l in textwrap.wrap(text, 92)) or "    (empty)"

    bar = "=" * 100
    print(f"\n{bar}\nSIDE-BY-SIDE — base vs fine-tuned ({args.adapter})   judge: ollama/{args.judge_model}\n{bar}")
    print(f"\nQUESTION:\n{block(question)}")
    print(f"\nEXPECTED RESPONSE (from test.jsonl):\n{block(expected)}")
    print(f"\nBASE MODEL RESPONSE (no fine-tuning):\n{block(base_out)}")
    print(f"\nFINE-TUNED MODEL RESPONSE:\n{block(actual)}")
    print(f"\n{'-'*100}")
    print(f"  {'metric':<13} {'base':>8} {'fine-tuned':>12}")
    print(f"  {'relevance':<13} {base_rel_s:>8} {ft_rel_s:>12}   (reference-free)")
    print(f"  {'correctness':<13} {base_cor_s:>8} {ft_cor_s:>12}   (vs expected answer)")
    print(f"{'-'*100}")
    print("\n  reasons (base):")
    print(f"    relevance  : {base_rel_r}")
    print(f"    correctness: {base_cor_r}")
    print("\n  reasons (fine-tuned):")
    print(f"    relevance  : {ft_rel_r}")
    print(f"    correctness: {ft_cor_r}\n")


if __name__ == "__main__":
    main()
