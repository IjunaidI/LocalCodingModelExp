# 10-rule experiment — the original spec (the "before")

The original 10-rule pricing/commission spec, in its **True/False** dialect. This is the
phrasing that trips `Qwen2.5-Coder-3B` (best attempts: 3/12 on the 3B, 1/12 on the 7B —
architecture correct, ~2–5% off on detail bugs).

Two constructs cause the failures:

1. **Rule 4, the volume tier.** `<100 → 0%, <1000 → 5%, ≥1000 → 10%` gets collapsed to
   `0.05 if v<100 else (0.1 if v<1000 else 0.1)` — wrong in two of three branches.
2. **Rule 10, the boolean.** The `tax verified` cell is the *string* `"False"`, which is
   truthy in Python, so `not row["tax verified"]` skips withholding when it should apply.

The fix — the *same ten rules* re-expressed so the model can't trip — lives in
[`../10-rule-v2/`](../10-rule-v2/), which scores **12/12**.

## Files
- `reference_simple.py` — ground truth for the original 10-rule spec (True/False dialect);
  regenerates `test-cases.csv` and self-checks that the targets reproduce.
- `test-cases.csv`      — 12 rows with the original True/False `tax verified` flag.

This folder is the baseline dataset + ground truth only; the generate/score harness and a
passing solution live in the v2 folder.

## Run
```bash
.venv/bin/python experiments/10-rule-original/reference_simple.py   # regenerate + self-check
```
