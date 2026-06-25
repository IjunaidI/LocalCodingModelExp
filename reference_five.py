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
