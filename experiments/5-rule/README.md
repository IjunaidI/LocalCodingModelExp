# 5-rule experiment — the minimal spec

Shrink the pricing spec to **5 rules**, each a single unambiguous operation, and see
whether a small local model produces fully correct code.

**Result: `Qwen2.5-Coder-3B-Instruct-4bit` passed 12/12 on the first iteration, no
repairs.** This is the clean lower bound — it removes every construct that broke the
model at 10 rules (no multi-tier conditionals, unambiguous `yes`/`no` boolean,
pre-stated arithmetic).

## Files
- `spec.md`            — the 5-rule spec (the prompt fed to the model).
- `reference_five.py`  — ground truth; regenerates `test-cases.csv` and self-checks 12/12.
- `test-cases.csv`     — 12 rows, targets baked in.
- `solve_five.py`      — MLX harness: generate → score → repair loop.
- `solution_best.py`   — the model's passing 12/12 output.
- `program-output.txt` — a captured run log.
- `model_cache`        — symlink to the repo-root shared cache (gitignored).

## Run
```bash
# from the repo root, using the project venv
.venv/bin/python experiments/5-rule/reference_five.py   # regenerate + self-check
.venv/bin/python experiments/5-rule/solve_five.py       # run the LLM loop (3B)
```
