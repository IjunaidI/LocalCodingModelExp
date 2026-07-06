"""
30-rule spec-dialect ladder. Same 27-rule problem and the same 23 targets at every rung;
only the spec's dialect changes, from prescriptive pseudocode (L1, = spec_30.md) down to the
raw business requirement (L5). Finds the rung where Qwen2.5-Coder-3B stops producing correct
code — the 30-rule analogue of experiments/sweet-spot/.

Per rung we take 1 greedy attempt + (samples-1) sampled attempts (single greedy is a
knife-edge), score total_receivables AND escrow, and report the greedy result, the best-of-N,
and the pass-rate.

Run on Apple Silicon (from repo root):
    .venv/bin/python experiments/30-rule/run_ladder_30.py                 # samples=5
    .venv/bin/python experiments/30-rule/run_ladder_30.py --samples 8 --temp 0.4
    .venv/bin/python experiments/30-rule/run_ladder_30.py --levels 1,3,5
    .venv/bin/python experiments/30-rule/run_ladder_30.py --model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit
"""

import os
import re
import csv
import json
import argparse
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
os.environ["HF_HOME"] = str(PROJECT_DIR / "model_cache")
os.environ["HF_HUB_CACHE"] = str(PROJECT_DIR / "model_cache")

# Reuse the exact scoring + code-extraction the single-spec harness uses.
from solve_30 import score, extract_code  # noqa: E402

MODEL = "mlx-community/Qwen2.5-Coder-3B-Instruct-4bit"
TARGET_COL = "Total_receivables"
ESCROW_COL = "Escrow"
MAX_TOKENS = 4000
LADDER_DIR = PROJECT_DIR / "ladder"
SPECS_DIR = LADDER_DIR / "specs"

# Constant instruction wrapper (identical to solve_30.py) — never part of what varies.
INSTRUCTION = (
    "Implement the Python function described in the specification below. Read the CSV with "
    "the standard `csv` module; a header name may contain an internal space (for example "
    "`payment type`) — match it exactly and strip only leading/trailing whitespace. Return "
    "a list with one dict per input row. Respond with ONLY the code, in a single "
    "```python block.\n\n"
)

BOOL_COLS = ["tax verified", "is high risk", "requires correction",
             "referral active", "senior citizen", "first order"]

LEVELS = [
    {"level": 1, "title": "Prescriptive pseudocode (= spec_30.md)", "spec": "level_1.md",
     "dataset": "test-cases-30.csv", "expect": "pass (anchor)"},
    {"level": 2, "title": "Declarative prose, tables kept", "spec": "level_2.md",
     "dataset": "test-cases-30.csv", "expect": "pass?"},
    {"level": 3, "title": "Business prose, tables removed", "spec": "level_3.md",
     "dataset": "test-cases-30.csv", "expect": "likely break"},
    {"level": 4, "title": "Natural rules (% and prose tiers)", "spec": "level_4.md",
     "dataset": "test-cases-30.csv", "expect": "break"},
    {"level": 5, "title": "Raw requirement (True/False)", "spec": "level_5.md",
     "dataset": "test-cases-30-tf.csv", "expect": "fail (anchor)"},
]


def generate_tf_dataset():
    """Write test-cases-30-tf.csv: same rows/targets as test-cases-30.csv, booleans rendered
    True/False (empty stays empty) — for the raw-requirement rung L5."""
    src = PROJECT_DIR / "test-cases-30.csv"
    dst = PROJECT_DIR / "test-cases-30-tf.csv"
    with src.open(newline="") as f:
        reader = csv.DictReader(f)
        cols = [c.strip() for c in reader.fieldnames]
        rows = [{k.strip(): (v.strip() if v else "") for k, v in r.items()} for r in reader]
    m = {"yes": "True", "no": "False", "": ""}
    for r in rows:
        for c in BOOL_COLS:
            if c in r:
                r[c] = m.get(r[c].lower(), r[c])
    with dst.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    return dst


def load_rows(dataset_path):
    with dataset_path.open(newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = [fn.strip() for fn in reader.fieldnames]
        rows, targets, escrows = [], [], []
        for raw in reader:
            clean = {k.strip(): (v.strip() if v else "") for k, v in raw.items()}
            targets.append(float(clean[TARGET_COL]))
            escrows.append(float(clean[ESCROW_COL]))
            rows.append({k: v for k, v in clean.items()
                         if k not in (TARGET_COL, ESCROW_COL)})
    input_cols = [c for c in fieldnames if c not in (TARGET_COL, ESCROW_COL)]
    return input_cols, rows, targets, escrows


def write_inputs_csv(input_cols, rows, path):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=input_cols)
        w.writeheader()
        w.writerows(rows)


def load_spec(path):
    text = path.read_text()
    return re.sub(r"<!--.*?-->\n?", "", text, flags=re.DOTALL).strip()


def classify(passed, total, err):
    if err is None:
        return "correct" if passed == total else f"ran, wrong numbers ({passed}/{total})"
    e = err.lower()
    if "keyerror" in e:
        return "crash: KeyError (table lookup)"
    if "not defined" in e or "nameerror" in e:
        return "crash: undefined name"
    if "attributeerror" in e:
        return "crash: attribute error (bool/type)"
    if "did not load" in e or "syntax" in e:
        return "crash: syntax/load"
    if "expected list" in e:
        return "wrong return shape"
    return "crash: other"


def build_repair_prompt(spec_text, prev_code, passed, total, lines, err):
    """Same feedback contract as solve_30.build_repair_prompt (traceback for a crash,
    per-row diffs for numeric errors), but appends THIS rung's spec."""
    problem = (f"Your previous code raised an error before it could be scored:\n  {err}\n"
               "Find the exact line that caused it and fix it (check dict-key types and "
               "casing, and that every variable is defined before use)."
               if err else
               f"Your previous code passed {passed}/{total} rows. These are wrong:\n"
               + "\n".join(lines))
    return ("Your previous attempt:\n```python\n" + prev_code + "\n```\n\n" + problem
            + "\n\nFix the code so EVERY row matches on both total_receivables and escrow. "
            "Respond with ONLY the full corrected function in a single ```python block.\n\n"
            + spec_text)


def run_repair_rung(ask_fn, spec_text, content, inputs_csv, targets, escrows, total,
                    greedy, repair_sampler, max_iters, trajectories):
    """Iteration 1 greedy; then up to max_iters repair iterations feeding the localized
    error/diff back, over `trajectories` independent stochastic repair runs."""
    code1 = extract_code(ask_fn(content, greedy))
    p1, l1, e1 = score(code1, inputs_csv, targets, escrows)
    print(f"  it1 greedy: {p1}/{total}"
          + (f"  [{classify(p1, total, e1)}]" if p1 < total else "  PASS"))
    overall = (p1, code1)
    if p1 == total:
        return {"greedy": p1, "best": p1, "code": code1, "converged": trajectories,
                "min_iters": 1, "trajectories": trajectories, "max_iters": max_iters,
                "paths": [[p1]] * trajectories}
    conv_iters, paths = [], []
    for t in range(trajectories):
        cur = build_repair_prompt(spec_text, code1, p1, total, l1, e1)
        best_s, best_c, conv, path = p1, code1, None, [p1]
        for it in range(2, max_iters + 1):
            code = extract_code(ask_fn(cur, repair_sampler))
            passed, lines, err = score(code, inputs_csv, targets, escrows)
            path.append(passed)
            print(f"    traj {t + 1} it{it}: {passed}/{total}"
                  + (f"  [{classify(passed, total, err)}]" if passed < total else "  PASS"))
            if passed > best_s:
                best_s, best_c = passed, code
            if passed == total:
                conv = it
                break
            cur = build_repair_prompt(spec_text, code, passed, total, lines, err)
        paths.append(path)
        if conv:
            conv_iters.append(conv)
        if best_s > overall[0]:
            overall = (best_s, best_c)
    return {"greedy": p1, "best": overall[0], "code": overall[1],
            "converged": len(conv_iters), "min_iters": (min(conv_iters) if conv_iters else None),
            "trajectories": trajectories, "max_iters": max_iters, "paths": paths}


def main():
    ap = argparse.ArgumentParser(description="Run the 30-rule spec-dialect ladder.")
    ap.add_argument("--samples", type=int, default=5,
                    help="attempts per rung; attempt 1 is greedy, the rest sampled.")
    ap.add_argument("--temp", type=float, default=0.4, help="temperature for sampled attempts.")
    ap.add_argument("--repair", action="store_true",
                    help="generate -> score -> repair loop per rung (iter 1 greedy, then "
                         "localized-feedback repairs) instead of the sampled-attempts read.")
    ap.add_argument("--trajectories", type=int, default=2, help="independent repair runs per rung.")
    ap.add_argument("--max-iters", dest="max_iters", type=int, default=5,
                    help="max iterations per repair trajectory (incl. the greedy iter 1).")
    ap.add_argument("--repair-temp", dest="repair_temp", type=float, default=0.6,
                    help="temperature for repair iterations.")
    ap.add_argument("--levels", type=str, default="", help="subset, e.g. 1,3,5.")
    ap.add_argument("--model", type=str, default=MODEL)
    args = ap.parse_args()

    generate_tf_dataset()
    wanted = {int(x) for x in args.levels.split(",") if x.strip()} if args.levels else None
    todo = [c for c in LEVELS if wanted is None or c["level"] in wanted]

    from mlx_lm import load, generate
    from mlx_lm.sample_utils import make_sampler
    greedy = make_sampler(temp=0.0)
    sampled = make_sampler(temp=args.temp, top_p=0.9)
    repair_sampler = make_sampler(temp=args.repair_temp, top_p=0.9)

    def ask(model, tok, content, sampler):
        prompt = tok.apply_chat_template([{"role": "user", "content": content}],
                                         add_generation_prompt=True)
        return generate(model, tok, prompt=prompt, max_tokens=MAX_TOKENS,
                        sampler=sampler, verbose=False)

    print(f"Loading {args.model} ...\n")
    model, tok = load(args.model)
    ask_fn = lambda content, sampler: ask(model, tok, content, sampler)  # noqa: E731

    if args.repair:
        print(f"Mode: repair loop — up to {args.max_iters} iters, "
              f"{args.trajectories} trajectories/rung, repair temp {args.repair_temp}.\n")

    results = []
    for cfg in todo:
        spec_text = load_spec(SPECS_DIR / cfg["spec"])
        input_cols, rows, targets, escrows = load_rows(PROJECT_DIR / cfg["dataset"])
        total = len(targets)
        inputs_csv = LADDER_DIR / f"_inputs_only_level_{cfg['level']}.csv"
        write_inputs_csv(input_cols, rows, inputs_csv)
        content = INSTRUCTION + spec_text

        print("=" * 64)
        print(f"LEVEL {cfg['level']} — {cfg['title']}  (expect: {cfg['expect']})")
        print("=" * 64)

        if args.repair:
            rr = run_repair_rung(ask_fn, spec_text, content, inputs_csv, targets, escrows,
                                 total, greedy, repair_sampler, args.max_iters,
                                 args.trajectories)
            (LADDER_DIR / f"level_{cfg['level']}_solution_repair.py").write_text(
                rr.get("code", "") + "\n")
            r = {"level": cfg["level"], "title": cfg["title"], "expect": cfg["expect"],
                 "dataset": cfg["dataset"], "total": total, **rr}
            r.pop("code", None)
            results.append(r)
            note = " (greedy first try)" if r["min_iters"] == 1 and r["converged"] else ""
            fastest = f", fastest iter {r['min_iters']}" if r["min_iters"] else ""
            print(f"  -> converged {r['converged']}/{r['trajectories']}{note}{fastest}, "
                  f"best {r['best']}/{total}")
            print(f"     paths {r['paths']}\n")
            continue

        attempts = []
        for a in range(args.samples):
            sampler = greedy if a == 0 else sampled
            code = extract_code(ask(model, tok, content, sampler))
            passed, _lines, err = score(code, inputs_csv, targets, escrows)
            attempts.append((passed, code, err))
            tag = "greedy" if a == 0 else f"s{a}"
            print(f"  attempt {tag}: {passed}/{total}"
                  + (f"  [{classify(passed, total, err)}]" if passed < total else "  PASS"))

        best = max(attempts, key=lambda x: x[0])
        (LADDER_DIR / f"level_{cfg['level']}_solution.py").write_text(best[1] + "\n")
        tally = {}
        for p, _c, e in attempts:
            k = classify(p, total, e)
            tally[k] = tally.get(k, 0) + 1
        r = {"level": cfg["level"], "title": cfg["title"], "expect": cfg["expect"],
             "dataset": cfg["dataset"], "total": total, "samples": args.samples,
             "greedy": attempts[0][0], "best": best[0],
             "perfect": sum(1 for p, _c, _e in attempts if p == total),
             "scores": [p for p, _c, _e in attempts],
             "reasons": sorted(tally.items(), key=lambda kv: -kv[1])}
        results.append(r)
        top = "; ".join(f"{k}×{n}" for k, n in r["reasons"][:3])
        print(f"  -> greedy {r['greedy']}/{total}, best-of-{args.samples} {r['best']}/{total}, "
              f"pass-rate {r['perfect']}/{args.samples}")
        print(f"     outcomes: {top}\n")

    # --- report -----------------------------------------------------------------------
    if args.repair:
        out_md, out_json = "results_ladder_repair.md", "results_ladder_repair.json"
        lines = ["# 30-rule ladder — repair-loop results", "",
                 f"Iteration 1 greedy, then up to {args.max_iters} repair iterations "
                 f"(temp {args.repair_temp}) with localized feedback, over {args.trajectories} "
                 "trajectories per rung; scored on total_receivables AND escrow.", "",
                 "| Level | Spec dialect | Greedy | Converged | Fastest | Best |",
                 "|:-----:|--------------|:------:|:---------:|:-------:|:----:|"]
        for r in results:
            conv = f"{r['converged']}/{r['trajectories']}"
            fastest = f"iter {r['min_iters']}" if r["min_iters"] else "—"
            lines.append(f"| L{r['level']} | {r['title']} | {r['greedy']}/{r['total']} | "
                         f"{conv} | {fastest} | {r['best']}/{r['total']} |")
        lines += ["", "Per-trajectory score paths (rows passed after each iteration):", ""]
        for r in results:
            lines.append(f"- **L{r['level']} {r['title']}** — {r['paths']}")
    else:
        out_md, out_json = "results_ladder.md", "results_ladder.json"
        lines = ["# 30-rule ladder — results", "",
                 f"{args.samples} attempts per rung (attempt 1 greedy, rest at temp {args.temp}); "
                 "scored on total_receivables AND escrow across all rows.", "",
                 "| Level | Spec dialect | Greedy | Best-of-N | Pass-rate | Most common outcome |",
                 "|:-----:|--------------|:------:|:---------:|:---------:|---------------------|"]
        for r in results:
            top = "; ".join(f"{k}×{n}" for k, n in r["reasons"][:2])
            lines.append(f"| L{r['level']} | {r['title']} | {r['greedy']}/{r['total']} | "
                         f"{r['best']}/{r['total']} | {r['perfect']}/{r['samples']} | {top} |")
        lines += ["", "Per-rung score distributions (each number is one attempt; attempt 1 greedy):", ""]
        for r in results:
            lines.append(f"- **L{r['level']} {r['title']}** — `{r['scores']}`; "
                         + ", ".join(f"{k} ×{n}" for k, n in r["reasons"]))
    (LADDER_DIR / out_md).write_text("\n".join(lines) + "\n")
    (LADDER_DIR / out_json).write_text(json.dumps(results, indent=2))

    print("=" * 64)
    print("LADDER SUMMARY")
    print("=" * 64)
    for r in results:
        mark = "PASS" if r["best"] == r["total"] else "FAIL"
        print(f"  L{r['level']}  {r['title']:<40} greedy {r['greedy']}/{r['total']}"
              f"  best {r['best']}/{r['total']}  ({mark})")

    def reachable(r):
        return r["best"] == r["total"]
    first_fail = next((r for r in results if not reachable(r)), None)
    print("-" * 64)
    if first_fail is None:
        print("  No failure across tested rungs — extend the ladder harder.")
    elif first_fail is results[0]:
        print(f"  Breaks immediately at L{first_fail['level']}.")
    else:
        prev = results[results.index(first_fail) - 1]
        print(f"  SWEET SPOT: holds through L{prev['level']} ({prev['title']}), "
              f"breaks at L{first_fail['level']} ({first_fail['title']}).")
    print(f"\nResults written to {LADDER_DIR.relative_to(PROJECT_DIR)}/results_ladder.md")


if __name__ == "__main__":
    main()
