# Can a tiny AI on an 8GB MacBook write real business logic? I ran the full experiment...

*A long-form, reproducible write-up of a local-LLM experiment. No API, no cloud, no per-token bill. Everything below runs on a single laptop, and everything below is included so you can run it yourself.*

---

## The question

Can a small language model, running **entirely on my own laptop**, write real business logic from a specification?

Not "write me a function to sort a list." I mean the gnarly, rule-laden code that actually shows up in finance and operations: a pricing-and-commission engine with interdependent rules, percentage stacking, conditional tiers, and tax withholding — the kind of thing where one wrong branch silently produces a number that is *almost* right.

My constraints were deliberately humble:

- **Hardware:** an M1 MacBook with **8 GB of unified RAM**. On 8 GB, a 7-billion-parameter 4-bit model (~4.3 GB resident) is the practical ceiling — anything larger thrashes swap or won't load.
- **Framework:** Apple's **MLX** (`mlx_lm`), which runs these models natively on Apple Silicon.
- **Models:** the open-source **Qwen2.5-Coder** family — 0.5B, 3B, and 7B.
- **Cost:** $0. Nothing leaves the machine; the weights are cached inside the project folder.

This article documents the entire experiment end to end: the warm-up, the real task, three escalating attempts, the plot twist where the *specification itself turned out to be wrong*, and a controlled follow-up that found the exact complexity boundary where a small local model flips from "useless" to "perfect." All of the code, the datasets, and the tests are reproduced in full so the whole thing is runnable.

**
NOTE: If you want to read the main insights, just scroll to the section "The real insight: it's not the number of rules"**

---

## Part 0 — The warm-up: can the 0.5B model even write code?

Before the hard task, a sanity check. Can the smallest model — Qwen2.5-Coder-**0.5B** — write a one-function task and have it actually pass tests? This establishes the floor: what a sub-1B model can reliably do.

The program loads the model locally via MLX, prompts it for a `sort_array` function, extracts the code from the reply, then **runs that code against five test cases** to prove it works.

**`generate_sort.py`**

```python
"""
Use Qwen2.5-Coder-0.5B (via MLX) to write a Python function that sorts an array.

Everything is kept inside this folder: the model is downloaded into ./model_cache
so nothing touches the global ~/.cache/huggingface.

Run:  python3 generate_sort.py
"""

import os
import re
from pathlib import Path

# --- Keep the model inside this project folder -----------------------------
PROJECT_DIR = Path(__file__).resolve().parent
os.environ["HF_HOME"] = str(PROJECT_DIR / "model_cache")
os.environ["HF_HUB_CACHE"] = str(PROJECT_DIR / "model_cache")

# Import AFTER setting the env vars so the cache location takes effect.
from mlx_lm import load, generate  # noqa: E402

# bf16 (not 4-bit): on a 0.5B model, quantization noise hurts code quality and
# the full-precision weights are only ~1 GB, so there is no reason to quantize.
MODEL = "mlx-community/Qwen2.5-Coder-0.5B-Instruct-bf16"

PROMPT = (
    "Write a Python function named `sort_array` that takes a list of numbers "
    "and returns a new list sorted in ascending order. "
    "Respond with only the code inside a single ```python code block."
)


def extract_code(text: str) -> str:
    """Pull the first python code block out of the model output."""
    match = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    return (match.group(1) if match else text).strip()


def main() -> None:
    print(f"Loading {MODEL} ...")
    print(f"(cached in {os.environ['HF_HUB_CACHE']})\n")
    model, tokenizer = load(MODEL)

    messages = [{"role": "user", "content": PROMPT}]
    prompt = tokenizer.apply_chat_template(
        messages, add_generation_prompt=True
    )

    print("Generating...\n" + "-" * 60)
    output = generate(
        model,
        tokenizer,
        prompt=prompt,
        max_tokens=400,
        verbose=True,
    )
    print("-" * 60)

    code = extract_code(output)
    code_path = PROJECT_DIR / "generated_sort.py"
    code_path.write_text(code + "\n")
    print(f"\nExtracted code written to: {code_path.name}\n")
    print(code)

    # --- Verify the generated code actually works --------------------------
    print("\n" + "=" * 60)
    print("VERIFYING the model's code against test cases")
    print("=" * 60)
    namespace: dict = {}
    try:
        exec(code, namespace)  # noqa: S102 - intentional: running model output
        sort_array = namespace["sort_array"]
    except Exception as e:  # model produced something unrunnable
        print(f"FAILED: generated code did not load: {e}")
        return

    tests = [
        ([3, 1, 2], [1, 2, 3]),
        ([5, -1, 0, 5, 2], [-1, 0, 2, 5, 5]),
        ([], []),
        ([42], [42]),
        ([2.5, 1.1, 3.3], [1.1, 2.5, 3.3]),
    ]
    all_ok = True
    for arr, expected in tests:
        try:
            result = sort_array(list(arr))
            ok = result == expected
        except Exception as e:
            result, ok = f"error: {e}", False
        all_ok &= ok
        print(f"  {'PASS' if ok else 'FAIL'}  sort_array({arr}) -> {result}")

    print("\n" + ("ALL TESTS PASSED ✅" if all_ok else "SOME TESTS FAILED ❌"))


if __name__ == "__main__":
    main()
```

The model produced exactly what you'd hope, and it passed all five cases (positives, negatives, duplicates, empty list, single element, floats) at ~54 tokens/sec with a 1.06 GB peak memory footprint:

**`generated_sort.py`** (the model's output)

```python
def sort_array(arr):
    """
    Sorts a list of numbers in ascending order.

    Parameters:
    arr (list): The list of numbers to be sorted.

    Returns:
    list: A new list of numbers sorted in ascending order.
    """
    return sorted(arr)
```

**Conclusion of the warm-up:** a 0.5B model handles a single, unambiguous, one-function task perfectly. That is genuinely useful — and it is also the entire competence envelope I was about to blow past.

---

## Part 1 — The real task: a 17-rule pricing & commission engine

Now the hard problem. I gave the model a `process_calculations(csv_path)` function to write against a spec with **17 interdependent rules** across ~20 fields: product rates by customer status, four stacked discounts, five loadings, a category multiplier, referral credits, high-risk fees, correction fees, escrow, and tax withholding. The CSV is deliberately messy — header names have stray spaces and some cells are empty — so the model also has to handle real-world input hygiene.

### Attempt 1a — throw the spec at the smallest model (0.5B, single shot)

This program hands the full spec to the 0.5B model and runs a **structural** smoke test on the result (does it run, return a list of dicts, expose the right keys). I had no illusions; the comment block says as much.

It implemented maybe 3 of the 17 rules, all incorrectly, and crashed on a `NameError`.

### Attempt 1b — give it the *examples* instead of the spec (0.5B, single shot)

A reasonable hypothesis: maybe the prose spec is the problem. What if I show the model the 19 input→answer examples and ask it to *infer* the formula? This is the "test-driven" framing.

It did **worse**. The model invented the same phantom `price` column and gave up after a few lines:

**Lesson one:** reverse-engineering a multi-rule formula from examples is *harder* for a small model than transcribing a spec, not easier. A single shot — from spec or from examples — is a dead end at this complexity.

---

## Part 2 — A feedback loop, and the bigger models

A single shot is unfair. Real engineering is iterative. So I built a **generate → score → repair** harness: the model writes the function, the harness runs it against every test row, and on failure it feeds the **specific failing rows back** ("row B: you predicted 765000, the answer is 810000") and asks the model to fix its own code — up to a few iterations, keeping the best-scoring version. I pointed it at the 3B and 7B models, the largest that fit in 8 GB.

### What the bigger models did

- The **3B** got the discount math exactly right but dropped the entire commission stack — every prediction collapsed to roughly the post-discount receivable. It plateaued at **0/19**.
- The **7B** wrote the most complete attempt — every rule present — but died on a header-normalization bug (`KeyError: 'customer name'`) that it never noticed across all five repair passes. Its underlying total formula was wrong anyway. Also **0/19**.

Here is the actual 7B run log. Note that the repair loop never localizes the bug; it regenerates the same failure five times:

**`run_7b.log`**

```text
Loaded 19 test cases. Target: Total_receivables

Loading mlx-community/Qwen2.5-Coder-7B-Instruct-4bit ...
============================================================
ITERATION 1/5  (generating...)
============================================================
  ERROR: process_calculations raised: 'customer name'
============================================================
ITERATION 2/5  (generating...)
============================================================
  ERROR: process_calculations raised: 'customer name'
============================================================
ITERATION 3/5  (generating...)
============================================================
  ERROR: process_calculations raised: 'customer name'
============================================================
ITERATION 4/5  (generating...)
============================================================
  ERROR: process_calculations raised: 'customer name'
============================================================
ITERATION 5/5  (generating...)
============================================================
  ERROR: process_calculations raised: 'customer name'

Stopped after 5 iterations.

------------------------------------------------------------
Best result: 0/19 passed.
Best code written to: solution_best.py
Did not fully converge ❌ (see solution_best.py)
```

**The repair loop barely helped.** Telling a small model "you got 81,000, expected 86,045" does not tell it *which line* is wrong. It just regenerates the same bug, confidently. The feedback signal — a numeric diff on the final total — is too far removed from the cause (a header dict, a tier boundary) for a small model to localize.

---

## Part 3 — The plot twist: the specification was wrong

To score anything I needed ground truth, and I couldn't get it from the prose spec, because the prose spec **contradicted itself**. So I reverse-engineered the exact formula by hand, fitting it against all 19 targets until it reproduced every one to the cent. In doing so I discovered:

- The high-risk fee (Rule P) and the $5 correction fee (Rule Q) — which the prose said to fold into `total_receivables` — are actually **excluded** from it. (Including them overshoots row C, the one row with all three flags on.)
- An **empty** `tax verified` cell does not mean "verified"; it secretly means "not verified," which triggers 3% withholding. Every row in the file has an empty `tax verified`.
- The referral credit (Rule N) lives *inside* the commission, as a multiplier, not as an added line.

That alone was worth the morning: **the most reliable way to nail a contradictory spec was to ignore the prose and fit the data.** But it left an itch — *how simple does the spec have to be before a small local model can actually do it?*

---

## Part 4 — The controlled experiment: how simple does the spec have to be?

This is the genuinely useful part. I kept the same harness and the same hardware, and shrank the spec twice.

### 4a — The 10-rule spec

I cut the 17 rules down to a clean 10-rule pipeline (dropping the contradictory and tracked-only rules) and rebuilt the ground truth from scratch.

**`spec.md` (10 rules)**

```markdown
# Simplified pricing spec — 10 rules

Build `process_calculations(csv_path)`. It reads a CSV (header names may have extra
spaces; cells may be empty) and returns a list of dicts, one per row, each containing
the key `total_receivables`.

## Input columns
- `productid` : 1, 2, or 3
- `status` : individual or corporate (case-insensitive)
- `volume` : integer
- `season` : spring / summer / winter / autumn
- `customer` : strategic / non-strategic
- `region` : EMEA / non-EMEA
- `payment type` : ach/wire or credit-card
- `transaction type` : domestic / international / cross-border
- `product category` : electronics / groceries / luxury
- `tax verified` : True / False (empty counts as False)

## Product rates
PRODUCT_RATES = {
    1: {"individual": 1000, "corporate": 900},
    2: {"individual": 1500, "corporate": 1200},
    3: {"individual": 2000, "corporate": 1700},
}

## The 10 rules (apply in order)
1. Rate: pick the rate from PRODUCT_RATES using productid and status.
2. Base: receivable_before_discount = volume * rate.
3. Spring discount: spring season → 5% (else 0%).
4. Volume discount: volume < 100 → 0%; < 1000 → 5%; ≥ 1000 → 10%.
5. Strategic discount: strategic customer → 5% (else 0%).
6. Apply discounts: total_discount_rate = rule3 + rule4 + rule5;
   receivable_after_discount = receivable_before_discount * (1 - total_discount_rate).
7. Region loading: EMEA → 10% of receivable_after_discount (else 0).
8. Payment loading: credit-card → 2.5% of receivable_after_discount (else 0).
9. Category multiplier: multiply the summed loadings (rule7 + rule8) by
   electronics 1.2, groceries 0.8, luxury 1.5 → this is the commission.
10. Tax withholding & total:
    subtotal = receivable_after_discount + commission;
    if tax verified is False (or empty) → withhold 3% of subtotal, else 0;
    total_receivables = subtotal - withholding.
```

**The ground truth — `reference_simple.py`** (also generates the test dataset and self-checks 12/12):

```python
"""
Ground-truth reference for the simplified 10-rule spec.

Running this module:
  1. computes total_receivables for a fixed set of input rows,
  2. writes test-cases.csv (inputs + the Total_receivables target),
  3. self-checks process_calculations against those targets.
"""

import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent

PRODUCT_RATES = {
    1: {"individual": 1000, "corporate": 900},
    2: {"individual": 1500, "corporate": 1200},
    3: {"individual": 2000, "corporate": 1700},
}

INPUT_COLS = [
    "productid", "status", "volume", "season", "customer",
    "region", "payment type", "transaction type", "product category", "tax verified",
]

# Diverse input rows (the target column is computed, not hand-written).
INPUT_ROWS = [
    {"productid": "1", "status": "individual", "volume": "90",   "season": "winter", "customer": "strategic",     "region": "non-EMEA", "payment type": "credit-card", "transaction type": "international", "product category": "luxury",      "tax verified": "False"},
    {"productid": "1", "status": "individual", "volume": "900",  "season": "winter", "customer": "strategic",     "region": "non-EMEA", "payment type": "ach/wire",    "transaction type": "international", "product category": "groceries",   "tax verified": "True"},
    {"productid": "2", "status": "corporate",  "volume": "140",  "season": "autumn", "customer": "strategic",     "region": "EMEA",     "payment type": "ach/wire",    "transaction type": "international", "product category": "groceries",   "tax verified": "False"},
    {"productid": "1", "status": "individual", "volume": "90",   "season": "spring", "customer": "non-strategic", "region": "EMEA",     "payment type": "ach/wire",    "transaction type": "domestic",     "product category": "electronics", "tax verified": "True"},
    {"productid": "3", "status": "individual", "volume": "320",  "season": "spring", "customer": "non-strategic", "region": "non-EMEA", "payment type": "ach/wire",    "transaction type": "cross-border", "product category": "electronics", "tax verified": "False"},
    {"productid": "3", "status": "corporate",  "volume": "1331", "season": "winter", "customer": "non-strategic", "region": "non-EMEA", "payment type": "credit-card", "transaction type": "cross-border", "product category": "groceries",   "tax verified": "True"},
    {"productid": "1", "status": "individual", "volume": "954",  "season": "winter", "customer": "strategic",     "region": "non-EMEA", "payment type": "credit-card", "transaction type": "domestic",     "product category": "groceries",   "tax verified": "False"},
    {"productid": "3", "status": "individual", "volume": "129",  "season": "summer", "customer": "non-strategic", "region": "non-EMEA", "payment type": "ach/wire",    "transaction type": "domestic",     "product category": "luxury",      "tax verified": "True"},
    {"productid": "2", "status": "corporate",  "volume": "1629", "season": "spring", "customer": "strategic",     "region": "EMEA",     "payment type": "ach/wire",    "transaction type": "international", "product category": "luxury",      "tax verified": "False"},
    {"productid": "1", "status": "corporate",  "volume": "265",  "season": "autumn", "customer": "non-strategic", "region": "non-EMEA", "payment type": "ach/wire",    "transaction type": "cross-border", "product category": "electronics", "tax verified": "True"},
    {"productid": "3", "status": "individual", "volume": "663",  "season": "summer", "customer": "strategic",     "region": "EMEA",     "payment type": "ach/wire",    "transaction type": "cross-border", "product category": "groceries",   "tax verified": "False"},
    {"productid": "1", "status": "individual", "volume": "62",   "season": "winter", "customer": "non-strategic", "region": "non-EMEA", "payment type": "credit-card", "transaction type": "domestic",     "product category": "electronics", "tax verified": "True"},
]


def _num(v, default=0.0):
    try:
        return float(str(v).strip())
    except (ValueError, AttributeError):
        return default


def _truthy(v):
    return str(v).strip().lower() in ("true", "1", "yes")


def process_calculations(csv_path):
    results = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            row = {(k.strip() if k else k): (v.strip() if isinstance(v, str) else v)
                   for k, v in raw.items()}

            status = row.get("status", "").lower()
            volume = _num(row.get("volume"))
            pid = int(_num(row.get("productid"), 1))
            rate = PRODUCT_RATES.get(pid, {}).get(status, 0)

            rbd = volume * rate

            d_spring = 0.05 if row.get("season", "").lower() == "spring" else 0.0
            if volume < 100:
                d_volume = 0.0
            elif volume < 1000:
                d_volume = 0.05
            else:
                d_volume = 0.10
            d_strategic = 0.05 if row.get("customer", "").lower() == "strategic" else 0.0

            rad = rbd * (1 - (d_spring + d_volume + d_strategic))

            region_loading = 0.10 * rad if row.get("region", "").upper() == "EMEA" else 0.0
            payment_loading = 0.025 * rad if row.get("payment type", "").lower() == "credit-card" else 0.0

            cat = row.get("product category", "").lower()
            multiplier = {"electronics": 1.2, "groceries": 0.8, "luxury": 1.5}.get(cat, 1.0)
            commission = (region_loading + payment_loading) * multiplier

            subtotal = rad + commission
            withholding = 0.03 * subtotal if not _truthy(row.get("tax verified")) else 0.0
            total_receivables = subtotal - withholding

            results.append({"total_receivables": total_receivables})
    return results


def _write_test_cases():
    tmp_inputs = HERE / "_tmp_inputs.csv"
    with tmp_inputs.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=INPUT_COLS)
        w.writeheader()
        w.writerows(INPUT_ROWS)

    targets = [r["total_receivables"] for r in process_calculations(str(tmp_inputs))]

    out = HERE / "test-cases.csv"
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(INPUT_COLS + ["Total_receivables"])
        for row, t in zip(INPUT_ROWS, targets):
            w.writerow([row[c] for c in INPUT_COLS] + [round(t, 6)])
    tmp_inputs.unlink()
    return out, targets


if __name__ == "__main__":
    out, targets = _write_test_cases()
    print(f"Wrote {out.name} with {len(targets)} rows.\n")
    check = [r["total_receivables"] for r in process_calculations(str(out))]
    ok = sum(abs(a - b) <= 0.5 for a, b in zip(check, targets))
    print(f"{'row':>4} {'total_receivables':>20}")
    for i, t in enumerate(targets):
        print(f"{i:>4} {t:>20.4f}")
    print(f"\nself-check: {ok}/{len(targets)} reproduce their own target")
```

**The 10-rule dataset — `test-cases.csv` (12 rows)**

```text
productid,status,volume,season,customer,region,payment type,transaction type,product category,tax verified,Total_receivables
1,individual,90,winter,strategic,non-EMEA,credit-card,international,luxury,False,86045.0625
1,individual,900,winter,strategic,non-EMEA,ach/wire,international,groceries,True,810000.0
2,corporate,140,autumn,strategic,EMEA,ach/wire,international,groceries,False,158397.12
1,individual,90,spring,non-strategic,EMEA,ach/wire,domestic,electronics,True,95760.0
3,individual,320,spring,non-strategic,non-EMEA,ach/wire,cross-border,electronics,False,558720.0
3,corporate,1331,winter,non-strategic,non-EMEA,credit-card,cross-border,groceries,True,2077158.6
1,individual,954,winter,strategic,non-EMEA,credit-card,domestic,groceries,False,849498.84
3,individual,129,summer,non-strategic,non-EMEA,ach/wire,domestic,luxury,True,245100.0
2,corporate,1629,spring,strategic,EMEA,ach/wire,international,luxury,False,1744463.52
1,corporate,265,autumn,non-strategic,non-EMEA,ach/wire,cross-border,electronics,True,226575.0
3,individual,663,summer,strategic,EMEA,ach/wire,cross-border,groceries,False,1250205.84
1,individual,62,winter,non-strategic,non-EMEA,credit-card,domestic,electronics,True,63860.0
```

**The 10-rule harness — `solve_simple.py`** (same loop, but now iteration 1 is greedy for a clean baseline and repairs use temperature so attempts actually diverge):

```python
"""
Iterative generate -> score -> repair loop against the simplified 10-rule spec.
Reuses the model cache from the sibling project (symlinked ./model_cache).

Run:  python3 solve_simple.py
Switch model size by editing MODEL.
"""

import os
import re
import csv
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
os.environ["HF_HOME"] = str(PROJECT_DIR / "model_cache")
os.environ["HF_HUB_CACHE"] = str(PROJECT_DIR / "model_cache")

from mlx_lm import load, generate  # noqa: E402
from mlx_lm.sample_utils import make_sampler  # noqa: E402

# MODEL = "mlx-community/Qwen2.5-Coder-3B-Instruct-4bit"
MODEL = "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit"

TEST_CSV = PROJECT_DIR / "test-cases.csv"
TARGET_COL = "Total_receivables"
TOLERANCE = 0.5
MAX_ITERS = 5
MAX_TOKENS = 2200
# Iteration 1 is greedy (temp 0) for a clean baseline; repairs use temperature so
# successive attempts actually diverge instead of regenerating identical code.
REPAIR_SAMPLER = make_sampler(temp=0.6, top_p=0.9)
GREEDY_SAMPLER = make_sampler(temp=0.0)

SPEC = (PROJECT_DIR / "spec.md").read_text()

INITIAL_INSTRUCTION = (
    "Implement the function described below. Strip spaces from CSV headers, treat "
    "empty cells as defaults, convert numeric strings to numbers, and never crash. "
    "Respond with ONLY code in a single ```python block.\n\n" + SPEC
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
    input_cols = [c for c in fieldnames if c != TARGET_COL]
    return input_cols, rows, targets


def write_inputs_csv(input_cols, rows, path):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=input_cols)
        w.writeheader()
        w.writerows(rows)


def extract_code(text):
    m = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    return (m.group(1) if m else text).strip()


def score(code, inputs_csv, rows, targets):
    ns = {}
    try:
        exec(code, ns)  # noqa: S102 - intentional: running model output
        fn = ns["process_calculations"]
    except Exception as e:
        return 0, [], f"code did not load: {e}"
    try:
        result = fn(str(inputs_csv))
    except Exception as e:
        return 0, [], f"process_calculations raised: {e}"
    if not isinstance(result, list) or len(result) != len(targets):
        return 0, [], (f"expected list of {len(targets)} dicts, got "
                       f"{type(result).__name__} len "
                       f"{len(result) if hasattr(result, '__len__') else 'n/a'}")
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
            + "\n\nFix the code so EVERY row matches. Re-check rule order and which "
            "rules multiply vs add. Respond with ONLY the full corrected function in "
            "a single ```python block.\n\n" + SPEC)


def ask(model, tokenizer, content, sampler):
    messages = [{"role": "user", "content": content}]
    prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True)
    return generate(model, tokenizer, prompt=prompt, max_tokens=MAX_TOKENS,
                    sampler=sampler, verbose=False)


def main():
    input_cols, rows, targets = load_test_rows()
    inputs_csv = PROJECT_DIR / "inputs_only.csv"
    write_inputs_csv(input_cols, rows, inputs_csv)
    print(f"Loaded {len(rows)} test cases. Target: {TARGET_COL}\n")

    print(f"Loading {MODEL} ...\n")
    model, tokenizer = load(MODEL)

    best = (-1, "")
    content = INITIAL_INSTRUCTION
    for it in range(1, MAX_ITERS + 1):
        print("=" * 60)
        print(f"ITERATION {it}/{MAX_ITERS}")
        print("=" * 60)
        sampler = GREEDY_SAMPLER if it == 1 else REPAIR_SAMPLER
        code = extract_code(ask(model, tokenizer, content, sampler))
        passed, lines, err = score(code, inputs_csv, rows, targets)
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
            print("\nALL TEST CASES PASSED ✅")
            break
        content = build_repair_prompt(code, passed, len(targets), lines, err)
    else:
        print(f"\nStopped after {MAX_ITERS} iterations.")

    (PROJECT_DIR / "solution_best.py").write_text(best[1] + "\n")
    print("\n" + "-" * 60)
    print(f"Best: {best[0]}/{len(targets)} passed. Written to solution_best.py")
    print("ALL TESTS PASSED ✅" if best[0] == len(targets) else "Did not fully converge ❌")


if __name__ == "__main__":
    main()
```

**Results at 10 rules:**

- **3B** moved from 0/19 (crashing at 17 rules) up to **3/12** — it now *runs*, and gets rate lookup, discounts, and the withholding structure right. Real progress, still not usable.
- **7B** got the architecture completely right (loadings scaled, multiplier, withholding) but two detail bugs left every row 2–5% off — just outside tolerance. **1/12.**

Here is the 7B run log — note that all five iterations produce the *identical* wrong numbers, because the model can't localize the two bugs from a numeric diff:

**`run_7b_simple.log`**

```text
Loaded 12 test cases. Target: Total_receivables

Loading mlx-community/Qwen2.5-Coder-7B-Instruct-4bit ...
============================================================
ITERATION 1/5
============================================================
  PASSED 1/12
  row 0: got 84037.5000, expected 86045.0625
  row 1: got 765000.0000, expected 810000.0000
  row 2: got 154224.0000, expected 158397.1200
  row 3: got 90720.0000, expected 95760.0000
  row 4: got 544000.0000, expected 558720.0000
  row 6: got 827118.0000, expected 849498.8400
  ... and 5 more
============================================================
ITERATION 2/5
============================================================
  PASSED 1/12
  ... (identical failures) ...
============================================================
ITERATION 5/5
============================================================
  PASSED 1/12
  ... (identical failures) ...

Stopped after 5 iterations.

------------------------------------------------------------
Best: 1/12 passed. Written to solution_best.py
Did not fully converge ❌
```

And the two killer bugs, visible in the 10-rule `solution_best.py` (the model's best attempt):

```python
import csv

PRODUCT_RATES = {
    1: {"individual": 1000, "corporate": 900},
    2: {"individual": 1500, "corporate": 1200},
    3: {"individual": 2000, "corporate": 1700},
}

def process_calculations(csv_path):
    results = []
    with open(csv_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Strip spaces from headers
            row = {k.strip(): v.strip() for k, v in row.items()}
            # Treat empty cells as defaults
            row = {k: v if v else None for k, v in row.items()}
            # Convert numeric strings to numbers
            for key in ['volume']:
                if row[key]:
                    row[key] = int(row[key])

            rate = PRODUCT_RATES.get(int(row['productid']), {}).get(row['status'].lower(), 0)
            receivable_before_discount = row['volume'] * rate if rate else 0

            spring_discount = 0.05 if row['season'].lower() == 'spring' else 0
            # BUG 1: both branches yield 0.1 (and <100 never yields 0). Spec is 0/5/10%.
            volume_discount = 0.05 if row['volume'] < 100 else (0.1 if row['volume'] < 1000 else 0.1)
            strategic_discount = 0.05 if row['customer'].lower() == 'strategic' else 0
            total_discount_rate = spring_discount + volume_discount + strategic_discount
            receivable_after_discount = receivable_before_discount * (1 - total_discount_rate)

            region_loading = 0.1 * receivable_after_discount if row['region'].lower() == 'emea' else 0
            payment_loading = 0.025 * receivable_after_discount if row['payment type'].lower() == 'credit-card' else 0
            commission = (region_loading + payment_loading) * 1.2 if row['product category'].lower() == 'electronics' else \
                         (region_loading + payment_loading) * 0.8 if row['product category'].lower() == 'groceries' else \
                         (region_loading + payment_loading) * 1.5 if row['product category'].lower() == 'luxury' else 0

            subtotal = receivable_after_discount + commission
            # BUG 2: the cell is the STRING "False" (truthy), so `not row[...]` is False
            #         and withholding is skipped exactly when it should apply.
            withholding = 0.03 * subtotal if not row['tax verified'] else 0
            total_receivables = subtotal - withholding

            results.append({'total_receivables': total_receivables})
    return results
```

The two errors partially cancel, which is the worst possible outcome: the totals look close enough to seem right, and wrong enough to be unshippable.

### 4b — The 5-rule spec (the floor)

Finally, I shrank to 5 rules — and, crucially, I changed *how each rule was expressed*, not just the count.

**`spec.md` (5 rules)**

```markdown
# Minimal pricing spec — 5 rules

Build `process_calculations(csv_path)`. It reads a CSV (header names may have extra
spaces; cells may be empty) and returns a list of dicts, one per row, each containing
the key `total_receivables`.

## Input columns
- `productid` : 1, 2, or 3
- `status` : individual or corporate (case-insensitive)
- `volume` : integer
- `season` : spring / summer / winter / autumn
- `customer` : strategic / non-strategic
- `tax verified` : the text "yes" or "no"

## Product rates
PRODUCT_RATES = {
    1: {"individual": 1000, "corporate": 900},
    2: {"individual": 1500, "corporate": 1200},
    3: {"individual": 2000, "corporate": 1700},
}

## The 5 rules (apply in order)
1. Rate: pick the rate from PRODUCT_RATES using productid and status.
2. Base: base = volume * rate.
3. Spring discount: if season is spring, multiply base by 0.95 (a 5% discount);
   otherwise leave it unchanged.
4. Strategic discount: if customer is strategic, multiply by another 0.95
   (a further 5% discount); otherwise leave it unchanged.
5. Tax withholding: if `tax verified` is the text "no", multiply by 0.97
   (a 3% withholding); if it is "yes", leave it unchanged.

total_receivables is the value after applying rules 1–5 in order.
Output: list of dicts, each with key total_receivables.
```

**The ground truth — `reference_five.py`**

```python
"""
Ground-truth reference for the minimal 5-rule spec.
Running it writes test-cases.csv (inputs + Total_receivables) and self-checks.
"""

import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent

PRODUCT_RATES = {
    1: {"individual": 1000, "corporate": 900},
    2: {"individual": 1500, "corporate": 1200},
    3: {"individual": 2000, "corporate": 1700},
}

INPUT_COLS = ["productid", "status", "volume", "season", "customer", "tax verified"]

INPUT_ROWS = [
    {"productid": "1", "status": "individual", "volume": "90",   "season": "winter", "customer": "strategic",     "tax verified": "no"},
    {"productid": "1", "status": "individual", "volume": "900",  "season": "spring", "customer": "strategic",     "tax verified": "yes"},
    {"productid": "2", "status": "corporate",  "volume": "140",  "season": "autumn", "customer": "strategic",     "tax verified": "no"},
    {"productid": "1", "status": "individual", "volume": "90",   "season": "spring", "customer": "non-strategic", "tax verified": "yes"},
    {"productid": "3", "status": "individual", "volume": "320",  "season": "spring", "customer": "non-strategic", "tax verified": "no"},
    {"productid": "3", "status": "corporate",  "volume": "1331", "season": "winter", "customer": "non-strategic", "tax verified": "yes"},
    {"productid": "1", "status": "individual", "volume": "954",  "season": "winter", "customer": "strategic",     "tax verified": "no"},
    {"productid": "3", "status": "individual", "volume": "129",  "season": "summer", "customer": "non-strategic", "tax verified": "yes"},
    {"productid": "2", "status": "corporate",  "volume": "1629", "season": "spring", "customer": "strategic",     "tax verified": "no"},
    {"productid": "1", "status": "corporate",  "volume": "265",  "season": "autumn", "customer": "non-strategic", "tax verified": "yes"},
    {"productid": "3", "status": "individual", "volume": "663",  "season": "summer", "customer": "strategic",     "tax verified": "no"},
    {"productid": "1", "status": "individual", "volume": "62",   "season": "winter", "customer": "non-strategic", "tax verified": "yes"},
]


def _num(v, default=0.0):
    try:
        return float(str(v).strip())
    except (ValueError, AttributeError):
        return default


def process_calculations(csv_path):
    results = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            row = {(k.strip() if k else k): (v.strip() if isinstance(v, str) else v)
                   for k, v in raw.items()}

            status = row.get("status", "").lower()
            volume = _num(row.get("volume"))
            pid = int(_num(row.get("productid"), 1))
            rate = PRODUCT_RATES.get(pid, {}).get(status, 0)

            amount = volume * rate
            if row.get("season", "").lower() == "spring":
                amount *= 0.95
            if row.get("customer", "").lower() == "strategic":
                amount *= 0.95
            if row.get("tax verified", "").lower() == "no":
                amount *= 0.97

            results.append({"total_receivables": amount})
    return results


def _write_test_cases():
    tmp = HERE / "_tmp_inputs.csv"
    with tmp.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=INPUT_COLS)
        w.writeheader()
        w.writerows(INPUT_ROWS)
    targets = [r["total_receivables"] for r in process_calculations(str(tmp))]
    out = HERE / "test-cases.csv"
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(INPUT_COLS + ["Total_receivables"])
        for row, t in zip(INPUT_ROWS, targets):
            w.writerow([row[c] for c in INPUT_COLS] + [round(t, 6)])
    tmp.unlink()
    return out, targets


if __name__ == "__main__":
    out, targets = _write_test_cases()
    print(f"Wrote {out.name} with {len(targets)} rows.\n")
    check = [r["total_receivables"] for r in process_calculations(str(out))]
    ok = sum(abs(a - b) <= 0.5 for a, b in zip(check, targets))
    print(f"{'row':>4} {'total_receivables':>20}")
    for i, t in enumerate(targets):
        print(f"{i:>4} {t:>20.4f}")
    print(f"\nself-check: {ok}/{len(targets)}")
```

**The 5-rule dataset — `test-cases.csv` (12 rows)**

```text
productid,status,volume,season,customer,tax verified,Total_receivables
1,individual,90,winter,strategic,no,82935.0
1,individual,900,spring,strategic,yes,812250.0
2,corporate,140,autumn,strategic,no,154812.0
1,individual,90,spring,non-strategic,yes,85500.0
3,individual,320,spring,non-strategic,no,589760.0
3,corporate,1331,winter,non-strategic,yes,2262700.0
1,individual,954,winter,strategic,no,879111.0
3,individual,129,summer,non-strategic,yes,258000.0
2,corporate,1629,spring,strategic,no,1711280.79
1,corporate,265,autumn,non-strategic,yes,238500.0
3,individual,663,summer,strategic,no,1221909.0
1,individual,62,winter,non-strategic,yes,62000.0
```

**The 5-rule harness — `solve_five.py`** (identical loop, pointed at the 3B by default):

```python
"""
Iterative generate -> score -> repair loop against the minimal 5-rule spec.
Reuses the symlinked ./model_cache. Run:  python3 solve_five.py
"""

import os
import re
import csv
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
os.environ["HF_HOME"] = str(PROJECT_DIR / "model_cache")
os.environ["HF_HUB_CACHE"] = str(PROJECT_DIR / "model_cache")

from mlx_lm import load, generate  # noqa: E402
from mlx_lm.sample_utils import make_sampler  # noqa: E402

MODEL = "mlx-community/Qwen2.5-Coder-3B-Instruct-4bit"
# MODEL = "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit"

TEST_CSV = PROJECT_DIR / "test-cases.csv"
TARGET_COL = "Total_receivables"
TOLERANCE = 0.5
MAX_ITERS = 6
MAX_TOKENS = 1800
REPAIR_SAMPLER = make_sampler(temp=0.6, top_p=0.9)
GREEDY_SAMPLER = make_sampler(temp=0.0)

SPEC = (PROJECT_DIR / "spec.md").read_text()

INITIAL_INSTRUCTION = (
    "Implement the function described below. Strip spaces from CSV headers, treat "
    "empty cells as defaults, convert numeric strings to numbers, and never crash. "
    "Respond with ONLY code in a single ```python block.\n\n" + SPEC
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
    input_cols, rows, targets = load_test_rows()
    inputs_csv = PROJECT_DIR / "inputs_only.csv"
    write_inputs_csv(input_cols, rows, inputs_csv)
    print(f"Loaded {len(rows)} test cases. Target: {TARGET_COL}\n")
    print(f"Loading {MODEL} ...\n")
    model, tokenizer = load(MODEL)

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
            print("\nALL TEST CASES PASSED ✅")
            break
        content = build_repair_prompt(code, passed, len(targets), lines, err)
    else:
        print(f"\nStopped after {MAX_ITERS} iterations.")

    (PROJECT_DIR / "solution_best.py").write_text(best[1] + "\n")
    print("\n" + "-" * 60)
    print(f"Best: {best[0]}/{len(targets)} passed. Written to solution_best.py")
    print("ALL TESTS PASSED ✅" if best[0] == len(targets) else "Did not fully converge ❌")


if __name__ == "__main__":
    main()
```

**Result: the 3B passed 12/12 on the very first iteration, no repairs needed.** And it did it cleanly — no harness-gaming, just a correct, readable implementation:

**`solution_best.py` (3B, 5-rule, 12/12 first try)**

```python
import csv
import re

PRODUCT_RATES = {
    1: {"individual": 1000, "corporate": 900},
    2: {"individual": 1500, "corporate": 1200},
    3: {"individual": 2000, "corporate": 1700},
}

def process_calculations(csv_path):
    try:
        with open(csv_path, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            headers = [re.sub(r'\s+', '', header).strip() for header in reader.fieldnames]
            rows = []

            for row in reader:
                productid = int(row.get('productid', 0))
                status = row.get('status', '').lower()
                volume = int(row.get('volume', 0))
                season = row.get('season', '').lower()
                customer = row.get('customer', '').lower()
                tax_verified = row.get('tax verified', '').lower()

                rate = PRODUCT_RATES.get(productid, {}).get(status, 0)
                base = volume * rate

                if season == 'spring':
                    base *= 0.95
                if customer == 'strategic':
                    base *= 0.95

                if tax_verified == 'no':
                    base *= 0.97

                total_receivables = base
                rows.append({'total_receivables': total_receivables})

        return rows
    except FileNotFoundError:
        return []
    except ValueError:
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

# Example usage:
# result = process_calculations('path_to_your_csv.csv')
# print(result)
```

---

## The real insight: it's not the number of rules

Going from 10 rules to 5 is *not* what fixed it. I changed **three specific things** in that final spec, and those — not the count — are why it suddenly worked:

1. **No multi-branch logic.** The three-tier volume conditional ("under 100 → 0%, under 1000 → 5%, else 10%") broke *both* models every single time — they collapsed the branches. The 5-rule spec used only simple, single-condition `if`s.
2. **No ambiguous booleans.** I used the plain text "yes"/"no" instead of `True`/`False`. The 7B had been mis-parsing the *string* `"False"` as truthy and skipping the withholding step entirely.
3. **No mental math.** I wrote "multiply by 0.95" instead of "apply a 5% discount," so the model never had to translate a percentage into a multiplier.

**The viability boundary for a small local model isn't how many rules you have. It's how hard each individual rule is to express in code.** One unambiguous operation per rule? A 3B model on a laptop nails it, first try. Multi-branch logic, type coercion, or "figure out the arithmetic yourself"? It quietly gets it wrong — and "quietly" is the dangerous part, because a 2% error looks like success.

---

## The full results, in one table

| Spec size | Approach / Model | Ran? | Score |
|---|---|---|---|
| Warm-up (sort) | 0.5B, single shot | ✅ | 5/5 ✅ |
| 17 rules | 0.5B vs spec | crashed (`NameError`) | — |
| 17 rules | 0.5B vs examples | crashed (invented `price`) | — |
| 17 rules | 3B repair loop | ran | 0/19 (discounts exact, commission dropped) |
| 17 rules | 7B repair loop | crashed all 5 iters (`KeyError: 'customer name'`) | 0/19 |
| 17 rules | **hand-derived reference** | ✅ | **19/19 ✅** |
| 10 rules | 3B repair loop | ran | 3/12 |
| 10 rules | 7B repair loop | ran | 1/12 (architecture right, ~2–5% off) |
| 10 rules | **hand-derived reference** | ✅ | **12/12 ✅** |
| **5 rules** | **3B, first try** | ✅ | **12/12 ✅** |
| 5 rules | **hand-derived reference** | ✅ | **12/12 ✅** |

---

## What I'm taking away from this

If you want to use a small, local, free model for real work on modest hardware — and there are good privacy and cost reasons to want that — the lever **isn't a bigger model.** You're capped by your RAM anyway. The lever is **writing the spec in the model's dialect**:

- Decompose multi-tier rules into separate single-condition steps.
- Hand it multipliers, not percentages.
- Use unambiguous string flags, not booleans.
- Keep the feedback loop, but don't expect a numeric diff to teach a small model *where* its bug is — it can't localize from "you got 81,000, expected 86,045."
- And always, *always* keep a ground-truth test set. It is the only thing that tells you the truth — because even your written spec might be lying to you.

A small model on an 8 GB laptop turns out to be a perfectly capable junior developer — as long as you write the ticket carefully and check its work.

### Honest caveats

This is an experiment, not a benchmark. A few things I'm *not* claiming: the test sets are small (12–19 rows); I ran a handful of seeds, not hundreds; results would shift with a different prompt, a higher token budget, or a non-4-bit quantization; and "5 rules works, 10 doesn't" is the boundary *for this task and these models*, not a universal constant. The defensible claim is narrower and, I think, more useful: **per-rule expressibility dominates rule count**, and a held-out numeric test set is non-negotiable.

---

## Run it yourself

Everything above is runnable on any Apple Silicon Mac. Here's the complete recipe.

### Requirements

- An Apple Silicon Mac (M1/M2/M3…). 8 GB RAM is enough for everything here; the 7B 4-bit model is the ceiling at that size.
- Python 3.9+ and `mlx_lm`:

```bash
pip install mlx-lm
```

The models download automatically on first run (0.5B ≈ 1 GB, 3B ≈ 1.8 GB, 7B ≈ 4.3 GB) and are cached inside each project folder via `HF_HOME` / `HF_HUB_CACHE`, so nothing pollutes your global cache. First run pulls weights; later runs start instantly.

### Layout

Create three folders and drop the files from this article into them:

```
qwen-warmup/
  generate_sort.py            # 0.5B writes + self-tests a sort function

experiment-10-rules/
  spec.md
  reference_simple.py         # generates test-cases.csv + self-checks 12/12
  solve_simple.py             # the loop (edit MODEL for 3B vs 7B)

experiment-5-rules/
  spec.md
  reference_five.py           # generates test-cases.csv + self-checks 12/12
  solve_five.py               # the loop (3B by default)
```

### Commands

```bash
# 0) Warm-up: prove the 0.5B model can write + pass a one-function task.
cd qwen-warmup
python3 generate_sort.py

# 1) The 10-rule task.
cd ../experiment-10-rules
python3 reference_simple.py      # regenerate test-cases.csv + self-check (12/12)
python3 solve_simple.py          # the loop; edit MODEL inside (3B ~3/12, 7B ~1/12)

# 2) The 5-rule task — the one that works.
cd ../experiment-5-rules
python3 reference_five.py        # regenerate test-cases.csv + self-check (12/12)
python3 solve_five.py            # 3B passes 12/12 on the first iteration ✅
```

A few practical notes:

- **Switching model size** is a one-line edit: change the `MODEL = "mlx-community/Qwen2.5-Coder-..."` constant at the top of any `solve_*.py`. The three sizes are `0.5B-Instruct-bf16`, `3B-Instruct-4bit`, and `7B-Instruct-4bit`.
- **The `reference_*.py` files are the ground truth.** Run them first — they generate (or self-check) the `test-cases.csv` that the LLM loop scores against. If you change the rules, regenerate the test set from the reference so the targets stay consistent.
- **The harness runs model-generated code with `exec`.** That's fine for a sandboxed personal experiment; don't point it at untrusted specs on a machine you care about.
- **`TOLERANCE`** is the absolute error allowed on `total_receivables` (0.5 against targets in the 10⁵–10⁶ range). Tighten it to make the loop stricter; loosen it to see "almost right" attempts pass.

That's the whole experiment. Clone the layout, run the commands top to bottom, and you'll watch a free model on your own laptop fail at 17 rules, crawl at 10, and nail 5 — and you'll see exactly *why* in the per-row diffs.

---

*Tools used: Apple MLX (`mlx_lm`), Qwen2.5-Coder (0.5B bf16, 3B & 7B 4-bit), on an M1 MacBook with 8 GB RAM. Total cloud cost: $0.*

*What's the most surprising place you've seen a small local model succeed — or fail? I'd genuinely like to know where your boundary landed.*
