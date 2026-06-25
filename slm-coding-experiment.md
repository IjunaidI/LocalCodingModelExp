# Can a tiny AI on an 8GB MacBook write real business logic? I ran the full experiment — here is every line of code, every dataset, and every test.

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

Here is the full spec exactly as it was handed to the model.

**The 17-rule spec (verbatim prompt)**

```text
The CSV input columns (names may have extra spaces; cells may be empty) are:
customer name, productid (1/2/3), season (spring/summer/winter/autumn),
volume (int), region (EMEA/non-EMEA), customer (strategic/non-strategic),
status (individual/corporate, case-insensitive), payment type (ach/wire or
credit-card), quarter (Q1-Q4), transaction type (domestic/international/
cross-border), product category (electronics/groceries/luxury),
seller years (int), processing speed (same-day/next-day/standard),
referral active (True/False), referral invoices remaining (int),
tax verified (bool, may be empty), is high risk (bool), requires correction (bool),
individual rate (number), corporate rate (number).

PRODUCT_RATES = {1:{"individual":1000,"corporate":900},
                 2:{"individual":1500,"corporate":1200},
                 3:{"individual":2000,"corporate":1700}}

Per row, compute (use the row's individual/corporate rate columns, selected by status):
- receivable_before_discount = volume * rate(status)
- Rule A discount: spring => 5% of receivable_before_discount
- Rule B volume_discount: volume<100 => 0%, <1000 => 5%, >=1000 => 10%
- Rule C category_discount: strategic customer => 5%
- Rule I loyalty: seller years>=5 => 15% (Platinum), >=2 => 10% (Gold), else 0%
- total_discounts = sum of A+B+C+I amounts (each = its % of receivable_before_discount)
- receivable_after_discount = receivable_before_discount - total_discounts
All loadings are computed on receivable_after_discount:
- Rule E region_loading: EMEA => +10%
- Rule F payment_method_loading: credit-card => +2.5%
- Rule G seasonal_pricing_tier_loading: Q1 => +2%, Q4 => -1%, else 0%
- Rule H geographic_zone_loading: domestic 5%, international 8%, cross-border 10%
- Rule L processing_speed_premium: same-day +15%, next-day +10%, standard 0%
- base_commission_total = region + payment + seasonal + geographic + processing speed loadings
- Rule J product_category_multiplier: electronics 1.2, groceries 0.8, luxury 1.5
- adjusted_commission_total = base_commission_total * product_category_multiplier
- Rule N referral credit: if referral active and invoices remaining>0, add 0.25% of adjusted_commission_total
- Rule P risk fee: if high risk, subtract 1.5% of adjusted_commission_total
- Rule Q correction_fee: requires correction => flat $5
- Rule O tax withholding: if tax NOT verified => 3% withholding on the pre-withholding total
- total_receivables = receivable_after_discount + adjusted_commission_total
                      + correction_fee - tax_withholding_amount

Return a list of dicts (one per row). Each dict MUST contain key 'total_receivables'.
```

To score *anything*, I needed ground truth. I built a labelled dataset of 19 rows where the last column, `Total_receivables`, is the correct answer and everything else is input. (How I derived those answers becomes the plot twist later — for now, treat them as truth.)

**The dataset — `test-cases.csv` (19 labelled rows)**

```text
customer name,productid,season,volume,region,customer,status,payment type,quarter,transaction type,product category,seller years,processing speed,referral active,referral invoices remaining,tax verified,is high risk,requires correction,individual rate,corporate rate,Total_receivables
A,1,winter,90,non-EMEA,strategic,INDIVIDUAL,credit-card,Q2,international,luxury,3,same-day,FALSE,0,,FALSE,FALSE,1000,900,102588.4125
B,1,winter,900,non-EMEA,strategic,INDIVIDUAL,ach/wire,Q2,international,groceries,5,standard,FALSE,0,,FALSE,FALSE,1000,900,696654
C,1,winter,90,EMEA,non-strategic,INDIVIDUAL,credit-card,Q4,international,luxury,5,same-day,TRUE,7,,TRUE,TRUE,1000,900,112702.0902
D,1,spring,90,EMEA,non-strategic,INDIVIDUAL,ach/wire,Q1,domestic,electronics,7,next-day,FALSE,0,,FALSE,FALSE,1000,900,92468.16
E,3,spring,320,non-EMEA,non-strategic,INDIVIDUAL,ach/wire,Q4,cross-border,electronics,4,standard,FALSE,0,,FALSE,FALSE,2000,1700,550277.12
F,2,autumn,140,EMEA,strategic,CORPORATE,ach/wire,Q4,international,groceries,8,next-day,FALSE,0,,FALSE,FALSE,1500,1200,148619.52
G,1,autumn,1854,EMEA,non-strategic,CORPORATE,credit-card,Q3,international,electronics,2,standard,FALSE,0,,FALSE,FALSE,1000,900,1613362.666
H,1,winter,954,non-EMEA,strategic,INDIVIDUAL,credit-card,Q4,domestic,groceries,0,standard,FALSE,0,,FALSE,FALSE,1000,900,876149.784
I,3,summer,129,non-EMEA,non-strategic,INDIVIDUAL,ach/wire,Q2,domestic,luxury,1,same-day,FALSE,0,,FALSE,FALSE,2000,1700,309071.1
J,3,winter,1331,non-EMEA,non-strategic,CORPORATE,credit-card,Q3,cross-border,groceries,9,same-day,FALSE,0,,FALSE,FALSE,2000,1700,2008259.385
K,1,autumn,758,EMEA,non-strategic,INDIVIDUAL,ach/wire,Q1,domestic,luxury,6,same-day,FALSE,0,,FALSE,FALSE,1000,900,870547.84
L,2,spring,1629,EMEA,strategic,CORPORATE,ach/wire,Q3,international,luxury,1,same-day,FALSE,0,,FALSE,FALSE,1500,1200,2267802.576
M,3,autumn,1883,non-EMEA,non-strategic,INDIVIDUAL,credit-card,Q2,cross-border,electronics,5,same-day,FALSE,0,,FALSE,FALSE,2000,1700,3643887.45
N,1,winter,62,non-EMEA,non-strategic,INDIVIDUAL,credit-card,Q4,domestic,electronics,6,next-day,FALSE,0,,FALSE,FALSE,1000,900,61240.562
O,3,summer,663,EMEA,strategic,INDIVIDUAL,ach/wire,Q1,cross-border,groceries,8,same-day,FALSE,0,,FALSE,FALSE,2000,1700,1250205.84
P,1,autumn,265,non-EMEA,non-strategic,CORPORATE,ach/wire,Q3,cross-border,electronics,5,standard,FALSE,0,,FALSE,FALSE,1000,900,207285.12
Q,3,winter,651,non-EMEA,strategic,CORPORATE,ach/wire,Q1,cross-border,luxury,6,standard,FALSE,0,,FALSE,FALSE,2000,1700,950046.615
R,3,summer,534,non-EMEA,non-strategic,INDIVIDUAL,ach/wire,Q3,international,groceries,7,same-day,FALSE,0,,FALSE,FALSE,2000,1700,981261.312
S,3,summer,145,EMEA,strategic,INDIVIDUAL,ach/wire,Q2,international,electronics,2,next-day,FALSE,0,,FALSE,FALSE,2000,1700,300653.44
```

### Attempt 1a — throw the spec at the smallest model (0.5B, single shot)

This program hands the full spec to the 0.5B model and runs a **structural** smoke test on the result (does it run, return a list of dicts, expose the right keys). I had no illusions; the comment block says as much.

**`generate_calculations.py`**

```python
"""
Use Qwen2.5-Coder-0.5B (via MLX) to write a Python `process_calculations`
function from the pricing/commission spec below.

Everything is kept inside this folder: the model is downloaded into ./model_cache
so nothing touches the global ~/.cache/huggingface.

Run:  python3 generate_calculations.py

NOTE: A 0.5B model is very unlikely to implement this 17-rule spec correctly in
one shot. Treat the generated file as a draft to inspect, not a finished function.
The verification step is a STRUCTURAL smoke test (runs on a messy CSV, returns a
list of dicts exposing total_receivables + escrow) -- it does NOT prove every rule
is numerically correct, because the spec itself has unresolved contradictions
(e.g. the total_receivables formula omits the Rule N referral credit and the
Rule P high-risk fee).
"""

import os
import re
import csv
from pathlib import Path

# --- Keep the model inside this project folder -----------------------------
PROJECT_DIR = Path(__file__).resolve().parent
os.environ["HF_HOME"] = str(PROJECT_DIR / "model_cache")
os.environ["HF_HUB_CACHE"] = str(PROJECT_DIR / "model_cache")

# Import AFTER setting the env vars so the cache location takes effect.
from mlx_lm import load, generate  # noqa: E402

MODEL = "mlx-community/Qwen2.5-Coder-0.5B-Instruct-bf16"

# The full requirement, handed to the model verbatim.
PROMPT = r"""
Write a single Python file that defines a function `process_calculations(csv_path)`.

The function takes a path to a CSV file. The CSV field names may have extra
leading/trailing spaces (strip them). Any cell value may be empty -- handle that
gracefully (treat empty as a sensible default and never crash). The CSV has these
fields:

- customer            : "strategic" or "non-strategic"
- productid           : 1, 2, or 3
- season              : spring, summer, winter, autumn
- volume              : integer
- region              : EMEA or non-EMEA
- quarter             : Q1, Q2, Q3, Q4
- payment type        : "ach/wire" or "credit-card"
- transaction type    : domestic, international, or cross-border
- product category    : electronics, groceries, or luxury
- seller years        : integer
- processing speed    : same-day, next-day, or standard
- tax verified        : boolean
- is high risk        : boolean
- requires correction : boolean
- status              : "individual" or "corporate" (the customer status)
- referral active     : True/False (is referral credit active)
- referral invoices remaining : integer counter

Product rates (Rule D -- each product has an individual and a corporate rate):
    PRODUCT_RATES = {
        1: {"individual": 1000, "corporate": 900},
        2: {"individual": 1500, "corporate": 1200},
        3: {"individual": 2000, "corporate": 1700},
    }

Compute the following per row (output values may be float):

- individual rate / corporate rate          : from PRODUCT_RATES (Rule D)
- receivable_before_discount = volume * (individual or corporate rate, by status)
- discount          : Rule A -- spring season => 5% discount
- volume_discount   : Rule B -- volume < 100 => 0%, < 1000 => 5%, >= 1000 => 10%
- category_discount : Rule C -- strategic customer => 5% discount
- loyalty_discount / loyalty_status : Rule I -- seller years >= 5 => Platinum 15%,
                       else seller years >= 2 => Gold 10%, else none 0%
- total_discounts = amounts from Rule A + Rule B + Rule C + Rule I, each computed
                    as its percentage of receivable_before_discount
- receivable_after_discount = receivable_before_discount - total_discounts

ALL loadings below are calculated strictly on receivable_after_discount:
- region_loading                : Rule E -- EMEA => +10%
- payment_method_loading        : Rule F -- credit-card => +2.5%
- seasonal_pricing_tier_loading : Rule G -- Q1 => +2%, Q4 => -1%, else 0%
- geographic_zone_loading       : Rule H -- domestic 5%, international 8%, cross-border 10%
- processing_speed_premium      : Rule L -- same-day +15%, next-day +10%, standard 0%

- product_category_multiplier   : Rule J -- electronics 1.2, groceries 0.8, luxury 1.5
- minimum_transaction_fee       : Rule K -- invoice under $50 => flat $2.50 fee
- escrow                        : Rule M -- 1% of gross invoice, tracked separately
- referral_credit_system        : Rule N -- if referral active and invoices remaining,
                       0.25% credit on adjusted commission total (next 10 invoices)
- tax_withholding_rate / tax_withholding_amount : Rule O -- if tax NOT verified,
                       additional 3% withholding on total receivables
- base_commission_total = region_loading + payment_method_loading
                          + seasonal_pricing_tier_loading + geographic_zone_loading
                          + processing_speed_premium
- risk_management_fee   : Rule P -- high-risk => 1.5% fee subtracted from adjusted commission
- correction_fee        : Rule Q -- requires correction => flat $5 admin fee
- adjusted_commission_total = base_commission_total * product_category_multiplier
- total_receivables = receivable_after_discount + adjusted_commission_total
                      + correction_fee - tax_withholding_amount
  (escrow is tracked separately and NOT included in total_receivables)
- comments

The function must return a list of dictionaries, one per CSV row, with all the
calculated values. Every returned dictionary MUST include the keys
`total_receivables` and `escrow`.

Respond with only the code inside a single ```python code block.
"""


def extract_code(text: str) -> str:
    """Pull the first python code block out of the model output."""
    match = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    return (match.group(1) if match else text).strip()


def write_sample_csv(path: Path) -> None:
    """A small, deliberately messy CSV: extra spaces in headers + empty cells."""
    headers = [
        " customer", "productid ", " season", "volume", "region", "quarter",
        "payment type", "transaction type", "product category", "seller years",
        "processing speed", "tax verified", "is high risk", "requires correction",
        "status", "referral active", "referral invoices remaining", "comments",
    ]
    rows = [
        ["strategic", "2", "spring", "1200", "EMEA", "Q1", "credit-card",
         "international", "electronics", "6", "same-day", "True", "False",
         "True", "corporate", "True", "4", "high-volume strategic deal"],
        ["non-strategic", "1", "summer", "50", "non-EMEA", "Q4", "ach/wire",
         "domestic", "groceries", "1", "standard", "False", "True",
         "False", "individual", "False", "0", "small order"],
        # A row with several empty values to exercise the empty-handling path.
        ["", "3", "", "", "", "", "", "cross-border", "luxury", "",
         "standard", "", "", "", "individual", "", "", ""],
    ]
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


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
        max_tokens=2500,  # this is a large function, not a one-liner
        verbose=True,
    )
    print("-" * 60)

    code = extract_code(output)
    code_path = PROJECT_DIR / "generated_calculations.py"
    code_path.write_text(code + "\n")
    print(f"\nExtracted code written to: {code_path.name}\n")
    print(code)

    # --- Verify the generated code (STRUCTURAL smoke test) -----------------
    print("\n" + "=" * 60)
    print("VERIFYING the model's code (structure / does-it-run)")
    print("=" * 60)

    sample_csv = PROJECT_DIR / "sample_input.csv"
    write_sample_csv(sample_csv)
    print(f"Sample CSV written to: {sample_csv.name}")

    namespace: dict = {}
    try:
        exec(code, namespace)  # noqa: S102 - intentional: running model output
        process_calculations = namespace["process_calculations"]
    except Exception as e:  # model produced something unrunnable
        print(f"FAIL: generated code did not load: {e}")
        return

    checks = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append(ok)
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))

    try:
        result = process_calculations(str(sample_csv))
    except Exception as e:
        check("process_calculations(csv) runs without error", False, str(e))
        print("\nSOME CHECKS FAILED ❌")
        return

    check("returns a list", isinstance(result, list), f"got {type(result).__name__}")
    check("one entry per CSV row (3)", isinstance(result, list) and len(result) == 3,
          f"got {len(result) if isinstance(result, list) else 'n/a'}")

    rows_are_dicts = isinstance(result, list) and all(isinstance(r, dict) for r in result)
    check("every entry is a dict", rows_are_dicts)

    if rows_are_dicts and result:
        has_total = all("total_receivables" in r for r in result)
        has_escrow = all("escrow" in r for r in result)
        check("every dict has key 'total_receivables'", has_total)
        check("every dict has key 'escrow'", has_escrow)

        def numeric(rows, key):
            return all(isinstance(r.get(key), (int, float)) for r in rows)

        if has_total:
            check("'total_receivables' values are numeric", numeric(result, "total_receivables"))
        if has_escrow:
            check("'escrow' values are numeric", numeric(result, "escrow"))

        print("\n  --- first row output ---")
        for k, v in result[0].items():
            print(f"    {k}: {v}")

    print("\n" + ("ALL STRUCTURAL CHECKS PASSED ✅"
                  if all(checks) else "SOME CHECKS FAILED ❌"))
    print("(Reminder: this verifies structure, not full numeric correctness of all 17 rules.)")


if __name__ == "__main__":
    main()
```

The 0.5B produced code that looked plausible for a few lines, then referenced a `price` column **that does not exist in the data**, mangled the discount tiers, and never produced a usable result. A representative slice of what it wrote (`generated_calculations.py`):

```python
# (excerpt of the 0.5B output — note the bugs)
receivable_before_discount = volume * (individual_rate if row['status'] == 'individual' else corporate_rate)
...
# 'amounts' is invented; 'total_receivables' is referenced but never defined
total_discounts = (amounts := row['amounts']) * (discount if row['status'] == 'individual' else category_discount)
...
results.append({'total_receivables': total_receivables, 'escrow': escrow})  # NameError: total_receivables
```

It implemented maybe 3 of the 17 rules, all incorrectly, and crashed on a `NameError`.

### Attempt 1b — give it the *examples* instead of the spec (0.5B, single shot)

A reasonable hypothesis: maybe the prose spec is the problem. What if I show the model the 19 input→answer examples and ask it to *infer* the formula? This is the "test-driven" framing.

**`generate_from_tests.py`**

```python
"""
Test-driven variant: instead of handing Qwen2.5-Coder-0.5B the written spec, we
hand it the input->target examples from test-cases.csv and ask it to write a
`process_calculations(csv_path)` function whose `total_receivables` output matches
the `Total_receivables` target column for every row.

Everything stays inside this folder (model cached in ./model_cache).

Run:  python3 generate_from_tests.py

REALITY CHECK: reverse-engineering a multi-rule pricing formula from 19 examples
is HARDER for a tiny model than transcribing a spec. Expect failure. The value
here is the harness: it scores the generated code against every test row and
reports the pass rate + per-row error, so you can see exactly how far off it is.
"""

import os
import re
import csv
from pathlib import Path

# --- Keep the model inside this project folder -----------------------------
PROJECT_DIR = Path(__file__).resolve().parent
os.environ["HF_HOME"] = str(PROJECT_DIR / "model_cache")
os.environ["HF_HUB_CACHE"] = str(PROJECT_DIR / "model_cache")

# Import AFTER setting the env vars so the cache location takes effect.
from mlx_lm import load, generate  # noqa: E402

MODEL = "mlx-community/Qwen2.5-Coder-0.5B-Instruct-bf16"

TEST_CSV = PROJECT_DIR / "test-cases.csv"
TARGET_COL = "Total_receivables"
TOLERANCE = 0.01  # absolute tolerance when comparing total_receivables


def load_test_rows():
    """Read test-cases.csv -> (list of input-only dict rows, list of targets)."""
    with TEST_CSV.open(newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = [fn.strip() for fn in reader.fieldnames]
        rows, targets = [], []
        for raw in reader:
            clean = {k.strip(): (v.strip() if v else "") for k, v in raw.items()}
            targets.append(float(clean[TARGET_COL]))
            inputs = {k: v for k, v in clean.items() if k != TARGET_COL}
            rows.append(inputs)
    input_cols = [c for c in fieldnames if c != TARGET_COL]
    return input_cols, rows, targets


def build_prompt(input_cols, rows, targets) -> str:
    """Show the model the columns and every input->target example."""
    examples = []
    for r, t in zip(rows, targets):
        feats = ", ".join(f"{c}={r[c]!r}" for c in input_cols)
        examples.append(f"  {feats}  ->  {TARGET_COL}={t}")
    examples_block = "\n".join(examples)

    return (
        "You are given labelled examples. Each row has input fields and one target "
        f"value `{TARGET_COL}`. Write a Python function "
        "`process_calculations(csv_path)` that reads a CSV with these input columns "
        "(field names may have extra spaces; cells may be empty) and returns a list "
        "of dictionaries, one per row, where each dictionary has the key "
        "`total_receivables` holding the computed target for that row.\n\n"
        f"Input columns: {', '.join(input_cols)}\n\n"
        "Examples (inputs -> target):\n"
        f"{examples_block}\n\n"
        "Infer the calculation rules from the examples so that your function "
        f"reproduces `{TARGET_COL}` for every row. "
        "Respond with only the code inside a single ```python code block."
    )


def extract_code(text: str) -> str:
    """Pull the first python code block out of the model output."""
    match = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    return (match.group(1) if match else text).strip()


def write_inputs_csv(input_cols, rows, path: Path) -> None:
    """Write an inputs-only CSV (target column removed) for the function to read."""
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=input_cols)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    input_cols, rows, targets = load_test_rows()
    print(f"Loaded {len(rows)} test cases from {TEST_CSV.name}")
    print(f"Target column: {TARGET_COL}\n")

    print(f"Loading {MODEL} ...")
    print(f"(cached in {os.environ['HF_HUB_CACHE']})\n")
    model, tokenizer = load(MODEL)

    prompt_text = build_prompt(input_cols, rows, targets)
    messages = [{"role": "user", "content": prompt_text}]
    prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True)

    print("Generating...\n" + "-" * 60)
    output = generate(
        model, tokenizer, prompt=prompt, max_tokens=2500, verbose=True,
    )
    print("-" * 60)

    code = extract_code(output)
    code_path = PROJECT_DIR / "generated_from_tests.py"
    code_path.write_text(code + "\n")
    print(f"\nExtracted code written to: {code_path.name}\n")
    print(code)

    # --- Score the generated code against every test row -------------------
    print("\n" + "=" * 60)
    print("SCORING the model's code against the test targets")
    print("=" * 60)

    inputs_csv = PROJECT_DIR / "inputs_only.csv"
    write_inputs_csv(input_cols, rows, inputs_csv)

    namespace: dict = {}
    try:
        exec(code, namespace)  # noqa: S102 - intentional: running model output
        process_calculations = namespace["process_calculations"]
    except Exception as e:
        print(f"FAIL: generated code did not load: {e}")
        return

    try:
        result = process_calculations(str(inputs_csv))
    except Exception as e:
        print(f"FAIL: process_calculations(csv) raised: {e}")
        return

    if not isinstance(result, list) or len(result) != len(targets):
        print(f"FAIL: expected a list of {len(targets)} dicts, "
              f"got {type(result).__name__} of len "
              f"{len(result) if hasattr(result, '__len__') else 'n/a'}")
        return

    passed = 0
    print(f"\n{'row':>4} {'predicted':>16} {'target':>16} {'abs err':>16}  result")
    for i, (pred_row, target) in enumerate(zip(result, targets)):
        label = rows[i].get("customer name", str(i))
        try:
            pred = float(pred_row.get("total_receivables"))
            err = abs(pred - target)
            ok = err <= TOLERANCE
        except Exception as e:
            pred, err, ok = None, None, False
            print(f"{label:>4} {'<bad value>':>16} {target:>16.4f} {'n/a':>16}  FAIL ({e})")
            continue
        passed += ok
        print(f"{label:>4} {pred:>16.4f} {target:>16.4f} {err:>16.4f}  "
              f"{'PASS' if ok else 'FAIL'}")

    print("\n" + "-" * 60)
    print(f"PASSED {passed}/{len(targets)} test cases "
          f"(tolerance ±{TOLERANCE})")
    print("ALL TESTS PASSED ✅" if passed == len(targets) else "TESTS FAILED ❌")


if __name__ == "__main__":
    main()
```

It did **worse**. The model invented the same phantom `price` column and gave up after a few lines:

**`generated_from_tests.py`** (the 0.5B output)

```python
import pandas as pd

def process_calculations(csv_path):
    # Read the CSV file into a DataFrame
    df = pd.read_csv(csv_path)

    # Define the calculation rules
    def calculate_total_receivables(row):
        # Calculate the total receivables
        total_receivables = row['volume'] * row['price']
        return total_receivables

    # Apply the calculation rules to each row
    result = df.apply(calculate_total_receivables, axis=1)

    return result.tolist()
```

**Lesson one:** reverse-engineering a multi-rule formula from examples is *harder* for a small model than transcribing a spec, not easier. A single shot — from spec or from examples — is a dead end at this complexity.

---

## Part 2 — A feedback loop, and the bigger models

A single shot is unfair. Real engineering is iterative. So I built a **generate → score → repair** harness: the model writes the function, the harness runs it against every test row, and on failure it feeds the **specific failing rows back** ("row B: you predicted 765000, the answer is 810000") and asks the model to fix its own code — up to a few iterations, keeping the best-scoring version. I pointed it at the 3B and 7B models, the largest that fit in 8 GB.

**The harness — `solve_local.py`**

```python
"""
Local-LLM solution tuned for an 8 GB M1 Mac.

Key idea: a small model will NOT one-shot this. So we run an iterative
generate -> score -> repair loop against the ground-truth test cases:

  1. Give the model the written spec and ask for `process_calculations`.
  2. Run the generated code against every row of test-cases.csv.
  3. If any row fails, feed the failing rows (predicted vs target) back to the
     model and ask it to FIX its previous code.
  4. Repeat up to MAX_ITERS, keeping the best-scoring version.

Everything stays in this folder (model cached in ./model_cache).

Run:  python3 solve_local.py

MODEL SIZING for 8 GB RAM (unified memory):
  - 7B 4-bit (~4.3 GB resident): best quality that still fits; expect some swap.
  - 3B 4-bit (~1.8 GB): safe + faster, lower quality. Use if 7B thrashes.
Switch by editing MODEL below.
"""

import os
import re
import csv
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
os.environ["HF_HOME"] = str(PROJECT_DIR / "model_cache")
os.environ["HF_HUB_CACHE"] = str(PROJECT_DIR / "model_cache")

from mlx_lm import load, generate  # noqa: E402

# --- Pick ONE. 7B is the max that fits 8 GB; 3B is the safe fallback. -------
MODEL = "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit"
# MODEL = "mlx-community/Qwen2.5-Coder-3B-Instruct-4bit"

TEST_CSV = PROJECT_DIR / "test-cases.csv"
TARGET_COL = "Total_receivables"
TOLERANCE = 0.5          # abs tolerance on total_receivables (targets ~1e5-1e6)
MAX_ITERS = 5            # generate + up-to-(MAX_ITERS-1) repair passes
MAX_TOKENS = 3000

SPEC = r"""
The CSV input columns (names may have extra spaces; cells may be empty) are:
customer name, productid (1/2/3), season (spring/summer/winter/autumn),
volume (int), region (EMEA/non-EMEA), customer (strategic/non-strategic),
status (individual/corporate, case-insensitive), payment type (ach/wire or
credit-card), quarter (Q1-Q4), transaction type (domestic/international/
cross-border), product category (electronics/groceries/luxury),
seller years (int), processing speed (same-day/next-day/standard),
referral active (True/False), referral invoices remaining (int),
tax verified (bool, may be empty), is high risk (bool), requires correction (bool),
individual rate (number), corporate rate (number).

PRODUCT_RATES = {1:{"individual":1000,"corporate":900},
                 2:{"individual":1500,"corporate":1200},
                 3:{"individual":2000,"corporate":1700}}

Per row, compute (use the row's individual/corporate rate columns, selected by status):
- receivable_before_discount = volume * rate(status)
- Rule A discount: spring => 5% of receivable_before_discount
- Rule B volume_discount: volume<100 => 0%, <1000 => 5%, >=1000 => 10%
- Rule C category_discount: strategic customer => 5%
- Rule I loyalty: seller years>=5 => 15% (Platinum), >=2 => 10% (Gold), else 0%
- total_discounts = sum of A+B+C+I amounts (each = its % of receivable_before_discount)
- receivable_after_discount = receivable_before_discount - total_discounts
All loadings are computed on receivable_after_discount:
- Rule E region_loading: EMEA => +10%
- Rule F payment_method_loading: credit-card => +2.5%
- Rule G seasonal_pricing_tier_loading: Q1 => +2%, Q4 => -1%, else 0%
- Rule H geographic_zone_loading: domestic 5%, international 8%, cross-border 10%
- Rule L processing_speed_premium: same-day +15%, next-day +10%, standard 0%
- base_commission_total = region + payment + seasonal + geographic + processing speed loadings
- Rule J product_category_multiplier: electronics 1.2, groceries 0.8, luxury 1.5
- adjusted_commission_total = base_commission_total * product_category_multiplier
- Rule N referral credit: if referral active and invoices remaining>0, add 0.25% of adjusted_commission_total
- Rule P risk fee: if high risk, subtract 1.5% of adjusted_commission_total
- Rule Q correction_fee: requires correction => flat $5
- Rule O tax withholding: if tax NOT verified => 3% withholding on the pre-withholding total
- total_receivables = receivable_after_discount + adjusted_commission_total
                      + correction_fee - tax_withholding_amount

Return a list of dicts (one per row). Each dict MUST contain key 'total_receivables'.
"""

INITIAL_INSTRUCTION = (
    "Write a Python function `process_calculations(csv_path)` implementing the "
    "rules below. Strip spaces from CSV headers; treat empty cells as defaults; "
    "do not crash on empty values. Convert numeric strings to numbers. "
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


def write_inputs_csv(input_cols, rows, path: Path) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=input_cols)
        writer.writeheader()
        writer.writerows(rows)


def extract_code(text: str) -> str:
    match = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    return (match.group(1) if match else text).strip()


def score(code: str, inputs_csv: Path, rows, targets):
    """Return (passed, total, report_lines, error_or_None)."""
    namespace: dict = {}
    try:
        exec(code, namespace)  # noqa: S102 - intentional: running model output
        fn = namespace["process_calculations"]
    except Exception as e:
        return 0, len(targets), [], f"code did not load/define process_calculations: {e}"
    try:
        result = fn(str(inputs_csv))
    except Exception as e:
        return 0, len(targets), [], f"process_calculations raised: {e}"
    if not isinstance(result, list) or len(result) != len(targets):
        return 0, len(targets), [], (
            f"expected list of {len(targets)} dicts, got "
            f"{type(result).__name__} len {len(result) if hasattr(result,'__len__') else 'n/a'}")

    passed, lines = 0, []
    for i, (pred_row, target) in enumerate(zip(result, targets)):
        label = rows[i].get("customer name", str(i))
        try:
            pred = float(pred_row["total_receivables"])
        except Exception as e:
            lines.append(f"  row {label}: bad/missing total_receivables ({e}); target={target}")
            continue
        if abs(pred - target) <= TOLERANCE:
            passed += 1
        else:
            lines.append(f"  row {label}: got {pred:.4f}, expected {target:.4f}")
    return passed, len(targets), lines, None


def build_repair_prompt(prev_code, passed, total, report_lines, err):
    if err:
        problem = f"Your previous code did not run: {err}"
    else:
        problem = (f"Your previous code passed {passed}/{total} rows. "
                   f"These rows are wrong:\n" + "\n".join(report_lines))
    return (
        "Your previous attempt:\n```python\n" + prev_code + "\n```\n\n"
        + problem + "\n\nFix the code so EVERY row's total_receivables matches the "
        "target. Re-check the rule order and which rules add vs subtract. "
        "Respond with ONLY the corrected full function in a single ```python block.\n\n"
        + SPEC
    )


def ask(model, tokenizer, content):
    messages = [{"role": "user", "content": content}]
    prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True)
    return generate(model, tokenizer, prompt=prompt, max_tokens=MAX_TOKENS, verbose=False)


def main() -> None:
    input_cols, rows, targets = load_test_rows()
    inputs_csv = PROJECT_DIR / "inputs_only.csv"
    write_inputs_csv(input_cols, rows, inputs_csv)
    print(f"Loaded {len(rows)} test cases. Target: {TARGET_COL}\n")

    print(f"Loading {MODEL} ...\n(cached in {os.environ['HF_HUB_CACHE']})\n")
    model, tokenizer = load(MODEL)

    best = (-1, "")  # (passed, code)
    content = INITIAL_INSTRUCTION
    for it in range(1, MAX_ITERS + 1):
        print("=" * 60)
        print(f"ITERATION {it}/{MAX_ITERS}  (generating...)")
        print("=" * 60)
        out = ask(model, tokenizer, content)
        code = extract_code(out)
        passed, total, report, err = score(code, inputs_csv, rows, targets)

        if err:
            print(f"  ERROR: {err}")
        else:
            print(f"  PASSED {passed}/{total}")
            for line in report[:8]:
                print(line)
            if len(report) > 8:
                print(f"  ... and {len(report) - 8} more failing rows")

        if passed > best[0]:
            best = (passed, code)
        if passed == total:
            print("\nALL TEST CASES PASSED ✅")
            break
        content = build_repair_prompt(code, passed, total, report, err)
    else:
        print(f"\nStopped after {MAX_ITERS} iterations.")

    best_passed, best_code = best
    out_path = PROJECT_DIR / "solution_best.py"
    out_path.write_text(best_code + "\n")
    print("\n" + "-" * 60)
    print(f"Best result: {best_passed}/{len(targets)} passed.")
    print(f"Best code written to: {out_path.name}")
    print("ALL TESTS PASSED ✅" if best_passed == len(targets)
          else "Did not fully converge ❌ (see solution_best.py)")


if __name__ == "__main__":
    main()
```

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

And the 7B's most complete attempt — structurally rich, every rule attempted, but wrong. This is `solution_best.py` from the 17-rule run:

```python
import csv
import re

PRODUCT_RATES = {1: {"individual": 1000, "corporate": 900},
                 2: {"individual": 1500, "corporate": 1200},
                 3: {"individual": 2000, "corporate": 1700}}

def process_calculations(csv_path):
    with open(csv_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        headers = {re.sub(r'\s+', '', header): header for header in reader.fieldnames}
        results = []
        for row in reader:
            row = {headers[key]: value.strip() for key, value in row.items()}
            if not row:
                continue
            volume = int(row.get('volume', 0))
            rate = PRODUCT_RATES[int(row.get('productid', 1))][row.get('status', 'individual').lower()]
            receivable_before_discount = volume * rate
            discounts = {
                'A': 0.05 * receivable_before_discount if row.get('season', '').lower() == 'spring' else 0,
                'B': 0.05 * receivable_before_discount if volume < 100 else 0.1 * receivable_before_discount if volume < 1000 else 0.15 * receivable_before_discount,
                'C': 0.05 * receivable_before_discount if row.get('customer', '').lower() == 'strategic' else 0,
                'I': 0.15 * receivable_before_discount if int(row.get('seller years', 0)) >= 5 else 0.1 * receivable_before_discount if int(row.get('seller years', 0)) >= 2 else 0
            }
            total_discounts = sum(discounts.values())
            receivable_after_discount = receivable_before_discount - total_discounts
            loadings = {
                'E': 0.1 * receivable_after_discount if row.get('region', '').lower() == 'emea' else 0,
                'F': 0.025 * receivable_after_discount if row.get('payment type', '').lower() == 'credit-card' else 0,
                'G': 0.02 * receivable_after_discount if row.get('quarter', '').lower() == 'q1' else -0.01 * receivable_after_discount if row.get('quarter', '').lower() == 'q4' else 0,
                'H': 0.05 * receivable_after_discount if row.get('transaction type', '').lower() == 'domestic' else 0.08 * receivable_after_discount if row.get('transaction type', '').lower() == 'international' else 0.1 * receivable_after_discount,
                'L': 0.15 * receivable_after_discount if row.get('processing speed', '').lower() == 'same-day' else 0.1 * receivable_after_discount if row.get('processing speed', '').lower() == 'next-day' else 0
            }
            base_commission_total = sum(loadings.values())
            adjusted_commission_total = base_commission_total * {
                'electronics': 1.2,
                'groceries': 0.8,
                'luxury': 1.5
            }.get(row.get('product category', '').lower(), 1)
            referral_credit = 0.0025 * adjusted_commission_total if row.get('referral active', 'false').lower() == 'true' and int(row.get('referral invoices remaining', 0)) > 0 else 0
            risk_fee = -0.015 * adjusted_commission_total if row.get('is high risk', 'false').lower() == 'true' else 0
            correction_fee = 5 if row.get('requires correction', 'false').lower() == 'true' else 0
            tax_withholding_amount = 0.03 * (receivable_after_discount + base_commission_total + adjusted_commission_total + correction_fee - referral_credit - risk_fee) if row.get('tax verified', 'false').lower() == 'false' else 0
            total_receivables = receivable_after_discount + base_commission_total + adjusted_commission_total + correction_fee - referral_credit - risk_fee - tax_withholding_amount
            results.append({'total_receivables': total_receivables})
        return results
```

**The repair loop barely helped.** Telling a small model "you got 81,000, expected 86,045" does not tell it *which line* is wrong. It just regenerates the same bug, confidently. The feedback signal — a numeric diff on the final total — is too far removed from the cause (a header dict, a tier boundary) for a small model to localize.

---

## Part 3 — The plot twist: the specification was wrong

To score anything I needed ground truth, and I couldn't get it from the prose spec, because the prose spec **contradicted itself**. So I reverse-engineered the exact formula by hand, fitting it against all 19 targets until it reproduced every one to the cent. In doing so I discovered:

- The high-risk fee (Rule P) and the $5 correction fee (Rule Q) — which the prose said to fold into `total_receivables` — are actually **excluded** from it. (Including them overshoots row C, the one row with all three flags on.)
- An **empty** `tax verified` cell does not mean "verified"; it secretly means "not verified," which triggers 3% withholding. Every row in the file has an empty `tax verified`.
- The referral credit (Rule N) lives *inside* the commission, as a multiplier, not as an added line.

The data was the real source of truth; the document was fiction in places. Here is the hand-derived reference that scores **19/19, exact, instantly, no model required** — the thing you'd actually ship.

**`reference_solution.py`**

```python
"""
Hand-derived reference implementation of process_calculations, reverse-engineered
from test-cases.csv (ground truth) rather than the contradictory prose spec.

Key findings from fitting against the 19 targets:
  - total_receivables = (receivable_after_discount + adjusted_commission_total)
                        * (1 - tax_withholding_rate)
  - adjusted_commission_total = base_commission_total * category_multiplier
                                * (1 + referral_credit_rate)
  - referral credit (Rule N) is INSIDE the commission (0.25% when active).
  - high-risk fee (Rule P) and correction fee (Rule Q) do NOT enter total_receivables
    (adding them overshoots row C, which has all three flags on).
  - an EMPTY 'tax verified' cell counts as NOT verified -> 3% withholding.
"""

import csv


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
            ind_rate = _num(row.get("individual rate"))
            corp_rate = _num(row.get("corporate rate"))
            rate = ind_rate if status == "individual" else corp_rate

            receivable_before_discount = volume * rate

            # Discounts (% of receivable_before_discount)
            disc_a = 0.05 if row.get("season", "").lower() == "spring" else 0.0
            if volume < 100:
                disc_b = 0.0
            elif volume < 1000:
                disc_b = 0.05
            else:
                disc_b = 0.10
            disc_c = 0.05 if row.get("customer", "").lower() == "strategic" else 0.0
            years = _num(row.get("seller years"))
            if years >= 5:
                disc_i = 0.15
            elif years >= 2:
                disc_i = 0.10
            else:
                disc_i = 0.0
            total_discounts = receivable_before_discount * (disc_a + disc_b + disc_c + disc_i)
            receivable_after_discount = receivable_before_discount - total_discounts

            # Loadings on receivable_after_discount
            rad = receivable_after_discount
            region_loading = 0.10 * rad if row.get("region", "").upper() == "EMEA" else 0.0
            payment_loading = 0.025 * rad if row.get("payment type", "").lower() == "credit-card" else 0.0
            q = row.get("quarter", "").upper()
            seasonal_loading = (0.02 * rad if q == "Q1" else -0.01 * rad if q == "Q4" else 0.0)
            tx = row.get("transaction type", "").lower()
            geo_rate = {"domestic": 0.05, "international": 0.08, "cross-border": 0.10}.get(tx, 0.0)
            geo_loading = geo_rate * rad
            speed = row.get("processing speed", "").lower()
            speed_rate = {"same-day": 0.15, "next-day": 0.10, "standard": 0.0}.get(speed, 0.0)
            speed_loading = speed_rate * rad

            base_commission_total = (region_loading + payment_loading + seasonal_loading
                                     + geo_loading + speed_loading)

            cat = row.get("product category", "").lower()
            multiplier = {"electronics": 1.2, "groceries": 0.8, "luxury": 1.5}.get(cat, 1.0)

            # Referral credit (Rule N) folds into the commission
            referral_on = _truthy(row.get("referral active")) and _num(row.get("referral invoices remaining")) > 0
            referral_rate = 0.0025 if referral_on else 0.0

            adjusted_commission_total = base_commission_total * multiplier * (1 + referral_rate)

            # Tax withholding (Rule O): empty 'tax verified' => not verified => 3%
            tax_verified = _truthy(row.get("tax verified"))
            withholding_rate = 0.0 if tax_verified else 0.03

            pre_withholding = receivable_after_discount + adjusted_commission_total
            tax_withholding_amount = pre_withholding * withholding_rate
            total_receivables = pre_withholding - tax_withholding_amount

            # Escrow (Rule M): 1% of gross invoice, tracked separately
            escrow = 0.01 * receivable_before_discount

            results.append({
                "receivable_before_discount": receivable_before_discount,
                "total_discounts": total_discounts,
                "receivable_after_discount": receivable_after_discount,
                "base_commission_total": base_commission_total,
                "product_category_multiplier": multiplier,
                "adjusted_commission_total": adjusted_commission_total,
                "tax_withholding_amount": tax_withholding_amount,
                "total_receivables": total_receivables,
                "escrow": escrow,
            })
    return results


if __name__ == "__main__":
    # Self-check against the ground-truth targets in test-cases.csv
    from pathlib import Path
    HERE = Path(__file__).resolve().parent
    TEST = HERE / "test-cases.csv"

    targets = []
    with TEST.open(newline="") as f:
        for r in csv.DictReader(f):
            targets.append(float(r["Total_receivables"]))

    # build inputs-only csv on the fly
    with TEST.open(newline="") as f:
        rows = list(csv.DictReader(f))
        cols = [c for c in (rows[0].keys()) if c.strip() != "Total_receivables"]
    tmp = HERE / "_ref_inputs.csv"
    with tmp.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r[c] for c in cols})

    out = process_calculations(str(tmp))
    passed = 0
    print(f"{'row':>4} {'predicted':>16} {'target':>16} {'abs err':>12}")
    for i, (o, t) in enumerate(zip(out, targets)):
        label = rows[i].get("customer name", str(i))
        pred = o["total_receivables"]
        err = abs(pred - t)
        ok = err <= 0.5
        passed += ok
        print(f"{label:>4} {pred:>16.4f} {t:>16.4f} {err:>12.4f}  {'PASS' if ok else 'FAIL'}")
    tmp.unlink()
    print(f"\n{passed}/{len(targets)} passed")
```

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

experiment-17-rules/
  test-cases.csv              # 19 labelled rows (ground truth)
  generate_calculations.py    # 0.5B single-shot vs the spec
  generate_from_tests.py      # 0.5B single-shot vs the examples
  solve_local.py              # generate -> score -> repair loop (3B / 7B)
  reference_solution.py       # hand-derived, 19/19 ✅

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

# 1) The 17-rule task.
cd ../experiment-17-rules
python3 reference_solution.py    # ground truth: self-checks 19/19 against test-cases.csv
python3 generate_calculations.py # 0.5B vs the spec (expect a crash / partial logic)
python3 generate_from_tests.py   # 0.5B vs the examples (expect worse)
python3 solve_local.py           # the repair loop; edit MODEL inside for 3B vs 7B

# 2) The 10-rule task.
cd ../experiment-10-rules
python3 reference_simple.py      # regenerate test-cases.csv + self-check (12/12)
python3 solve_simple.py          # the loop; edit MODEL inside (3B ~3/12, 7B ~1/12)

# 3) The 5-rule task — the one that works.
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
