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
    def j(size, name):
        return {x["level"]: x for x in json.loads((SS / size / "outputs" / name).read_text())}
    return {
        # 3B — round 1
        "r": j("3b", "results_s10.json"), "g": j("3b", "results_greedy.json"),
        "t06": j("3b", "results_repair_rules_t06.json"), "t03": j("3b", "results_repair_rules_t03.json"),
        # round 2
        "g7": j("7b", "results_greedy.json"), "s7": j("7b", "results_s10.json"),
        "ex": j("3b", "results_extract-s10.json"), "pf": j("3b", "results_prefill-s10.json"),
        "xx": j("3b", "results_xextract.json"),
        "anch": j("3b", "results_repair2-anchored.json"), "fresh": j("3b", "results_repair2-fresh.json"),
        "fresh7": j("7b", "results_repair2-fresh.json"), "cool": j("3b", "results_repair2-cool.json"),
    }


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


def scale_table(g, r, g7, s7):
    rows = []
    for n in range(1, 9):
        s3, S7 = r[n], s7[n]
        g3s = f"{g[n]['best']}/12"
        g7s = f"{g7[n]['best']}/12"
        s3s = f"{s3['best']}/12"
        s7s = f"{S7['best']}/12&nbsp;({S7['perfect']}/{S7['samples']})"
        cls = "ok" if g7[n]["best"] == 12 else "bad"
        rows.append(
            f'<tr class="{cls}"><td>L{n}</td><td class="l">{esc(LEVEL_TITLE[n])}</td>'
            f'<td>{g3s}</td><td>{g7s}</td><td>{s3s}</td><td>{s7s}</td></tr>'
        )
    return ('<table class="tbl"><thead><tr><th>Rung</th><th class="l">Spec dialect</th>'
            '<th>3B greedy</th><th>7B greedy</th><th>3B best-of-10</th>'
            '<th>7B best-of-10 (pass-rate)</th></tr></thead><tbody>'
            + "".join(rows) + "</tbody></table>")


def hybrid_table(r, ex, pf, xx):
    rows = []
    for n in (3, 4, 5):
        e_ok = "tables ✓" if ex[n].get("extraction_ok") else "tables ✗"
        x_ok = "tables ✓" if xx[n].get("extraction_ok") else "tables ✗"
        rows.append(
            f'<tr><td>L{n}</td><td class="l">{esc(LEVEL_TITLE[n])}</td>'
            f'<td>{r[n]["best"]}/12</td>'
            f'<td>{ex[n]["best"]}/12 <span class="mono">{e_ok}</span></td>'
            f'<td>{pf[n]["best"]}/12</td>'
            f'<td>{xx[n]["best"]}/12 <span class="mono">{x_ok}</span></td></tr>'
        )
    return ('<table class="tbl"><thead><tr><th>Rung</th><th class="l">Spec dialect</th>'
            '<th>plain<br>best-of-10</th><th>self-extract<br>best-of-10</th>'
            '<th>prefill<br>best-of-10</th><th>7B extracts,<br>3B codes (greedy)</th>'
            '</tr></thead><tbody>' + "".join(rows) + "</tbody></table>")


def repair2_table(anch, fresh, cool, fresh7):
    variants = [
        ("anchored — previous code in the prompt (3B)", anch),
        ("fresh — regenerate from feedback (3B)", fresh),
        ("fresh, cool-start control 0.3→0.15 (3B)", cool),
        ("fresh (7B)", fresh7),
    ]
    rows = []
    for name, d in variants:
        cells, all_conv = [], True
        for n in (3, 4, 5):
            x = d[n]
            conv = x["converged"] > 0
            cells.append(f'<td>{x["best"]}/12' + (f' <b>✓ iter&nbsp;{x["min_iters"]}</b>' if conv else "") + "</td>")
            all_conv = all_conv and conv
        cls = ' class="ok"' if all_conv else ""
        rows.append(f'<tr{cls}><td class="l">{esc(name)}</td>' + "".join(cells) + "</tr>")
    return ('<table class="tbl"><thead><tr><th class="l">Repair-2.0 variant</th>'
            '<th>L3 business prose</th><th>L4 natural tier</th><th>L5 original dialect</th>'
            '</tr></thead><tbody>' + "".join(rows) + "</tbody></table>")


def build_html():
    R = load_results()
    r, g, t06, t03 = R["r"], R["g"], R["t06"], R["t03"]

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
a cleverer repair loop. A second round then tests three escapes from that boundary. <b>Scale</b>: the identical
ladder on the 7B leaves the greedy cliff exactly in place while making every rung reachable by sampling.
<b>Hybrids</b>: three ways of handing the lookup tables back (self-extraction, response prefill, cross-model)
all fail — extraction is 100% correct on both model sizes, so missing knowledge was never the bottleneck.
<b>Repair 2.0</b>: showing a small model its own code during repair collapses exploration entirely
("anchoring"), while a fresh-regeneration white-box loop <b>converges 12/12 on all three de-scaffolded rungs
with the 7B — including the business-prose rung nothing else cracked.</b></div>

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

<h2>6&nbsp;&nbsp;Round&nbsp;2 — scale, hybrids, and a second-generation repair loop</h2>
<p>Round one ended with a single stubborn cell: L3, the fully de-scaffolded business prose. The second round
asks three questions about it. <i>Does the cliff move with scale?</i> — run the identical ladder on
<code>Qwen2.5-Coder-7B-Instruct-4bit</code>, changing nothing but <code>--model</code>. <i>Is missing knowledge
the bottleneck?</i> — hand the lookup tables back in three different ways. <i>Can a better loop close it?</i> —
rebuild the repair loop around what round one taught. Every run below re-scores offline from its saved
artifact (<code>prove_ladder.py --tag&nbsp;…</code>).</p>

<h3>6.1&nbsp;&nbsp;Scale: the cliff does not move — reachability does</h3>
<p>Under greedy decoding the 7B draws <i>exactly the same boundary</i> as the 3B: every structured rung passes
(and L2, the 3B's one greedy wobble, is repaired by scale to 12/12), while every tables-removed rung fails at
4/12 — one row better than the 3B's 3/12, from case-handling rather than from any commission progress. Four
billion additional parameters do not buy a first-try pass on business prose. Sampling is a different story:
the 7B reaches 12/12 on L3, L4 <i>and</i> L5 within ten attempts — rungs the 3B never reached in any
experiment — but only at a pass-rate of 1–2 in 10. Spec structure is still worth more than parameters: the
structured rungs run at 8–10 in 10.</p>
{scale_table(g, r, R["g7"], R["s7"])}
<div class="cap">Table&nbsp;4 · The identical ladder at both model sizes (row colour = 7B greedy result). The
greedy cliff is unchanged; sampling makes every rung reachable for the 7B, at 1–2/10 reliability on the
prose rungs.</div>
<p><b>Scale swaps traps rather than removing them.</b> On the natural-tier control rungs the 7B gets stuck at
exactly 10/12 in 17 of 20 samples (L6 and L8, greedy included): it writes
<code>0.05 if volume &gt;= 100 else 0.10 if volume &gt;= 1000 else 0.0</code> — a misordered chained ternary
whose <code>0.10</code> branch is unreachable, so every <code>volume ≥ 1000</code> row gets half its discount.
This is the article's original Rule-4 tier trap resurfacing in a new surface form: the 3B collapsed the tier
bounds, the 7B misorders the ternary — and the additive phrasing (L7, kept from the v2 dialect) stays robust
at both sizes.</p>

<h3>6.2&nbsp;&nbsp;Hybrids: the model knows the tables — it cannot wield them from prose</h3>
<p>If the cliff were about missing data, handing the tables back should fix it. Three probes hand them back
three ways. <b>Self-extraction</b>: a first pass asks the model to rebuild
<code>PRODUCT_RATES</code>/<code>CATEGORY_MULTIPLIER</code> from the prose as Python literals; a second pass
codes with its own extraction appended. <b>Response prefill</b>: the reply is <i>seeded</i> so it already opens
with the true tables written out as code, and the model merely continues. <b>Cross-model</b>: the 7B extracts,
the 3B codes.</p>
{hybrid_table(r, R["ex"], R["pf"], R["xx"])}
<div class="cap">Table&nbsp;5 · Handing the tables back to the failing rungs (3B coder; best scores).
"tables&nbsp;✓" = the extracted constants matched ground truth exactly — which they did in <b>every run, on
both model sizes</b>.</div>
<p>Extraction never failed once. What fails, with correct tables in hand — its own! — is the same assembly:
the coder reads "a <b>10%</b> surcharge" as <code>receivable&nbsp;*=&nbsp;1.10</code> instead of materializing
a separate <code>0.10&nbsp;×&nbsp;receivable</code> <i>amount</i>, so the two loading values never exist as
variables and the commission has nothing to sum. (A second failure seam appears only in the two-stage
pipeline: the extractor writes <code>"1"</code>-style string keys, and half the coder samples index them with
<code>int</code> — the model is not even consistent with itself across two of its own turns.) This sharpens
round one's conclusion: the load-bearing scaffold is not the table <i>values</i> but the <b>code-shaped
decomposition</b> that comes with them — bare decimals and named quantities that force each step to exist.</p>

<h3>6.3&nbsp;&nbsp;Repair 2.0: anchoring versus regeneration</h3>
<p>Round one's white-box loop regenerated from scratch each iteration. Repair&nbsp;2.0 added four levers on
top of the per-step diffs: the <i>previous code in the prompt</i> with "edit only the first wrong step", a
freeze-list of steps verified correct on every row, <i>branch-3</i> (three candidates per iteration, keep the
best), and a temperature anneal. The first surprise was that the full combination is <b>worse than
round&nbsp;one</b> — and the per-iteration logs isolate the culprit cleanly. In the <b>anchored</b> runs the
instrumentation succeeds (all thirteen intermediates exposed), the localization works (culprit named,
freeze-list built) — and then every one of twelve repair candidates per level scores an <i>identical</i> 3/12
at every temperature from 0.5 to 0.2. Shown its own code, a 3B copies it. Removing the code from the prompt
(<b>fresh</b>) restores exploration instantly: candidate scores per iteration jump to spreads like
<code>[12,&nbsp;2,&nbsp;0]</code>, and the loop starts climbing.</p>
{repair2_table(R["anch"], R["fresh"], R["cool"], R["fresh7"])}
<div class="cap">Table&nbsp;6 · Repair&nbsp;2.0 variants on the failing rungs (best score; ✓ = converged to
12/12 at the given iteration). Anchoring flat-lines despite working localization; fresh regeneration rescues
L5 on the 3B; <b>the 7B converges on all three rungs.</b></div>
<p>Two honest footnotes from the controls. The cool-start run <i>refuted</i> our own working hypothesis — the
hot anneal phase (0.6→0.4, scores 0–2 everywhere) looked like wasted budget, yet starting cold did not
reproduce the L5 rescue: at 3B scale these single-trajectory outcomes are a lottery over candidates, and what
moves the odds is candidate <i>volume</i> (branch × iterations × trajectories), not schedule fine-tuning. And
nearly every scoring iteration picks one good candidate out of <code>[x,&nbsp;0,&nbsp;0]</code> — branch-3 is
three lottery tickets per iteration, which is precisely why it helps.</p>
<div class="keybox"><b>The round-2 headline: 7B + fresh white-box repair closes the board.</b> All three
de-scaffolded rungs converge to 12/12 within five iterations — including L3, the business-prose cell that
resisted every other lever in both rounds. Business prose in, numerically-correct code out, fully on-device.</div>

<h3>6.4&nbsp;&nbsp;The revised recipe</h3>
<div class="keybox" style="background:#eef4f8;border-color:#b7cede">For this ten-rule task on a small local
model, in increasing order of cost: <b>(1)</b> write the spec in the model's dialect — literal tables, bare
decimals, named steps — and the 3B passes greedy, first try; <b>(2)</b> keep the business prose and run
<b>7B + fresh white-box repair</b> — converged 12/12 on every prose rung in ≤5 iterations in our runs;
<b>(3)</b> sample the 7B and accept 1–2-in-10 reliability. What does <i>not</i> work: handing the tables back
in any form (the knowledge was never missing), showing a small model its own code during repair (anchoring),
or expecting scale alone to fix a first-try dialect failure.</div>

<h2>7&nbsp;&nbsp;Conclusion</h2>
<p>Yes — a tiny AI on an 8&nbsp;GB MacBook can write real, numerically-correct business logic, <i>provided the
specification is written in its dialect.</i> Holding the model fixed and moving only the words, we located the
boundary precisely: correctness survives plain declarative prose but collapses the moment the author stops
handing over the data tables and expects the model to assemble a multi-step derived quantity from narrative.
The two constructs long blamed for the failure turn out to be handled fine; the true fragility is
structural composition.</p>
<p>The second round hardened that finding from three directions and then, finally, broke through it. Scale
does not move the cliff — the 7B fails greedy business prose exactly where the 3B does, and re-arms the old
tier trap in a new disguise. Knowledge is not the constraint — both models rebuild the tables from prose
flawlessly and still cannot assemble the chain. And repair loops obey a sharp rule of their own: <b>shown its
own code, a small model stops exploring; forced to regenerate against per-step diffs, it climbs.</b> The
practical frontier today is a two-tier recipe: engineer the spec and a 3B delivers on the first deterministic
attempt — or keep the prose, add four billion parameters and a fresh-regeneration white-box loop, and converge
in a handful of iterations. Either way the original lesson stands: <b>the dependable lever is the words the
model reads, not the weights it runs on.</b></p>

<div class="foot">Models: <code>mlx-community/Qwen2.5-Coder-3B-Instruct-4bit</code> and (round&nbsp;2)
<code>…-7B-Instruct-4bit</code> via <code>mlx-lm 0.29.1</code> (Python&nbsp;3.9, Apple&nbsp;Silicon; round-2
runs on a 16&nbsp;GB M2&nbsp;Pro — the 4-bit 7B (~4.3&nbsp;GB) also fits an 8&nbsp;GB machine). Dataset: 12
rows, tolerance 0.5. Ladder metric: best-of-10 at temperature&nbsp;0.4. Repair: iteration-1 greedy, subsequent
iterations sampled. All specs, code, datasets, and result JSONs are in <code>experiments/sweet-spot/</code>;
this report is generated from those artifacts by <code>docs/build_report.py</code>.</div>

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
