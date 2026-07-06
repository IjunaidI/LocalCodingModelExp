"""
Iterative generate -> score -> repair loop against the 30-rule spec (spec_30.md).

Same loop as the 10-rule-v2 deliverable, scaled up: iteration 1 is greedy for a clean
baseline; repairs use temperature so attempts diverge. A row passes only if BOTH
`total_receivables` and `escrow` match within tolerance.

Run on Apple Silicon (from repo root):
    .venv/bin/python experiments/30-rule/solve_30.py
    .venv/bin/python experiments/30-rule/solve_30.py --model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit

Offline plumbing check (no model loaded), scores an existing solution file:
    .venv/bin/python experiments/30-rule/solve_30.py --score-only model_solution_30.py
"""

import os
import re
import csv
import argparse
import traceback
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
os.environ["HF_HOME"] = str(PROJECT_DIR / "model_cache")
os.environ["HF_HUB_CACHE"] = str(PROJECT_DIR / "model_cache")

MODEL = "mlx-community/Qwen2.5-Coder-3B-Instruct-4bit"

TEST_CSV = PROJECT_DIR / "test-cases-30.csv"
TARGET_COL = "Total_receivables"
ESCROW_COL = "Escrow"
TOLERANCE = 0.5
MAX_ITERS = 6
MAX_TOKENS = 4000

SPEC = (PROJECT_DIR / "spec_30.md").read_text()

# Constant, precise instruction wrapper (same wording as sweet-spot/run_ladder.py): no
# ambiguous "strip spaces" / "never crash" that would induce error-swallowing try/except.
INSTRUCTION = (
    "Implement the Python function described in the specification below. Read the CSV with "
    "the standard `csv` module; a header name may contain an internal space (for example "
    "`payment type`) — match it exactly and strip only leading/trailing whitespace. Return "
    "a list with one dict per input row. Respond with ONLY the code, in a single "
    "```python block.\n\n" + SPEC
)


def load_test_rows():
    with TEST_CSV.open(newline="") as f:
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


def extract_code(text):
    m = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    return (m.group(1) if m else text).strip()


def _crash_detail(code):
    """The failing line + exception, so a crash can be localized in the repair prompt
    (a bare `KeyError: 'Q2'` tells the model nothing about WHERE it blew up)."""
    tb = traceback.format_exc().strip().splitlines()
    # Keep the exception line and the innermost `process_calculations` frame.
    exc = tb[-1]
    frame = next((tb[i + 1].strip() for i in range(len(tb) - 1)
                  if "process_calculations" in tb[i] or ", line" in tb[i]), "")
    return f"{exc}" + (f"  (at: `{frame}`)" if frame else "")


def score(code, inputs_csv, targets, escrows):
    ns = {}
    try:
        exec(code, ns)  # noqa: S102
        fn = ns["process_calculations"]
    except Exception:
        return 0, [], f"code did not load: {_crash_detail(code)}"
    try:
        result = fn(str(inputs_csv))
    except Exception:
        return 0, [], f"process_calculations crashed: {_crash_detail(code)}"
    if not isinstance(result, list) or len(result) != len(targets):
        return 0, [], (f"expected list of {len(targets)} dicts, got "
                       f"{type(result).__name__}")
    passed, lines = 0, []
    for i, (pred_row, tr, esc) in enumerate(zip(result, targets, escrows)):
        try:
            got_tr = float(pred_row["total_receivables"])
            got_esc = float(pred_row["escrow"])
        except Exception as e:
            lines.append(f"  row {i}: bad/missing total_receivables or escrow ({e})")
            continue
        ok_tr = abs(got_tr - tr) <= TOLERANCE
        ok_esc = abs(got_esc - esc) <= TOLERANCE
        if ok_tr and ok_esc:
            passed += 1
        else:
            parts = []
            if not ok_tr:
                parts.append(f"total_receivables got {got_tr:.4f}, expected {tr:.4f}")
            if not ok_esc:
                parts.append(f"escrow got {got_esc:.4f}, expected {esc:.4f}")
            lines.append(f"  row {i}: " + "; ".join(parts))
    return passed, lines, None


def build_repair_prompt(prev_code, passed, total, lines, err):
    problem = (f"Your previous code raised an error before it could be scored:\n  {err}\n"
               "Find the exact line that caused it and fix it (check dict-key types and "
               "casing, and that every variable is defined before use)."
               if err else
               f"Your previous code passed {passed}/{total} rows. These are wrong:\n"
               + "\n".join(lines))
    return ("Your previous attempt:\n```python\n" + prev_code + "\n```\n\n" + problem
            + "\n\nFix the code so EVERY row matches on both total_receivables and escrow. "
            "Respond with ONLY the full corrected function in a single ```python block.\n\n"
            + SPEC)


def ask(model, tokenizer, content, sampler):
    messages = [{"role": "user", "content": content}]
    prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True)
    from mlx_lm import generate
    return generate(model, tokenizer, prompt=prompt, max_tokens=MAX_TOKENS,
                    sampler=sampler, verbose=False)


def run_score_only(path):
    input_cols, rows, targets, escrows = load_test_rows()
    inputs_csv = PROJECT_DIR / "inputs_only_30.csv"
    write_inputs_csv(input_cols, rows, inputs_csv)
    code = (PROJECT_DIR / path).read_text()
    passed, lines, err = score(code, inputs_csv, targets, escrows)
    print(f"Score-only: {path}")
    if err:
        print(f"  ERROR: {err}")
    else:
        print(f"  {passed}/{len(targets)}")
        for ln in lines:
            print(ln)
    return passed == len(targets) and not err


def main():
    ap = argparse.ArgumentParser(description="Generate + repair against the 30-rule spec.")
    ap.add_argument("--model", default=MODEL,
                    help="any Qwen2.5-Coder Instruct 4-bit id (default: the 3B)")
    ap.add_argument("--score-only", dest="score_only", default="",
                    help="score an existing solution file offline (no model loaded), then exit")
    args = ap.parse_args()

    if args.score_only:
        ok = run_score_only(args.score_only)
        raise SystemExit(0 if ok else 1)

    from mlx_lm import load
    from mlx_lm.sample_utils import make_sampler
    greedy = make_sampler(temp=0.0)
    repair = make_sampler(temp=0.6, top_p=0.9)

    m = re.search(r"(\d+(?:[._]\d+)?)B", args.model, re.IGNORECASE)
    suffix = "" if args.model == MODEL else "_" + ((m.group(1).lower() + "b") if m else "alt")
    out_name = f"solution_best_30{suffix}.py"

    input_cols, rows, targets, escrows = load_test_rows()
    inputs_csv = PROJECT_DIR / "inputs_only_30.csv"
    write_inputs_csv(input_cols, rows, inputs_csv)
    print(f"Loaded {len(rows)} test cases. Targets: {TARGET_COL} + {ESCROW_COL}\n")
    print(f"Loading {args.model} ...\n")
    model, tokenizer = load(args.model)

    best = (-1, "")
    content = INSTRUCTION
    for it in range(1, MAX_ITERS + 1):
        print("=" * 60)
        print(f"ITERATION {it}/{MAX_ITERS}")
        print("=" * 60)
        sampler = greedy if it == 1 else repair
        code = extract_code(ask(model, tokenizer, content, sampler))
        passed, lines, err = score(code, inputs_csv, targets, escrows)
        if err:
            print(f"  ERROR: {err}")
        else:
            print(f"  PASSED {passed}/{len(targets)}")
            for ln in lines[:8]:
                print(ln)
            if len(lines) > 8:
                print(f"  ... and {len(lines) - 8} more")
        if passed > best[0]:
            best = (passed, code)
        if passed == len(targets):
            print("\nALL TEST CASES PASSED")
            break
        content = build_repair_prompt(code, passed, len(targets), lines, err)
    else:
        print(f"\nStopped after {MAX_ITERS} iterations.")

    (PROJECT_DIR / out_name).write_text(best[1] + "\n")
    print("\n" + "-" * 60)
    print(f"Best: {best[0]}/{len(targets)} passed. Written to {out_name}")
    print("ALL TESTS PASSED" if best[0] == len(targets) else "Did not fully converge")


if __name__ == "__main__":
    main()
