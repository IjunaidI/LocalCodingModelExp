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
