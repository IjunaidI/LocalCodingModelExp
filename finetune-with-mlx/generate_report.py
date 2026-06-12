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
import gc
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


def fmt(s):
    return f"{s:.2f}" if isinstance(s, (int, float)) else "n/a"


def write_md(out_path: Path, cache: dict, questions: list, n_cases: int, adapter: str,
             judge_model: str) -> int:
    """Render the full comparison md from the current cache. Called after EVERY eval,
    so the file always reflects all progress so far. Returns the count of n/a cells.

    Written atomically (tmp + replace) so a kill mid-write can't corrupt the file.
    """
    def mean(xs):
        return statistics.mean(xs) if xs else float("nan")

    agg = {"base_rel": [], "base_cor": [], "ft_rel": [], "ft_cor": []}
    na = 0
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    tmp = out_path.with_suffix(".md.tmp")
    with tmp.open("w") as f:
        f.write(f"# Eval comparison — base vs fine-tuned (`{adapter}`)\n\n")
        f.write(f"- Last updated: {ts} UTC\n- Base model: `{BASE_MODEL}`\n")
        f.write(f"- Judge: `ollama/{judge_model}` (relevance reference-free; "
                f"correctness vs expected answer)\n")
        f.write(f"- Test cases: {n_cases} (held-out, from `data/test.jsonl`)\n\n")
        f.write("Relevance = on-topic. Correctness = matches expected facts. "
                "High relevance + low correctness = fluent but wrong.\n\n")

        scored = sum(
            1 for q in questions
            if all(isinstance(cache[q].get(k), (int, float))
                   for k in ("base_rel", "base_cor", "ft_rel", "ft_cor"))
        )
        f.write(f"**Progress: {scored}/{len(questions)} questions fully scored.**\n\n---\n\n")

        for i, q in enumerate(questions, 1):
            c = cache[q]
            for k in agg:
                if isinstance(c.get(k), (int, float)):
                    agg[k].append(c[k])
            for k in ("base_rel", "base_cor", "ft_rel", "ft_cor"):
                if not isinstance(c.get(k), (int, float)):
                    na += 1
            f.write(f"## Q{i}. {q}\n\n")
            f.write(f"**Expected:** {c.get('expected','')}\n\n")
            f.write(f"**Base model (no fine-tuning):** {c.get('base_out','')}\n\n")
            f.write(f"**Fine-tuned (`{adapter}`):** {c.get('ft_out','')}\n\n")
            f.write("| metric | base | fine-tuned |\n|---|---|---|\n")
            f.write(f"| relevance | {fmt(c.get('base_rel'))} | {fmt(c.get('ft_rel'))} |\n")
            f.write(f"| correctness | {fmt(c.get('base_cor'))} | {fmt(c.get('ft_cor'))} |\n\n")
            f.write("<details><summary>judge reasons</summary>\n\n")
            f.write(f"- base relevance: {c.get('base_rel_r','')}\n")
            f.write(f"- base correctness: {c.get('base_cor_r','')}\n")
            f.write(f"- fine-tuned relevance: {c.get('ft_rel_r','')}\n")
            f.write(f"- fine-tuned correctness: {c.get('ft_cor_r','')}\n\n</details>\n\n---\n\n")

        improved = sum(
            1 for q in questions
            if isinstance(cache[q].get("base_cor"), (int, float))
            and isinstance(cache[q].get("ft_cor"), (int, float))
            and cache[q]["ft_cor"] > cache[q]["base_cor"]
        )
        regressed = sum(
            1 for q in questions
            if isinstance(cache[q].get("base_cor"), (int, float))
            and isinstance(cache[q].get("ft_cor"), (int, float))
            and cache[q]["ft_cor"] < cache[q]["base_cor"]
        )
        n_pairs = min(len(agg["base_cor"]), len(agg["ft_cor"]))
        f.write("## Summary — mean scores (over scored questions so far)\n\n")
        f.write("| metric | base | fine-tuned | scored n |\n|---|---|---|---|\n")
        f.write(f"| relevance | {mean(agg['base_rel']):.2f} | {mean(agg['ft_rel']):.2f} | "
                f"{min(len(agg['base_rel']), len(agg['ft_rel']))} |\n")
        f.write(f"| correctness | {mean(agg['base_cor']):.2f} | {mean(agg['ft_cor']):.2f} | "
                f"{n_pairs} |\n\n")
        f.write(f"Correctness: fine-tuning improved {improved}, regressed {regressed}, "
                f"of {n_pairs} scored pairs.\n\n")
        f.write(f"Unscored cells (judge n/a): {na}/{len(questions)*4}. "
                f"Re-run the same command to fill them.\n")
    tmp.replace(out_path)
    return na


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", default="adapters_v5")
    ap.add_argument("--judge-model", default="gemma2:2b")
    ap.add_argument("--max-tokens", type=int, default=150)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--max-new", type=int, default=0,
                    help="score at most N questions then exit (batch mode; 0 = all). "
                         "Used by the watchdog wrapper to restart Ollama before gemma2:2b "
                         "wedges under sustained load.")
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

        import mlx.core as mx
        gc.collect()  # gc imported at module level
        try:
            mx.clear_cache()
        except Exception:
            pass

    # ---- scoring (only where missing/n-a) ----
    SCORE_KEYS = ("base_rel", "base_cor", "ft_rel", "ft_cor")

    def cell_open(c, k):
        # Score a cell only if it has no value AND has never been attempted.
        # Once a cell fails (reason recorded), it's terminal n/a — never retried.
        # This is what lets the cursor advance PAST a poison question instead of
        # re-hitting it every batch and re-wedging the judge.
        return c.get(k) is None and not c.get(k + "_r")

    def needs_attempt(c):
        return any(cell_open(c, k) for k in SCORE_KEYS)

    todo = [q for q in questions if needs_attempt(cache[q])]
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

        def make_relevancy():
            return AnswerRelevancyMetric(model=judge, async_mode=False, verbose_mode=False)

        def make_correctness():
            return GEval(
                name="Correctness",
                criteria=(
                    "Compare the actual output to the expected output. Score high only if the "
                    "actual output is factually correct and agrees with the expected answer on "
                    "all key facts (names, dates, numbers). Penalize wrong/contradictory facts."
                ),
                evaluation_params=[
                    LLMTestCaseParams.INPUT,
                    LLMTestCaseParams.ACTUAL_OUTPUT,
                    LLMTestCaseParams.EXPECTED_OUTPUT,
                ],
                model=judge, async_mode=False, verbose_mode=False,
            )

        # A single judge call can hang on a blocking socket read and freeze the whole
        # run (signal.alarm can't interrupt a C-level read). Two-layer defense:
        #  1) socket-level read timeout so a stuck request aborts and frees the runner;
        #  2) a daemon-thread wrapper that ABANDONS a call exceeding `timeout` and moves
        #     on (recording n/a, retried on a later resume). Fresh metric per call so an
        #     abandoned thread can't corrupt shared metric state.
        import socket
        import threading
        socket.setdefaulttimeout(90)

        def score(make_metric, q, out, timeout=120):
            box = {}

            def work():
                try:
                    m = make_metric()
                    m.measure(LLMTestCase(input=q, actual_output=out,
                                          expected_output=expected[q]))
                    box["s"], box["r"] = float(m.score), (m.reason or "").strip()
                except Exception as e:
                    box["err"] = f"{type(e).__name__}: {e}"

            t = threading.Thread(target=work, daemon=True)
            t.start()
            t.join(timeout)
            if t.is_alive():
                return None, f"scoring failed: abandoned after {timeout}s (judge hung)"
            if "err" in box:
                return None, f"scoring failed: {box['err']}"
            return box.get("s"), box.get("r", "")

        out_path = Path(f"eval_comparison_base_vs_{args.adapter}.md")
        for n, q in enumerate(todo, 1):
            c = cache[q]
            if cell_open(c, "base_rel"):
                c["base_rel"], c["base_rel_r"] = score(make_relevancy, q, c["base_out"])
            if cell_open(c, "base_cor"):
                c["base_cor"], c["base_cor_r"] = score(make_correctness, q, c["base_out"])
            if cell_open(c, "ft_rel"):
                c["ft_rel"], c["ft_rel_r"] = score(make_relevancy, q, c["ft_out"])
            if cell_open(c, "ft_cor"):
                c["ft_cor"], c["ft_cor_r"] = score(make_correctness, q, c["ft_out"])

            # persist BOTH the cache and the md after every eval, so progress is never lost
            save_cache(cache_path, cache, questions)
            write_md(out_path, cache, questions, len(rows), args.adapter, args.judge_model)

            # flush memory each iteration (user runs slow on purpose to stay within RAM)
            gc.collect()

            bc = c.get("base_cor"); fc = c.get("ft_cor")
            print(f"[{n}/{len(todo)}] {q[:45]!r} base_cor="
                  f"{bc if is_num(bc) else 'n/a'} ft_cor={fc if is_num(fc) else 'n/a'}", flush=True)

            if args.max_new and n >= args.max_new:
                print(f"batch limit ({args.max_new}) reached — exiting for Ollama restart",
                      flush=True)
                break

    # final render (covers the case where nothing needed scoring)
    out_path = Path(f"eval_comparison_base_vs_{args.adapter}.md")
    na = write_md(out_path, cache, questions, len(rows), args.adapter, args.judge_model)
    gc.collect()
    print(f"\nSaved: {out_path}")
    print(f"n/a cells: {na}/{len(questions)*4}")


if __name__ == "__main__":
    main()
