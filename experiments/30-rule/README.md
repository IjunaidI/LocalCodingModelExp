# 30-rule spec — Qwen2.5-Coder-3B passes 23/23, first greedy try

Can the spec-not-model thesis survive a **much bigger** ruleset? This experiment takes a
fresh ~30-rule pricing/commission requirement (27 lettered rules, A–V and X–AB) and drives
`Qwen2.5-Coder-3B-Instruct-4bit` (Apple MLX) to generate a `process_calculations(csv_path)`
that is numerically correct on **every** row.

**Result: 23/23 on the first greedy attempt, no repairs** — once the spec is written in the
model's dialect. Same lesson as the 10-rule work, at 3× the rules: it is not the *number* of
rules that breaks a small model, it is the difficulty of the individual constructs.

## The task

Fahad's requirement (verbatim in [`requirements-source.md`](requirements-source.md)) is a
deep, ordered pipeline: product-rate lookup → four stacked discounts → five commission
loadings → category multiplier → risk/referral/correction adjustments → tax withholding →
then a **ten-step cascade of total-receivables discounts** (capital city, senior, first
order, luxury tax, heavy weight, and five conditional bundle discounts X/Y/Z/AA/AB). Many
fields are booleans; the volume discount is a multi-tier conditional.

## Ground truth (how we score "correct")

Fahad's CSV is **input data** — it also carries some pre-computed scratch columns, but those
contradict the prose in places (e.g. a 5% luxury tax on a groceries row) and his post-cascade
column is incomplete (row I records a 7% Rule-X discount but never applies it). So we do not
trust them.

Instead, [`reference_30.py`](reference_30.py) implements every rule straight from the prose
and **is** the ground truth. It is validated two ways:

- its pre-cascade total **reproduces Fahad's `total Receivable` column exactly on all 19
  original rows** (this pins the otherwise-ambiguous risk/referral/correction/withholding
  ordering — row C only matches under one specific sequence);
- it self-checks 23/23 against its own baked targets.

The final R–AB cascade is applied **multiplicatively** (`× (1 − rate)`), so the prose's
under-specified ordering is immaterial. Ambiguity resolutions are documented in
[`../../docs/superpowers/specs/2026-07-06-30-rule-experiment-design.md`](../../docs/superpowers/specs/2026-07-06-30-rule-experiment-design.md).

## Dataset

[`test-cases-30.csv`](test-cases-30.csv) — 23 rows:

- **19** are Fahad's rows A–S, stripped to genuine input columns, with booleans converted
  `TRUE/FALSE → yes/no` (the dialect fix that dodges the truthy-string trap) and rates
  **derived** via Rule D (his rate columns dropped);
- **4** are synthetic coverage rows, because Fahad's data never triggers Rule AA
  (`volume > 5000`), Rule K (`invoice < $50`), or the X/Y/Z/AB bundle. With them, **every
  rule A–AB fires at least once.**

## The finding: hand over the tables *keyed to match the data*

The first "precise" spec still **crashed** on the greedy attempt — and not on arithmetic.
The 3B copied the lookup tables verbatim (as intended) but blew up on the *lookups*:

- `QUARTER_LOADING["Q2"]` against lowercase keys → `KeyError: 'Q2'`;
- `PRODUCT_RATES["1"]` against integer keys → `KeyError: '1'`;
- calling `.lower()` on a cell it had converted to a Python bool.

Every failure was a **crash**, and the scalar repair loop couldn't recover, because a bare
`KeyError: '1'` doesn't say *where* it blew up. Two fixes turned 0/23 into 23/23 first try:

1. **Key the tables to the data's exact type/casing** — product ids as the strings
   `"1"/"2"/"3"`, `quarter` matched upper-case (`Q1`), and Rule G re-expressed as explicit
   additive `if`s (the same dialect that already tamed the volume tier). Now no lookup can
   `KeyError`.
2. **Give the repair loop the traceback**, not just `str(e)`, so a crash localizes to the
   offending line (belt-and-suspenders — the greedy attempt passed before repair was needed).

So the 10-rule lesson ("hand over the literal lookup tables") sharpens at scale: hand them
over **keyed to match the data**, or a small model crashes on the lookup before any rule
arithmetic runs.

## Phase 2 — the spec-dialect ladder ([`ladder/`](ladder/))

Holding the problem fixed and varying only the spec's dialect (prescriptive pseudocode →
raw business requirement) locates where the 3B breaks — and the answer is stark:

- **The pass is a knife-edge.** The same L1 spec that greedy-passes 23/23 via `solve_30.py`
  drops to 16/23 when a single **trailing-newline byte** is stripped (controlled, same model
  instance: `23/23` with the newline, `16/23` without). One byte, 7 rows.
- **Below prescriptive pseudocode it collapses to 0/23 — via crashes** (KeyError lookups,
  undefined names, syntax), not numeric drift. Even L2, which keeps the lookup tables
  verbatim, can no longer emit runnable code.
- **Scale raises the cliff:** the 10-rule ladder broke at L2→L3 (tables removed); at 30 rules
  it breaks one rung higher, L1→L2 — the step-by-step imperative recipe itself is
  load-bearing, tables alone aren't enough.
- **Repair loops rescue nothing** (`--repair`): every rung converges 0/2. L1 misses on
  exactly the 7 capital-city rows because of a single wrong constant (Rule R coded `1 - 0.01`
  instead of `1 - 0.10`), and per-row-total feedback never localizes it over 4 iterations
  (it even regresses 16→5); L2–L5 stay crashed. Iteration is not a lever at 30 rules.

Full data and interpretation in [`ladder/README.md`](ladder/README.md).

## Files

- [`spec_30.md`](spec_30.md) — the precise, model-dialect spec handed to the 3B (the deliverable)
- [`solve_30.py`](solve_30.py) — MLX generate → score → repair harness (RUN THIS)
- [`test-cases-30.csv`](test-cases-30.csv) — 23-row dataset, targets baked in
- [`reference_30.py`](reference_30.py) — ground truth; regenerates the dataset, self-checks 23/23
- [`model_solution_30.py`](model_solution_30.py) — a passing solution written from the spec alone (proves the spec is sufficient)
- [`prove_30.py`](prove_30.py) — offline scorer, NO MLX (checks any solution: total_receivables + escrow)
- [`solution_best_30.py`](solution_best_30.py) — the 3B's actual 23/23 output
- [`requirements-source.md`](requirements-source.md) — the original prose + Fahad's raw CSV (provenance)

## How to run

```bash
# Live: 3B generates the solution, harness scores it, writes solution_best_30.py
.venv/bin/python experiments/30-rule/solve_30.py

# Offline: score any candidate (no MLX / no GPU needed)
.venv/bin/python experiments/30-rule/prove_30.py solution_best_30.py

# Regenerate the dataset + validate ground truth against Fahad's column
.venv/bin/python experiments/30-rule/reference_30.py
```

First run downloads `mlx-community/Qwen2.5-Coder-3B-Instruct-4bit` (~1.8 GB) into the shared
`./model_cache`. Expected: **`PASSED 23/23`** on iteration 1.

## Status — validated end-to-end

`solve_30.py` prints `PASSED 23/23` on iteration 1 (greedy) and writes `solution_best_30.py`,
which re-scores 23/23 offline via `prove_30.py`. `reference_30.py` self-checks 23/23 and
matches Fahad's `total Receivable` on all 19 original rows. A spec-only `model_solution_30.py`
also scores 23/23, proving the spec — not any hidden knowledge — carries the result.
