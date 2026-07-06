# Small language models on a pricing spec — the complexity floor

Can a small, locally-hosted LLM (Apple MLX, 8 GB M1) write **numerically correct**
business logic? This repo pins down *where* it breaks and *why* — and shows that the
lever is the **spec, not the model**.

The task throughout: get a model to generate a `process_calculations(csv_path)` that
applies a pricing/commission ruleset and matches ground-truth totals on all 12 rows.

## The main insight

It is **not** the number of rules that breaks a small model — it is the **difficulty of
the individual constructs**. Re-express the *same* rules so each is a single unambiguous
operation and a 3B model gets them right.

Two constructs broke `Qwen2.5-Coder-3B` on the 10-rule spec:

1. **Multi-tier conditionals.** `<100 → 0%, <1000 → 5%, ≥1000 → 10%` gets collapsed
   (both upper branches emitted as `0.1`). Fix: two independent additive `if`s
   (`if v>=100: +0.05`, `if v>=1000: +0.05`).
2. **Boolean parsing.** The cell `"False"` is a *truthy string* in Python, so
   `not row["tax verified"]` skips withholding exactly when it should apply. Fix: use
   `yes`/`no` text and compare explicitly.

A third lever helps: **pre-state the arithmetic** (say "multiply by 0.95", not "5%
discount") so the model doesn't have to translate prose into math.

## Experiment progression

| Spec | Model | Score | What it shows |
|---|---|---|---|
| 17 rules | 0.5B | crashes | too much for the smallest model |
| 17 rules | 3B / 7B | 0/19 | header + total-formula bugs |
| 10 rules (original) | 3B | 3/12 | multi-tier + boolean constructs break it |
| 10 rules (original) | 7B | 1/12 | architecture right, ~2–5% off on detail bugs |
| **5 rules** | **3B** | **12/12** ✅ | removing hard constructs fixes it |
| **10 rules (v2 re-dialect)** | **3B** | **12/12** ✅ | **same 10 rules, re-phrased → passes** |
| **~30 rules (v2 dialect)** | **3B** | **23/23** ✅ | **thesis holds at 3× the rules — key the tables to the data** |

The last row is the point: keeping all ten rules but rewriting them in the model's
dialect closes the gap from 1/12 to **12/12 on the first greedy attempt**. Same
arithmetic (max abs diff vs. the original targets = 0.0), phrased so the model can't trip.

## Pinning the boundary — the spec ladder

[`experiments/sweet-spot/`](experiments/sweet-spot/) turns the v2 → original gap into a
5-rung ladder (same 10 rules, same targets, only the spec dialect changes) and finds the
exact rung where the 3B stops producing correct code:

| Rung | Spec dialect | Best of 10 | Reachable? |
|:--:|--|:--:|:--:|
| L1 | prescriptive pseudocode (= v2) | 12/12 | ✅ |
| L2 | declarative prose, **literal tables kept** | 12/12 | ✅ |
| L3 | business prose, **tables removed** (`$`/`%`) | 4/12 | ❌ |
| L4 | + natural volume-tier phrasing | 3/12 | ❌ |
| L5 | + True/False boolean (= original) | 4/12 | ❌ |

**The break is the L2 → L3 boundary, and it's a sharper result than the two-trap story
above.** Dropping the step-by-step recipe (L1 → L2) costs nothing; dropping the literal
`copy-these-exactly` lookup tables (L2 → L3) is the cliff. And the failures aren't the
tier/boolean traps at all — at L3–L5 the model gets those right; it's the **3-step
commission chain** (`(region + payment loading) × category multiplier`) it can no longer
assemble from prose. Only the four zero-commission rows survive.

Three **control** rungs (L6–L8) nail it down: keep the literal tables but re-arm the tier
and boolean traps — all three still reach **12/12**, even both traps together. So the
literal lookup tables are necessary and nearly sufficient; the famous traps are neither.
So: plain prose is fine, but hand over the data tables verbatim and name every multi-step
derived quantity. Full method, evidence, and reproduction in the folder's
[`README`](experiments/sweet-spot/README.md).

## Repository layout

```
experiments/
├── 5-rule/            Minimal 5-rule spec. 3B passes 12/12, first try.
├── 10-rule-original/  The True/False 10-rule baseline that trips the model (the "before").
├── 10-rule-v2/        ★ The deliverable: same 10 rules re-dialected → 12/12.
├── sweet-spot/        5-level spec ladder pinning the exact dialect boundary where it breaks.
└── 30-rule/           Scale test: a fresh ~30-rule spec (27 rules) → 3B passes 23/23 first try.
docs/
└── slm-coding-experiment.md   Full narrative writeup of the experiment.
finetune-with-mlx/     Sibling subproject: LoRA fine-tuning experiments (self-contained).
unit-test-11-mar-26/   Sibling subproject: procurement-reader unit tests (self-contained).
model_cache/           Shared MLX/HF model cache (gitignored; downloaded on first run).
```

Each `experiments/*` folder is **self-contained and independently runnable** — its
scripts, spec, and dataset live together, and it has its own `README.md`.

## Environment

MLX requires **Apple Silicon**. This repo was validated with system **Python 3.9**,
which pins the stack to `mlx-lm 0.29.1` (newer `mlx-lm` needs Python ≥ 3.10).

```bash
python3 -m venv .venv
.venv/bin/python -m pip install mlx-lm      # ~mlx-lm 0.29.1 on Python 3.9
```

## Quick start (the deliverable)

```bash
# Live: 3B generates the solution, harness scores it, writes solution_best_v2.py
.venv/bin/python experiments/10-rule-v2/solve_simple_v2.py

# Offline: score any candidate against the ground truth (no MLX / no GPU needed)
.venv/bin/python experiments/10-rule-v2/prove_v2.py solution_best_v2.py
```

First run downloads `mlx-community/Qwen2.5-Coder-3B-Instruct-4bit` (~1.8 GB) into
`./model_cache`. Expected result: **`PASSED 12/12`** on iteration 1.

See each experiment's `README.md` for details, and `docs/slm-coding-experiment.md`
for the full writeup.
