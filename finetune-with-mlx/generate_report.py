"""Resumable side-by-side report over ALL held-out test cases (data/test.jsonl).

For every test question: expected answer, base-model answer, fine-tuned answer,
and relevance + correctness scores for both models. Judge = local Ollama.

Kill-proof: every question's result is cached to report_cache_<adapter>.jsonl as it
completes. Re-running reuses good (non-n/a) results and only (re)generates/(re)judges
what's missing — so a killed run loses nothing, just resume by running again. MLX
models are loaded ONLY if some answer still needs generating (re-judging cached
answers needs no MLX at all).

Usage:
    python generate_report.py --adapter adapters_v5
    python generate_report.py --adapter adapters_v5 --judge-model gemma2:2b
"""
import os

# DeepEval phones home to PostHog after every metric; with no internet those uploads
# hang on 15s timeouts and strangle the run. Opt out BEFORE importing deepeval.
os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "YES")
os.environ.setdefault("DEEPEVAL_DISABLE_TELEMETRY", "YES")
os.environ.setdefault("ERROR_REPORTING", "0")

import argparse
import json
import statistics
import warnings
from datetime import datetime
from pathlib import Path

warnings.filterwarnings("ignore")
BASE_MODEL = "mlx-community/SmolLM2-135M-Instruct"


def is_num(x):
    return isinstance(x, (int, float))


def load_cache(path: Path) -> dict:
    cache = {}
    if path.exists():
        for line in path.open():
            line = line.strip()
            if line:
                r = json.loads(line)
                cache[r["q"]] = r
    return cache


def save_cache(path: Path, cache: dict, order: list) -> None:
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        for q in order:
            if q in cache:
                f.write(json.dumps(cache[q]) + "\n")
    tmp.replace(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", default="adapters_v5")
    ap.add_argument("--judge-model", default="gemma2:2b")
    ap.add_argument("--max-tokens", type=int, default=150)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    rows = [json.loads(l) for l in open(Path("data") / "test.jsonl")]
    if args.limit:
        rows = rows[: args.limit]
    questions = [r["messages"][0]["content"] for r in rows]
    expected = {r["messages"][0]["content"]: r["messages"][1]["content"] for r in rows}

    cache_path = Path(f"report_cache_{args.adapter}.jsonl")
    cache = load_cache(cache_path)
    for q in questions:
        cache.setdefault(q, {"q": q, "expected": expected[q]})

    # ---- figure out what still needs generating ----
    need_base = [q for q in questions if not cache[q].get("base_out")]
    need_ft = [q for q in questions if not cache[q].get("ft_out")]
    print(f"{len(questions)} questions | base gens needed: {len(need_base)} | "
          f"ft gens needed: {len(need_ft)}")

    if need_base or need_ft:
        from mlx_lm import load, generate
        from mlx_lm.sample_utils import make_sampler
        sampler = make_sampler(temp=0.0, top_p=1.0)

        def gen_for(adapter_path, qs, key):
            if not qs:
                return
            model, tok = load(BASE_MODEL, adapter_path=adapter_path)
            for i, q in enumerate(qs, 1):
                prompt = tok.apply_chat_template(
                    [{"role": "user", "content": q}], tokenize=False, add_generation_prompt=True
                )
                cache[q][key] = generate(model, tok, prompt=prompt, max_tokens=args.max_tokens,
                                         sampler=sampler, verbose=False).strip()
                if i % 10 == 0:
                    save_cache(cache_path, cache, questions)
                    print(f"  {key}: {i}/{len(qs)} generated")
            save_cache(cache_path, cache, questions)

        gen_for(None, need_base, "base_out")
        gen_for(args.adapter, need_ft, "ft_out")

        import gc
        import mlx.core as mx
        gc.collect()
        try:
            mx.clear_cache()
        except Exception:
            pass

    # ---- scoring (only where missing/n-a) ----
    def fully_scored(c):
        return all(is_num(c.get(k)) for k in ("base_rel", "base_cor", "ft_rel", "ft_cor"))

    todo = [q for q in questions if not fully_scored(cache[q])]
    print(f"scoring needed for {len(todo)}/{len(questions)} questions")

    if todo:
        from deepeval.models import OllamaModel
        from deepeval.metrics import AnswerRelevancyMetric, GEval
        from deepeval.test_case import LLMTestCase, LLMTestCaseParams

        judge = OllamaModel(model=args.judge_model, temperature=0.0)
        try:
            judge.generate("Reply with OK.")
            print("Judge warmed.")
        except Exception as e:
            print(f"Judge warmup failed: {type(e).__name__}: {e}")

        relevancy = AnswerRelevancyMetric(model=judge, async_mode=False, verbose_mode=False)
        correctness = GEval(
            name="Correctness",
            criteria=(
                "Compare the actual output to the expected output. Score high only if the actual "
                "output is factually correct and agrees with the expected answer on all key facts "
                "(names, dates, numbers). Penalize wrong or contradictory facts."
            ),
            evaluation_params=[
                LLMTestCaseParams.INPUT,
                LLMTestCaseParams.ACTUAL_OUTPUT,
                LLMTestCaseParams.EXPECTED_OUTPUT,
            ],
            model=judge, async_mode=False, verbose_mode=False,
        )

        def score(metric, q, out):
            tc = LLMTestCase(input=q, actual_output=out, expected_output=expected[q])
            try:
                metric.measure(tc)
                return float(metric.score), (metric.reason or "").strip()
            except Exception as e:
                return None, f"scoring failed: {type(e).__name__}: {e}"

        for n, q in enumerate(todo, 1):
            c = cache[q]
            if not is_num(c.get("base_rel")):
                c["base_rel"], c["base_rel_r"] = score(relevancy, q, c["base_out"])
            if not is_num(c.get("base_cor")):
                c["base_cor"], c["base_cor_r"] = score(correctness, q, c["base_out"])
            if not is_num(c.get("ft_rel")):
                c["ft_rel"], c["ft_rel_r"] = score(relevancy, q, c["ft_out"])
            if not is_num(c.get("ft_cor")):
                c["ft_cor"], c["ft_cor_r"] = score(correctness, q, c["ft_out"])
            save_cache(cache_path, cache, questions)  # persist after every question
            bc = c.get("base_cor"); fc = c.get("ft_cor")
            print(f"[{n}/{len(todo)}] {q[:45]!r} base_cor="
                  f"{bc if is_num(bc) else 'n/a'} ft_cor={fc if is_num(fc) else 'n/a'}")

    # ---- render markdown from cache ----
    def fmt(s):
        return f"{s:.2f}" if is_num(s) else "n/a"

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_path = Path(f"eval_comparison_base_vs_{args.adapter}_{ts}.md")
    agg = {"base_rel": [], "base_cor": [], "ft_rel": [], "ft_cor": []}
    na = 0

    with out_path.open("w") as f:
        f.write(f"# Eval comparison — base vs fine-tuned (`{args.adapter}`)\n\n")
        f.write(f"- Generated: {ts} UTC\n- Base model: `{BASE_MODEL}`\n")
        f.write(f"- Judge: `ollama/{args.judge_model}` (relevance reference-free; "
                f"correctness vs expected answer)\n")
        f.write(f"- Test cases: {len(rows)} (held-out, from `data/test.jsonl`)\n\n")
        f.write("Relevance = on-topic. Correctness = matches expected facts. "
                "High relevance + low correctness = fluent but wrong.\n\n---\n\n")
        for i, q in enumerate(questions, 1):
            c = cache[q]
            for k in agg:
                if is_num(c.get(k)):
                    agg[k].append(c[k])
            for k in ("base_rel", "base_cor", "ft_rel", "ft_cor"):
                if not is_num(c.get(k)):
                    na += 1
            f.write(f"## Q{i}. {q}\n\n")
            f.write(f"**Expected:** {c['expected']}\n\n")
            f.write(f"**Base model (no fine-tuning):** {c.get('base_out','')}\n\n")
            f.write(f"**Fine-tuned (`{args.adapter}`):** {c.get('ft_out','')}\n\n")
            f.write("| metric | base | fine-tuned |\n|---|---|---|\n")
            f.write(f"| relevance | {fmt(c.get('base_rel'))} | {fmt(c.get('ft_rel'))} |\n")
            f.write(f"| correctness | {fmt(c.get('base_cor'))} | {fmt(c.get('ft_cor'))} |\n\n")
            f.write("<details><summary>judge reasons</summary>\n\n")
            f.write(f"- base relevance: {c.get('base_rel_r','')}\n")
            f.write(f"- base correctness: {c.get('base_cor_r','')}\n")
            f.write(f"- fine-tuned relevance: {c.get('ft_rel_r','')}\n")
            f.write(f"- fine-tuned correctness: {c.get('ft_cor_r','')}\n\n</details>\n\n---\n\n")

        def mean(xs):
            return statistics.mean(xs) if xs else float("nan")

        improved = sum(
            1 for q in questions
            if is_num(cache[q].get("base_cor")) and is_num(cache[q].get("ft_cor"))
            and cache[q]["ft_cor"] > cache[q]["base_cor"]
        )
        regressed = sum(
            1 for q in questions
            if is_num(cache[q].get("base_cor")) and is_num(cache[q].get("ft_cor"))
            and cache[q]["ft_cor"] < cache[q]["base_cor"]
        )
        f.write("## Summary — mean scores\n\n")
        f.write("| metric | base | fine-tuned | scored n |\n|---|---|---|---|\n")
        f.write(f"| relevance | {mean(agg['base_rel']):.2f} | {mean(agg['ft_rel']):.2f} | "
                f"{min(len(agg['base_rel']), len(agg['ft_rel']))} |\n")
        f.write(f"| correctness | {mean(agg['base_cor']):.2f} | {mean(agg['ft_cor']):.2f} | "
                f"{min(len(agg['base_cor']), len(agg['ft_cor']))} |\n\n")
        f.write(f"Correctness: fine-tuning improved {improved}, regressed {regressed}, "
                f"of {min(len(agg['base_cor']), len(agg['ft_cor']))} scored pairs.\n\n")
        f.write(f"Unscored cells (judge n/a): {na}/{len(questions)*4}. "
                f"Re-run the same command to fill them.\n")

    print(f"\nSaved: {out_path}")
    print(f"n/a cells: {na}/{len(questions)*4}")


if __name__ == "__main__":
    main()
