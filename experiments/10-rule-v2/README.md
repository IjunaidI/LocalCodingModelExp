# 10-rule experiment v2 — the deliverable ★

The **same ten rules** as [`../10-rule-original/`](../10-rule-original/), re-expressed in
the model's dialect so `Qwen2.5-Coder-3B-Instruct-4bit` emits correct code. Result:
**`PASSED 12/12` on iteration 1 (greedy), no repairs** — and the identical spec does the
same on the **7B** (`--model`, also 12/12 first try, `solution_best_v2_7b.py`). The v2
dialect is size-robust: contrast the original spec, where the 7B managed only 1/12.

The arithmetic is bit-identical to the original (targets match with max abs diff = 0.0) —
this is a *phrasing* fix, not a problem change:

- **Rule 4** decomposed into two independent single-condition adds
  (`if v>=100: +0.05`, `if v>=1000: +0.05`), with an explicit "no elif".
- **`tax verified`** expressed as `yes`/`no` text in both the spec **and** the data.
- Every percentage given as a bare decimal; rates + category multiplier as dict lookups.

## Files
- `spec_simple_v2.md`          — the rewritten spec (the actual deliverable / the prompt).
- `solve_simple_v2.py`         — MLX harness: generate → score → repair loop. **Run this.**
- `test-cases-v2.csv`          — 12 rows, `yes`/`no` flag, targets baked in.
- `reference_simple_v2.py`     — ground truth; regenerates the dataset, self-checks 12/12.
- `model_solution_v2.py`       — a hand-written passing solution (proves the spec suffices).
- `solution_best_v2.py`        — the 3B's actual 12/12 output.
- `solution_best_v2_7b.py`     — the 7B's 12/12 output from the same spec (first try too).
- `prove_v2.py`                — offline scorer; no MLX needed (check any solution).
- `buggy_solution_original.py` — the article's failing 7B output (1/12), for before/after.
- `model_cache`                — symlink to the repo-root shared cache (gitignored).

## Run
```bash
# Live: 3B generates → harness scores → writes solution_best_v2.py
.venv/bin/python experiments/10-rule-v2/solve_simple_v2.py

# Same spec on the 7B (writes solution_best_v2_7b.py)
.venv/bin/python experiments/10-rule-v2/solve_simple_v2.py --model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit

# Offline: score a candidate against the ground truth (works anywhere, no model)
.venv/bin/python experiments/10-rule-v2/prove_v2.py solution_best_v2.py
.venv/bin/python experiments/10-rule-v2/prove_v2.py solution_best_v2_7b.py
```

First run downloads `mlx-community/Qwen2.5-Coder-3B-Instruct-4bit` (~1.8 GB) into the
shared `./model_cache`. Success = `solve_simple_v2.py` prints `PASSED 12/12`.
