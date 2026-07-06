"""
Offline proof harness for the 30-rule spec (no MLX required).

Scores a candidate solution file against test-cases-30.csv with the SAME logic the live
solve_30.py harness uses, so a faithful implementation of spec_30.md can be verified without
the Apple-Silicon model runtime. A row passes only if BOTH `total_receivables` and `escrow`
match their targets within TOLERANCE.

Usage:  python3 prove_30.py model_solution_30.py
"""

import csv
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEST_CSV = HERE / "test-cases-30.csv"
TARGET_COL = "Total_receivables"
ESCROW_COL = "Escrow"
TOLERANCE = 0.5


def load_targets_and_inputs():
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
    inputs_csv = HERE / "_inputs_only_30.csv"
    with inputs_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=input_cols)
        w.writeheader()
        w.writerows(rows)
    return inputs_csv, targets, escrows


def load_fn(path):
    spec = importlib.util.spec_from_file_location("candidate", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.process_calculations


def score(fn, inputs_csv, targets, escrows):
    result = fn(str(inputs_csv))
    if not isinstance(result, list) or len(result) != len(targets):
        got = type(result).__name__ + (f" of len {len(result)}" if hasattr(result, "__len__") else "")
        return 0, [f"expected list of {len(targets)} dicts, got {got}"]
    passed, lines = 0, []
    for i, (pred_row, tr, esc) in enumerate(zip(result, targets, escrows)):
        try:
            got_tr = float(pred_row["total_receivables"])
            got_esc = float(pred_row["escrow"])
        except (KeyError, TypeError, ValueError) as e:
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
    return passed, lines


def main():
    candidate = sys.argv[1] if len(sys.argv) > 1 else "model_solution_30.py"
    inputs_csv, targets, escrows = load_targets_and_inputs()
    fn = load_fn(HERE / candidate)
    passed, lines = score(fn, inputs_csv, targets, escrows)
    print(f"Candidate: {candidate}")
    print(f"PASSED {passed}/{len(targets)}")
    for ln in lines:
        print(ln)
    print("\nALL TEST CASES PASSED" if passed == len(targets) else "Did NOT fully pass")
    sys.exit(0 if passed == len(targets) else 1)


if __name__ == "__main__":
    main()
