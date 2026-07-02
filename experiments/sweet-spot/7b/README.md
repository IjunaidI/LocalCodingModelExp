# 7B results — Qwen2.5-Coder-7B-Instruct-4bit

The scaling arm of the ladder: the **identical** specs, harness, datasets and scorer as
the 3B — only `--model` changes. Method and narrative in the
[experiment README](../README.md). Re-score anything here offline:

```bash
python3 experiments/sweet-spot/prove_ladder.py --dir 7b --tag greedy
python3 experiments/sweet-spot/prove_ladder.py --dir 7b --tag s10
python3 experiments/sweet-spot/prove_ladder.py --dir 7b --tag repair2-fresh 3 4 5
```

## The ladder at 7B (vs the 3B)

| Rung | Spec dialect | 3B greedy | **7B greedy** | 3B best-of-10 | **7B best-of-10 (pass-rate)** |
|:--:|--|:--:|:--:|:--:|:--:|
| L1 | Prescriptive pseudocode | 12/12 | **12/12** | 12/12 | **12/12** (10/10) |
| L2 | Declarative spec | 9/12 | **12/12** | 12/12 | **12/12** (8/10) |
| L3 | Business prose | 3/12 | 4/12 | 4/12 | **12/12** (2/10) |
| L4 | Natural rules (tier) | 3/12 | 4/12 | 3/12 | **12/12** (1/10) |
| L5 | Original dialect (boolean) | 3/12 | 4/12 | 6/12 | **12/12** (2/10) |
| L6 | Tables + natural tier | 12/12 | 10/12 | 12/12 | **12/12** (1/10) |
| L7 | Tables + True/False | 12/12 | **12/12** | 12/12 | **12/12** (9/10) |
| L8 | Tables + tier + True/False | 12/12 | 10/12 | 12/12 | **12/12** (2/10) |

Three findings:

- **The cliff does not move.** Greedy fails every tables-removed rung at 4/12, exactly
  where the 3B breaks. Doubling parameters does not buy a first-try pass on prose.
- **Scale buys reachability.** Best-of-10 reaches 12/12 on L3/L4/L5 — rungs the 3B never
  reached anywhere — but only at 1–2 in 10 reliability. A well-written spec on the 3B
  still beats a prose spec on the 7B.
- **Scale swaps traps.** On the natural-tier rungs the 7B sticks at exactly 10/12
  (17 of 20 samples across L6/L8, greedy included) with a misordered chained ternary —
  `0.05 if v >= 100 else 0.10 if v >= 1000 else 0.0`, whose `0.10` branch is unreachable.
  The article's original Rule-4 trap, new disguise. The additive phrasing (L7) stays
  robust at 9/10.

## Repair 2.0 (`--repair2 --fresh`): closes the board

| Rung | before repair (greedy) | after |
|:--:|:--:|:--:|
| L3 business prose | 4/12 | **12/12 ✅ converged iter 5** |
| L4 natural tier | 4/12 | **12/12 ✅ converged iter 2** |
| L5 original dialect | 4/12 | **12/12 ✅ converged iter 5** |

The white-box loop (per-step intermediate diffs, fresh regeneration, branch-3,
anneal 0.6→0.2) converges the 7B on **all three** de-scaffolded rungs — including L3,
which resisted every other lever in both rounds. The anchored variant (previous code in
the prompt) flat-lines at 4/12 on the 7B too: the anchoring failure mode is not a
small-model quirk.

## Files

- `outputs/level_N_solution_greedy.py` / `_s10.py` — greedy and best-of-10 winners
- `outputs/level_N_solution_repair2-fresh.py` — the three repaired 12/12 solutions
- `outputs/results_greedy.{json,md}`, `results_s10.{json,md}`,
  `results_repair2-fresh.{json,md}` — score tables

Runs used a 16 GB M2 Pro; the 4-bit 7B (~4.3 GB) also fits an 8 GB machine, one model
resident at a time.
