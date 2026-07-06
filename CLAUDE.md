# 10-rule spec — Qwen2.5-Coder-3B handoff

Context for Claude Code. This repo makes the Qwen2.5-Coder-3B model emit correct code
for the 10-rule pricing spec from Ansar Muhammad's SLM experiment.

The user-facing overview lives in [`README.md`](README.md); the full narrative is in
[`docs/slm-coding-experiment.md`](docs/slm-coding-experiment.md). This file is the
working handoff for the v2 deliverable.

## Repository layout
```
experiments/5-rule/            Minimal 5-rule spec — 3B passes 12/12, first try.
experiments/10-rule-original/  Original True/False 10-rule baseline — trips the model.
experiments/10-rule-v2/        ★ The deliverable — same 10 rules re-dialected → 12/12.
experiments/sweet-spot/        5-level spec ladder — locates the dialect break (L2→L3).
experiments/30-rule/           Scale test — a fresh ~30-rule spec; 3B passes 23/23 first try.
docs/                          Writeup.
finetune-with-mlx/             Sibling subproject (LoRA fine-tuning).
unit-test-11-mar-26/           Sibling subproject (procurement-reader tests).
model_cache/                   Shared model cache (gitignored; symlinked into experiments).
```
Each `experiments/*` folder is self-contained and independently runnable, with its own
`README.md`.

## The task (from engineering director)
Get `Qwen2.5-Coder-3B-Instruct-4bit` (via Apple MLX) to generate a
`process_calculations(csv_path)` that passes **12/12** on the 10-rule pricing &
commission spec. Model is fixed — use the **Coder** variant, not general Qwen,
and do not swap in another model. The lever is the SPEC, not the model.

Source article: https://www.linkedin.com/pulse/coding-small-language-models-hosted-your-local-ansar-bbbxf/
Source repo:    https://github.com/ansarmuhammad/mlx (branch: mlx)

## Why the 3B fails on the original 10-rule spec (diagnosed, reproduced)
Running the article's harness reproduces the 7B's best attempt at **1/12**, every
row 2–5% off. Two root-cause bugs, both linguistic, not capability:

1. **Rule 4, the volume tier.** Spec says `<100 → 0%`, `<1000 → 5%`, `≥1000 → 10%`.
   The model collapses the three-way conditional to
   `0.05 if v<100 else (0.1 if v<1000 else 0.1)` — wrong in two of three branches.
2. **Rule 10, the boolean.** The `tax verified` cell is the *string* `"False"`,
   which is truthy in Python, so `not row["tax verified"]` skips withholding
   exactly when it should apply.

## The fix (the deliverable)
`experiments/10-rule-v2/spec_simple_v2.md` re-expresses the SAME ten rules in the
model's dialect:
- Rule 4 decomposed into two independent single-condition adds
  (`if v>=100: +0.05`, `if v>=1000: +0.05`) with an explicit "no elif".
- `tax verified` expressed as `yes`/`no` text in both spec AND data.
- Every percentage given as a bare decimal; rates + category multiplier as dict lookups.

The arithmetic is bit-identical to the original: the yes/no dataset's targets match the
True/False targets with max abs diff = 0.0. Same problem, phrased so the model can't trip.

## Files (in `experiments/10-rule-v2/`)
- `spec_simple_v2.md`        — the rewritten spec (the actual deliverable)
- `solve_simple_v2.py`       — MLX harness: generate → score → repair loop (RUN THIS)
- `test-cases-v2.csv`        — 12-row dataset (yes/no flag), targets baked in
- `reference_simple_v2.py`   — ground truth; regenerates the dataset, self-checks 12/12
- `model_solution_v2.py`     — a passing reference solution (proves the spec is sufficient)
- `prove_v2.py`              — offline scorer, NO MLX needed (check any solution)
- `buggy_solution_original.py` — the article's failing output (1/12), for before/after
- `solution_best_v2.py`      — the model's actual 12/12 output

## Environment (Apple Silicon only — MLX requires a Mac)
Validated with system **Python 3.9**, which pins the stack to `mlx-lm 0.29.1`
(newer `mlx-lm` needs Python ≥ 3.10).
```bash
python3 -m venv .venv
.venv/bin/python -m pip install mlx-lm
```

## How to run
```bash
# Live generation → score → writes solution_best_v2.py
.venv/bin/python experiments/10-rule-v2/solve_simple_v2.py

# Offline check of any candidate (works anywhere, no model needed)
.venv/bin/python experiments/10-rule-v2/prove_v2.py solution_best_v2.py
```
First run downloads `mlx-community/Qwen2.5-Coder-3B-Instruct-4bit` (~1.8 GB) into the
shared `./model_cache`.

## Status — validated end-to-end
`solve_simple_v2.py` prints `PASSED 12/12` and writes `solution_best_v2.py`, on
iteration 1 (greedy). Confirmed on Apple Silicon: the live 3B run scored 12/12 with no
repairs, and the model's output re-scores 12/12 via `prove_v2.py`. Also verified offline:
ground truth 12/12, targets identical across flag formats (diff 0.0), and buggy baseline
1/12.

## If you want to extend
- Benchmark alternates: the harness is model-agnostic — change `MODEL` at the top of
  `experiments/10-rule-v2/solve_simple_v2.py` and re-run against this same spec + dataset
  for a clean apples-to-apples read. (Task says keep Coder-3B, but this is the clean way
  to test.)
- Improve the repair loop: it currently feeds a numeric diff, which can't localize a bug.
  Feeding per-rule intermediate values would help — a separate lever from the spec.
- Complexity sweet spot — DONE, see `experiments/sweet-spot/`. An 8-spec ladder (same 10
  rules, only the spec dialect varies) locates the break at the **L2 → L3 boundary**:
  declarative prose is fine, but removing the literal `copy-these-exactly` lookup tables
  is the cliff. The failing rungs don't fail on the tier/boolean traps (the model handles
  those in prose) — they fail to assemble the 3-step commission chain. Controls L6–L8
  (tables kept, traps re-armed) all reach 12/12, proving the tables — not the traps — are
  load-bearing. Two methodology findings baked in: single greedy is a knife-edge (a
  one-line title change flipped L1 from 12/12 to 0/12 — evaluate by sampling), and the
  instruction wrapper's wording ("strip spaces", "never crash") can dominate results, so
  it's now precise and constant. Metrics: `run_ladder.py --samples N` (best-of-N staircase)
  or `--repair` (iterations to converge). Offline re-score with `prove_ladder.py`.
- Rescue attempt — DONE. `run_ladder.py --repair-rules` is a white-box loop: a reference
  (`reference_intermediates`) computes every pipeline intermediate and the loop tells the
  model the FIRST step that diverges ("`commission` = 0.0, should be 3206.25"). At the
  default repair temp (0.6) it lifts partial scores but converges 0/3 (paths oscillate —
  fixing one step regresses another). At `--repair-temp 0.3` the conservative edits stick:
  **L5 converges to 12/12 in one repair iter** (saved `3b/outputs/level_5_repaired.py`), L4
  climbs to 8/12, but L3 still resists (best 7–8). So white-box repair is a real booster
  (rescues the boolean rung) but not a guarantee for a fully de-scaffolded spec; the durable
  lever remains the spec (put the table back / spec-repair). See `3b/outputs/results_repair_rules.md`.
- Round 2 (scale / hybrids / repair 2.0) — DONE, 2026-07-02. Full data + narrative in
  `experiments/sweet-spot/README.md` § "Round 2"; artifacts are segregated per model size
  into `experiments/sweet-spot/3b/outputs/` and `7b/outputs/` (same filenames both sides,
  each folder has its own result-sheet README); every run re-scores offline with
  `prove_ladder.py --dir 3b|7b --tag <tag>`. The v2 deliverable spec also passes the 7B
  first-try greedy (`solve_simple_v2.py --model …7B… → solution_best_v2_7b.py`, 12/12).
  Headlines: (1) **the cliff doesn't move with scale** —
  7B greedy fails L3–L5 at 4/12 exactly where the 3B does, but best-of-10 makes all three
  *reachable* (pass-rate 1–2/10); the 7B also re-arms the article's tier trap in a new form
  (misordered chained ternary → stuck at 10/12 on L6/L8). (2) **Knowledge was never the
  bottleneck** — `--extract` / `--prefill` / `--extract-model` hand the tables back three
  ways; extraction is 100% correct on both sizes, yet the coder still reads "10% surcharge"
  as `*= 1.10` and never materializes the loading amounts (no rescue). (3) **Repair 2.0**
  (`--repair2`): anchored variant (prev code in prompt) flat-lines — 12 identical 3/12
  candidates per level, cleanly logged; `--fresh` (regenerate from feedback + branch-3 +
  anneal) rescues L5 on the 3B and **converges 12/12 on ALL of L3/L4/L5 with the 7B in ≤5
  iters** — the L3 cell nothing else cracked. Winning recipe:
  `--repair2 --fresh --branch 3 --anneal 0.6:0.2`. At 3B the outcome is a lottery over
  candidates (a cool-start control at 0.3:0.15 refuted the "hot phase is wasted"
  hypothesis — L5 did not re-converge): candidate volume matters, schedule fine-tuning
  doesn't measurably.
- Scale test — a fresh ~30-rule spec (DONE, 2026-07-06, `experiments/30-rule/`). A new,
  much bigger requirement from Fahad (27 lettered rules A–V, X–AB: a deep ordered pipeline
  + a 10-step total-receivables discount cascade). Ground truth is `reference_30.py`, built
  from the prose and validated to reproduce Fahad's `total Receivable` column **exactly on
  all 19 original rows** (Fahad's CSV is input-only; his post-cascade column is incomplete,
  so the cascade is computed from the prose, multiplicatively). Dataset = 19 Fahad rows
  (booleans → yes/no) + 4 synthetic coverage rows so every rule A–AB fires. **The 3B passes
  23/23 on the first greedy attempt** with the precise dialect spec (`spec_30.md`) — the
  thesis holds at 3× the rules. Key finding: the *first* precise spec still crashed greedy,
  and NOT on arithmetic — on the lookups (`PRODUCT_RATES["1"]` vs int keys → KeyError;
  `QUARTER_LOADING["Q2"]` vs lowercase keys). Fix: key every table to the data's exact
  type/casing (product ids as strings, quarter matched upper-case, Rule G as additive
  `if`s), which extends the 10-rule "hand over the tables" lesson to "hand them over keyed
  to match the data." Also hardened the repair loop to feed the traceback (crashes localize;
  greedy passed before it was needed). Offline re-score: `prove_30.py` (total_receivables +
  escrow). A spec-only `model_solution_30.py` scores 23/23, proving the spec carries it.
  Phase 2 — the dialect ladder (`experiments/30-rule/ladder/`, `run_ladder_30.py`, 5 rungs
  L1 pseudocode → L5 raw requirement, greedy + best-of-5): two sharp findings. (1) **The
  pass is a knife-edge** — L1 (= the deliverable spec) greedy-passes 23/23 via `solve_30.py`
  but scores 16/23 in the ladder; the two prompts differ by exactly ONE byte (a trailing
  newline `.strip()` removes), and a controlled same-instance test confirms `23/23` with it
  vs `16/23` without — one byte, 7 rows (the extreme of the sweet-spot "greedy is a
  knife-edge" caution). (2) **Scale raises the cliff to L1→L2**: below prescriptive
  pseudocode the 3B collapses to 0/23 and the failures are CRASHES (KeyError lookups,
  undefined names, syntax) not numeric drift — even L2, which keeps the lookup tables
  verbatim, can't emit runnable code. The 10-rule cliff was L2→L3 (tables); at 30 rules the
  step-by-step imperative recipe itself is load-bearing, tables alone aren't enough. (3)
  **Repair loops rescue nothing** (`run_ladder_30.py --repair`, iter1 greedy + localized
  feedback, 2 trajectories × 5 iters): every rung converges 0/2. L1's stripped-prompt greedy
  misses on exactly the 7 capital-city rows from a single wrong constant (Rule R coded
  `1 - 0.01` not `1 - 0.10`), and per-row-total feedback never localizes it (holds at 16/23,
  one trajectory regresses to 5); L2–L5 stay crashed (at L3 the model even wraps rows in a
  try/except that skips them → wrong return shape). Scalar/exception repair can't localize in
  a 27-rule pipeline — matches the sweet-spot plain-`--repair` 0/3; only `--repair2 --fresh`
  cracked hard rungs there, but that targets numeric oscillation, not the unrunnable-code
  failure seen here. Full data in `ladder/README.md`.
