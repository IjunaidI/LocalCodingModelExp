# Session: Minimal 5-rule spec vs local LLM (8 GB M1)

## Goal
Continue the complexity-floor experiment: shrink the pricing spec to 5 rules and see
whether a small local LLM can finally produce fully correct code.

## Result
**Qwen2.5-Coder-3B-4bit passed 12/12 on the FIRST iteration, no repairs.**
`solution_best.py` is a clean, correct implementation (no harness-gaming).

## Full experiment progression (across the three project folders)
| Spec size | Model | Score |
|---|---|---|
| 17 rules | 0.5B | crashes |
| 17 rules | 3B | 0/19 |
| 17 rules | 7B | 0/19 (most complete, but header bug + wrong total formula) |
| 10 rules | 3B | 3/12 |
| 10 rules | 7B | 1/12 (architecture correct, ~2-5% off on detail bugs) |
| **5 rules** | **3B** | **12/12, first try ✅** |

## The real insight: it wasn't only rule COUNT
The 5-rule spec succeeded because it removed the specific constructs that broke the
model at 10 rules, not merely because there were fewer rules:
1. **No multi-tier conditional.** The 10-rule volume discount (`<100 -> 0%, <1000 ->
   5%, >=1000 -> 10%`) broke BOTH models (they collapsed the branches). The 5-rule
   spec has only single-condition `if`s.
2. **Unambiguous boolean.** Used the text "yes"/"no" instead of True/False, which the
   7B mis-parsed (`not "False"` is False -> skipped withholding).
3. **Pre-stated the arithmetic.** Spec says "multiply by 0.95" rather than "5%
   discount", so the model didn't have to translate percentages into multipliers.

Takeaway: a small local model on 8 GB can write correct numeric code when each rule
is a single unambiguous operation. It fails when a rule needs multi-branch logic,
boolean parsing, or translating a description into arithmetic. The viability boundary
is the per-rule construct difficulty, not the rule count alone.

## Files
- `spec.md` — the 5-rule spec.
- `reference_five.py` — ground truth; generates `test-cases.csv` + self-checks 12/12.
- `test-cases.csv` — 12 generated rows.
- `solve_five.py` — generate->score->repair loop (temperature sampling on repairs).
- `solution_best.py` — the model's 12/12 output.
- `model_cache` — symlink to the sibling project's cache.

## Run
```bash
python3 reference_five.py   # regenerate test cases + self-check
python3 solve_five.py       # run the LLM loop (3B by default)
```
