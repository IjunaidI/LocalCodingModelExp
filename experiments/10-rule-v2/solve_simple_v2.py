"""
Iterative generate -> score -> repair loop against the v2 (small-model dialect)
10-rule spec. Same loop as the original experiment; iteration 1 is greedy for a
clean baseline and repairs use temperature so attempts diverge.

Run on Apple Silicon:  python3 solve_simple_v2.py
Switch model size with --model (e.g. the 7B id below); the solution file is
suffixed per size so runs never clobber each other.
"""

import os
import re
import csv
import argparse
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
os.environ["HF_HOME"] = str(PROJECT_DIR / "model_cache")
os.environ["HF_HUB_CACHE"] = str(PROJECT_DIR / "model_cache")

from mlx_lm import load, generate  # noqa: E402
from mlx_lm.sample_utils import make_sampler  # noqa: E402

MODEL = "mlx-community/Qwen2.5-Coder-3B-Instruct-4bit"
# MODEL = "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit"

TEST_CSV = PROJECT_DIR / "test-cases-v2.csv"
TARGET_COL = "Total_receivables"
TOLERANCE = 0.5
MAX_ITERS = 6
MAX_TOKENS = 2000
REPAIR_SAMPLER = make_sampler(temp=0.6, top_p=0.9)
GREEDY_SAMPLER = make_sampler(temp=0.0)

SPEC = (PROJECT_DIR / "spec_simple_v2.md").read_text()

INITIAL_INSTRUCTION = (
    "Implement the function described below. Strip spaces from CSV headers, treat "
    "empty cells as defaults, convert numeric strings to numbers, and never crash. "
    "Follow the rules exactly and in order. Respond with ONLY code in a single "
    "```python block.\n\n" + SPEC
)


def load_test_rows():
    with TEST_CSV.open(newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = [fn.strip() for fn in reader.fieldnames]
        rows, targets = [], []
        for raw in reader:
            clean = {k.strip(): (v.strip() if v else "") for k, v in raw.items()}
            targets.append(float(clean[TARGET_COL]))
            rows.append({k: v for k, v in clean.items() if k != TARGET_COL})
    return [c for c in fieldnames if c != TARGET_COL], rows, targets


def write_inputs_csv(input_cols, rows, path):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=input_cols)
        w.writeheader()
        w.writerows(rows)


def extract_code(text):
    m = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    return (m.group(1) if m else text).strip()


def score(code, inputs_csv, targets):
    ns = {}
    try:
        exec(code, ns)  # noqa: S102
        fn = ns["process_calculations"]
    except Exception as e:
        return 0, [], f"code did not load: {e}"
    try:
        result = fn(str(inputs_csv))
    except Exception as e:
        return 0, [], f"process_calculations raised: {e}"
    if not isinstance(result, list) or len(result) != len(targets):
        return 0, [], (f"expected list of {len(targets)} dicts, got "
                       f"{type(result).__name__}")
    passed, lines = 0, []
    for i, (pred_row, target) in enumerate(zip(result, targets)):
        try:
            pred = float(pred_row["total_receivables"])
        except Exception as e:
            lines.append(f"  row {i}: bad/missing total_receivables ({e}); target={target:.4f}")
            continue
        if abs(pred - target) <= TOLERANCE:
            passed += 1
        else:
            lines.append(f"  row {i}: got {pred:.4f}, expected {target:.4f}")
    return passed, lines, None


def build_repair_prompt(prev_code, passed, total, lines, err):
    problem = (f"Your previous code did not run: {err}" if err else
               f"Your previous code passed {passed}/{total} rows. These are wrong:\n"
               + "\n".join(lines))
    return ("Your previous attempt:\n```python\n" + prev_code + "\n```\n\n" + problem
            + "\n\nFix the code so EVERY row matches. Respond with ONLY the full "
            "corrected function in a single ```python block.\n\n" + SPEC)


def ask(model, tokenizer, content, sampler):
    messages = [{"role": "user", "content": content}]
    prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True)
    return generate(model, tokenizer, prompt=prompt, max_tokens=MAX_TOKENS,
                    sampler=sampler, verbose=False)


def main():
    ap = argparse.ArgumentParser(description="Generate + repair against the v2 spec.")
    ap.add_argument("--model", default=MODEL,
                    help="any Qwen2.5-Coder Instruct 4-bit id (default: the 3B)")
    args = ap.parse_args()
    m = re.search(r"(\d+(?:[._]\d+)?)B", args.model, re.IGNORECASE)
    suffix = "" if args.model == MODEL else "_" + ((m.group(1).lower() + "b") if m else "alt")
    out_name = f"solution_best_v2{suffix}.py"

    input_cols, rows, targets = load_test_rows()
    inputs_csv = PROJECT_DIR / "inputs_only_v2.csv"
    write_inputs_csv(input_cols, rows, inputs_csv)
    print(f"Loaded {len(rows)} test cases. Target: {TARGET_COL}\n")
    print(f"Loading {args.model} ...\n")
    model, tokenizer = load(args.model)

    best = (-1, "")
    content = INITIAL_INSTRUCTION
    for it in range(1, MAX_ITERS + 1):
        print("=" * 60)
        print(f"ITERATION {it}/{MAX_ITERS}")
        print("=" * 60)
        sampler = GREEDY_SAMPLER if it == 1 else REPAIR_SAMPLER
        code = extract_code(ask(model, tokenizer, content, sampler))
        passed, lines, err = score(code, inputs_csv, targets)
        if err:
            print(f"  ERROR: {err}")
        else:
            print(f"  PASSED {passed}/{len(targets)}")
            for ln in lines[:6]:
                print(ln)
            if len(lines) > 6:
                print(f"  ... and {len(lines) - 6} more")
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
