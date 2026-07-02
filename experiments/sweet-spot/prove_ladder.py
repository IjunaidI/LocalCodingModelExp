"""
Offline re-scorer for the ladder — NO MLX needed, runs anywhere.

Re-scores each saved outputs/level_N_solution.py against its level's dataset and prints
the same PASS/FAIL table run_ladder.py produced live. Use this to verify the committed
outputs on a machine without Apple Silicon, or to re-check after editing a solution.

    python3 experiments/sweet-spot/prove_ladder.py            # all saved levels
    python3 experiments/sweet-spot/prove_ladder.py 4 5        # only levels 4 and 5
    python3 experiments/sweet-spot/prove_ladder.py --tag 7b   # tagged run (level_N_solution_7b.py)
"""

import sys
import csv
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent

TARGET_COL = "Total_receivables"
OUTPUT_KEY = "total_receivables"
TOLERANCE = 0.5

# Which dataset each level was scored against (mirrors LEVELS in run_ladder.py).
LEVEL_DATASET = {
    1: "test-cases-v2.csv",
    2: "test-cases-v2.csv",
    3: "test-cases-v2.csv",
    4: "test-cases-v2.csv",
    5: "test-cases.csv",
    6: "test-cases-v2.csv",
    7: "test-cases.csv",
    8: "test-cases.csv",
}
LEVEL_TITLE = {
    1: "Prescriptive pseudocode",
    2: "Declarative spec",
    3: "Business prose",
    4: "Natural rules (tier trap)",
    5: "Original dialect (boolean trap)",
    6: "Tables + natural tier (yes/no)",
    7: "Tables + True/False boolean",
    8: "Tables + tier + True/False",
}


def load_targets(dataset_path):
    with dataset_path.open(newline="") as f:
        reader = csv.DictReader(f)
        input_cols = [fn.strip() for fn in reader.fieldnames if fn.strip() != TARGET_COL]
        rows, targets = [], []
        for raw in reader:
            clean = {k.strip(): (v.strip() if v else "") for k, v in raw.items()}
            targets.append(float(clean[TARGET_COL]))
            rows.append({k: v for k, v in clean.items() if k != TARGET_COL})
    return input_cols, rows, targets


def write_inputs_csv(input_cols, rows, path):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=input_cols)
        w.writeheader()
        w.writerows(rows)


def score(code, inputs_csv, targets):
    ns = {}
    try:
        exec(code, ns)  # noqa: S102
        fn = ns["process_calculations"]
        result = fn(str(inputs_csv))
    except Exception as e:
        return 0, f"error: {e}"
    if not isinstance(result, list) or len(result) != len(targets):
        return 0, "wrong shape"
    passed = 0
    for pred_row, target in zip(result, targets):
        try:
            if abs(float(pred_row[OUTPUT_KEY]) - target) <= TOLERANCE:
                passed += 1
        except Exception:
            pass
    return passed, None


def main():
    argv = sys.argv[1:]
    tag = ""
    if "--tag" in argv:
        i = argv.index("--tag")
        tag = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    suffix = f"_{tag}" if tag else ""
    wanted = [int(a) for a in argv] or sorted(LEVEL_DATASET)
    if tag:
        print(f"Re-scoring tagged outputs: level_N_solution{suffix}.py")
    print(f"{'Level':<7} {'Spec dialect':<34} {'Score':<8} Result")
    print("-" * 62)
    results = []
    for lvl in wanted:
        sol = PROJECT_DIR / "outputs" / f"level_{lvl}_solution{suffix}.py"
        if not sol.exists():
            print(f"L{lvl:<6} {LEVEL_TITLE.get(lvl, '?'):<34} {'--':<8} (no saved output)")
            continue
        input_cols, rows, targets = load_targets(PROJECT_DIR / LEVEL_DATASET[lvl])
        inputs_csv = PROJECT_DIR / "outputs" / f"_inputs_only_level_{lvl}.csv"
        write_inputs_csv(input_cols, rows, inputs_csv)
        passed, err = score(sol.read_text(), inputs_csv, targets)
        tag = "PASS" if passed == len(targets) else "FAIL"
        note = f"  [{err}]" if err else ""
        print(f"L{lvl:<6} {LEVEL_TITLE.get(lvl, '?'):<34} {passed}/{len(targets):<6} {tag}{note}")
        results.append((lvl, passed, len(targets)))

    fails = [r for r in results if r[1] != r[2]]
    print("-" * 62)
    if results and not fails:
        print("All saved levels pass.")
    elif fails:
        print(f"First failing level: L{fails[0][0]} ({LEVEL_TITLE.get(fails[0][0], '?')}).")


if __name__ == "__main__":
    main()
