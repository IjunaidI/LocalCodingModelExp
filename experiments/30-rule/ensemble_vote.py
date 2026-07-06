"""
Out-of-box experiment 1 — ENSEMBLE VOTING: correct answers from a committee of buggy programs.

Generate K independent solutions, run all that execute, and for EACH ROW take the majority
(largest tolerance-cluster) of the K programs' numeric outputs. Hypothesis: the 3B's
near-miss programs have *different* bugs (one flubs capital-city, another withholding, ...),
so if the errors are independent, per-row majority can reach a full pass even when no single
program does. If the ensemble beats the best single program, the errors are independent
(votable); if it doesn't, they're correlated.

By default it samples from the L1 spec via the ladder's stripped prompt — the harder ~16/23
regime where every program is sub-perfect — so the test is meaningful.

Run (from repo root):
    .venv/bin/python experiments/30-rule/ensemble_vote.py --k 9 --temp 0.7
"""

import os
import re
import csv
import json
import argparse
import statistics
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
os.environ["HF_HOME"] = str(PROJECT_DIR / "model_cache")
os.environ["HF_HUB_CACHE"] = str(PROJECT_DIR / "model_cache")

from solve_30 import extract_code, load_test_rows, write_inputs_csv, MODEL, MAX_TOKENS  # noqa: E402

TOL = 0.5
OUT_DIR = PROJECT_DIR / "outofbox"
INSTRUCTION = (
    "Implement the Python function described in the specification below. Read the CSV with "
    "the standard `csv` module; a header name may contain an internal space (for example "
    "`payment type`) — match it exactly and strip only leading/trailing whitespace. Return "
    "a list with one dict per input row. Respond with ONLY the code, in a single "
    "```python block.\n\n"
)


def run_program(code, inputs_csv, n):
    """Exec a candidate and return its per-row [(total, escrow), ...], or None if it crashes
    or returns the wrong shape."""
    ns = {}
    try:
        exec(code, ns)  # noqa: S102
        result = ns["process_calculations"](str(inputs_csv))
    except Exception:
        return None
    if not isinstance(result, list) or len(result) != n:
        return None
    out = []
    for row in result:
        try:
            out.append((float(row["total_receivables"]), float(row["escrow"])))
        except Exception:
            return None
    return out


def score_pairs(pairs, targets, escrows):
    return sum(1 for (t, e), tt, ee in zip(pairs, targets, escrows)
              if abs(t - tt) <= TOL and abs(e - ee) <= TOL)


def vote(values, tol=TOL):
    """Representative of the largest tolerance-cluster (majority within tol); returns
    (representative_value, agreement_count)."""
    best_rep, best_count = values[0], 0
    for v in values:
        cluster = [x for x in values if abs(x - v) <= tol]
        if len(cluster) > best_count:
            best_count, best_rep = len(cluster), sum(cluster) / len(cluster)
    return best_rep, best_count


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=9, help="number of solutions to sample.")
    ap.add_argument("--temp", type=float, default=0.7)
    ap.add_argument("--spec", type=str, default="ladder/specs/level_1.md",
                    help="spec to sample from (default L1, loaded stripped => ~16/23 regime).")
    ap.add_argument("--full-prompt", dest="full_prompt", action="store_true",
                    help="use the EXACT deliverable prompt (solve_30, spec with trailing "
                         "newline => the capable 23/23 greedy regime) instead of stripped L1.")
    ap.add_argument("--model", type=str, default=MODEL)
    args = ap.parse_args()
    OUT_DIR.mkdir(exist_ok=True)

    if args.full_prompt:
        import solve_30
        content_full = solve_30.INSTRUCTION  # wrapper + spec_30.md (keeps trailing newline)
        spec_text = None
    else:
        spec_text = re.sub(r"<!--.*?-->\n?", "", (PROJECT_DIR / args.spec).read_text(),
                           flags=re.DOTALL).strip()
    input_cols, rows, targets, escrows = load_test_rows()
    n = len(targets)
    inputs_csv = OUT_DIR / "_inputs_only_ensemble.csv"
    write_inputs_csv(input_cols, rows, inputs_csv)

    from mlx_lm import load, generate
    from mlx_lm.sample_utils import make_sampler
    print(f"Loading {args.model} ...\n")
    model, tok = load(args.model)
    sampler = make_sampler(temp=args.temp, top_p=0.9)
    content = content_full if args.full_prompt else (INSTRUCTION + spec_text)

    running, indiv_scores = [], []
    for j in range(args.k):
        prompt = tok.apply_chat_template([{"role": "user", "content": content}],
                                         add_generation_prompt=True)
        code = extract_code(generate(model, tok, prompt=prompt, max_tokens=MAX_TOKENS,
                                     sampler=sampler, verbose=False))
        pairs = run_program(code, inputs_csv, n)
        if pairs is None:
            print(f"  program {j + 1}: crashed / wrong shape (no vote)")
            continue
        s = score_pairs(pairs, targets, escrows)
        indiv_scores.append(s)
        running.append(pairs)
        print(f"  program {j + 1}: {s}/{n}")

    if not running:
        print("\nNo running programs — nothing to vote on.")
        return

    # Per-row majority (largest tolerance-cluster) and median aggregators.
    voted, median = [], []
    per_row_agree = []
    for i in range(n):
        totals = [p[i][0] for p in running]
        escs = [p[i][1] for p in running]
        tv, tc = vote(totals)
        ev, _ = vote(escs)
        voted.append((tv, ev))
        median.append((statistics.median(totals), statistics.median(escs)))
        per_row_agree.append(tc)

    vote_score = score_pairs(voted, targets, escrows)
    median_score = score_pairs(median, targets, escrows)
    best_single = max(indiv_scores) if indiv_scores else 0

    # How often was the CORRECT total available in the committee but out-voted?
    correct_available = sum(1 for i in range(n)
                            if any(abs(p[i][0] - targets[i]) <= TOL for p in running))

    print("\n" + "=" * 56)
    print(f"running programs: {len(running)}/{args.k}   individual scores: {sorted(indiv_scores, reverse=True)}")
    print(f"best single      : {best_single}/{n}")
    print(f"ENSEMBLE (majority vote): {vote_score}/{n}")
    print(f"ensemble (median)       : {median_score}/{n}")
    print(f"rows where the correct total was SOMEWHERE in the committee: {correct_available}/{n}")
    verdict = ("errors are INDEPENDENT — voting beats the best single program"
               if vote_score > best_single else
               "errors are CORRELATED — voting does not beat the best single program")
    print(f"=> {verdict}")

    result = {"k": args.k, "temp": args.temp, "spec": args.spec, "n": n,
              "running": len(running), "individual": sorted(indiv_scores, reverse=True),
              "best_single": best_single, "ensemble_majority": vote_score,
              "ensemble_median": median_score, "correct_available": correct_available,
              "per_row_agreement": per_row_agree, "verdict": verdict}
    (OUT_DIR / "ensemble_result.json").write_text(json.dumps(result, indent=2))
    print(f"\nwritten to {OUT_DIR.relative_to(PROJECT_DIR)}/ensemble_result.json")


if __name__ == "__main__":
    main()
