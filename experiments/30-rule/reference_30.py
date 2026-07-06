"""
Ground-truth reference for the 30-rule pricing/commission spec (rules A–V, X, Y, Z, AA, AB).

This module IS the correct method. It implements every rule straight from the prose in
`requirements-source.md`, resolving the prose's ambiguities with the documented judgment
calls in `docs/superpowers/specs/2026-07-06-30-rule-experiment-design.md`. Its output is the
ground truth the experiment scores against.

Validation: the pre-cascade total (`pre_cascade_total`) reproduces Fahad's `total Receivable`
column exactly on all 19 original rows (see FAHAD_PRECASCADE). Fahad's *post*-cascade
"total receiveables after" column is NOT used — it is demonstrably incomplete (e.g. row I
records a 7% Rule-X discount in its own column but never applies it to the after-total), so
the R–AB cascade is computed here strictly from the prose.

Running this module:
  1. writes test-cases-30.csv (input columns + Total_receivables + Escrow targets),
  2. self-checks process_calculations reproduces those targets,
  3. cross-checks the pre-cascade total against Fahad's column.
"""

import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ---- Lookup tables (verbatim from the prose) -----------------------------------------
PRODUCT_RATES = {
    1: {"individual": 1000, "corporate": 900},
    2: {"individual": 1500, "corporate": 1200},
    3: {"individual": 2000, "corporate": 1700},
}
CATEGORY_MULTIPLIER = {"electronics": 1.2, "groceries": 0.8, "luxury": 1.5}   # Rule J
ZONE_LOADING = {"domestic": 0.05, "international": 0.08, "cross-border": 0.10}  # Rule H
SPEED_PREMIUM = {"same-day": 0.15, "next-day": 0.10, "standard": 0.0}          # Rule L
QUARTER_LOADING = {"Q1": 0.02, "Q2": 0.0, "Q3": 0.0, "Q4": -0.01}             # Rule G
CAPITAL_CITIES = {"karachi", "lahore", "islamabad", "peshawar", "quetta"}      # Rule R

INPUT_COLS = [
    "productid", "status", "customer", "season", "volume", "region", "quarter",
    "payment type", "transaction type", "product category", "seller years",
    "processing speed", "tax verified", "is high risk", "requires correction",
    "referral active", "referral invoices remaining", "city", "senior citizen",
    "first order", "weight",
]


def _num(v, d=0.0):
    try:
        return float(str(v).strip())
    except (ValueError, AttributeError, TypeError):
        return d


def _yes(v):
    # yes/no text booleans; empty (or anything not "yes") is False.
    return str(v).strip().lower() == "yes"


def _loyalty(years):
    # Rule I: Platinum 5+ years (15%), Gold 2+ years (10%), else none.
    if years >= 5:
        return "platinum", 0.15
    if years >= 2:
        return "gold", 0.10
    return "none", 0.0


def compute(row):
    """All intermediates for one input row, in canonical order. Returns the full dict."""
    g = lambda k: str(row.get(k, "")).strip()
    pid = int(_num(g("productid"), 0))
    status = g("status").lower()
    customer = g("customer").lower()
    season = g("season").lower()
    category = g("product category").lower()
    volume = _num(g("volume"))
    years = _num(g("seller years"))

    rate = PRODUCT_RATES.get(pid, {}).get(status, 0)                # Rule D
    rbd = volume * rate                                            # receivable before discount

    spring = 0.05 if season == "spring" else 0.0                   # Rule A
    vol_tier = (0.05 if volume >= 100 else 0.0) + (0.05 if volume >= 1000 else 0.0)  # Rule B
    strategic = 0.05 if customer == "strategic" else 0.0           # Rule C
    loyalty_status, loyalty = _loyalty(years)                      # Rule I
    total_discount_rate = spring + vol_tier + strategic + loyalty
    rad = rbd * (1 - total_discount_rate)                          # receivable after discount

    region_loading = 0.10 * rad if g("region").lower() == "emea" else 0.0        # Rule E
    payment_loading = 0.025 * rad if g("payment type").lower() == "credit-card" else 0.0  # Rule F
    quarter_loading = QUARTER_LOADING.get(g("quarter").upper(), 0.0) * rad        # Rule G
    zone_loading = ZONE_LOADING.get(g("transaction type").lower(), 0.0) * rad     # Rule H
    speed_loading = SPEED_PREMIUM.get(g("processing speed").lower(), 0.0) * rad   # Rule L
    base_commission = (region_loading + payment_loading + quarter_loading
                       + zone_loading + speed_loading)

    adjusted = base_commission * CATEGORY_MULTIPLIER.get(category, 1.0)  # Rule J
    if _yes(g("is high risk")):                                    # Rule P
        adjusted -= 0.015 * adjusted
    if _yes(g("referral active")) and _num(g("referral invoices remaining")) > 0:  # Rule N
        adjusted += 0.0025 * adjusted

    correction_fee = 5.0 if _yes(g("requires correction")) else 0.0   # Rule Q
    min_fee = 2.50 if (rad + adjusted) < 50 else 0.0                  # Rule K

    pre_wh = rad + adjusted + correction_fee + min_fee
    withholding = 0.0 if _yes(g("tax verified")) else 0.03 * pre_wh   # Rule O
    total = pre_wh - withholding                                     # master total (T0)
    pre_cascade_total = total

    # Cascade — every adjustment multiplicative on the running total, so order is immaterial.
    city = g("city").lower()
    if city in CAPITAL_CITIES:
        total *= (1 - 0.10)                                          # Rule R
    if _yes(g("senior citizen")):
        total *= (1 - 0.02)                                          # Rule S
    if _yes(g("first order")):
        total *= (1 - 0.05)                                          # Rule T
    if category == "luxury":
        total *= (1 - 0.04)                                          # Rule U
    if _num(g("weight")) > 20:
        total *= (1 - 0.03)                                          # Rule V
    if (customer == "strategic" and loyalty_status == "platinum"
            and volume >= 1000 and correction_fee == 0.0):
        total *= (1 - 0.07)                                          # Rule X
    if season == "spring" and category == "luxury" and g("processing speed").lower() == "same-day":
        total *= (1 - 0.06)                                          # Rule Y
    if (status == "corporate" and city in CAPITAL_CITIES
            and g("payment type").lower() != "credit-card" and _yes(g("tax verified"))):
        total *= (1 - 0.04)                                          # Rule Z
    if (g("transaction type").lower() == "international" and customer == "strategic"
            and not _yes(g("first order")) and volume > 5000):
        total *= (1 - 0.08)                                          # Rule AA
    if (loyalty_status == "platinum" and _yes(g("referral active"))
            and not _yes(g("is high risk")) and _yes(g("tax verified"))):
        total *= (1 - 0.05)                                          # Rule AB

    escrow = 0.01 * rbd                                             # Rule M (tracked separately)

    return {
        "loyalty_status": loyalty_status,
        "receivable_before_discount": rbd,
        "total_discount_rate": total_discount_rate,
        "receivable_after_discount": rad,
        "base_commission_total": base_commission,
        "adjusted_commission_total": adjusted,
        "correction_fee": correction_fee,
        "minimum_transaction_fee": min_fee,
        "tax_withholding_amount": withholding,
        "pre_cascade_total": pre_cascade_total,
        "total_receivables": total,
        "escrow": escrow,
    }


def process_calculations(csv_path):
    results = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            row = {(k.strip() if k else k): (v.strip() if isinstance(v, str) else v)
                   for k, v in raw.items()}
            results.append(compute(row))
    return results


# ---- Dataset ------------------------------------------------------------------------
def R(pid, status, cust, season, vol, region, qtr, pay, txn, cat, years, speed,
      tax, risk, corr, ref, refrem, city, senior, first, wt):
    return dict(zip(INPUT_COLS, [pid, status, cust, season, vol, region, qtr, pay, txn,
                                 cat, years, speed, tax, risk, corr, ref, refrem, city,
                                 senior, first, wt]))


# 19 Fahad rows (A–S), transcribed from requirements-source.md. Booleans TRUE/FALSE -> yes/no,
# empty `tax verified` kept empty (treated as not-verified -> withhold). Rate columns dropped
# (rate is derived via Rule D). `senoir citizen` header fixed to `senior citizen`.
INPUT_ROWS = [
    R("1", "individual", "strategic",     "winter", "90",   "non-EMEA", "Q2", "credit-card", "international", "luxury",      "4",  "same-day", "",    "no",  "no",  "no",  "0", "karachi",         "no",  "no",  "1"),   # A
    R("1", "individual", "strategic",     "winter", "900",  "non-EMEA", "Q1", "credit-card", "international", "groceries",   "3",  "standard", "",    "no",  "no",  "no",  "0", "lahore",          "no",  "no",  "1"),   # B
    R("1", "individual", "non-strategic", "winter", "90",   "EMEA",     "Q4", "credit-card", "international", "luxury",      "5",  "same-day", "no",  "yes", "yes", "yes", "8", "hyderabad",       "no",  "no",  "1"),   # C
    R("1", "individual", "non-strategic", "spring", "90",   "EMEA",     "Q3", "credit-card", "domestic",     "electronics", "0",  "next-day", "",    "no",  "no",  "no",  "0", "sukkur",          "no",  "no",  "1"),   # D
    R("1", "corporate",  "strategic",     "summer", "315",  "non-EMEA", "Q1", "credit-card", "cross-border", "groceries",   "3",  "standard", "",    "no",  "no",  "no",  "0", "ferozpur",        "no",  "no",  "1"),   # E
    R("2", "corporate",  "strategic",     "summer", "1790", "non-EMEA", "Q2", "ach/wire",    "cross-border", "groceries",   "6",  "same-day", "",    "no",  "no",  "no",  "0", "dera ghazi khan", "yes", "yes", "22"),  # F
    R("1", "individual", "non-strategic", "autumn", "747",  "non-EMEA", "Q1", "ach/wire",    "cross-border", "electronics", "4",  "next-day", "",    "no",  "no",  "no",  "0", "islamabad",       "no",  "yes", "1"),   # G
    R("2", "individual", "strategic",     "summer", "971",  "non-EMEA", "Q3", "ach/wire",    "domestic",     "electronics", "1",  "same-day", "",    "no",  "no",  "no",  "0", "faislabad",       "no",  "no",  "1"),   # H
    R("1", "individual", "strategic",     "winter", "1773", "EMEA",     "Q1", "ach/wire",    "international", "electronics", "8",  "same-day", "",    "no",  "no",  "no",  "0", "rawalpindi",      "no",  "no",  "25"),  # I
    R("3", "individual", "strategic",     "spring", "1718", "EMEA",     "Q2", "credit-card", "cross-border", "luxury",      "4",  "same-day", "",    "no",  "no",  "no",  "0", "rawalpindi",      "yes", "no",  "1"),   # J
    R("2", "corporate",  "strategic",     "autumn", "170",  "EMEA",     "Q1", "ach/wire",    "domestic",     "luxury",      "2",  "standard", "",    "no",  "no",  "no",  "0", "peshawar",        "yes", "yes", "32"),  # K
    R("3", "individual", "non-strategic", "spring", "86",   "EMEA",     "Q4", "ach/wire",    "cross-border", "groceries",   "10", "next-day", "",    "no",  "no",  "no",  "0", "faislabad",       "no",  "no",  "1"),   # L
    R("3", "individual", "strategic",     "autumn", "1826", "non-EMEA", "Q2", "ach/wire",    "international", "groceries",   "8",  "standard", "",    "no",  "no",  "no",  "0", "faislabad",       "no",  "no",  "1"),   # M
    R("3", "individual", "non-strategic", "winter", "850",  "non-EMEA", "Q4", "credit-card", "domestic",     "luxury",      "3",  "standard", "",    "no",  "no",  "no",  "0", "ferozpur",        "no",  "no",  "1"),   # N
    R("3", "individual", "strategic",     "spring", "198",  "EMEA",     "Q3", "credit-card", "international", "groceries",   "3",  "next-day", "",    "no",  "no",  "no",  "0", "nawabshah",       "yes", "no",  "1"),   # O
    R("3", "corporate",  "strategic",     "spring", "1113", "non-EMEA", "Q1", "credit-card", "international", "groceries",   "10", "same-day", "",    "no",  "no",  "no",  "0", "sialkot",         "no",  "no",  "1"),   # P
    R("3", "corporate",  "strategic",     "spring", "449",  "non-EMEA", "Q1", "ach/wire",    "international", "electronics", "3",  "standard", "",    "no",  "no",  "no",  "0", "karachi",         "no",  "no",  "1"),   # Q
    R("2", "individual", "non-strategic", "winter", "12",   "EMEA",     "Q2", "credit-card", "cross-border", "groceries",   "7",  "standard", "",    "no",  "no",  "no",  "0", "quetta",          "no",  "yes", "1"),   # R
    R("3", "individual", "strategic",     "autumn", "1020", "non-EMEA", "Q2", "ach/wire",    "international", "electronics", "0",  "next-day", "",    "no",  "no",  "no",  "0", "larkana",         "yes", "no",  "1"),   # S
    # --- Synthetic coverage rows (not Fahad's data) — each fires a rule his 19 rows never do:
    R("3", "corporate",  "strategic",     "summer", "6000", "non-EMEA", "Q2", "ach/wire",    "international", "electronics", "6",  "standard", "yes", "no",  "no",  "no",  "0", "multan",          "no",  "no",  "1"),   # S1: Rule AA (volume>5000)
    R("1", "individual", "non-strategic", "summer", "0",    "non-EMEA", "Q3", "ach/wire",    "domestic",     "groceries",   "0",  "standard", "yes", "no",  "no",  "no",  "0", "multan",          "no",  "no",  "1"),   # S2: Rule K (invoice < $50)
    R("3", "corporate",  "strategic",     "spring", "1500", "EMEA",     "Q1", "ach/wire",    "international", "luxury",      "6",  "same-day", "yes", "no",  "no",  "yes", "5", "karachi",         "yes", "yes", "25"),  # S3: R/S/T/U/V + X/Y/Z/AB cascade
    R("2", "individual", "non-strategic", "winter", "500",  "EMEA",     "Q4", "credit-card", "cross-border", "electronics", "3",  "next-day", "no",  "yes", "yes", "no",  "0", "multan",          "yes", "yes", "30"),  # S4: P/Q/O + negative-Q4 G + S/T/V
]

# Fahad's `total Receivable` column (the pre-cascade total) for the 19 original rows;
# None for the 4 synthetic rows. The reference's pre_cascade_total must match this.
FAHAD_PRECASCADE = [
    102588.4125, 768240.0, 112129.4839, 110303.55, 245515.536, 1750190.4, 778499.496,
    1576690.38, 1709491.14, 3645381.25, 198671.52, 164437.50400000002, 2638409.312,
    1538310.875, 358383.96, 1455422.2410000002, 621936.84, 17512.38, 2045287.68,
    None, None, None, None,
]


def _write_test_cases():
    tmp = HERE / "_tmp_inputs_30.csv"
    with tmp.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=INPUT_COLS)
        w.writeheader()
        w.writerows(INPUT_ROWS)
    computed = process_calculations(str(tmp))
    targets = [r["total_receivables"] for r in computed]
    escrows = [r["escrow"] for r in computed]

    out = HERE / "test-cases-30.csv"
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(INPUT_COLS + ["Total_receivables", "Escrow"])
        for row, t, e in zip(INPUT_ROWS, targets, escrows):
            w.writerow([row[c] for c in INPUT_COLS] + [round(t, 6), round(e, 6)])
    tmp.unlink()
    return out, targets, escrows


if __name__ == "__main__":
    out, targets, escrows = _write_test_cases()
    print(f"Wrote {out.name} with {len(targets)} rows "
          f"({len(INPUT_ROWS) - 4} Fahad + 4 synthetic).\n")

    check = process_calculations(str(out))
    ok = sum(abs(float(r["total_receivables"]) - t) <= 0.5 for r, t in zip(check, targets))
    print(f"self-check (total_receivables): {ok}/{len(targets)} reproduce their own target")

    rows = [compute(r) for r in INPUT_ROWS]
    matches, mism = 0, []
    for i, (r, fah) in enumerate(zip(rows, FAHAD_PRECASCADE)):
        if fah is None:
            continue
        if abs(r["pre_cascade_total"] - fah) <= 0.5:
            matches += 1
        else:
            mism.append((i, r["pre_cascade_total"], fah))
    print(f"Fahad pre-cascade cross-check: {matches}/19 match")
    for i, got, exp in mism:
        print(f"  row {i} ({'ABCDEFGHIJKLMNOPQRS'[i]}): reference {got:.4f} vs Fahad {exp:.4f}")

    assert ok == len(targets), "reference must reproduce its own targets"
    print("\nOK: reference is self-consistent.")
