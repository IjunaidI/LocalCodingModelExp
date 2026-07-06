# 30-rule spec-dialect ladder — where the 3B breaks

Phase 2 of the 30-rule experiment: hold the problem and the 23 targets fixed, vary **only
the spec's dialect** from prescriptive pseudocode (L1) down to the raw business requirement
(L5), and find the rung where `Qwen2.5-Coder-3B` stops producing correct code. The 30-rule
analogue of [`../../sweet-spot/`](../../sweet-spot/).

Metric: 1 greedy attempt + 4 sampled (temp 0.4) per rung, scored on `total_receivables`
**and** `escrow`. Run: `.venv/bin/python experiments/30-rule/run_ladder_30.py`.

## Results

| Rung | Spec dialect | Greedy | Best-of-5 | Pass-rate | Dominant failure |
|:--:|--|:--:|:--:|:--:|--|
| L1 | prescriptive pseudocode (= `spec_30.md`) | 16/23 \* | 16/23 | 0/5 | numeric drift |
| L2 | declarative prose, **tables kept verbatim** | 0/23 | 0/23 | 0/5 | **crashes** (KeyError lookups, undefined names) |
| L3 | business prose, tables removed | 0/23 | 0/23 | 0/5 | crashes |
| L4 | natural rules (`%`, prose tiers) | 0/23 | 0/23 | 0/5 | crashes (syntax/undefined) |
| L5 | raw requirement (True/False) | 0/23 | 0/23 | 0/5 | crashes |

\* **L1 is the same spec that passes 23/23 via `solve_30.py`.** The 16/23 here is not a
different spec — see finding 1.

## Finding 1 — the 30-rule pass is real, but a knife-edge (one byte moves 7 rows)

`solve_30.py` drives L1's spec to **23/23** on greedy, reproducibly. The ladder feeds the
*same* spec and greedy-scores **16/23**. The two prompts differ by **exactly one character**
— a trailing newline the ladder's `.strip()` removes (`8453` vs `8452` chars, otherwise
byte-identical). A controlled back-to-back test on one model instance:

```
WITH trailing newline (deliverable):  23/23
WITHOUT trailing newline (ladder L1): 16/23
=> one-byte prompt change moved the score by 7 rows
```

Greedy is deterministic, so this is causal, not variance. It is the sweet-spot experiment's
"single greedy is a knife-edge — evaluate by sampling" caution in its most extreme form: at
30 rules a single whitespace byte swings a third of the rows. The deliverable pass stands
(its exact prompt passes every time), but its margin is one newline wide — and best-of-5 did
**not** recover 23/23 from the stripped prompt.

## Finding 2 — below prescriptive pseudocode it collapses to 0/23, via *crashes*

L2–L5 all score **0/23 on best-of-5**, and the failures are overwhelmingly **crashes** —
`KeyError` on a table lookup, an undefined name, a syntax error — not subtle numeric drift.
Once the numbered, imperative step-by-step recipe is gone, the 3B can no longer even emit
*runnable* code for a 27-rule pipeline: it mis-keys the lookups (int vs string, casing),
references variables before defining them, or mangles the syntax of a long function. The few
runs that executed still scored 0.

## Finding 3 — scale RAISES the cliff (L1→L2, not L2→L3)

The 10-rule sweet-spot ladder found declarative-prose-with-tables (L2) still reached 12/12,
and the cliff was **L2→L3** (removing the literal lookup tables). At 30 rules the cliff moves
**up one rung, to L1→L2**: L2 keeps the lookup tables **verbatim** and still collapses to
0/23. So at this scale the tables are no longer sufficient scaffolding — the *step-by-step
imperative recipe itself* is load-bearing. More rules ⇒ the small model needs the whole
pipeline spelled out imperatively, not just the data handed over.

**Takeaway.** For a 27-rule spec on a 3B, the usable dialect is a razor-thin band at the very
top of the ladder: fully prescriptive pseudocode, keyed to the data, and even then the pass
is one whitespace byte wide. Anything more natural doesn't degrade gracefully — it stops
compiling.

## Files

- [`specs/level_1.md`](specs/level_1.md) … [`level_5.md`](specs/level_5.md) — the five rung specs (only the dialect varies)
- [`../run_ladder_30.py`](../run_ladder_30.py) — the ladder harness (greedy + best-of-N)
- [`results_ladder.md`](results_ladder.md) / `results_ladder.json` — the raw result sheet
- `level_N_solution.py` — the best attempt saved per rung
- [`../test-cases-30-tf.csv`](../test-cases-30-tf.csv) — the True/False dataset variant used by L5 (same targets)
