# 3B results — Qwen2.5-Coder-3B-Instruct-4bit

Result sheet for the ladder's star model. Method, spec rungs and the full narrative live
in the [experiment README](../README.md); this folder holds every 3B artifact, all
re-scorable offline:

```bash
python3 experiments/sweet-spot/prove_ladder.py                       # best-of-10 staircase (default)
python3 experiments/sweet-spot/prove_ladder.py --dir 3b --tag greedy # any other tag likewise
```

## The ladder

| Rung | Spec dialect | Greedy | Best-of-10 (pass-rate) | Reachable? |
|:--:|--|:--:|:--:|:--:|
| L1 | Prescriptive pseudocode | **12/12** | **12/12** (3/10) | ✅ |
| L2 | Declarative spec | 9/12 | **12/12** (4/10) | ✅ |
| L3 | Business prose | 3/12 | 4/12 | ❌ |
| L4 | Natural rules (tier) | 3/12 | 3/12 | ❌ |
| L5 | Original dialect (boolean) | 3/12 | 6/12 | ❌ |
| L6 | Tables + natural tier | **12/12** | **12/12** (2/10) | ✅ |
| L7 | Tables + True/False | **12/12** | **12/12** (3/10) | ✅ |
| L8 | Tables + tier + True/False | **12/12** | **12/12** (2/10) | ✅ |

The 2×2 in one line: tables present ⇒ reachable (and greedy-passing, L2's terse volume
prose aside); tables removed ⇒ never reaches 12/12. The failure is the 3-step commission
chain, not the tier/boolean traps.

## Hybrids on the failing rungs (round 2)

| Mode (L3 / L4 / L5, best) | Result |
|--|--|
| extract-then-code (self-scaffold) | tables rebuilt **100% correctly**, code still 0 / 6 / 9 |
| response prefill (tables seeded into the reply) | 4 / 4 / 2 |
| cross-model (7B extracts → 3B codes) | tables perfect, code 4 / 1 / 0 |

Knowledge was never the bottleneck; the coder reads "10% surcharge" as `*= 1.10` and the
loading amounts never exist as variables.

## Repair loops on the failing rungs

| Loop | L3 | L4 | L5 |
|--|:--:|:--:|:--:|
| round-1 white-box (`--repair-rules`) @ 0.6 | 8/12 | 4/12 | 9/12 (oscillates) |
| round-1 white-box @ 0.3 | 7/12 | 8/12 | **12/12 ✅ iter 2** |
| repair 2.0 anchored (prev code in prompt) | 3/12 flat | 3/12 flat | 3/12 flat |
| repair 2.0 `--fresh` (anneal 0.6→0.2, branch 3) | 4/12 | 9/12 | **12/12 ✅ iter 4** |
| repair 2.0 `--fresh` cool-start control (0.3→0.15) | 4/12 | 3/12 | 3/12 |

Two 3B-specific lessons: **anchoring** (showing the model its own code) collapses
candidate variance to zero and flat-lines the loop; and outcomes are a lottery over
candidates — branch-3's extra draws matter, schedule fine-tuning doesn't measurably
(the cool-start control refuted the "hot phase is wasted" hypothesis).

## Files

- `outputs/level_N_solution_s10.py` — best-of-10 sampled winners (the round-1 staircase)
- `outputs/level_N_solution_<tag>.py` — per-mode bests (`greedy` runs overwrite by tag;
  `extract`, `prefill`, `xextract`, `repair2-anchored`, `repair2-fresh`, `repair2-cool`)
- `outputs/level_N_extracted_<tag>.py` — the constants the model rebuilt from prose
- `outputs/level_5_repaired.py` — the round-1 white-box rescue @ 0.3
- `outputs/results_<tag>.{json,md}` — per-run score tables
  (`s10`, `greedy`, `repair_rules_t06/t03`, plus the round-2 tags above)
