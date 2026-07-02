# White-box repair (`--repair-rules`) — results

The loop feeds per-step intermediate diffs ("row 0: correct through `payment_loading`, but
`commission` = 0.0000, should be 3206.25") and asks the model to expose intermediates so
they can be compared. Run on the three failing rungs, 3 trajectories × up to 6 iterations,
at two repair temperatures. Raw data: `results_repair_rules_t06.json`, `results_repair_rules_t03.json`.

## Best score and convergence, vs single-shot best-of-10

| Level | best-of-10 (no repair) | repair-rules @0.6 | repair-rules @0.3 |
|:-----:|:----------------------:|:-----------------:|:-----------------:|
| L3 Business prose            | 4/12 | 8/12 (0/3) | 7/12 (0/3) |
| L4 Natural rules (tier)      | 3/12 | 4/12 (0/3) | **8/12** (0/3) |
| L5 Original dialect (boolean)| 4/12 | 9/12 (0/3) | **12/12 (converged 1/3, iter 2)** ✅ |

`(c/3)` = trajectories that reached a full 12/12.

## Reading it

- **Per-step feedback works** — the model does fix the flagged step; partial scores rise
  well above the no-repair best-of-N on every rung.
- **Lower repair temperature helps it stick.** At 0.3 the edits are conservative enough that
  fixing the flagged step stops regressing the others: L5 converges to 12/12 in a single
  repair iteration (path `[4, 12]`, saved as `level_5_repaired.py`), and L4 climbs to 8/12.
- **L3 still resists** (best 7–8, never 12). Rebuilding the whole commission chain from pure
  `$`/`%` prose is the hardest cell; conservative edits raise partial correctness but don't
  close it in this budget.
- **The score paths still oscillate** at both temperatures (e.g. `[0, 7, 5, 4, 0, 0]`) — the
  3B's grip on all 13 intermediates at once is shaky, and emitting the extra keys every turn
  destabilizes generation (the `0`s are crashes).

## Takeaway

White-box per-step feedback is a real lever — enough to rescue the boolean rung (L5) and
nearly the tier rung (L4) at low temperature — but it does not reliably rescue the fully
de-scaffolded L3. For a 3B the dependable fix remains the **spec** (hand the table back, or
a spec-repair loop), with white-box repair as a useful booster rather than a guarantee.
