"""
Out-of-box experiment 2 — RULE-BY-RULE COMPILER: decompose the monolith.

The ladder showed the 3B can't *assemble* a 27-rule pipeline from prose. So don't ask it to.
Ask it for ~two dozen tiny PURE functions (one rule each), unit-test every function against
the reference and resample until it passes, then let a FIXED assembler (our code) wire them
into `process_calculations` in the correct order. This isolates the question: with assembly
handled deterministically, is per-rule generation reliable?

Run (from repo root):
    .venv/bin/python experiments/30-rule/compiler.py --retries 4
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

from solve_30 import extract_code, load_test_rows, write_inputs_csv, score, MODEL  # noqa: E402

OUT_DIR = PROJECT_DIR / "outofbox"
CAPS = {"karachi", "lahore", "islamabad", "peshawar", "quetta"}

# Reference implementations (the correct atomic behavior) — used ONLY to unit-test the
# model's version of each function, never handed to the model.
def _r_product_rate(pid, status):
    return {"1": {"individual": 1000, "corporate": 900}, "2": {"individual": 1500, "corporate": 1200},
            "3": {"individual": 2000, "corporate": 1700}}.get(pid, {}).get(status, 0)
def _r_spring(s): return 0.05 if s == "spring" else 0.0
def _r_volume(v): return (0.05 if v >= 100 else 0.0) + (0.05 if v >= 1000 else 0.0)
def _r_strategic(c): return 0.05 if c == "strategic" else 0.0
def _r_loystatus(y): return "platinum" if y >= 5 else ("gold" if y >= 2 else "none")
def _r_loyrate(y): return 0.15 if y >= 5 else (0.10 if y >= 2 else 0.0)
def _r_region(r): return 0.10 if r == "emea" else 0.0
def _r_payment(p): return 0.025 if p == "credit-card" else 0.0
def _r_quarter(q): return 0.02 if q == "Q1" else (-0.01 if q == "Q4" else 0.0)
def _r_zone(t): return {"domestic": 0.05, "international": 0.08, "cross-border": 0.10}.get(t, 0.0)
def _r_speed(s): return {"same-day": 0.15, "next-day": 0.10, "standard": 0.0}.get(s, 0.0)
def _r_catmult(c): return {"electronics": 1.2, "groceries": 0.8, "luxury": 1.5}.get(c, 1.0)
def _r_risk(h): return 0.015 if h == "yes" else 0.0
def _r_referral(a, n): return 0.0025 if (a == "yes" and n > 0) else 0.0
def _r_correction(rc): return 5.0 if rc == "yes" else 0.0
def _r_minfee(x): return 2.50 if x < 50 else 0.0
def _r_withhold(tv): return 0.0 if tv == "yes" else 0.03
def _r_capital(city): return 0.10 if city in CAPS else 0.0
def _r_senior(s): return 0.02 if s == "yes" else 0.0
def _r_first(f): return 0.05 if f == "yes" else 0.0
def _r_luxury(c): return 0.04 if c == "luxury" else 0.0
def _r_heavy(w): return 0.03 if w > 20 else 0.0
def _r_accel(cust, ls, vol, corr): return 0.07 if (cust == "strategic" and ls == "platinum" and vol >= 1000 and corr == 0.0) else 0.0
def _r_bundle(season, cat, speed): return 0.06 if (season == "spring" and cat == "luxury" and speed == "same-day") else 0.0
def _r_corpinc(status, city, pay, tv): return 0.04 if (status == "corporate" and city in CAPS and pay != "credit-card" and tv == "yes") else 0.0
def _r_global(txn, cust, first, vol): return 0.08 if (txn == "international" and cust == "strategic" and first != "yes" and vol > 5000) else 0.0
def _r_elite(ls, ref, hr, tv): return 0.05 if (ls == "platinum" and ref == "yes" and hr != "yes" and tv == "yes") else 0.0
def _r_escrow(rbd): return 0.01 * rbd

# name -> (signature, micro-spec, ref_fn, test_arg_tuples)
FUNCS = [
    ("product_rate", "product_rate(productid, status)",
     'productid is the text "1","2","3"; status is "individual" or "corporate". Return the '
     'unit rate from this table: product "1" is 1000 for individual and 900 for corporate; '
     'product "2" is 1500 for individual and 1200 for corporate; product "3" is 2000 for '
     'individual and 1700 for corporate.', _r_product_rate,
     [("1", "individual"), ("1", "corporate"), ("2", "individual"), ("3", "corporate")]),
    ("spring_rate", "spring_rate(season)",
     'Return 0.05 if season == "spring", else 0.0.', _r_spring,
     [("spring",), ("summer",), ("winter",)]),
    ("volume_rate", "volume_rate(volume)",
     "Return 0.0 if volume < 100, 0.05 if 100 <= volume < 1000, 0.10 if volume >= 1000.",
     _r_volume, [(0,), (99,), (100,), (999,), (1000,), (5000,)]),
    ("strategic_rate", "strategic_rate(customer)",
     'Return 0.05 if customer == "strategic", else 0.0.', _r_strategic,
     [("strategic",), ("non-strategic",)]),
    ("loyalty_status", "loyalty_status(seller_years)",
     'Return "platinum" if seller_years >= 5, "gold" if seller_years >= 2, else "none".',
     _r_loystatus, [(0,), (1,), (2,), (4,), (5,), (10,)]),
    ("loyalty_rate", "loyalty_rate(seller_years)",
     "Return 0.15 if seller_years >= 5, 0.10 if seller_years >= 2, else 0.0.", _r_loyrate,
     [(0,), (2,), (4,), (5,), (8,)]),
    ("region_loading_rate", "region_loading_rate(region)",
     'Return 0.10 if region == "emea", else 0.0.', _r_region, [("emea",), ("non-emea",)]),
    ("payment_loading_rate", "payment_loading_rate(payment_type)",
     'Return 0.025 if payment_type == "credit-card", else 0.0.', _r_payment,
     [("credit-card",), ("ach/wire",)]),
    ("quarter_loading_rate", "quarter_loading_rate(quarter)",
     'quarter is upper-case. Return 0.02 if quarter == "Q1", -0.01 if quarter == "Q4", else 0.0.',
     _r_quarter, [("Q1",), ("Q2",), ("Q3",), ("Q4",)]),
    ("zone_loading_rate", "zone_loading_rate(transaction_type)",
     "Return 0.05 for domestic, 0.08 for international, 0.10 for cross-border, else 0.0.",
     _r_zone, [("domestic",), ("international",), ("cross-border",)]),
    ("speed_loading_rate", "speed_loading_rate(processing_speed)",
     "Return 0.15 for same-day, 0.10 for next-day, 0.0 for standard.", _r_speed,
     [("same-day",), ("next-day",), ("standard",)]),
    ("category_multiplier", "category_multiplier(category)",
     "Return 1.2 for electronics, 0.8 for groceries, 1.5 for luxury, else 1.0.", _r_catmult,
     [("electronics",), ("groceries",), ("luxury",)]),
    ("risk_fee_rate", "risk_fee_rate(is_high_risk)",
     'is_high_risk is "yes"/"no". Return 0.015 if it is "yes", else 0.0.', _r_risk,
     [("yes",), ("no",)]),
    ("referral_credit_rate", "referral_credit_rate(referral_active, remaining)",
     'Return 0.0025 if referral_active == "yes" AND remaining > 0, else 0.0.', _r_referral,
     [("yes", 5), ("yes", 0), ("no", 5), ("no", 0)]),
    ("correction_fee", "correction_fee(requires_correction)",
     'Return 5.0 if requires_correction == "yes", else 0.0.', _r_correction,
     [("yes",), ("no",)]),
    ("min_fee", "min_fee(base_amount)",
     "Return 2.50 if base_amount < 50, else 0.0.", _r_minfee, [(0,), (49,), (50,), (1000,)]),
    ("withholding_rate", "withholding_rate(tax_verified)",
     'tax_verified is "yes"/"no"/empty. Return 0.0 if it is "yes", else 0.03.', _r_withhold,
     [("yes",), ("no",), ("",)]),
    ("capital_city_rate", "capital_city_rate(city)",
     "Return 0.10 if city is one of karachi, lahore, islamabad, peshawar, quetta, else 0.0.",
     _r_capital, [("karachi",), ("quetta",), ("multan",), ("hyderabad",)]),
    ("senior_rate", "senior_rate(senior_citizen)",
     'Return 0.02 if senior_citizen == "yes", else 0.0.', _r_senior, [("yes",), ("no",)]),
    ("first_order_rate", "first_order_rate(first_order)",
     'Return 0.05 if first_order == "yes", else 0.0.', _r_first, [("yes",), ("no",)]),
    ("luxury_tax_rate", "luxury_tax_rate(category)",
     'Return 0.04 if category == "luxury", else 0.0.', _r_luxury,
     [("luxury",), ("groceries",), ("electronics",)]),
    ("heavy_weight_rate", "heavy_weight_rate(weight)",
     "Return 0.03 if weight > 20, else 0.0.", _r_heavy, [(1,), (20,), (21,), (32,)]),
    ("accelerator_rate", "accelerator_rate(customer, loyalty_status, volume, correction_fee)",
     'Return 0.07 if customer == "strategic" AND loyalty_status == "platinum" AND volume >= '
     "1000 AND correction_fee == 0.0, else 0.0.", _r_accel,
     [("strategic", "platinum", 1000, 0.0), ("strategic", "platinum", 1000, 5.0),
      ("strategic", "gold", 1000, 0.0), ("non-strategic", "platinum", 1000, 0.0),
      ("strategic", "platinum", 999, 0.0)]),
    ("bundle_rate", "bundle_rate(season, category, processing_speed)",
     'Return 0.06 if season == "spring" AND category == "luxury" AND processing_speed == '
     '"same-day", else 0.0.', _r_bundle,
     [("spring", "luxury", "same-day"), ("spring", "luxury", "next-day"),
      ("summer", "luxury", "same-day")]),
    ("corp_incentive_rate", "corp_incentive_rate(status, city, payment_type, tax_verified)",
     'Return 0.04 if status == "corporate" AND city is a capital city (karachi, lahore, '
     'islamabad, peshawar, quetta) AND payment_type != "credit-card" AND tax_verified == '
     '"yes", else 0.0.', _r_corpinc,
     [("corporate", "karachi", "ach/wire", "yes"), ("corporate", "karachi", "credit-card", "yes"),
      ("individual", "karachi", "ach/wire", "yes"), ("corporate", "multan", "ach/wire", "yes"),
      ("corporate", "karachi", "ach/wire", "no")]),
    ("global_expansion_rate", "global_expansion_rate(transaction_type, customer, first_order, volume)",
     'Return 0.08 if transaction_type == "international" AND customer == "strategic" AND '
     'first_order != "yes" AND volume > 5000, else 0.0.', _r_global,
     [("international", "strategic", "no", 6000), ("international", "strategic", "yes", 6000),
      ("domestic", "strategic", "no", 6000), ("international", "strategic", "no", 5000)]),
    ("elite_rate", "elite_rate(loyalty_status, referral_active, is_high_risk, tax_verified)",
     'Return 0.05 if loyalty_status == "platinum" AND referral_active == "yes" AND '
     'is_high_risk != "yes" AND tax_verified == "yes", else 0.0.', _r_elite,
     [("platinum", "yes", "no", "yes"), ("platinum", "yes", "yes", "yes"),
      ("gold", "yes", "no", "yes"), ("platinum", "no", "no", "yes")]),
    ("escrow_amount", "escrow_amount(receivable_before_discount)",
     "Return 0.01 * receivable_before_discount.", _r_escrow, [(0,), (90000,), (2148000,)]),
]

# Fixed assembler (OUR code): normalizes the row and wires the model's functions in order.
ASSEMBLER = '''

def process_calculations(csv_path):
    import csv as _csv
    results = []
    with open(csv_path, newline="") as f:
        for raw in _csv.DictReader(f):
            r = {(k.strip() if k else k): (v.strip() if isinstance(v, str) else v) for k, v in raw.items()}
            def t(k): return str(r.get(k, "")).strip()
            def tl(k): return t(k).lower()
            def num(k):
                try: return float(t(k))
                except Exception: return 0.0
            pid = t("productid"); status = tl("status"); customer = tl("customer")
            season = tl("season"); category = tl("product category"); city = tl("city")
            region = tl("region"); pay = tl("payment type"); txn = tl("transaction type")
            speed = tl("processing speed"); quarter = t("quarter").upper()
            volume = num("volume"); years = num("seller years"); weight = num("weight")
            remaining = num("referral invoices remaining")
            hr = tl("is high risk"); corr_flag = tl("requires correction")
            ref = tl("referral active"); senior = tl("senior citizen")
            first = tl("first order"); tax = tl("tax verified")

            rate = product_rate(pid, status)
            rbd = volume * rate
            disc = spring_rate(season) + volume_rate(volume) + strategic_rate(customer) + loyalty_rate(years)
            rad = rbd * (1 - disc)
            base = (region_loading_rate(region) + payment_loading_rate(pay)
                    + quarter_loading_rate(quarter) + zone_loading_rate(txn)
                    + speed_loading_rate(speed)) * rad
            adj = base * category_multiplier(category)
            adj *= (1 - risk_fee_rate(hr))
            adj *= (1 + referral_credit_rate(ref, remaining))
            corr = correction_fee(corr_flag)
            mf = min_fee(rad + adj)
            pre = rad + adj + corr + mf
            total = pre - withholding_rate(tax) * pre
            ls = loyalty_status(years)
            total *= (1 - capital_city_rate(city))
            total *= (1 - senior_rate(senior))
            total *= (1 - first_order_rate(first))
            total *= (1 - luxury_tax_rate(category))
            total *= (1 - heavy_weight_rate(weight))
            total *= (1 - accelerator_rate(customer, ls, volume, corr))
            total *= (1 - bundle_rate(season, category, speed))
            total *= (1 - corp_incentive_rate(status, city, pay, tax))
            total *= (1 - global_expansion_rate(txn, customer, first, volume))
            total *= (1 - elite_rate(ls, ref, hr, tax))
            results.append({"total_receivables": total, "escrow": escrow_amount(rbd)})
    return results
'''

PROMPT = ("Implement exactly this one Python function. Respond with ONLY the function "
          "definition in a single ```python block, no explanation.\n\n"
          "def {sig}:\n    \"\"\"{spec}\"\"\"\n")


def unit_test(fn, ref, tests):
    for args in tests:
        try:
            got, exp = fn(*args), ref(*args)
        except Exception as e:
            return False, f"raised on {args}: {e}"
        ok = (abs(got - exp) <= 1e-9 if isinstance(exp, (int, float)) else got == exp)
        if not ok:
            return False, f"{args} -> {got!r}, expected {exp!r}"
    return True, "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--retries", type=int, default=4, help="resample attempts per function.")
    ap.add_argument("--model", type=str, default=MODEL)
    args = ap.parse_args()
    OUT_DIR.mkdir(exist_ok=True)

    from mlx_lm import load, generate
    from mlx_lm.sample_utils import make_sampler
    print(f"Loading {args.model} ...\n")
    model, tok = load(args.model)
    greedy = make_sampler(temp=0.0)
    warm = make_sampler(temp=0.5, top_p=0.9)

    accepted, report = {}, []
    for name, sig, spec, ref, tests in FUNCS:
        prompt_text = PROMPT.format(sig=sig, spec=spec)
        status = "FAIL"; tries = 0; note = ""
        for attempt in range(args.retries):
            tries = attempt + 1
            sampler = greedy if attempt == 0 else warm
            p = tok.apply_chat_template([{"role": "user", "content": prompt_text}],
                                        add_generation_prompt=True)
            code = extract_code(generate(model, tok, prompt=p, max_tokens=400,
                                         sampler=sampler, verbose=False))
            ns = {}
            try:
                exec(code, ns)  # noqa: S102
                fn = ns[name]
            except Exception as e:
                note = f"exec/def error: {e}"
                continue
            ok, note = unit_test(fn, ref, tests)
            if ok:
                accepted[name] = code
                status = "OK"
                break
        print(f"  {name:<24} {status} (try {tries})" + (f"  [{note}]" if status == "FAIL" else ""))
        report.append({"function": name, "status": status, "tries": tries, "note": note})

    n_ok = sum(1 for r in report if r["status"] == "OK")
    print(f"\nfunctions passing their unit test: {n_ok}/{len(FUNCS)}")

    # Assemble whatever we have; missing functions fall back to the reference so the pipeline
    # still runs and we can see the ceiling. (Report separates model-passed vs fallback.)
    parts = [f"CAPS = {CAPS!r}"]  # needed by any reference fallback that closes over CAPS
    fallback = []
    for name, sig, spec, ref, tests in FUNCS:
        if name in accepted:
            parts.append(accepted[name])
        else:
            fallback.append(name)
            # deterministic reference fallback via a thin wrapper around the ref logic
            import inspect
            src = inspect.getsource(ref).replace(f"def _r_", "def _fallback_")
            wrapper_name = re.search(r"def (\w+)\(", src).group(1)
            parts.append(src + f"\n{sig.split('(')[0]} = {wrapper_name}\n")

    assembled = "\n\n".join(parts) + "\n" + ASSEMBLER
    (OUT_DIR / "compiler_solution.py").write_text(assembled)

    input_cols, rows, targets, escrows = load_test_rows()
    inputs_csv = OUT_DIR / "_inputs_only_compiler.csv"
    write_inputs_csv(input_cols, rows, inputs_csv)
    passed, lines, err = score(assembled, inputs_csv, targets, escrows)
    print(f"\nassembled program score: {passed}/{len(targets)}" + (f"  ERR {err}" if err else ""))
    if fallback:
        print(f"(used reference fallback for {len(fallback)} model-failed function(s): {fallback})")
    for ln in lines[:8]:
        print(ln)

    result = {"functions_total": len(FUNCS), "functions_model_ok": n_ok,
              "model_failed": fallback, "assembled_score": passed, "total": len(targets),
              "retries": args.retries, "report": report}
    (OUT_DIR / "compiler_result.json").write_text(json.dumps(result, indent=2))
    print(f"\nwritten to {OUT_DIR.relative_to(PROJECT_DIR)}/compiler_result.json")


if __name__ == "__main__":
    main()
