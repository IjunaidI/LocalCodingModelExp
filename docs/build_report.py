"""
Build the semi-research-paper PDF report from the live experiment artifacts.

Reads the 8 spec files + the result JSONs so the figures/tables stay in sync with the
actual runs, emits a self-contained styled HTML, and renders it to PDF with headless
Chrome (the only PDF engine available on this machine).

    python3 docs/build_report.py
"""

import re
import csv
import json
import html
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SS = ROOT / "experiments" / "sweet-spot"
OUT_HTML = ROOT / "docs" / "slm-tiny-ai-report.html"
OUT_PDF = ROOT / "docs" / "slm-tiny-ai-report.pdf"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

LEVEL_TITLE = {
    1: "Prescriptive pseudocode", 2: "Declarative spec", 3: "Business prose",
    4: "Natural rules (tier)", 5: "Original dialect (boolean)",
    6: "Tables + natural tier", 7: "Tables + True/False", 8: "Tables + tier + True/False",
}


def spec_body(n):
    """The model-visible spec text: strip the HTML authoring comment, collapse blank runs."""
    t = (SS / "specs" / f"level_{n}.md").read_text()
    t = re.sub(r"<!--.*?-->\n?", "", t, flags=re.DOTALL).strip()
    t = re.sub(r"\n\s*\n+", "\n", t)          # collapse blank lines so all 8 fit one page
    return t


def load_results():
    r = {x["level"]: x for x in json.loads((SS / "outputs" / "results.json").read_text())}
    g = {x["level"]: x for x in json.loads((SS / "outputs" / "results_greedy.json").read_text())}
    t06 = {x["level"]: x for x in json.loads((SS / "outputs" / "results_repair_rules_t06.json").read_text())}
    t03 = {x["level"]: x for x in json.loads((SS / "outputs" / "results_repair_rules_t03.json").read_text())}
    return r, g, t06, t03


def esc(s):
    return html.escape(s)


# ----------------------------------------------------------------------------- content ---

def specs_figure():
    cells = []
    for n in range(1, 9):
        cells.append(
            f'<div class="spec"><div class="spec-h">L{n} · {esc(LEVEL_TITLE[n])}</div>'
            f'<pre>{esc(spec_body(n))}</pre></div>'
        )
    return '<div class="spec-grid">' + "".join(cells) + "</div>"


def greedy_table(g):
    rows = []
    for n in range(1, 9):
        d = g[n]
        score = f"{d['best']}/{d['total']}"
        ok = d["best"] == d["total"]
        cls = "ok" if ok else "bad"
        rows.append(
            f'<tr class="{cls}"><td>L{n}</td><td class="l">{esc(LEVEL_TITLE[n])}</td>'
            f'<td>{score}</td><td class="c">{"PASS" if ok else "fail"}</td></tr>'
        )
    return ('<table class="tbl"><thead><tr><th>Rung</th><th class="l">Spec dialect</th>'
            '<th>Greedy score</th><th>Result</th></tr></thead><tbody>'
            + "".join(rows) + "</tbody></table>")


def staircase_table(r):
    rows = []
    for n in range(1, 9):
        d = r[n]
        pr = f"{d['perfect']}/{d['samples']}"
        best = f"{d['best']}/{d['total']}"
        reach = "✓" if d["best"] == d["total"] else "✗"
        cls = "ok" if d["best"] == d["total"] else "bad"
        grp = "control" if n >= 6 else ("cliff" if n in (3, 4, 5) else "pass")
        rows.append(
            f'<tr class="{cls}"><td>L{n}</td><td class="l">{esc(LEVEL_TITLE[n])}</td>'
            f'<td>{pr}</td><td>{best}</td><td class="c">{reach}</td></tr>'
        )
    return ('<table class="tbl"><thead><tr><th>Rung</th><th class="l">Spec dialect</th>'
            '<th>Pass-rate</th><th>Best of 10</th><th>Reachable</th></tr></thead><tbody>'
            + "".join(rows) + "</tbody></table>")


def repair_table(t06, t03, r):
    rows = []
    for n in (3, 4, 5):
        base = f"{r[n]['best']}/12"
        a = t06[n]
        b = t03[n]
        a_s = f"{a['best']}/12 ({a['converged']}/{a['trajectories']})"
        b_conv = f"{b['converged']}/{b['trajectories']}"
        b_extra = f", iter {b['min_iters']}" if b["min_iters"] else ""
        b_s = f"{b['best']}/12 ({b_conv}{b_extra})"
        star = ' class="ok"' if b["best"] == b["total"] else ""
        rows.append(f'<tr{star}><td>L{n}</td><td class="l">{esc(LEVEL_TITLE[n])}</td>'
                    f'<td>{base}</td><td>{a_s}</td><td>{b_s}</td></tr>')
    return ('<table class="tbl"><thead><tr><th>Rung</th><th class="l">Spec dialect</th>'
            '<th>best-of-10<br>(no repair)</th><th>repair-rules<br>@ temp 0.6</th>'
            '<th>repair-rules<br>@ temp 0.3</th></tr></thead><tbody>'
            + "".join(rows) + "</tbody></table>")


def build_html():
    r, g, t06, t03 = load_results()

    css = """
    @page { size: A4; margin: 17mm 16mm 16mm 16mm; }
    @page fig { size: A4; margin: 7mm; }
    html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    body { font-family: Georgia,'Times New Roman',serif; font-size:10.2pt; line-height:1.46;
           color:#191919; margin:0; }
    h1 { font-family:'Helvetica Neue',Arial,sans-serif; font-size:22pt; line-height:1.15;
         margin:0 0 4pt; color:#111; letter-spacing:-.3px; }
    .sub { font-family:'Helvetica Neue',Arial,sans-serif; font-size:11.5pt; color:#444;
           font-weight:500; margin:0 0 14pt; }
    h2 { font-family:'Helvetica Neue',Arial,sans-serif; font-size:13.5pt; color:#0b3d5c;
         border-bottom:1.5px solid #0b3d5c; padding-bottom:2pt; margin:20pt 0 8pt; }
    h3 { font-family:'Helvetica Neue',Arial,sans-serif; font-size:11pt; color:#134; margin:13pt 0 4pt; }
    p { margin:0 0 8pt; text-align:justify; }
    .byline { font-family:'Helvetica Neue',Arial,sans-serif; font-size:10pt; color:#333;
              border-top:2px solid #0b3d5c; border-bottom:1px solid #ccc; padding:6pt 0; margin:2pt 0 14pt; }
    .byline b { color:#0b3d5c; }
    .abstract { background:#f4f7f9; border-left:3px solid #0b3d5c; padding:9pt 12pt; margin:0 0 6pt;
                font-size:9.7pt; line-height:1.5; }
    .abstract .lbl { font-family:'Helvetica Neue',Arial,sans-serif; font-size:8.5pt; letter-spacing:.6px;
                  text-transform:uppercase; color:#0b3d5c; display:block; margin-bottom:3pt; font-weight:700; }
    code, .mono { font-family:'SF Mono',Menlo,Consolas,monospace; font-size:8.8pt;
                  background:#f0f2f4; padding:.5px 3px; border-radius:2px; }
    .tbl { border-collapse:collapse; width:100%; font-size:9.2pt; margin:6pt 0 4pt;
           font-family:'Helvetica Neue',Arial,sans-serif; }
    .tbl th { background:#0b3d5c; color:#fff; padding:4pt 6pt; text-align:center; font-weight:600; }
    .tbl td { border:1px solid #cfd8dd; padding:3.5pt 6pt; text-align:center; }
    .tbl td.l, .tbl th.l { text-align:left; }
    .tbl tr.ok td { background:#e9f6ec; }
    .tbl tr.bad td { background:#fdecec; }
    .cap { font-size:8.6pt; color:#555; font-style:italic; margin:2pt 0 10pt; text-align:center;
           font-family:'Helvetica Neue',Arial,sans-serif; }
    .keybox { background:#fbf6e9; border:1px solid #e6d8a8; border-radius:4px; padding:8pt 11pt;
              margin:8pt 0; font-size:9.6pt; }
    .keybox b { color:#7a5c00; }
    .fig-page { page:fig; page-break-before:always; page-break-after:always; }
    .fig-title { font-family:'Helvetica Neue',Arial,sans-serif; font-size:12pt; color:#0b3d5c;
                 font-weight:700; margin:0 0 5pt; }
    .spec-grid { column-count:2; column-gap:8px; }
    .spec { border:1px solid #c9d3d9; border-radius:3px; overflow:hidden; break-inside:avoid;
            display:inline-block; width:100%; margin:0 0 4px; }
    .spec-h { background:#0b3d5c; color:#fff; font-family:'Helvetica Neue',Arial,sans-serif;
              font-size:5.4pt; font-weight:700; padding:1.5px 4px; }
    .spec pre { font-family:'SF Mono',Menlo,Consolas,monospace; font-size:3.8pt; line-height:1.06;
                white-space:pre-wrap; word-break:break-word; margin:0; padding:2px 4px; color:#222; }
    ul { margin:2pt 0 8pt; padding-left:16pt; } li { margin:2pt 0; text-align:justify; }
    .foot { margin-top:14pt; padding-top:6pt; border-top:1px solid #ccc; font-size:8.4pt; color:#666;
            font-family:'Helvetica Neue',Arial,sans-serif; }
    """

    doc = f"""<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head><body>

<h1>Can a Tiny AI on an 8&nbsp;GB MacBook Write Real Business Logic?</h1>
<div class="sub">Locating the spec-dialect boundary where a 3-billion-parameter coder model stops producing correct code</div>
<div class="byline"><b>Muhammad Junaid</b> — iteration, ladder experiments &amp; repair loops&nbsp;&nbsp;·&nbsp;&nbsp;
<b>Muhammad Ansar</b> — original research &amp; problem&nbsp;&nbsp;·&nbsp;&nbsp;2 July 2026</div>

<div class="abstract"><span class="lbl">Abstract</span>
We ask whether <code>Qwen2.5-Coder-3B-Instruct-4bit</code>, run locally on Apple MLX, can generate a
<code>process_calculations()</code> that scores a perfect 12/12 on a ten-rule pricing-and-commission
specification. The model is fixed; the only lever is the <i>spec</i>. A re-dialected spec (v2) closes the
gap from the original's 1/12 to <b>12/12 on the first greedy attempt</b>. We then build an eight-rung
<i>spec ladder</i> — same ten rules and same targets, varying only the phrasing — to find the exact point of
failure. The break is sharp and surprising: it is not the two constructs originally blamed (a multi-tier
conditional and a truthy-string boolean), but the removal of the literal lookup tables, after which the 3B
can no longer assemble the multi-step <i>commission</i> calculation. Three control rungs confirm it: keep the
tables and the model tolerates every "trap." Finally, a white-box repair loop that feeds per-step
intermediate diffs rescues the boolean rung to 12/12 at a low temperature, but does not reliably rescue the
fully de-scaffolded rung — reaffirming that for a small model the dependable lever is the specification, not
a cleverer repair loop.</div>

<h2>1&nbsp;&nbsp;The question and the setup</h2>
<p>Small, locally-hosted language models are attractive: no data leaves the laptop, no per-token bill, and an
8&nbsp;GB Apple&nbsp;Silicon MacBook can host a 3B model comfortably. The open question is whether such a model
can produce <i>numerically correct</i> business logic — not plausible-looking code, but code whose output
matches ground truth to the cent, on every row.</p>
<p>The task is fixed throughout. A model must emit a Python function <code>process_calculations(csv_path)</code>
that applies a ten-rule pricing and commission ruleset to each row of a CSV and returns the running total
<code>total_receivables</code>. Success is <b>12/12</b>: all twelve ground-truth rows matched within a
0.5 tolerance. The model is fixed at <code>Qwen2.5-Coder-3B-Instruct-4bit</code> (the <i>Coder</i> variant,
via <code>mlx-lm</code>); we never swap in a larger or different model. Every experiment holds the model,
the harness, and the arithmetic constant, and changes only the wording of the spec.</p>

<h2>2&nbsp;&nbsp;The initial win — and why the old solution failed</h2>
<p>A five-rule version of the spec, each rule a single unambiguous operation, is solved by the 3B on the
first try: <b>12/12, no repairs.</b> The trouble begins at ten rules. Running the article's original
<i>True/False</i> spec, the model's best attempts are <b>3/12 on the 3B</b> and <b>1/12 on the 7B</b> — the
architecture is right but every row is 2–5% off. Two failures, both <i>linguistic</i> rather than a
capability ceiling, explain it:</p>
<ul>
<li><b>Rule&nbsp;4 — the volume tier.</b> The spec's three-way tier (<code>&lt;100&nbsp;→&nbsp;0%</code>,
<code>&lt;1000&nbsp;→&nbsp;5%</code>, <code>≥1000&nbsp;→&nbsp;10%</code>) is collapsed by the model into
<code>0.05 if v&lt;100 else (0.1 if v&lt;1000 else 0.1)</code> — wrong in two of three branches.</li>
<li><b>Rule&nbsp;10 — the boolean.</b> The <code>tax verified</code> cell is the string <code>"False"</code>,
which is <i>truthy</i> in Python, so <code>not row["tax verified"]</code> skips withholding at exactly the
rows where it should apply.</li>
</ul>
<p>The fix (the "v2" spec) re-expresses the <i>same ten rules</i> in the model's dialect: Rule&nbsp;4 becomes
two independent additive checks (<code>if v&gt;=100: +0.05</code>; <code>if v&gt;=1000: +0.05</code>) with an
explicit "no elif"; the boolean becomes <code>yes</code>/<code>no</code> text in both spec and data; rates are
handed over as literal Python dictionaries and bare decimals. The arithmetic is bit-identical to the original
(maximum absolute difference in targets = 0.0). The result: <b>12/12 on the first greedy attempt</b>. Same
problem, phrased so the model cannot trip — the lever is the spec, not the model.</p>

<h2>3&nbsp;&nbsp;The sweet-spot experiment</h2>
<p>The v2 spec passes and the original fails, but those are two distant points. <i>Where exactly</i> is the
boundary, and how technical must a spec author be to stay on the right side of it? To answer precisely we
build a ladder of eight specs. Every rung describes the identical ten-rule problem against identical targets;
the harness is frozen at the configuration that produced the validated 12/12 (same instruction wrapper,
same decoding, same scorer). <b>Only the spec file changes</b>, so any change in outcome is attributable to
the spec's dialect alone.</p>
<p>Rungs&nbsp;L1–L5 strip one layer of authoring scaffolding at a time, from the heavily-engineered v2 dialect
down to the natural original. Rungs&nbsp;L6–L8 are <i>controls</i>: they keep the literal lookup tables but
re-arm the volume-tier and boolean "traps," to test whether those traps are what actually break the model.</p>

<h3>Greedy first: the deterministic result</h3>
<p>We score each spec two ways. The simplest is to run it once with <b>greedy</b> decoding
(temperature&nbsp;0), which always takes the single most-likely next token — so the <i>same prompt yields the
identical program every time</i>, giving one reproducible score per spec (every spec carries an explicit
one-line normalization step so letter-case never confounds the reading — see the methodology note in §4).
Greedy already draws the boundary: <b>every rung that hands over the literal lookup tables passes 12/12</b> (L1, L6, L7, L8), while
every rung that removes them fails (L3–L5). The one exception is <b>L2</b> — it keeps the tables but phrases
the volume rule as terse additive prose, which greedy mis-formulates (see §4).</p>
{greedy_table(g)}
<div class="cap">Table&nbsp;1 · Greedy (deterministic) — one temperature-0 attempt per spec. Tables present ⇒
12/12 (except L2's prose-additive volume rule); tables removed (L3–L5) ⇒ fail. A single deterministic shot
already reproduces the boundary the sampled view confirms below.</div>

<h3>Sampling: measuring reliability</h3>
<p>A single greedy shot is still a knife-edge — it carries whatever the top completion produces, and a
trivial rewording can flip it (a one-line change to a spec's <i>title</i> once flipped L1 from 12/12 to 0/12).
To gauge how <i>reliably</i> a spec works, we also <b>sample</b>: at temperature&nbsp;0.4 the same prompt yields
<i>different</i> code on each run, so we ask each spec ten times and record the <b>best of the ten</b>
(reachable?) and the <b>pass-rate</b> (how many of the ten were fully correct). The sampled staircase below
confirms the same boundary and adds the reliability dimension a single greedy shot cannot show.</p>

<p class="cap">Figure&nbsp;1 (next page) shows all eight specs as the model sees them, scaled to a single page.
The prose after it walks through each rung.</p>

<div class="fig-page">
  <div class="fig-title">Figure&nbsp;1 &nbsp;·&nbsp; The eight-rung spec ladder (exactly the text fed to the model, HTML authoring notes stripped)</div>
  {specs_figure()}
</div>

<h3>Walking the ladder</h3>
<ul>
<li><b>L1 — Prescriptive pseudocode</b> (mirrors v2). Literal dicts, additive Rule&nbsp;4 with "no elif",
<code>yes/no</code> boolean, bare decimals, step-by-step recipe. The anchor: <b>reachable, 12/12.</b></li>
<li><b>L2 — Declarative spec.</b> Drops the imperative "<code>Start x = 0.0</code> … do NOT use elif" recipe;
states <i>what</i> each rule computes in plain prose. Tables still handed over. <b>Reachable, 12/12</b> — the
recipe was not load-bearing.</li>
<li><b>L3 — Business prose.</b> Removes the literal dictionaries and bare decimals; rates now appear as a
<code>$</code>/<code>%</code> narrative the model must turn into its own data structures. <b>Never reaches
more than 4/12.</b> This is the cliff.</li>
<li><b>L4 — Natural rules.</b> Re-arms the volume tier as natural bands ("under 100 … 100–999 … 1000+").
Already past the cliff: <b>best 3/12.</b></li>
<li><b>L5 — Original dialect.</b> Also re-arms the True/False boolean — the article's original phrasing.
<b>Best 6/12</b> (the case fix corrects its region rows, but the commission chain still breaks).</li>
<li><b>L6 — Tables + natural tier.</b> Control: the L4 tier phrasing, but with the literal tables kept.
<b>Reachable, 12/12.</b></li>
<li><b>L7 — Tables + True/False.</b> Control: the L5 boolean, tables kept. <b>Reachable, 12/12.</b></li>
<li><b>L8 — Tables + tier + True/False.</b> Control: <i>both</i> traps at once, tables kept. Still
<b>reachable, 12/12.</b></li>
</ul>

{staircase_table(r)}
<div class="cap">Table&nbsp;2 · Best-of-ten (sampled, temperature 0.4) per rung. Pass-rate is how many of ten
attempts hit a full 12/12; "reachable" means at least one did. Tables present (L1, L2, L6, L7, L8) ⇒
reachable; tables removed (L3, L4, L5) ⇒ not.</div>

<h2>4&nbsp;&nbsp;What the ladder shows — a summary</h2>
<p>The break is the <b>L2&nbsp;→&nbsp;L3 boundary</b>, and it is sharper than the original two-trap story.
Dropping the step-by-step recipe (L1&nbsp;→&nbsp;L2) costs nothing. Dropping the literal lookup tables
(L2&nbsp;→&nbsp;L3) is the cliff. And the failures are <i>not</i> the tier or boolean at all: at L3–L5 the model
handles both correctly in prose. Inspecting <i>which rows pass</i> at the failing rungs, it is always exactly
the four rows that are <code>non-emea</code> <b>and</b> <code>ach/wire</code> — the rows whose region and
payment loadings are both zero, i.e. <b>commission&nbsp;=&nbsp;0</b>. Every wrong row has a non-zero loading,
and the error is precisely the missing commission: for instance an electronics/EMEA row scores a ratio of
<code>0.8929&nbsp;=&nbsp;1/1.12</code>, exactly the effect of dropping
<code>commission = (region + payment&nbsp;loading) × 1.2</code> from the subtotal.</p>
<div class="keybox"><b>The load-bearing scaffold is the literal lookup tables, not the phrasing of the
famous traps.</b> With the tables present, every dialect is reachable (L1, L2, L6, L7, L8 → 12/12); with the
tables removed, none is (L3, L4, L5). The tables are necessary and nearly sufficient; the tier and boolean
traps are neither necessary nor sufficient — even both together (L8) still pass. Once the model must build
its own data structures from prose, what collapses is the multi-step <i>commission</i> chain, not the two
single-line constructs. <b>Greedy decoding draws the same line</b>: every table-keeping rung passes a single
deterministic shot (L1, L6, L7, L8), and every tables-removed rung fails it.</div>
<p><b>One nuance — phrasing still affects one-shot reliability.</b> L2 keeps the tables and is reachable when
sampled (12/12), yet it is the only table-keeping rung to miss on a single greedy shot (9/12): its terse
additive volume wording leads greedy to a wrong closed form that drops the sub-100 floor
(<code>0.05·(1 + (v≥1000))</code>). L6, which states the same rule as explicit tier bands, passes greedy on
the first try. So once the tables are present, whether a rule lands on the <i>first</i> attempt still depends
on stating each case explicitly — an additive one-liner is reachable but not one-shot-reliable.</p>
<p><b>Takeaway for a spec author.</b> You may write the ten-rule spec in plain declarative prose — but you
must (a) hand over the lookup tables verbatim and (b) name every multi-step derived quantity (here, the
commission) as its own explicit sub-step. Narrating a multi-step formula in one breath is the thing a 3B
cannot reliably reconstruct.</p>
<div class="keybox" style="background:#eef4f8;border-color:#b7cede"><b>Three methodology notes.</b> First,
<i>single greedy decoding is a knife-edge</i>: a one-line change to a spec's title flipped L1's deterministic
output from 12/12 to 0/12, so a small model must be evaluated by sampling, not one greedy roll. Second,
<i>the instruction wrapper can dominate the result</i>: an ambiguous "strip spaces from headers" made the
model delete the space inside <code>payment type</code> and crash, and "never crash" induced
<code>try/except</code> that swallowed the real bug — both were removed so the wrapper is precise and identical
for every rung. Third, <i>letter-case must be normalized explicitly</i>: the dataset stores <code>region</code>
as <code>EMEA</code>/<code>non-EMEA</code> in uppercase, so every spec now carries a one-line
<code>value.strip().lower()</code> normalization; without it the model compared <code>region == "emea"</code>
against <code>"EMEA"</code> and silently dropped the EMEA loading on those rows.</p></div>

<h2>5&nbsp;&nbsp;Can a repair loop rescue the failing rungs?</h2>
<p>The repository's standard loop generates code, scores it, and feeds the failure back for another attempt.
Its feedback is a <b>scalar total diff</b> ("row 3: got X, expected Y") — but the L3 failure is a
<i>localizable structural omission</i>: the whole commission chain is dropped. A single wrong number cannot
say <i>which</i> of ten steps is missing, so the model flails. We therefore built <code>--repair-rules</code>,
a <b>white-box loop</b>: a reference computes every intermediate in the pipeline, and on each failing row the
loop reports the <i>first</i> step that diverges — e.g. <i>"row 0: correct through <code>payment_loading</code>,
but <code>commission</code> = 0.00, should be 3206.25"</i> — asking the model to expose those intermediates so
they can be compared.</p>
<p>We ran it on the three failing rungs (three trajectories, up to six iterations) as an A/B on the repair
temperature. The localization works — the model does fix the flagged step. At the default temperature (0.6)
the score paths <i>oscillate</i> (<code>[4,&nbsp;0,&nbsp;1,&nbsp;0,&nbsp;0,&nbsp;9]</code>): fixing one step
regresses another, and nothing converges. <b>Dropping the repair temperature to 0.3</b> makes the edits
conservative enough to stick.</p>

{repair_table(t06, t03, r)}
<div class="cap">Table&nbsp;3 · White-box repair on the failing rungs. Cell shows best score and, in parentheses,
trajectories (of three) that reached a full 12/12. At temperature 0.3 the boolean rung <b>L5 converges to
12/12 in a single repair iteration</b> (path <code>[4,&nbsp;12]</code>); L4 climbs to 8/12; L3 still resists.</div>

<p><b>Interpretation.</b> White-box, per-step feedback is a <i>real</i> lever — enough to rescue the boolean
rung and nearly the tier rung at a low temperature — but <b>not a guarantee</b> for a fully de-scaffolded
spec. Rebuilding the entire commission chain from pure prose (L3) remains out of reach in this budget, and
the extra burden of emitting a dozen intermediate values every turn itself destabilizes a 3B's generation
(the residual zero-scores are crashes). The dependable fix for L3 is still the <i>spec</i> — put the table
back, or run a spec-repair loop that rewrites the prose toward the L1/L2 dialect — rather than out-arguing the
model with cleverer diffs.</p>

<h2>6&nbsp;&nbsp;Conclusion</h2>
<p>Yes — a tiny AI on an 8&nbsp;GB MacBook can write real, numerically-correct business logic, <i>provided the
specification is written in its dialect.</i> Holding the model fixed and moving only the words, we located the
boundary precisely: correctness survives plain declarative prose but collapses the moment the author stops
handing over the data tables and expects the model to assemble a multi-step derived quantity from narrative.
The two constructs long blamed for the failure turn out to be handled fine; the true fragility is
structural composition. A white-box repair loop can push the frontier outward — rescuing the boolean rung to
a perfect score at a conservative temperature — but the reliable, general lever remains the one this line of
work started from: <b>engineer the spec, not the model.</b></p>

<div class="foot">Model: <code>mlx-community/Qwen2.5-Coder-3B-Instruct-4bit</code> via <code>mlx-lm 0.29.1</code>
(Python&nbsp;3.9, Apple&nbsp;Silicon). Dataset: 12 rows, tolerance 0.5. Ladder metric: best-of-10 at
temperature&nbsp;0.4. Repair: iteration-1 greedy, subsequent iterations sampled. All specs, code, datasets, and
result JSONs are in <code>experiments/sweet-spot/</code>; this report is generated from those artifacts by
<code>docs/build_report.py</code>.</div>

</body></html>"""
    return doc


def main():
    OUT_HTML.write_text(build_html())
    print(f"wrote {OUT_HTML}")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={OUT_PDF}", OUT_HTML.as_uri()], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"wrote {OUT_PDF}")


if __name__ == "__main__":
    main()
