"""
Sweet-spot ladder: run the SAME 10-rule problem past a fixed model, varying only the
spec dialect from heavily-engineered (level 1) to fully natural (level 5), and find the
rung where the model stops producing correct code.

Everything is held constant except the spec file: same instruction wrapper, same decoding
settings, same 12-row targets (levels 1-4 use the yes/no dataset, level 5 the True/False
dataset — identical targets, diff 0.0). So any change in outcome is attributable to the
spec's dialect alone.

Two metrics:

  * default / --samples N : single-shot. Generate N independent attempts per level
    (N=1 is deterministic greedy) and report the score distribution + best-of-N. Shows
    how good the FIRST cut of code is from each dialect.

  * --repair : the repo's own generate -> score -> repair loop. Iteration 1 is greedy;
    subsequent iterations feed the error / per-row diff back and resample. Reports how
    many repair iterations each dialect needs to reach 12/12 (or that it never does),
    over --trajectories independent repair runs. Trivial defects (a missing import, a
    mangled header) heal in an iteration or two; a dialect that steers the model into a
    genuinely wrong construct (collapsed volume tier, truthy-string boolean) does not,
    because a numeric diff can't tell the model which rule is wrong. That gap is the
    sweet spot.

Run on Apple Silicon (from repo root):
    .venv/bin/python experiments/sweet-spot/run_ladder.py                 # greedy, 1/level
    .venv/bin/python experiments/sweet-spot/run_ladder.py --samples 10 --temp 0.4
    .venv/bin/python experiments/sweet-spot/run_ladder.py --repair --trajectories 3
    .venv/bin/python experiments/sweet-spot/run_ladder.py --levels 1,4,5

Round-2 modes. Artifacts are routed into a per-model-size folder (3b/outputs/,
7b/outputs/, ...) chosen from --model, and suffixed with a mode tag (--tag, auto-set
per mode), so runs at different sizes or modes never clobber each other:
    --extract            two-stage self-scaffold: the model first rebuilds the lookup
                         tables from the spec's own prose, then codes with them appended
    --extract-model M    cross-model hybrid: model M rebuilds the tables, --model codes
    --prefill            seed the assistant turn so the reply already starts with the
                         tables written out as code (tests input- vs output-side scaffold)
    --repair2            white-box repair + freeze verified steps + branch-k candidate
                         selection + temperature annealing (--branch, --anneal 0.6:0.2)
    --model / --tag      run the identical ladder on another Qwen2.5-Coder size (e.g. 7B)
"""

import os
import re
import csv
import json
import argparse
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
os.environ["HF_HOME"] = str(PROJECT_DIR / "model_cache")
os.environ["HF_HUB_CACHE"] = str(PROJECT_DIR / "model_cache")

from mlx_lm import load, generate  # noqa: E402
from mlx_lm.sample_utils import make_sampler  # noqa: E402

MODEL = "mlx-community/Qwen2.5-Coder-3B-Instruct-4bit"

TARGET_COL = "Total_receivables"
OUTPUT_KEY = "total_receivables"
TOLERANCE = 0.5
MAX_TOKENS = 2000

GREEDY_SAMPLER = make_sampler(temp=0.0)
REPAIR_SAMPLER = make_sampler(temp=0.6, top_p=0.9)

# Every artifact this run writes (saved solutions, results files) goes into a
# per-model-size folder — experiments/sweet-spot/3b/outputs/ or 7b/outputs/ — chosen
# from --model in main(), and carries a mode suffix from --tag. So runs at different
# sizes or modes never clobber each other.
OUT_DIR = PROJECT_DIR / "3b" / "outputs"
OUT_TAG = ""


def _tagged(stem, ext):
    return f"{stem}_{OUT_TAG}.{ext}" if OUT_TAG else f"{stem}.{ext}"

# Constant across every level — NOT part of what the experiment varies. Precise,
# minimal robustness guidance (no ambiguous "strip spaces", no "never crash" that would
# induce error-swallowing try/except). Every spec-dialect scaffold under test lives in
# the per-level spec file, never here.
INSTRUCTION = (
    "Implement the Python function described in the specification below. Read the CSV "
    "with the standard `csv` module; a header name may contain an internal space (for "
    "example `payment type`) — match it exactly and strip only leading/trailing "
    "whitespace. Return a list with one dict per input row. Respond with ONLY the code, "
    "in a single ```python block.\n\n"
)

# The ladder. Each level = same 10 rules + same arithmetic targets; only `spec` changes.
LEVELS = [
    {"level": 1, "title": "Prescriptive pseudocode", "spec": "level_1.md",
     "dataset": "test-cases-v2.csv", "expect": "pass (anchor)"},
    {"level": 2, "title": "Declarative spec", "spec": "level_2.md",
     "dataset": "test-cases-v2.csv", "expect": "pass?"},
    {"level": 3, "title": "Business prose", "spec": "level_3.md",
     "dataset": "test-cases-v2.csv", "expect": "pass?"},
    {"level": 4, "title": "Natural rules (tier trap)", "spec": "level_4.md",
     "dataset": "test-cases-v2.csv", "expect": "likely break"},
    {"level": 5, "title": "Original dialect (boolean trap)", "spec": "level_5.md",
     "dataset": "test-cases.csv", "expect": "fail (anchor)"},
    # Controls (Part 2): keep the literal lookup tables (the load-bearing L2 scaffold) but
    # re-arm the tier / boolean traps, to confirm the traps aren't what breaks it.
    {"level": 6, "title": "Tables + natural tier (yes/no)", "spec": "level_6.md",
     "dataset": "test-cases-v2.csv", "expect": "control: tier w/ tables"},
    {"level": 7, "title": "Tables + True/False boolean", "spec": "level_7.md",
     "dataset": "test-cases.csv", "expect": "control: boolean w/ tables"},
    {"level": 8, "title": "Tables + tier + True/False", "spec": "level_8.md",
     "dataset": "test-cases.csv", "expect": "control: both w/ tables"},
]

# --- White-box reference (for --repair-rules) -----------------------------------------
# The ground-truth value of every intermediate in the 10-rule pipeline, in canonical
# order. Used to tell the model WHICH step diverged, instead of only a wrong total.
PRODUCT_RATES = {
    1: {"individual": 1000, "corporate": 900},
    2: {"individual": 1500, "corporate": 1200},
    3: {"individual": 2000, "corporate": 1700},
}
CATEGORY_MULTIPLIER = {"electronics": 1.2, "groceries": 0.8, "luxury": 1.5}
CANON_KEYS = [
    "rate", "receivable_before_discount", "spring_rate", "volume_rate", "strategic_rate",
    "total_discount_rate", "receivable_after_discount", "region_loading",
    "payment_loading", "commission", "subtotal", "withholding", "total_receivables",
]


def _num(v, default=0.0):
    try:
        return float(str(v).strip())
    except (ValueError, AttributeError, TypeError):
        return default


def _verified(v):
    # "tax verified" is truthy for yes/true/1; empty or no/false is NOT verified (withhold).
    return str(v).strip().lower() in ("yes", "true", "1")


def reference_intermediates(row):
    """Every pipeline intermediate for one input row (handles yes/no and True/False)."""
    g = lambda k: str(row.get(k, "")).strip()
    pid = int(_num(g("productid"), 1))
    status = g("status").lower()
    volume = _num(g("volume"))
    rate = PRODUCT_RATES.get(pid, {}).get(status, 0)
    rbd = volume * rate
    spring_rate = 0.05 if g("season").lower() == "spring" else 0.0
    volume_rate = (0.05 if volume >= 100 else 0.0) + (0.05 if volume >= 1000 else 0.0)
    strategic_rate = 0.05 if g("customer").lower() == "strategic" else 0.0
    tdr = spring_rate + volume_rate + strategic_rate
    rad = rbd * (1 - tdr)
    region_loading = 0.10 * rad if g("region").lower() == "emea" else 0.0
    payment_loading = 0.025 * rad if g("payment type").lower() == "credit-card" else 0.0
    multiplier = CATEGORY_MULTIPLIER.get(g("product category").lower(), 1.0)
    commission = (region_loading + payment_loading) * multiplier
    subtotal = rad + commission
    withholding = 0.0 if _verified(g("tax verified")) else 0.03 * subtotal
    total = subtotal - withholding
    return {
        "rate": rate, "receivable_before_discount": rbd, "spring_rate": spring_rate,
        "volume_rate": volume_rate, "strategic_rate": strategic_rate,
        "total_discount_rate": tdr, "receivable_after_discount": rad,
        "region_loading": region_loading, "payment_loading": payment_loading,
        "commission": commission, "subtotal": subtotal, "withholding": withholding,
        "total_receivables": total,
    }


def load_spec(path):
    """Read a spec, stripping HTML comments so repo-facing authoring notes (which include
    trap descriptions) never leak into the model's prompt."""
    text = path.read_text()
    return re.sub(r"<!--.*?-->\n?", "", text, flags=re.DOTALL).strip()


def classify(passed, total, err):
    """Bucket one attempt so the report can show WHY a level fails: a crash, code that
    runs but computes wrong numbers (the dialect traps), or a clean pass."""
    if err is None:
        return "correct" if passed == total else f"ran, wrong numbers ({passed}/{total})"
    e = err.lower()
    if "syntax" in e:
        return "syntax error"
    if "not defined" in e:
        return "undefined name (forgot a table/import)"
    if "expected list" in e or "got " in e:
        return "wrong return shape"
    if "did not load" in e:
        return "load error"
    return "runtime crash"


def load_test_rows(dataset_path):
    with dataset_path.open(newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = [fn.strip() for fn in reader.fieldnames]
        rows, targets = [], []
        for raw in reader:
            clean = {k.strip(): (v.strip() if v else "") for k, v in raw.items()}
            targets.append(float(clean[TARGET_COL]))
            rows.append({k: v for k, v in clean.items() if k != TARGET_COL})
    return [c for c in fieldnames if c != TARGET_COL], rows, targets


def write_inputs_csv(input_cols, rows, path):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=input_cols)
        w.writeheader()
        w.writerows(rows)


def extract_code(text):
    m = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    return (m.group(1) if m else text).strip()


def score(code, inputs_csv, targets):
    ns = {}
    try:
        exec(code, ns)  # noqa: S102
        fn = ns["process_calculations"]
    except Exception as e:
        return 0, [], f"code did not load: {e}"
    try:
        result = fn(str(inputs_csv))
    except Exception as e:
        return 0, [], f"process_calculations raised: {e}"
    if not isinstance(result, list) or len(result) != len(targets):
        got = f"{type(result).__name__}" + (f" of len {len(result)}" if hasattr(result, "__len__") else "")
        return 0, [], f"expected list of {len(targets)} dicts, got {got}"
    passed, lines = 0, []
    for i, (pred_row, target) in enumerate(zip(result, targets)):
        try:
            pred = float(pred_row[OUTPUT_KEY])
        except Exception as e:
            lines.append(f"  row {i}: bad/missing {OUTPUT_KEY} ({e}); target={target:.4f}")
            continue
        if abs(pred - target) <= TOLERANCE:
            passed += 1
        else:
            lines.append(f"  row {i}: got {pred:.4f}, expected {target:.4f}")
    return passed, lines, None


def build_repair_prompt(spec_text, prev_code, passed, total, lines, err):
    problem = (f"Your previous code did not run: {err}" if err else
               f"Your previous code passed {passed}/{total} rows. These rows are wrong:\n"
               + "\n".join(lines))
    return ("Your previous attempt:\n```python\n" + prev_code + "\n```\n\n" + problem
            + "\n\nFix the code so EVERY row matches. Respond with ONLY the full "
            "corrected function in a single ```python block.\n\n" + spec_text)


def ask(model, tokenizer, content, sampler):
    messages = [{"role": "user", "content": content}]
    prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True)
    return generate(model, tokenizer, prompt=prompt, max_tokens=MAX_TOKENS,
                    sampler=sampler, verbose=False)


def _prep(cfg):
    spec_text = load_spec(PROJECT_DIR / "specs" / cfg["spec"])
    input_cols, rows, targets = load_test_rows(PROJECT_DIR / cfg["dataset"])
    inputs_csv = OUT_DIR / f"_inputs_only_level_{cfg['level']}.csv"
    write_inputs_csv(input_cols, rows, inputs_csv)
    return spec_text, inputs_csv, targets


def save_best(cfg, code):
    (OUT_DIR / _tagged(f"level_{cfg['level']}_solution", "py")).write_text(code + "\n")


# ---------------------------------------------------------------- single-shot mode ----

def run_level_single(cfg, model, tokenizer, sampler, samples):
    spec_text, inputs_csv, targets = _prep(cfg)
    total = len(targets)
    attempts = []
    for _ in range(samples):
        code = extract_code(ask(model, tokenizer, INSTRUCTION + spec_text, sampler))
        passed, _lines, err = score(code, inputs_csv, targets)
        attempts.append((passed, code, err))

    best = max(attempts, key=lambda a: a[0])
    save_best(cfg, best[1])
    tally = {}
    for passed, _code, err in attempts:
        c = classify(passed, total, err)
        tally[c] = tally.get(c, 0) + 1
    reasons = sorted(tally.items(), key=lambda kv: -kv[1])
    return {
        "mode": "single", "level": cfg["level"], "title": cfg["title"],
        "expect": cfg["expect"], "dataset": cfg["dataset"], "total": total,
        "best": best[0], "samples": samples,
        "perfect": sum(1 for a in attempts if a[0] == total),
        "scores": [a[0] for a in attempts], "reasons": reasons,
    }


# ---------------------------------------------------- extract-then-code (hybrid) ------
# The ladder showed the literal lookup tables are the load-bearing scaffold. This mode
# asks: can the model BUILD ITS OWN scaffold? Stage 1 (greedy): rebuild the tables from
# the spec's prose as Python literals. Stage 2: a normal codegen prompt with those
# self-extracted tables appended. If this rescues a tables-removed rung, the cliff is a
# one-pass working-memory limit, not missing knowledge.

EXTRACT_INSTRUCTION = (
    "Read the specification below. Do NOT implement the function yet. First restate, as "
    "Python literals in a single ```python block, every constant the specification "
    "defines: a dict `PRODUCT_RATES` mapping each product id to its unit rate per "
    "status, a dict `CATEGORY_MULTIPLIER` mapping each product category to its "
    "commission multiplier, and a named constant for every percentage the rules use "
    "(discount rates, loadings, withholding) written as a bare decimal. Respond with "
    "ONLY that ```python block.\n\n"
)


def check_extraction(code):
    """Exec the model's extracted constants and compare the two load-bearing tables to
    ground truth (key types and case normalized). Returns (ok, note)."""
    ns = {}
    try:
        exec(code, ns)  # noqa: S102
    except Exception as e:
        return False, f"extraction did not exec: {e}"
    notes = []
    try:
        pr = {str(k): {str(s).lower(): float(v) for s, v in d.items()}
              for k, d in ns["PRODUCT_RATES"].items()}
        ref = {str(k): {s: float(v) for s, v in d.items()} for k, d in PRODUCT_RATES.items()}
        if pr != ref:
            notes.append(f"PRODUCT_RATES mismatch: {ns['PRODUCT_RATES']}")
    except Exception:
        notes.append("PRODUCT_RATES missing/malformed")
    try:
        cm = {str(k).lower(): float(v) for k, v in ns["CATEGORY_MULTIPLIER"].items()}
        if cm != CATEGORY_MULTIPLIER:
            notes.append(f"CATEGORY_MULTIPLIER mismatch: {ns['CATEGORY_MULTIPLIER']}")
    except Exception:
        notes.append("CATEGORY_MULTIPLIER missing/malformed")
    return (not notes), "; ".join(notes)


def _finish_single(mode, cfg, attempts, samples, total, **extra):
    """Shared bookkeeping for the single-shot-style modes (extract / prefill)."""
    best = max(attempts, key=lambda a: a[0])
    save_best(cfg, best[1])
    tally = {}
    for passed, _code, err in attempts:
        c = classify(passed, total, err)
        tally[c] = tally.get(c, 0) + 1
    r = {"mode": mode, "level": cfg["level"], "title": cfg["title"],
         "expect": cfg["expect"], "dataset": cfg["dataset"], "total": total,
         "best": best[0], "samples": samples,
         "perfect": sum(1 for a in attempts if a[0] == total),
         "scores": [a[0] for a in attempts],
         "reasons": sorted(tally.items(), key=lambda kv: -kv[1])}
    r.update(extra)
    return r


def run_level_extract(cfg, model, tokenizer, sampler, samples, extraction=None, extractor="self"):
    spec_text, inputs_csv, targets = _prep(cfg)
    total = len(targets)
    if extraction is None:
        extraction = extract_code(ask(model, tokenizer, EXTRACT_INSTRUCTION + spec_text,
                                      GREEDY_SAMPLER))
        extractor = "self"
    ok, note = check_extraction(extraction)
    (OUT_DIR / _tagged(f"level_{cfg['level']}_extracted", "py")
     ).write_text(extraction + "\n")

    stage2 = (INSTRUCTION + spec_text
              + "\n\n## Constants extracted from this specification\nUse these exactly "
              "as given:\n```python\n" + extraction + "\n```\n")
    attempts = []
    for _ in range(samples):
        code = extract_code(ask(model, tokenizer, stage2, sampler))
        # The pipeline's program is extraction + function: the model may reference the
        # given constants without restating them, so assemble before scoring (a double
        # definition, if it did copy them, is harmless).
        assembled = extraction + "\n\n" + code
        passed, _lines, err = score(assembled, inputs_csv, targets)
        attempts.append((passed, assembled, err))
    return _finish_single("extract", cfg, attempts, samples, total,
                          extractor=extractor, extraction_ok=ok, extraction_note=note)


# ------------------------------------------------------------ response-prefill mode ----
# Seed the assistant turn so the reply ALREADY contains the true lookup tables written
# out as code; the model merely continues past them. Distinguishes "tables help because
# they sit in the spec (input context)" from "tables help once they exist in the model's
# own output context".

PREFILL_CODE = '''import csv

PRODUCT_RATES = {
    1: {"individual": 1000, "corporate": 900},
    2: {"individual": 1500, "corporate": 1200},
    3: {"individual": 2000, "corporate": 1700},
}
CATEGORY_MULTIPLIER = {"electronics": 1.2, "groceries": 0.8, "luxury": 1.5}


def process_calculations(csv_path):
    '''


def ask_prefilled(model, tokenizer, content, prefix_text, sampler):
    messages = [{"role": "user", "content": content}]
    prompt = list(tokenizer.apply_chat_template(messages, add_generation_prompt=True))
    prompt += tokenizer.encode(prefix_text, add_special_tokens=False)
    return generate(model, tokenizer, prompt=prompt, max_tokens=MAX_TOKENS,
                    sampler=sampler, verbose=False)


def run_level_prefill(cfg, model, tokenizer, sampler, samples):
    spec_text, inputs_csv, targets = _prep(cfg)
    total = len(targets)
    attempts = []
    for _ in range(samples):
        completion = ask_prefilled(model, tokenizer, INSTRUCTION + spec_text,
                                   "```python\n" + PREFILL_CODE, sampler)
        full = PREFILL_CODE + completion
        cut = full.find("```")
        code = (full[:cut] if cut != -1 else full).strip()
        passed, _lines, err = score(code, inputs_csv, targets)
        attempts.append((passed, code, err))
    return _finish_single("prefill", cfg, attempts, samples, total)


# --------------------------------------------------------------------- repair mode ----

def run_level_repair(cfg, model, tokenizer, max_iters, trajectories, repair_sampler=REPAIR_SAMPLER):
    spec_text, inputs_csv, targets = _prep(cfg)
    total = len(targets)

    # Iteration 1 is greedy and deterministic — compute it once, shared by all trajectories.
    code1 = extract_code(ask(model, tokenizer, INSTRUCTION + spec_text, GREEDY_SAMPLER))
    p1, l1, e1 = score(code1, inputs_csv, targets)
    overall_best = (p1, code1)

    if p1 == total:
        save_best(cfg, code1)
        return {"mode": "repair", "level": cfg["level"], "title": cfg["title"],
                "expect": cfg["expect"], "total": total, "trajectories": trajectories,
                "max_iters": max_iters, "converged": trajectories, "min_iters": 1,
                "best": total, "first_try": True, "paths": [[p1]] * trajectories}

    conv_iters, paths = [], []
    for _t in range(trajectories):
        content = build_repair_prompt(spec_text, code1, p1, total, l1, e1)
        best_score, best_code, conv, path = p1, code1, None, [p1]
        for it in range(2, max_iters + 1):
            code = extract_code(ask(model, tokenizer, content, repair_sampler))
            passed, lines, err = score(code, inputs_csv, targets)
            path.append(passed)
            if passed > best_score:
                best_score, best_code = passed, code
            if passed == total:
                conv = it
                break
            content = build_repair_prompt(spec_text, code, passed, total, lines, err)
        paths.append(path)
        if conv:
            conv_iters.append(conv)
        if best_score > overall_best[0]:
            overall_best = (best_score, best_code)

    save_best(cfg, overall_best[1])
    return {"mode": "repair", "level": cfg["level"], "title": cfg["title"],
            "expect": cfg["expect"], "total": total, "trajectories": trajectories,
            "max_iters": max_iters, "converged": len(conv_iters),
            "min_iters": (min(conv_iters) if conv_iters else None),
            "best": overall_best[0], "first_try": False, "paths": paths}


# ------------------------------------------------------ white-box (repair-rules) mode ---

def execute(code, inputs_csv):
    """Run the model's function; return (result_object_or_None, error_string_or_None)."""
    ns = {}
    try:
        exec(code, ns)  # noqa: S102
        result = ns["process_calculations"](str(inputs_csv))
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"
    return result, None


def _close(a, b):
    return abs(a - b) <= 1e-4 * max(1.0, abs(b))


def localize(result, err, ref_ints, targets):
    """Score total_receivables AND, for each failing row, name the FIRST pipeline step
    whose value diverges from the reference (when the model exposed intermediates).
    Returns (passed, feedback_lines, had_intermediates, culprit_steps) — culprit_steps
    holds the first-divergent CANON key per failing row (None when not localizable)."""
    total = len(targets)
    if err is not None:
        return 0, [f"the code did not run: {err}"], False, []
    if not isinstance(result, list) or len(result) != total:
        got = type(result).__name__ + (f" of len {len(result)}" if hasattr(result, "__len__") else "")
        return 0, [f"return a list of {total} dicts (got {got})"], False, []

    passed, lines, had, culprit_steps = 0, [], False, []
    for i, (row, ref, tgt) in enumerate(zip(result, ref_ints, targets)):
        if not isinstance(row, dict):
            lines.append(f"  row {i}: each item must be a dict")
            culprit_steps.append(None)
            continue
        try:
            got_total = float(row.get("total_receivables"))
        except (TypeError, ValueError):
            got_total = None
        if got_total is not None and abs(got_total - tgt) <= TOLERANCE:
            passed += 1
            continue
        # Failing row: find the first intermediate that's wrong, if the model exposed them.
        exposed = [k for k in CANON_KEYS[:-1] if k in row]
        if exposed:
            had = True
            culprit = None
            for k in CANON_KEYS:
                if k not in row:
                    continue
                try:
                    mv = float(row[k])
                except (TypeError, ValueError):
                    culprit = (k, str(row[k]), ref[k])
                    break
                if not _close(mv, ref[k]):
                    culprit = (k, mv, ref[k])
                    break
            if culprit:
                k, mv, rv = culprit
                idx = CANON_KEYS.index(k)
                prefix = f"correct through `{CANON_KEYS[idx - 1]}`, but " if idx > 0 else ""
                shown = mv if isinstance(mv, str) else f"{mv:.4f}"
                lines.append(f"  row {i}: {prefix}`{k}` = {shown}, should be {rv:.4f}")
                culprit_steps.append(k)
            else:
                gt = "missing" if got_total is None else f"{got_total:.4f}"
                lines.append(f"  row {i}: `total_receivables` = {gt}, should be {tgt:.4f}")
                culprit_steps.append(None)
        else:
            gt = "missing" if got_total is None else f"{got_total:.4f}"
            lines.append(f"  row {i}: `total_receivables` = {gt}, should be {tgt:.4f}")
            culprit_steps.append(None)
    return passed, lines, had, culprit_steps


def build_repair_rules_prompt(spec_text, passed, total, feedback_lines):
    head = f"Your previous code passed {passed}/{total} rows.\n"
    if feedback_lines:
        head += ("Here is the first calculation step that is wrong on each failing row "
                 "(everything before it is already correct):\n" + "\n".join(feedback_lines) + "\n")
    instr = ("\nSo I can pinpoint the bug, make each returned dict ALSO include these "
             "intermediate values (keep `total_receivables` too), using EXACTLY these keys:\n  "
             + ", ".join(CANON_KEYS[:-1]) + ".\n")
    return (head + instr + "\nFix the code so every row's `total_receivables` matches. Respond "
            "with ONLY the full corrected function in one ```python block.\n\n" + spec_text)


def run_level_repair_rules(cfg, model, tokenizer, max_iters, trajectories, repair_sampler=REPAIR_SAMPLER):
    spec_text = load_spec(PROJECT_DIR / "specs" / cfg["spec"])
    input_cols, rows, targets = load_test_rows(PROJECT_DIR / cfg["dataset"])
    total = len(targets)
    ref_ints = [reference_intermediates(r) for r in rows]
    inputs_csv = OUT_DIR / f"_inputs_only_level_{cfg['level']}.csv"
    write_inputs_csv(input_cols, rows, inputs_csv)

    # Iteration 1: greedy, normal output contract (comparable to the other modes).
    code1 = extract_code(ask(model, tokenizer, INSTRUCTION + spec_text, GREEDY_SAMPLER))
    res1, err1 = execute(code1, inputs_csv)
    p1, fb1, _had1, _c1 = localize(res1, err1, ref_ints, targets)
    overall_best = (p1, code1)

    if p1 == total:
        save_best(cfg, code1)
        return {"mode": "repair-rules", "level": cfg["level"], "title": cfg["title"],
                "expect": cfg["expect"], "total": total, "trajectories": trajectories,
                "max_iters": max_iters, "converged": trajectories, "min_iters": 1,
                "best": total, "first_try": True, "paths": [[p1]] * trajectories}

    conv_iters, paths = [], []
    for _t in range(trajectories):
        content = build_repair_rules_prompt(spec_text, p1, total, fb1)
        best_score, best_code, conv, path = p1, code1, None, [p1]
        for it in range(2, max_iters + 1):
            code = extract_code(ask(model, tokenizer, content, repair_sampler))
            res, err = execute(code, inputs_csv)
            passed, fb, _had, _c = localize(res, err, ref_ints, targets)
            path.append(passed)
            if passed > best_score:
                best_score, best_code = passed, code
            if passed == total:
                conv = it
                break
            content = build_repair_rules_prompt(spec_text, passed, total, fb)
        paths.append(path)
        if conv:
            conv_iters.append(conv)
        if best_score > overall_best[0]:
            overall_best = (best_score, best_code)

    save_best(cfg, overall_best[1])
    return {"mode": "repair-rules", "level": cfg["level"], "title": cfg["title"],
            "expect": cfg["expect"], "total": total, "trajectories": trajectories,
            "max_iters": max_iters, "converged": len(conv_iters),
            "min_iters": (min(conv_iters) if conv_iters else None),
            "best": overall_best[0], "first_try": False, "paths": paths}


# ------------------------------------------------------------ repair 2.0 (--repair2) ---
# Upgrades over --repair-rules, each aimed at an observed failure of the round-1 loops:
#   * previous code included in the prompt + "edit ONLY the first wrong step"  -> the
#     round-1 white-box loop regenerated from scratch each iteration, which is where the
#     oscillation came from;
#   * step FREEZING: intermediates verified correct on every row are declared off-limits;
#   * BRANCH-k: sample k candidate fixes per iteration, keep the best (score, then
#     deepest first-divergence) instead of betting one trajectory on a single draw;
#   * temperature ANNEALING across iterations (explore early, commit late) — bridges the
#     observed gap between t=0.6 (oscillates) and t=0.3 (sticks but can stall).


def step_ledger(result, ref_ints):
    """Per-step verdict across all rows: 'ok' = exposed in every row and matching
    everywhere; 'bad' = at least one mismatch. Steps never exposed are absent."""
    ledger = {}
    if not isinstance(result, list):
        return ledger
    for k in CANON_KEYS[:-1]:
        seen, good = 0, True
        for row, ref in zip(result, ref_ints):
            if not isinstance(row, dict) or k not in row:
                continue
            seen += 1
            try:
                if not _close(float(row[k]), ref[k]):
                    good = False
            except (TypeError, ValueError):
                good = False
        if seen == len(ref_ints) and good:
            ledger[k] = "ok"
        elif seen and not good:
            ledger[k] = "bad"
    return ledger


def _first_culprit(culprit_steps):
    keys = [k for k in culprit_steps if k]
    return min(keys, key=CANON_KEYS.index) if keys else None


def _divergence_depth(culprit_steps):
    idxs = [CANON_KEYS.index(k) for k in culprit_steps if k]
    return min(idxs) if idxs else 0


def _anneal_temp(it, max_iters, t_start, t_end):
    if max_iters <= 2:
        return t_end
    frac = (it - 2) / (max_iters - 2)
    return t_start + (t_end - t_start) * frac


def build_instrument_prompt(spec_text, prev_code):
    """First repair2 phase: the greedy code exposes no intermediates, so nothing is
    localizable and a minimal-edit prompt just anchors the model to its broken code
    (observed: paths flat-line). Ask for instrumentation ONLY — same logic, plus the
    canonical intermediate keys — then repair with real localization from iter 3 on."""
    return ("Here is your current code:\n```python\n" + prev_code + "\n```\n\n"
            "Do NOT change its calculation logic. Rewrite it so each returned dict ALSO "
            "includes every intermediate value it computes, using EXACTLY these keys:\n  "
            + ", ".join(CANON_KEYS[:-1]) + "\n(keep `total_receivables` too; a step your "
            "code folds into another line must be pulled out into its own variable so it "
            "can be reported). Respond with ONLY the full function in one "
            "```python block.\n\n" + spec_text)


def build_repair2_prompt(spec_text, prev_code, passed, total, feedback_lines, frozen, culprit,
                         include_code=True):
    """include_code=False is the --fresh variant: same freeze-list / culprit / feedback,
    but the previous code is NOT shown, so the model regenerates instead of minimally
    editing. Motivation: with the code in the prompt, a 3B anchors on it and the score
    path flat-lines (observed on three separate runs)."""
    head = f"Your previous code passed {passed}/{total} rows.\n"
    if frozen:
        head += ("These steps are VERIFIED CORRECT on every row — do NOT change how they "
                 "are computed: " + ", ".join(f"`{k}`" for k in frozen) + ".\n")
    if culprit:
        edit_scope = ("Edit ONLY the code that computes it" if include_code
                      else "Pay special attention to that step")
        head += f"The FIRST incorrect step is `{culprit}`. {edit_scope}.\n"
    if feedback_lines:
        head += "Failing rows (first wrong step on each):\n" + "\n".join(feedback_lines) + "\n"
    if include_code and prev_code:
        head += "\nYour previous code:\n```python\n" + prev_code + "\n```\n"
    instr = ("\nMake each returned dict ALSO include these intermediate values (keep "
             "`total_receivables` too), using EXACTLY these keys:\n  "
             + ", ".join(CANON_KEYS[:-1]) + ".\n"
             "Respond with ONLY the full corrected function in one ```python block.\n\n")
    return head + instr + spec_text


def run_level_repair2(cfg, model, tokenizer, max_iters, trajectories, branch, t_start, t_end,
                      fresh=False):
    spec_text = load_spec(PROJECT_DIR / "specs" / cfg["spec"])
    input_cols, rows, targets = load_test_rows(PROJECT_DIR / cfg["dataset"])
    total = len(targets)
    ref_ints = [reference_intermediates(r) for r in rows]
    inputs_csv = OUT_DIR / f"_inputs_only_level_{cfg['level']}.csv"
    write_inputs_csv(input_cols, rows, inputs_csv)

    code1 = extract_code(ask(model, tokenizer, INSTRUCTION + spec_text, GREEDY_SAMPLER))
    res1, err1 = execute(code1, inputs_csv)
    p1, fb1, had1, culps1 = localize(res1, err1, ref_ints, targets)
    overall_best = (p1, code1)
    print(f"     it1 greedy: {p1}/{total}, exposes intermediates: {had1}")

    if p1 == total:
        save_best(cfg, code1)
        return {"mode": "repair2", "level": cfg["level"], "title": cfg["title"],
                "expect": cfg["expect"], "total": total, "trajectories": trajectories,
                "max_iters": max_iters, "branch": branch, "anneal": [t_start, t_end],
                "converged": trajectories, "min_iters": 1, "best": total,
                "first_try": True, "paths": [[p1]] * trajectories}

    conv_iters, paths = [], []
    for _t in range(trajectories):
        code, passed, fb, culps, res, had = code1, p1, fb1, culps1, res1, had1
        best_score, best_code, conv, path = p1, code1, None, [p1]
        for it in range(2, max_iters + 1):
            if not had and not fresh:
                # Instrumentation pass: expose the intermediates before repairing.
                # (In --fresh mode the repair prompt itself demands the intermediate
                # keys, round-1 style, so no separate pass is needed.)
                content = build_instrument_prompt(spec_text, code)
                c = extract_code(ask(model, tokenizer, content,
                                     make_sampler(temp=t_end, top_p=0.9)))
                r, e = execute(c, inputs_csv)
                pp, ff, hh, cc = localize(r, e, ref_ints, targets)
                # Accept on exposure alone: the instrumented rewrite usually DIPS in
                # score (a 3B can't do "same logic + 12 new keys" losslessly), but the
                # localization it unlocks is the whole point — and overall_best keeps
                # the un-instrumented floor, so the dip risks nothing.
                accepted = bool(hh)
                print(f"     it{it} instrument: scored {pp}/{total}, exposed={hh}, "
                      f"err={'yes' if e else 'no'}, accepted={accepted}")
                if accepted:
                    code, passed, fb, culps, res, had = c, pp, ff, cc, r, True
                path.append(passed)
                if passed > best_score:
                    best_score, best_code = passed, code
                if passed == total:
                    conv = it
                    break
                continue
            ledger = step_ledger(res, ref_ints)
            frozen = [k for k in CANON_KEYS[:-1] if ledger.get(k) == "ok"]
            culprit = _first_culprit(culps)
            content = build_repair2_prompt(spec_text, code, passed, total, fb,
                                           frozen, culprit, include_code=not fresh)
            temp = _anneal_temp(it, max_iters, t_start, t_end)
            sampler = make_sampler(temp=temp, top_p=0.9)
            cands = []
            for _b in range(branch):
                c = extract_code(ask(model, tokenizer, content, sampler))
                r, e = execute(c, inputs_csv)
                pp, ff, hh, cc = localize(r, e, ref_ints, targets)
                cands.append((pp, 1 if hh else 0, _divergence_depth(cc), c, ff, cc, r, hh))
            cands.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
            print(f"     it{it} repair t={temp:.2f} frozen={len(frozen)} "
                  f"culprit={culprit or '-'} cands={[c[0] for c in cands]} "
                  f"-> pick {cands[0][0]}/{total}")
            passed, _e, _d, code, fb, culps, res, had = cands[0]
            path.append(passed)
            if passed > best_score:
                best_score, best_code = passed, code
            if passed == total:
                conv = it
                break
        paths.append(path)
        if conv:
            conv_iters.append(conv)
        if best_score > overall_best[0]:
            overall_best = (best_score, best_code)

    save_best(cfg, overall_best[1])
    return {"mode": "repair2", "level": cfg["level"], "title": cfg["title"],
            "expect": cfg["expect"], "total": total, "trajectories": trajectories,
            "max_iters": max_iters, "branch": branch, "anneal": [t_start, t_end],
            "converged": len(conv_iters), "min_iters": (min(conv_iters) if conv_iters else None),
            "best": overall_best[0], "first_try": False, "paths": paths}


# ------------------------------------------------------------------------- reporting ---

def write_results_md(results, mode, samples):
    lines = ["# Sweet-spot ladder — results", ""]
    if mode in ("repair", "repair-rules", "repair2"):
        r0 = results[0]
        kind = {"repair-rules": "white-box repair (per-rule intermediate feedback)",
                "repair": "repair loop (scalar total diff)",
                "repair2": "repair 2.0 (white-box + previous code + step freezing + "
                           "branch-k + temperature annealing)"}[mode]
        lines += [f"{kind}: iteration 1 greedy, up to {r0['max_iters']} iterations, "
                  f"{r0['trajectories']} independent trajectories per level.", "",
                  "| Level | Spec dialect | Converged | Fastest | Best score |",
                  "|:-----:|--------------|:---------:|:-------:|:----------:|"]
        for r in results:
            conv = f"{r['converged']}/{r['trajectories']}"
            fastest = f"iter {r['min_iters']}" if r["min_iters"] else "—"
            note = " (first try)" if r.get("first_try") else ""
            lines.append(f"| L{r['level']} | {r['title']} | {conv}{note} | {fastest} | {r['best']}/{r['total']} |")
        lines += ["", "Per-trajectory score paths (rows passed after each iteration):", ""]
        for r in results:
            lines.append(f"- **L{r['level']} {r['title']}** — {r['paths']}")
    elif samples == 1:
        lines += ["Greedy (temperature 0), one attempt per level.", "",
                  "| Level | Spec dialect | Score | Result |",
                  "|:-----:|--------------|:-----:|:------:|"]
        for r in results:
            mark = "PASS" if r["best"] == r["total"] else "FAIL"
            lines.append(f"| L{r['level']} | {r['title']} | {r['best']}/{r['total']} | {mark} |")
    else:
        lines += [f"{samples} sampled attempts per level.", "",
                  "| Level | Spec dialect | Pass-rate | Best | Most common outcome |",
                  "|:-----:|--------------|:---------:|:----:|---------------------|"]
        for r in results:
            top = "; ".join(f"{c}×{n}" for c, n in r["reasons"][:2])
            lines.append(f"| L{r['level']} | {r['title']} | {r['perfect']}/{samples} | {r['best']}/{r['total']} | {top} |")
        lines += ["", "Per-level score distributions (each number is one sampled attempt):", ""]
        for r in results:
            lines.append(f"- **L{r['level']} {r['title']}** — scores `{r['scores']}`; "
                         + ", ".join(f"{c} ×{n}" for c, n in r["reasons"]))
    if mode == "extract":
        lines += ["", "Extraction check (did the model rebuild the tables correctly?):", ""]
        for r in results:
            ok = "correct" if r.get("extraction_ok") else f"WRONG — {r.get('extraction_note')}"
            lines.append(f"- **L{r['level']}** (extractor: {r.get('extractor')}): tables {ok}")
    lines.append("")
    (OUT_DIR / _tagged("results", "md")).write_text("\n".join(lines))
    (OUT_DIR / _tagged("results", "json")).write_text(json.dumps(results, indent=2))


def main():
    ap = argparse.ArgumentParser(description="Run the spec-difficulty ladder.")
    ap.add_argument("--samples", type=int, default=1, help="single-shot attempts per level.")
    ap.add_argument("--temp", type=float, default=0.4, help="temperature when --samples > 1.")
    ap.add_argument("--repair", action="store_true", help="repair loop with scalar total-diff feedback.")
    ap.add_argument("--repair-rules", dest="repair_rules", action="store_true",
                    help="white-box repair: feed per-rule intermediate diffs (localizes the bug).")
    ap.add_argument("--trajectories", type=int, default=3, help="repair runs per level.")
    ap.add_argument("--max-iters", type=int, default=6, help="max repair iterations.")
    ap.add_argument("--repair-temp", dest="repair_temp", type=float, default=0.6,
                    help="temperature for repair iterations (lower = more conservative edits).")
    ap.add_argument("--levels", type=str, default="", help="subset, e.g. 1,4,5.")
    ap.add_argument("--model", type=str, default=MODEL)
    ap.add_argument("--tag", type=str, default="",
                    help="suffix for output artifacts (e.g. 7b); auto-set for round-2 modes.")
    ap.add_argument("--extract", action="store_true",
                    help="two-stage self-scaffold: rebuild the tables from the spec, then code.")
    ap.add_argument("--extract-model", dest="extract_model", type=str, default="",
                    help="use this model for the table-extraction stage (cross-model hybrid).")
    ap.add_argument("--prefill", action="store_true",
                    help="seed the assistant turn with the lookup tables already written as code.")
    ap.add_argument("--repair2", action="store_true",
                    help="white-box repair + step freezing + branch-k + temperature annealing.")
    ap.add_argument("--branch", type=int, default=3, help="candidates per repair2 iteration.")
    ap.add_argument("--anneal", type=str, default="0.6:0.2",
                    help="repair2 temperature schedule start:end across iterations.")
    ap.add_argument("--fresh", action="store_true",
                    help="repair2 without showing the previous code (regenerate from "
                         "feedback; avoids the small-model anchoring flat-line).")
    args = ap.parse_args()

    mode = ("repair2" if args.repair2 else
            "repair-rules" if args.repair_rules else
            "repair" if args.repair else
            "extract" if args.extract else
            "prefill" if args.prefill else "single")
    t_start, t_end = (float(x) for x in args.anneal.split(":"))

    # Route every artifact into a per-model-size folder (3b/outputs, 7b/outputs, ...),
    # and give every run an explicit mode tag so nothing is ever ambiguous on disk.
    global OUT_DIR, OUT_TAG
    m = re.search(r"(\d+(?:[._]\d+)?)B", args.model, re.IGNORECASE)
    size = (m.group(1).lower().replace("_", ".") + "b") if m else "alt"
    OUT_DIR = PROJECT_DIR / size / "outputs"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_TAG = args.tag
    if not OUT_TAG:
        if mode in ("extract", "prefill", "repair2"):
            OUT_TAG = mode
        elif mode == "single":
            OUT_TAG = "greedy" if args.samples == 1 else f"s{args.samples}"
    wanted = {int(x) for x in args.levels.split(",") if x.strip()} if args.levels else None
    todo = [c for c in LEVELS if wanted is None or c["level"] in wanted]

    if mode == "repair2":
        print(f"Mode: repair 2.0 (freeze verified steps, branch {args.branch}, temp anneal "
              f"{t_start}->{t_end}), up to {args.max_iters} iters, "
              f"{args.trajectories} trajectories/level.\n")
    elif mode == "repair-rules":
        print(f"Mode: white-box repair (per-rule intermediate feedback), up to {args.max_iters} "
              f"iters, {args.trajectories} trajectories/level, repair temp {args.repair_temp}.\n")
    elif mode == "repair":
        print(f"Mode: repair loop (scalar diff), up to {args.max_iters} iters, "
              f"{args.trajectories} trajectories/level, repair temp {args.repair_temp}.\n")
    elif mode == "extract":
        who = args.extract_model or "the same model"
        print(f"Mode: extract-then-code ({who} rebuilds the tables; "
              f"{args.samples} codegen attempt(s)/level).\n")
    elif mode == "prefill":
        print(f"Mode: response prefill (tables seeded into the assistant turn; "
              f"{args.samples} attempt(s)/level).\n")
    elif args.samples == 1:
        print("Mode: greedy (temperature 0), 1 attempt per level.\n")
    else:
        print(f"Mode: {args.samples} attempts per level at temperature {args.temp}.\n")
    print(f"Outputs: {OUT_DIR.relative_to(PROJECT_DIR)}/"
          + (f" (tag _{OUT_TAG})" if OUT_TAG else "") + "\n")

    extractions = {}
    if mode == "extract" and args.extract_model:
        print(f"Loading extractor {args.extract_model} ...\n")
        ext_model, ext_tok = load(args.extract_model)
        for cfg in todo:
            spec_text = load_spec(PROJECT_DIR / "specs" / cfg["spec"])
            extractions[cfg["level"]] = extract_code(
                ask(ext_model, ext_tok, EXTRACT_INSTRUCTION + spec_text, GREEDY_SAMPLER))
            print(f"  L{cfg['level']}: constants extracted")
        # Free the extractor before the coder loads — the two are never co-resident.
        del ext_model, ext_tok
        import gc
        gc.collect()
        try:
            import mlx.core as mx
            (mx.clear_cache if hasattr(mx, "clear_cache") else mx.metal.clear_cache)()
        except Exception:
            pass
        print()

    print(f"Loading {args.model} ...\n")
    model, tokenizer = load(args.model)
    sampler = GREEDY_SAMPLER if args.samples == 1 else make_sampler(temp=args.temp, top_p=0.9)
    repair_sampler = make_sampler(temp=args.repair_temp, top_p=0.9)

    results = []
    for cfg in todo:
        print("=" * 64)
        print(f"LEVEL {cfg['level']} — {cfg['title']}  (expect: {cfg['expect']})")
        print("=" * 64)
        if mode in ("repair", "repair-rules", "repair2"):
            if mode == "repair2":
                r = run_level_repair2(cfg, model, tokenizer, args.max_iters,
                                      args.trajectories, args.branch, t_start, t_end,
                                      fresh=args.fresh)
            else:
                runner = run_level_repair_rules if mode == "repair-rules" else run_level_repair
                r = runner(cfg, model, tokenizer, args.max_iters, args.trajectories, repair_sampler)
            note = " (greedy first try)" if r.get("first_try") else ""
            fastest = f", fastest iter {r['min_iters']}" if r["min_iters"] else ""
            print(f"  -> converged {r['converged']}/{r['trajectories']}{note}{fastest}, "
                  f"best {r['best']}/{r['total']}")
            print(f"     paths {r['paths']}\n")
        else:
            if mode == "extract":
                r = run_level_extract(cfg, model, tokenizer, sampler, args.samples,
                                      extraction=extractions.get(cfg["level"]),
                                      extractor=(args.extract_model or "self"))
                tick = "OK" if r["extraction_ok"] else f"WRONG ({r['extraction_note']})"
                print(f"     extracted tables: {tick}")
            elif mode == "prefill":
                r = run_level_prefill(cfg, model, tokenizer, sampler, args.samples)
            else:
                r = run_level_single(cfg, model, tokenizer, sampler, args.samples)
            if args.samples == 1:
                print(f"  -> {r['best']}/{r['total']}  {'PASS' if r['best'] == r['total'] else 'FAIL'}\n")
            else:
                top = "; ".join(f"{c}×{n}" for c, n in r["reasons"][:3])
                print(f"  -> pass-rate {r['perfect']}/{args.samples}, best {r['best']}/{r['total']}, "
                      f"scores {r['scores']}")
                print(f"     outcomes: {top}\n")
        results.append(r)

    write_results_md(results, mode, args.samples)

    print("=" * 64)
    print("LADDER SUMMARY")
    print("=" * 64)
    for r in results:
        if mode in ("repair", "repair-rules", "repair2"):
            fastest = f"iter {r['min_iters']}" if r["min_iters"] else "—"
            print(f"  L{r['level']}  {r['title']:<34} converged {r['converged']}/{r['trajectories']}"
                  f"  fastest {fastest:<7} best {r['best']}/{r['total']}")
        elif args.samples == 1:
            print(f"  L{r['level']}  {r['title']:<34} {r['best']}/{r['total']}  "
                  f"{'PASS' if r['best'] == r['total'] else 'FAIL'}")
        else:
            print(f"  L{r['level']}  {r['title']:<34} pass-rate {r['perfect']}/{args.samples}"
                  f"  best {r['best']}/{r['total']}")

    def is_pass(r):
        # Reachability: did any attempt (or repair trajectory) reach a full 12/12? For a
        # small, single-shot-noisy model this "can the dialect get there at all" threshold
        # discriminates far better than demanding a 100% pass-rate.
        if mode in ("repair", "repair-rules", "repair2"):
            return r["converged"] > 0
        return r["best"] == r["total"]

    first_fail = next((r for r in results if not is_pass(r)), None)
    print("-" * 64)
    if first_fail is None:
        print("  No failure across the tested levels — extend the ladder harder.")
    elif first_fail["level"] == todo[0]["level"]:
        print(f"  Breaks immediately at L{first_fail['level']} — make an easier rung.")
    else:
        prev = results[results.index(first_fail) - 1]
        print(f"  SWEET SPOT: holds through L{prev['level']} ({prev['title']}), "
              f"breaks at L{first_fail['level']} ({first_fail['title']}).")
    rel = OUT_DIR.relative_to(PROJECT_DIR)
    print(f"\nResults written to {rel}/{_tagged('results', 'md')} "
          f"and {rel}/{_tagged('results', 'json')}")


if __name__ == "__main__":
    main()
