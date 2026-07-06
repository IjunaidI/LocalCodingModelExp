# 30-rule spec experiment — design

**Date:** 2026-07-06
**Status:** approved design, pre-implementation
**Owner:** handoff for a technical reviewer

## Goal

Does the "the lever is the spec, not the model" thesis survive at **~30 rules**? Take the
new pricing/commission requirement Fahad sent (rules A–V, X, Y, Z, AA, AB — no W — i.e.
27 lettered rules, "a 30-rule set") and drive `Qwen2.5-Coder-3B-Instruct-4bit` (Apple MLX)
to emit a `process_calculations(csv_path)` that is numerically correct on every row.

**Phase 1 (this spec):** reach a full pass with ONE *precise* spec (the low-skill-ceiling
end of the dialect ladder). Prove 30 rules is reachable at all.
**Phase 2 (later, optional):** simplify the spec in rungs to locate the sweet spot, as the
`sweet-spot/` experiment did for 10 rules.

Model is fixed: the **Coder-3B** variant. The lever is the spec.

## Why a reference is needed (ground truth)

The requirement is prose; Fahad's CSV is **input data with some pre-computed scratch
columns mixed in**. The scratch columns are internally inconsistent with the prose (e.g.
a 5% luxury tax on a groceries row), so they are **not** authoritative. We therefore
author `reference_30.py` — a faithful implementation of the prose — and *its* output is
the ground truth, baked into the dataset as the target column. This mirrors how
`10-rule-v2/reference_simple_v2.py` produced its targets.

**The reference reading was validated by hand against Fahad's `total Receivable`
(pre-cascade) column and reproduces it exactly:**

| Row | Exercises | Reference `total_receivables` (pre-cascade) | Fahad's column |
|-----|-----------|---------------------------------------------|----------------|
| A | discount+loading+multiplier+withholding | 102588.4125 | 102588.4125 ✓ |
| F | volume-tier + platinum loyalty + groceries mult | 1750190.4 | 1750190.4 ✓ |
| C | **high-risk P + referral N + correction Q + withholding O together** | 112129.4839 | 112129.4839 ✓ |

Row C only lands exactly under one specific ordering (see table below), which pins the
otherwise-ambiguous P/N/Q/O sequence. Row A's post-cascade value (`88636.39`) also
reproduces exactly with multiplicative cascade stacking.

## Rule-resolution table (defines ground truth)

**Core pipeline, per row:**

1. `rate` — Rule D lookup `PRODUCT_RATES[productid][status]`.
2. `receivable_before_discount = volume × rate`.
3. Discounts (Rules A, B, C, I) as **additive rates, subtracted once**:
   `RAD = rbd × (1 − (spring + volume_tier + strategic + loyalty))`.
4. Loadings (Rules E, F, G, H, L) **each computed on RAD, summed** →
   `base_commission_total`. Rule G (quarter) may be **negative** (Q1 +2%, Q4 −1%, Q2/Q3 0).
5. `adjusted_commission_total = base_commission_total × CATEGORY_MULTIPLIER[category]` (Rule J).
6. Rule P: if high-risk, `adjusted −= 0.015 × adjusted`.
7. Rule N: if `referral active` and `referral invoices remaining > 0`,
   `adjusted += 0.0025 × adjusted` (on the post-risk figure).
8. Rule Q: if `requires correction`, `correction_fee = 5.0`, else 0.
9. Rule O: if not tax-verified, `withholding = 0.03 × (RAD + adjusted + correction_fee)`, else 0.
10. `T0 = RAD + adjusted + correction_fee − withholding`  (the master formula).

**Then the total-receivables cascade on `T0`, all multiplicative `× (1 − rate)`** (so the
relative order is immaterial): R capital-city 10% → S senior 2% → T first-order 5% →
U luxury 4% → V heavyweight 3% (`weight > 20`) → X 7% → Y 6% → Z 4% → AA 8% → AB 5%.
Each fires only when its condition holds (conditions per prose).

| Ambiguity | Resolution | Basis |
|---|---|---|
| Loyalty status from `seller years` | `≥5 → Platinum` (15% discount), `≥2 → Gold` (10%), else `None` (0%) | matches Fahad's `loyalty_status` column |
| A/B/C/I combine | additive rates, one subtraction | same as 10-rule; row A/C/F exact |
| Rule B volume tier | `+0.05 if v≥100`, `+0.05 if v≥1000` (no elif) | v2 dialect |
| P / N / Q / O ordering | adjusted → −1.5% risk → +0.25% referral (post-risk) → +$5 → 3% withholding on (RAD+adjusted+correction) | **row C exact** |
| `escrow` base ("gross invoice") | `0.01 × receivable_before_discount`; reported separately, NOT in total | prose: "tracked separately" |
| Cascade R–AB stacking | multiplicative on running total | row A exact |
| Empty `tax verified` | treated as not-verified → withhold | same as 10-rule |
| Rule N eligibility | `referral active` AND `remaining > 0` | "next 10 invoices" + active flag |
| Rule AA "international" | `transaction type == international` (cross-border excluded) | literal reading; AA needs volume>5000 anyway |

**Rules dormant on Fahad's 19 rows:** K (min-fee — all invoices ≫ $50) and AA (needs
`volume > 5000`; max in data is 1826). Implemented faithfully; **synthetic coverage rows
(below) will exercise them.**

## Dataset

- Start from Fahad's 19 rows (A–S).
- **Strip** the pre-computed output columns; keep only genuine inputs:
  `productid, status, customer, season, volume, region, quarter, payment type,
  transaction type, product category, seller years, processing speed, tax verified,
  is high risk, requires correction, referral active, referral invoices remaining, city,
  senior citizen, first order, weight`.
- **Drop** Fahad's `individual rate`/`corporate rate` columns from the inputs — the rate is
  **derived** from `PRODUCT_RATES[productid][status]` (Rule D), keeping Rule D a real
  operation the model must perform, comparable to `10-rule-v2` (which had no rate columns).
- **Convert booleans `TRUE/FALSE` → `yes/no`** (the proven dialect fix that dodges the
  truthy-string trap).
- **Append ~3–5 synthetic coverage rows** engineered so every rule fires at least once:
  one with `volume > 5000` (Rule AA), one tiny invoice `< $50` (Rule K), and one
  all-boolean-`yes` row that triggers the X/Y/Z/AB cascade. These extra rows are clearly
  marked as synthetic in the reference. Final dataset ≈ 22–24 rows.
- `reference_30.py` regenerates this CSV and bakes in the `Total_receivables` (and
  `Escrow`) target columns, then self-checks that it reproduces its own targets 100%.

## Spec dialect (Phase 1 — precise)

The low-skill-ceiling end of the ladder:

- lookup tables (`PRODUCT_RATES`, `CATEGORY_MULTIPLIER`, geographic-zone, processing-speed,
  quarter) copied **verbatim** as literals to be used as-is;
- every rate written as a **bare decimal** (`0.025`, not "2.5%");
- each rule expressed as a **single-condition operation** (no multi-tier collapse);
- the cascade written as **explicit multiplicative steps**;
- booleans compared as explicit `yes`/`no` text.

## Scoring metric

- Primary target: `total_receivables` within `TOLERANCE = 0.5` on **every** row.
- Also scored: `escrow` (clean independent quantity).
- The model returns the full result dict per the prose ("output keys should match
  exactly"), but the pass/fail keys are `total_receivables` (+ `escrow`).
- Pass condition: `N/N` (all rows), matching prior experiments' "12/12" convention.

## Harness

Adapt `10-rule-v2/solve_simple_v2.py` (single precise spec → generate → score → repair
loop, greedy iteration 1, temperature-sampled repairs). Changes:

- read the 30-rule spec + dataset;
- `MAX_TOKENS` raised (~4000) for the longer function;
- score both `total_receivables` and `escrow`;
- constant, precise instruction wrapper (as `run_ladder.py` uses — no ambiguous
  "strip spaces"/"never crash");
- writes `solution_best_30.py`; offline re-score via `prove_30.py`.

## Files

```
experiments/30-rule/
├── reference_30.py       # correct method; regenerates dataset; self-checks
├── test-cases-30.csv     # input-only + baked Total_receivables/Escrow targets
├── spec_30.md            # the precise v2-dialect spec handed to the model
├── solve_30.py           # MLX generate→score→repair harness (RUN THIS)
├── prove_30.py           # offline scorer, no MLX
├── requirements-source.md# the original prose requirement, verbatim (provenance)
└── README.md             # self-contained writeup
```

## Out of scope (Phase 1)

- The full dialect ladder / sweet-spot search (Phase 2).
- Exact-match scoring on all ~30 intermediate output keys (metric is `total_receivables`
  + `escrow`).
- Fine-tuning, alternate models (task fixes Coder-3B).

## Success criteria

`solve_30.py` drives Coder-3B to a full pass (all rows within tolerance on
`total_receivables` and `escrow`); `reference_30.py` self-checks 100%; `prove_30.py`
re-scores the saved solution offline to the same result; the reference reproduces Fahad's
`total Receivable` column on the original 19 rows.
