# Sweet-spot experiment — where the spec dialect stops working

The 5-rule spec is easy to author: a non-technical person can write it and the 3B passes.
The 10-rule spec only passes once it's been carefully engineered into the model's dialect
(see [`../10-rule-v2/`](../10-rule-v2/)). **This experiment finds the boundary between
those two worlds** — how much a spec author has to spoon-feed before
`Qwen2.5-Coder-3B-Instruct-4bit` stops producing correct code.

## Method — one variable, everything else constant

Same 10-rule problem, same arithmetic, same 12-row targets at every rung. The harness is
frozen: identical instruction wrapper, identical decoding, identical scorer. **The only
thing that changes between levels is the spec file**, so any change in outcome is
attributable to the spec's dialect alone. The ladder strips one authoring layer per rung,
from the heavily-engineered v2 spec down to the natural original:

| Level | Spec dialect | What it removes vs. the rung above | Rule 4 (volume) | `tax verified` | Rates |
|:-----:|--------------|------------------------------------|-----------------|----------------|-------|
| **L1** | Prescriptive pseudocode | — (mirrors the validated v2 dialect) | additive + "no elif" | yes/no | literal dicts + bare decimals |
| **L2** | Declarative spec | the step-by-step coding recipe | additive (prose) | yes/no | literal dicts + bare decimals |
| **L3** | Business prose | the literal `copy-these-exactly` tables; `%` not decimals | additive (prose) | yes/no | `$`/`%` prose, model builds its own |
| **L4** | Natural rules | re-arms the volume-**tier** phrasing | natural 3-tier band | yes/no | `$`/`%` prose |
| **L5** | Original dialect | re-arms the **True/False** boolean | natural 3-tier band | **True/False** | `$`/`%` prose |

Levels 1–4 score against the `yes/no` dataset; L5 against the `True/False` dataset (identical
targets, max abs diff `0.0`, so scores are directly comparable). A constant, precise
Input-columns data-dictionary is present in every spec — that's the data contract, not a
coding scaffold, so it is *not* one of the variables.

## Results

Best-of-10 sampled attempts per level, temperature 0.4 (full distributions in
[`3b/outputs/results_s10.md`](3b/outputs/results_s10.md)):

| Level | Spec dialect | Pass-rate | Best of 10 | Reachable? |
|:-----:|--------------|:---------:|:----------:|:----------:|
| **L1** | Prescriptive pseudocode | 3/10 | **12/12** | ✅ |
| **L2** | Declarative spec | 4/10 | **12/12** | ✅ |
| **L3** | Business prose | 0/10 | 4/12 | ❌ |
| **L4** | Natural rules (tier) | 0/10 | 3/12 | ❌ |
| **L5** | Original dialect (boolean) | 0/10 | 4/12 | ❌ |

### The sweet spot is the L2 → L3 boundary

- **L1 → L2 costs nothing.** Dropping the imperative "`Start x = 0.0` … do NOT use elif"
  recipe does *not* hurt — L2 is if anything a touch more reliable (4/10 vs 3/10). Plain
  declarative prose is fine **as long as the data tables are handed over literally.**
- **L2 → L3 is the cliff.** The moment the spec stops handing over the literal
  `PRODUCT_RATES` / `CATEGORY_MULTIPLIER` dicts and bare decimals — forcing the model to
  build its own data structures from `$`/`%` business prose — it never once reaches 12/12
  in 10 tries. **The load-bearing scaffold is the literal lookup tables + per-rule
  decimal decomposition, not the step-by-step phrasing.**

### What actually breaks (and what doesn't)

The failures are not where the original diagnosis predicted. Looking at *which rows pass*
at L3–L5, it is always exactly the four rows that are `non-emea` **and** `ach/wire` — the
rows whose region and payment loadings are both zero, i.e. **commission = 0**. Every wrong
row has a non-zero loading, and the error is exactly the missing commission: e.g. L3 row 3
(electronics, EMEA) scores a ratio of `0.8929 = 1 / 1.12`, precisely the effect of dropping
`commission = (region_loading + payment_loading) × 1.2` from the subtotal.

So once the scaffold is gone, the 3B still gets the price table, all three discounts, the
volume tier, **and** the tax withholding (booleans included) right — it mis-assembles the
**3-step commission chain** (`Rule 7 + 8 → ×Rule 9 multiplier → into Rule 10 subtotal`).
The famous volume-tier and True/False traps (L4, L5) are downstream of a break that has
already happened at L3; in the surviving samples the model handles both correctly
(`if 100 <= v < 1000 … elif v >= 1000`; `tax_verified = cell == 'True'`).

### Controls confirm it — keep the table, the traps don't bite

L6–L8 re-run the L4/L5 traps but **keep the literal lookup tables** (branching from L2).
If the traps were the real problem, these would fail; they don't:

| Level | Dialect (tables kept) | Pass-rate | Best of 10 | Reachable? |
|:--:|--|:--:|:--:|:--:|
| **L6** | + natural volume-tier (yes/no) | 2/10 | **12/12** | ✅ |
| **L7** | + True/False boolean | 3/10 | **12/12** | ✅ |
| **L8** | + tier **and** True/False (both) | 2/10 | **12/12** | ✅ |

This is the clean 2×2: with the tables **present**, every dialect (additive or tiered,
yes/no or True/False) is reachable (L1, L2, L6, L7, L8 → 12/12); with the tables
**removed**, none is (L3, L4, L5 → 0/10). **The literal lookup tables are necessary and
nearly sufficient; the tier/boolean traps are neither necessary nor sufficient to break
the model** — even both together (L8) still pass. The traps do cost some reliability
(pass-rate ~2–3/10 vs L1/L2's 3–4/10), but they never gate reachability.

**Takeaway for a spec author:** you can write the 10-rule spec in plain declarative prose
— but you must (a) hand over the lookup tables verbatim and (b) decompose any multi-step
derived quantity (here, commission) into explicit named sub-steps. Narrating a multi-step
formula in one breath is what a 3B cannot reliably reconstruct.

## Methodology notes (for anyone reproducing)

- **Single greedy is a knife-edge.** A one-line *title* change flipped L1's deterministic
  greedy output from 12/12 to 0/12 (it dropped the `PRODUCT_RATES` definition). Evaluate
  a small model by **sampling**, not by one greedy roll — hence best-of-N + pass-rate.
- **"Reachable" (best-of-N hits 12/12) vs "reliable" (pass-rate).** For a model this
  single-shot-noisy, reachability is the meaningful capability threshold; even the passing
  L1/L2 are only 30–40% reliable per attempt.
- **Two harness-wording artifacts were removed** because they dominated results, not the
  dialect: "*strip spaces from headers*" made the model delete the space inside
  `payment type` and crash, and "*never crash*" induced `try/except` that swallowed the
  real bug. The wrapper now says exactly what to do, and identically for every level.
- `--repair` runs the repo's generate→score→repair loop (iterations-to-converge) as an
  alternative metric; left available but not the headline here.

## Rescuing the failing rungs — the `--repair-rules` loop

The built-in `--repair` loop feeds a **scalar total diff** (`row 3: got X, expected Y`),
but L3's failure is a *localizable structural omission* — the whole commission chain is
dropped — and a single wrong number can't say which of ten steps is missing. So we built
`--repair-rules`, a **white-box loop**: a reference computes every intermediate in the
pipeline (`reference_intermediates`), and on each failing row the loop reports the *first*
step that diverges — *"row 0: correct through `payment_loading`, but `commission` = 0.0000,
should be 3206.25."* (It asks the model to expose those intermediates so they can be compared.)

**Result — it helps, and at a low repair temperature it rescues the boolean rung** (3
trajectories × up to 6 iters; full data + paths in
[`3b/outputs/results_repair_rules.md`](3b/outputs/results_repair_rules.md)):

| Level | best-of-10 (no repair) | `--repair-rules` @0.6 | `--repair-rules` @0.3 |
|:--:|:--:|:--:|:--:|
| L3 | 4/12 | 8/12 (0/3) | 7/12 (0/3) |
| L4 | 3/12 | 4/12 (0/3) | **8/12** (0/3) |
| L5 | 4/12 | 9/12 (0/3) | **12/12 — converged 1/3, iter 2** ✅ |

The localization works — the model *does* fix the flagged step. At the default repair
temperature (0.6) the score paths **oscillate** (`[4, 0, 1, 0, 0, 9]`): fixing one step
regresses another, so nothing converges. **Dropping the repair temperature to 0.3** makes
the edits conservative enough to stick: **L5 converges to a full 12/12 in a single repair
iteration** (path `[4, 12]`, saved as [`3b/outputs/level_5_repaired.py`](3b/outputs/level_5_repaired.py)),
and L4 climbs to 8/12. **L3 still resists** — rebuilding the whole commission chain from pure
`$`/`%` prose is the hardest cell, and conservative edits raise partial correctness but don't
close it in this budget. (Emitting 12 extra intermediate keys every turn also destabilizes a
3B; the residual `0`s are crashes from the heavier output contract.)

**So white-box repair is a real lever** — enough to rescue the boolean dialect and nearly the
tier dialect at low temperature — **but not a guarantee for a fully de-scaffolded spec.** The
L6–L8 controls already showed the traps don't need rescuing (they pass with tables); the one
stubborn cell is table-removal at L3, where the dependable fix is still the **spec** (put the
table back, or a spec-repair loop) rather than out-arguing the model with cleverer diffs.
Levers left to try on L3: more iterations/trajectories, or a diagnostic pass that instruments
once then drops the instrumentation for the fix.

## Round 2 — scale (7B), hybrids, and repair 2.0

Round 1 ended with one stubborn cell: L3, the fully de-scaffolded business prose. Round 2
asks three questions about it. **Does the cliff move with scale?** (run the identical
ladder on `Qwen2.5-Coder-7B-Instruct-4bit`). **Is missing knowledge the bottleneck?**
(hybrids that hand the tables back). **Can a better loop out-argue the dialect?**
(repair 2.0). Everything below re-scores offline via `prove_ladder.py --dir 3b|7b --tag <tag>`;
per-model result sheets and artifacts live in [`3b/`](3b/README.md) and [`7b/`](7b/README.md).

### 7B: the cliff doesn't move — reachability does

Same 8 rungs, same harness, only `--model` changes
([`7b/outputs/results_greedy.json`](7b/outputs/results_greedy.json),
[`7b/outputs/results_s10.json`](7b/outputs/results_s10.json)):

| Rung | 3B greedy | 7B greedy | 3B best-of-10 | 7B best-of-10 (pass-rate) |
|:--:|:--:|:--:|:--:|:--:|
| L1 | 12/12 | 12/12 | 12/12 | 12/12 (10/10) |
| L2 | 9/12 | **12/12** | 12/12 | 12/12 (8/10) |
| L3 | 3/12 | 4/12 | 4/12 ❌ | **12/12** (2/10) |
| L4 | 3/12 | 4/12 | 3/12 ❌ | **12/12** (1/10) |
| L5 | 3/12 | 4/12 | 6/12 ❌ | **12/12** (2/10) |
| L6 | 12/12 | 10/12 | 12/12 | 12/12 (1/10) |
| L7 | 12/12 | 12/12 | 12/12 | 12/12 (9/10) |
| L8 | 12/12 | 10/12 | 12/12 | 12/12 (1/10) |

- **Greedy: the cliff is in the same place.** The 7B passes the structured rungs and
  fails every tables-removed rung at 4/12 — doubling parameters does not buy a first-try
  pass on business prose. Spec structure (L1/L2/L7 at 8–10/10 pass-rate) is still worth
  more than 4 billion extra parameters (L3–L5 at 1–2/10).
- **Sampling: scale buys reachability.** The 7B reaches 12/12 on L3/L4/L5 within 10
  samples — rungs the 3B *never* reached. The capability is present at 7B; the dialect
  still makes it a ~1-in-5-to-10 event instead of a habit.
- **Scale swaps traps.** On the natural-tier controls the 7B gets *stuck at exactly
  10/12* in 17 of 20 samples (L6+L8), always the two `volume ≥ 1000` rows: it writes
  `0.05 if volume >= 100 else 0.10 if volume >= 1000 else 0.0` — a misordered chained
  ternary whose `0.10` branch is unreachable. That is the article's original Rule-4 tier
  trap resurfacing in the bigger model in a new surface form (the 3B collapsed the
  bounds; the 7B misorders the ternary). The additive phrasing (L7) stays robust for
  both sizes.

### Hybrids: the model KNOWS the tables — it can't wield them from prose

Three ways of handing the tables back to the failing rungs
([`results_extract-s10.json`](3b/outputs/results_extract-s10.json),
[`results_prefill-s10.json`](3b/outputs/results_prefill-s10.json),
[`results_xextract.json`](3b/outputs/results_xextract.json)):

| Mode (L3 / L4 / L5, best) | What it does | Result |
|--|--|--|
| `--extract` (self-scaffold) | model rebuilds the tables from the prose, then codes with them appended | extraction **correct 100% of the time**, code still fails: 0 / 6 / 9 |
| `--prefill` | reply is *seeded* so it already starts with the true tables as code | 4 / 4 / 2 — no rescue |
| `--extract-model 7B` (cross-model) | 7B extracts, 3B codes | extraction perfect, code 4 / 1 / 0 |

Every extraction — both model sizes, every rung, every run — rebuilt
`PRODUCT_RATES` / `CATEGORY_MULTIPLIER` exactly. **Knowledge was never the bottleneck.**
With correct tables in hand (its own!), the coder still mis-assembles the same chain:
it reads "a **10%** surcharge" as `receivable *= 1.10` instead of materializing a
separate `0.10 * receivable` amount, so the two loading amounts never exist as values
and the commission has nothing to sum. (A second seam: the extractor writes `"1"`
string keys, half the coder samples index with `int` — the crash rows in the extract
column.) What L1/L2/L6–L8 really provide is not the table *values* but the
**code-shaped decomposition** — bare decimals and named quantities that force each
step to exist as a variable.

### Repair 2.0: show a 3B its own code and it stops exploring

Round 1's white-box loop (`--repair-rules`, temp 0.3) rescued L5 but regenerated from
scratch each iteration. Repair 2.0 (`--repair2`) adds four levers: the previous code in
the prompt + edit-only-the-culprit, a freeze-list of steps verified correct on every row,
branch-3 candidate selection per iteration, and temperature annealing. The A/B that
matters ([`results_repair2-anchored.json`](3b/outputs/results_repair2-anchored.json) vs
[`results_repair2-fresh.json`](3b/outputs/results_repair2-fresh.json), per-iteration logs
in the run logs):

| Variant | L3 | L4 | L5 |
|--|:--:|:--:|:--:|
| anchored (prev code in prompt), 3B | 3/12 flat | 3/12 flat | 3/12 flat |
| `--fresh` (regenerate from feedback), 3B | 4/12 | 9/12 ↗ | **12/12 ✅ iter 4** |
| `--fresh` cool-start (0.3→0.15, 8 iters), 3B | 4/12 | 3/12 | 3/12 |
| `--fresh`, **7B** | **12/12 ✅ iter 5** | **12/12 ✅ iter 2** | **12/12 ✅ iter 5** |

- **Anchoring is the failure mode, cleanly isolated.** In the anchored runs the
  instrumentation pass *succeeds* (all 13 intermediates exposed, culprit named,
  freeze-list built) — and then every one of 12 repair candidates per level scores an
  identical 3/12 at every temperature. Same levers, same feedback; remove the previous
  code from the prompt and candidate variance explodes (`[12, 2, 0]` in one L5
  iteration). A 3B shown its own code copies it; forced to regenerate, it explores.
- **Branch-3 is where the wins come from.** Nearly every scoring iteration picks a
  single good candidate out of `[x, 0, 0]` — three lottery tickets per iteration
  instead of one.
- **At 3B the outcome is a lottery over candidates, not a schedule effect.** We
  hypothesized the hot anneal phase (0.6→0.4, scores 0–2 everywhere) was wasted budget —
  the cool-start control (`--anneal 0.3:0.15`, 8 iterations) *refuted* that: L5 did not
  re-converge and nothing improved. With single trajectories, whether a run converges
  turns on drawing one good candidate; total candidate volume (branch × iterations ×
  trajectories) matters, schedule fine-tuning doesn't measurably.
- **7B + fresh white-box repair closes the board**: converged 12/12 on all three
  de-scaffolded rungs within 5 iterations
  ([`7b/outputs/results_repair2-fresh.json`](7b/outputs/results_repair2-fresh.json)) — including
  L3, the cell nothing else cracked. Business prose → correct code, fully on-device.

### Round-2 takeaway

For the 10-rule spec on an entry-level Mac, the working recipes are now, in order of
cost: **(1)** write the spec in the model's dialect (tables + bare decimals + named
steps) and a 3B passes greedy, first try; **(2)** keep the business prose but run
**7B + fresh white-box repair** — converged 12/12 on all three prose rungs in ≤5
iterations in our runs; **(3)** sampling the 7B reaches 12/12 but at 1–2 in 10
reliability. What does *not*
work: handing back the lookup tables (any of three ways — the knowledge was never
missing), showing a small model its own code during repair (anchoring flat-line), or
expecting scale alone to fix a first-try dialect failure.

## Files
- `specs/level_1.md … level_8.md` — the rungs. L1–L5 strip scaffolding down the ladder;
  L6–L8 are controls (tables kept, traps re-armed). Everything above the first `#` heading
  is an HTML comment (authoring notes, incl. trap descriptions) and is **stripped before
  the spec reaches the model**.
- `run_ladder.py` — **run this.** `--samples N` (single-shot best-of-N, default greedy),
  `--repair` (scalar-diff repair loop), `--repair-rules` (white-box per-step feedback),
  `--levels 1,4,5`, `--temp`, `--trajectories`, `--max-iters`. Round-2 additions:
  `--model` (any Qwen2.5-Coder size — artifacts are routed automatically into that size's
  folder), `--tag` (mode suffix, auto-set per mode), `--extract` (+ optional
  `--extract-model` for the cross-model hybrid), `--prefill`, and `--repair2` with
  `--fresh` / `--branch` / `--anneal start:end`.
- **`3b/`** and **`7b/`** — one folder per model size, each with its own result-sheet
  `README.md` and an `outputs/` holding every saved solution and results table for that
  size. Same filenames on both sides (`level_N_solution_<tag>.py`,
  `results_<tag>.{json,md}`), so the two are directly diffable. See
  [`3b/README.md`](3b/README.md) and [`7b/README.md`](7b/README.md).
- `prove_ladder.py` — offline re-scorer, no MLX needed. `--dir 3b|7b` picks the model
  folder, `--tag` the run (defaults re-score the 3B best-of-10 staircase).
- `test-cases-v2.csv` / `test-cases.csv` — the `yes/no` and `True/False` datasets.
- `3b/outputs/level_5_repaired.py` — the 12/12 solution the round-1 white-box loop
  produced for L5 (@0.3); the round-2 repaired winners are
  `{3b,7b}/outputs/level_N_solution_repair2-fresh.py`.
- `model_cache` — symlink to the repo-root shared cache (gitignored).

## Run
```bash
# The staircase (best-of-10 sampled attempts per level)
.venv/bin/python experiments/sweet-spot/run_ladder.py --samples 10 --temp 0.4

# Repair loop (scalar total diff), iterations-to-converge
.venv/bin/python experiments/sweet-spot/run_ladder.py --repair --trajectories 3

# White-box repair: per-step intermediate feedback (tries to rescue the failing rungs)
.venv/bin/python experiments/sweet-spot/run_ladder.py --repair-rules --levels 3,4,5

# Re-score the saved outputs anywhere, no model needed (defaults: 3B staircase)
python3 experiments/sweet-spot/prove_ladder.py

# --- Round 2 ---
# The identical ladder on the 7B (greedy, then best-of-10). Artifacts route to
# 7b/outputs/ automatically; tags auto-set to greedy / s10.
.venv/bin/python experiments/sweet-spot/run_ladder.py --model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit
.venv/bin/python experiments/sweet-spot/run_ladder.py --model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit --samples 10 --temp 0.4

# Hybrids on the failing rungs (self-scaffold / prefill / 7B-extracts-3B-codes)
.venv/bin/python experiments/sweet-spot/run_ladder.py --extract --levels 3,4,5
.venv/bin/python experiments/sweet-spot/run_ladder.py --prefill --levels 3,4,5
.venv/bin/python experiments/sweet-spot/run_ladder.py --extract --extract-model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit --levels 3,4,5 --tag xextract

# Repair 2.0 — the winning configuration (fresh regeneration + branch-3 + anneal)
.venv/bin/python experiments/sweet-spot/run_ladder.py --repair2 --fresh --levels 3,4,5 --max-iters 6 --branch 3 --anneal 0.6:0.2 --trajectories 1 --tag repair2-fresh
.venv/bin/python experiments/sweet-spot/run_ladder.py --repair2 --fresh --levels 3,4,5 --max-iters 6 --branch 3 --anneal 0.6:0.2 --trajectories 1 --model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit --tag repair2-fresh

# Offline re-score of any run: --dir picks the model size, --tag the run
python3 experiments/sweet-spot/prove_ladder.py --dir 7b --tag repair2-fresh 3 4 5
```
