"""
Offline proof harness (no MLX required).

Scores a candidate solution file against test-cases-v2.csv using the SAME
scoring logic as the real solve_simple_v2.py harness, so we can verify that a
faithful implementation of spec_simple_v2.md passes 12/12 without needing the
Apple-Silicon model runtime.

Usage:  python3 prove_v2.py model_solution_v2.py
"""

import csv
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEST_CSV = HERE / "test-cases-v2.csv"
TARGET_COL = "Total_receivables"
TOLERANCE = 0.5


def load_targets_and_inputs():
    with TEST_CSV.open(newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = [fn.strip() for fn in reader.fieldnames]
        rows, targets = [], []
        for raw in reader:
            clean = {k.strip(): (v.strip() if v else "") for k, v in raw.items()}
            targets.append(float(clean[TARGET_COL]))
            rows.append({k: v for k, v in clean.items() if k != TARGET_COL})
    input_cols = [c for c in fieldnames if c != TARGET_COL]
    inputs_csv = HERE / "_inputs_only_v2.csv"
    with inputs_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=input_cols)
        w.writeheader()
        w.writerows(rows)
    return inputs_csv, targets


def load_fn(path):
    spec = importlib.util.spec_from_file_location("candidate", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.process_calculations


def score(fn, inputs_csv, targets):
    result = fn(str(inputs_csv))
    if not isinstance(result, list) or len(result) != len(targets):
        return 0, [f"expected list of {len(targets)} dicts, got {type(result).__name__}"]
    passed, lines = 0, []
    for i, (pred_row, target) in enumerate(zip(result, targets)):
        pred = float(pred_row["total_receivables"])
        if abs(pred - target) <= TOLERANCE:
            passed += 1
        else:
            lines.append(f"  row {i}: got {pred:.4f}, expected {target:.4f}")
    return passed, lines


def main():
    candidate = sys.argv[1] if len(sys.argv) > 1 else "model_solution_v2.py"
    inputs_csv, targets = load_targets_and_inputs()
    fn = load_fn(HERE / candidate)
    passed, lines = score(fn, inputs_csv, targets)
    print(f"Candidate: {candidate}")
    print(f"PASSED {passed}/{len(targets)}")
    for ln in lines:
        print(ln)
    print("\nALL TEST CASES PASSED" if passed == len(targets) else "Did NOT fully pass")


if __name__ == "__main__":
    main()
