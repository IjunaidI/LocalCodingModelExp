"""
Build the follow-up report: the 7B scaling study, as a standalone semi-research paper.

Extends section 6 of the main report (slm-tiny-ai-report.pdf) with the detail that
did not fit there: per-rung score distributions, repair score-paths, the row-level
anatomy of the resurfaced tier trap, and the v2-deliverable cross-size result.
Everything is generated live from the committed result JSONs in
experiments/sweet-spot/{3b,7b}/outputs/, so tables stay in sync with the runs.

    python3 docs/build_report_7b.py
"""

import json
import subprocess

from build_report import ROOT, SS, CHROME, LEVEL_TITLE, esc

OUT_HTML = ROOT / "docs" / "slm-7b-scaling-report.html"
OUT_PDF = ROOT / "docs" / "slm-7b-scaling-report.pdf"


def j(size, name):
    return {x["level"]: x for x in json.loads((SS / size / "outputs" / name).read_text())}


def load():
    return {
        "g3": j("3b", "results_greedy.json"), "s3": j("3b", "results_s10.json"),
        "g7": j("7b", "results_greedy.json"), "s7": j("7b", "results_s10.json"),
        "ex": j("3b", "results_extract-s10.json"), "pf": j("3b", "results_prefill-s10.json"),
        "xx": j("3b", "results_xextract.json"),
        "anch": j("3b", "results_repair2-anchored.json"),
        "fresh3": j("3b", "results_repair2-fresh.json"),
        "cool": j("3b", "results_repair2-cool.json"),
        "fresh7": j("7b", "results_repair2-fresh.json"),
    }


# ----------------------------------------------------------------------------- tables ---

def greedy_table(g3, g7):
    rows = []
    for n in range(1, 9):
        cls = "ok" if g7[n]["best"] == 12 else "bad"
        rows.append(f'<tr class="{cls}"><td>L{n}</td><td class="l">{esc(LEVEL_TITLE[n])}</td>'
                    f'<td>{g3[n]["best"]}/12</td><td>{g7[n]["best"]}/12</td></tr>')
    return ('<table class="tbl"><thead><tr><th>Rung</th><th class="l">Spec dialect</th>'
            '<th>3B greedy</th><th>7B greedy</th></tr></thead><tbody>'
            + "".join(rows) + "</tbody></table>")


def dist_table(s3, s7):
    rows = []
    for n in range(1, 9):
        d = s7[n]
        dist = ", ".join(str(x) for x in sorted(d["scores"], reverse=True))
        cls = "ok" if d["perfect"] >= 8 else ("bad" if d["perfect"] <= 2 else "")
        rows.append(f'<tr class="{cls}"><td>L{n}</td><td class="l">{esc(LEVEL_TITLE[n])}</td>'
                    f'<td class="l"><span class="mono">{dist}</span></td>'
                    f'<td>{d["perfect"]}/10</td><td>{s3[n]["perfect"]}/10</td></tr>')
    return ('<table class="tbl"><thead><tr><th>Rung</th><th class="l">Spec dialect</th>'
            '<th class="l">7B — ten sampled scores (sorted)</th><th>7B pass-rate</th>'
            '<th>3B pass-rate</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table>")


def hybrid_table(s3, ex, pf, xx):
    rows = []
    for n in (3, 4, 5):
        rows.append(f'<tr><td>L{n}</td><td class="l">{esc(LEVEL_TITLE[n])}</td>'
                    f'<td>{s3[n]["best"]}/12</td><td>{ex[n]["best"]}/12</td>'
                    f'<td>{pf[n]["best"]}/12</td><td>{xx[n]["best"]}/12</td></tr>')
    return ('<table class="tbl"><thead><tr><th>Rung</th><th class="l">Spec dialect</th>'
            '<th>plain 3B<br>best-of-10</th><th>3B extracts,<br>3B codes</th>'
            '<th>prefilled<br>tables</th><th><b>7B extracts</b>,<br>3B codes</th>'
            '</tr></thead><tbody>' + "".join(rows) + "</tbody></table>")


def _path(d, n):
    p = d[n]["paths"][0]
    s = " → ".join(str(x) for x in p)
    return f'<span class="mono">{s}</span>' + (" ✓" if d[n]["converged"] else "")


def repair_paths_table(anch, fresh3, cool, fresh7):
    variants = [
        ("anchored (3B) — previous code in prompt", anch),
        ("fresh (3B) — regenerate from feedback", fresh3),
        ("fresh cool-start control (3B)", cool),
        ("fresh (7B)", fresh7),
    ]
    rows = []
    for name, d in variants:
        conv = all(d[n]["converged"] for n in (3, 4, 5))
        cls = ' class="ok"' if conv else ""
        cells = "".join(f'<td class="l">{_path(d, n)}</td>' for n in (3, 4, 5))
        rows.append(f'<tr{cls}><td class="l">{esc(name)}</td>{cells}</tr>')
    return ('<table class="tbl"><thead><tr><th class="l">Variant</th>'
            '<th class="l">L3 score path</th><th class="l">L4 score path</th>'
            '<th class="l">L5 score path</th></tr></thead><tbody>'
            + "".join(rows) + "</tbody></table>")


def v2_table():
    return ('<table class="tbl"><thead><tr><th class="l">Spec</th><th>3B</th><th>7B</th>'
            '</tr></thead><tbody>'
            '<tr class="bad"><td class="l">Original ten-rule spec (True/False dialect)</td>'
            '<td>3/12 best</td><td>1/12 best</td></tr>'
            '<tr class="ok"><td class="l">v2 spec — same rules, model\'s dialect</td>'
            '<td><b>12/12 first greedy try</b></td><td><b>12/12 first greedy try</b></td></tr>'
            '</tbody></table>')


# ------------------------------------------------------------------------------- html ---

CSS = """
@page { size: A4; margin: 17mm 16mm 16mm 16mm; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-family: Georgia,'Times New Roman',serif; font-size:10.2pt; line-height:1.46;
       color:#191919; margin:0; }
h1 { font-family:'Helvetica Neue',Arial,sans-serif; font-size:21pt; line-height:1.15;
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
.codeblock { font-family:'SF Mono',Menlo,Consolas,monospace; font-size:8.8pt; background:#f0f2f4;
             border:1px solid #dde3e8; border-radius:3px; padding:6pt 9pt; margin:4pt 0 8pt;
             white-space:pre; overflow:hidden; }
.tbl { border-collapse:collapse; width:100%; font-size:9.2pt; margin:6pt 0 4pt;
       font-family:'Helvetica Neue',Arial,sans-serif; page-break-inside:avoid; }
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
ul { margin:2pt 0 8pt; padding-left:16pt; } li { margin:2pt 0; text-align:justify; }
.foot { margin-top:14pt; padding-top:6pt; border-top:1px solid #ccc; font-size:8.4pt; color:#666;
        font-family:'Helvetica Neue',Arial,sans-serif; }
"""


def build_html():
    R = load()
    doc = f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>

<h1>What Four Billion More Parameters Buy — and What They Don't</h1>
<div class="sub">Qwen2.5-Coder-7B on the spec ladder: a follow-up to
"Can a Tiny AI on an 8&nbsp;GB MacBook Write Real Business Logic?"</div>
<div class="byline"><b>Muhammad Junaid</b> — experiments &amp; analysis&nbsp;&nbsp;·&nbsp;&nbsp;
<b>Muhammad Ansar</b> — original research &amp; problem&nbsp;&nbsp;·&nbsp;&nbsp;3 July 2026</div>

<div class="abstract"><span class="lbl">Abstract</span>
The first report located a sharp boundary for <code>Qwen2.5-Coder-3B-Instruct-4bit</code> on a ten-rule
pricing spec: with the literal lookup tables in the spec the model reaches 12/12; strip them and it never
recovers, failing on the multi-step commission chain. Here we hold everything constant and change one
thing — the model, to the 7B of the same family — and follow up with hybrid probes and repair loops at
both sizes. Four results. <b>(1)</b>&nbsp;The greedy cliff does not move: the 7B fails every de-scaffolded
rung at 4/12, exactly where the 3B breaks. <b>(2)</b>&nbsp;Scale converts "unreachable" into "rare":
best-of-ten sampling reaches 12/12 on all three prose rungs — at a 1–2-in-10 pass-rate, versus 8–10-in-10
for the structured rungs. <b>(3)</b>&nbsp;Scale swaps traps rather than removing them: the 7B re-arms the
article's original volume-tier bug in a new syntactic disguise, pinning 17 of 20 natural-tier samples at
exactly 10/12. <b>(4)</b>&nbsp;Paired with a fresh-regeneration white-box repair loop, the 7B converges
12/12 on <i>every</i> prose rung within five iterations — including the business-prose rung that resisted
every other lever at both sizes. The closing symmetry: the re-dialected v2 spec passes first-try greedy on
<i>both</i> sizes, while the original spec fails on both — the words, not the weights, remain the lever.</div>

<h2>1&nbsp;&nbsp;Setup: one variable, again</h2>
<p>The methodology is inherited unchanged from the first report: eight spec rungs describing the identical
ten-rule problem against identical 12-row targets — L1/L2 structured, L3–L5 progressively de-scaffolded
prose, L6–L8 controls that keep the lookup tables while re-arming the volume-tier and boolean traps. Frozen
harness, frozen instruction wrapper, frozen scorer (pass&nbsp;=&nbsp;12/12 within&nbsp;0.5). The single new
variable is <code>--model&nbsp;mlx-community/Qwen2.5-Coder-7B-Instruct-4bit</code> — same family, same
4-bit quantization, ~4.3&nbsp;GB against the 3B's ~1.8&nbsp;GB. Artifacts for each size live in
<code>experiments/sweet-spot/3b/</code> and <code>7b/</code> under identical filenames, and every number
below re-scores offline via <code>prove_ladder.py --dir 7b --tag&nbsp;…</code>.</p>

<h2>2&nbsp;&nbsp;The greedy cliff does not move</h2>
<p>One deterministic temperature-0 attempt per rung, both sizes:</p>
{greedy_table(R["g3"], R["g7"])}
<div class="cap">Table&nbsp;1 · Greedy, one attempt per rung (row colour = 7B result). The boundary is
unchanged: structured specs pass, de-scaffolded specs fail — at either size.</div>
<p>Three details are worth the ink. The 7B repairs the 3B's one greedy wobble (L2, a terse additive volume
phrasing, 9/12&nbsp;→&nbsp;12/12). On the prose rungs it fails at 4/12 versus the 3B's 3/12 — the extra row
comes from cleaner text normalization, not from any progress on the commission chain; inspection shows the
same missing-commission signature (only the zero-loading rows pass, plus one). And on two rungs the 7B is
<i>worse</i> than the 3B (L6, L8: 10/12 vs 12/12) — the subject of §4.</p>

<h2>3&nbsp;&nbsp;Sampling: scale buys reachability, not reliability</h2>
<p>Ten attempts per rung at temperature 0.4. The full score distributions make the pattern legible at a
glance:</p>
{dist_table(R["s3"], R["s7"])}
<div class="cap">Table&nbsp;2 · The 7B's ten sampled scores per rung (sorted), with pass-rates for both
sizes. Green = reliable (≥8/10); red = rare (≤2/10).</div>
<p>Every rung is now <i>reachable</i> — the 7B hits 12/12 at least once everywhere, including the three
prose rungs the 3B never solved in any experiment. But the distributions show what "reachable" is worth:
on L3 the modal outcome is still a 4–5/12 with the commission chain mangled, and the two perfect samples
are draws from a long tail. Structure is worth more than scale: the structured rungs run at 8–10/10
while the prose rungs run at 1–2/10. A spec author who writes in the model's dialect gets a better
machine than one who buys the bigger model.</p>

<h2>4&nbsp;&nbsp;The trap that came back</h2>
<p>The strangest cells in Tables 1–2 are L6 and L8, where the <i>bigger</i> model is stuck at exactly
10/12 in 17 of its 20 samples (greedy included) on rungs the 3B passes cleanly. The failing rows are
always the two with <code>volume ≥ 1000</code>, and the generated code always contains the same construct:</p>
<div class="codeblock">volume_rate = 0.05 if volume >= 100 else 0.10 if volume >= 1000 else 0.0</div>
<p>A misordered chained ternary: the first condition captures every <code>volume ≥ 100</code>, so the
<code>0.10</code> branch is unreachable and the large-volume rows get half their discount — off by exactly
the ratio the scorer shows (e.g. 1.0556&nbsp;=&nbsp;(1−0.05·…)/(1−0.10·…) on the affected rows). This is
the original article's Rule-4 volume-tier bug, resurfacing at 7B in a new syntactic disguise: the 3B
collapsed the tier <i>bounds</i>; the 7B orders the ternary <i>conditions</i> wrong. Meanwhile L7 — which
keeps the v2 dialect's additive phrasing ("+0.05 once volume reaches 100, a further +0.05 at 1000") —
runs at 9/10 on the 7B and 12/12 greedy on both sizes. <b>The additive decomposition is robust across
model sizes; the natural tier phrasing finds a new way to fail at each size.</b> Trap-proofing a spec
against one model does not certify it for the next.</p>

<h2>5&nbsp;&nbsp;The 7B as knowledge donor: hybrids still fail</h2>
<p>If the prose rungs failed for lack of the tables, a bigger model could donate them. In the cross-model
hybrid the 7B reads the prose spec and emits the lookup tables as Python literals; the 3B then codes with
that extraction appended. The 7B's extractions were <b>correct in every run</b> — as were the 3B's own
(both sizes rebuild <code>PRODUCT_RATES</code> and <code>CATEGORY_MULTIPLIER</code> from prose flawlessly,
every time). None of it rescues the coder:</p>
{hybrid_table(R["s3"], R["ex"], R["pf"], R["xx"])}
<div class="cap">Table&nbsp;3 · Handing the tables back to the failing rungs (best scores; the 3B is
always the coder). Extraction was correct in 100% of runs, both sizes.</div>
<p>With correct tables in hand — its own, or the 7B's — the coder still reads "a 10% surcharge" as
<code>receivable *= 1.10</code>, never materializes the two loading <i>amounts</i>, and the commission has
nothing to sum. Knowledge was never the bottleneck; the code-shaped decomposition (bare decimals, named
quantities) that accompanies literal tables is what carries the chain.</p>

<h2>6&nbsp;&nbsp;Repair loops: where the 7B breaks through</h2>
<p>The white-box repair loop tells the model, per failing row, the <i>first</i> pipeline step whose value
diverges from a reference ("<code>commission</code> = 0.00, should be 3206.25"). Round two rebuilt it with
four levers — previous code in the prompt with "edit only the culprit step", a freeze-list of verified
steps, three sampled candidates per iteration (keep the best), and a temperature anneal — and the
per-iteration score paths tell the whole story:</p>
{repair_paths_table(R["anch"], R["fresh3"], R["cool"], R["fresh7"])}
<div class="cap">Table&nbsp;4 · Score after each iteration (row 1 = the greedy attempt; ✓ = converged to
12/12). "Anchored" shows the model its previous code; "fresh" regenerates from feedback alone.</div>
<ul>
<li><b>Anchoring kills exploration at both sizes.</b> With its own code in the prompt the model copies it:
every candidate, every iteration, an identical score — despite the localization working (culprit named,
freeze-list built). The flat paths above are 12 consecutive identical-scoring candidates per rung.</li>
<li><b>Fresh regeneration restores variance</b> — candidate spreads like <span class="mono">[12, 2, 0]</span>
within a single iteration — and the loop starts climbing. On the 3B that buys back the boolean rung (L5)
and lifts L4 to 9/12; L3 stays out of reach, and a cool-start control shows the outcome is a lottery over
candidates rather than a schedule effect.</li>
<li><b>On the 7B it closes the board.</b> All three prose rungs converge — L4 in a single repair iteration
(one of its first three candidates scored 12/12), L3 and L5 by iteration five as the anneal reaches 0.3.
L3, business prose, is the cell that resisted every other lever at both sizes across both rounds.</li>
</ul>
<div class="keybox"><b>The design rule this isolates: give a small model feedback about its code — never
the code itself.</b> And the capability rule: the white-box loop is the first lever where scale genuinely
pays. Prose in, numerically-correct code out, fully on-device — 7B plus fresh white-box repair.</div>

<h2>7&nbsp;&nbsp;The deliverable spec, at both sizes</h2>
<p>The v2 spec — the first report's deliverable, whose dialect the ladder's L1 mirrors — completes the
symmetry. Run unchanged on the 7B it passes exactly as it does on the 3B:</p>
{v2_table()}
<div class="cap">Table&nbsp;5 · The original ten-rule spec vs the re-dialected v2, both model sizes
(v2 7B run: <code>solve_simple_v2.py --model …7B…</code>, saved as
<code>solution_best_v2_7b.py</code>, re-verified offline).</div>
<p>The original spec fails on both sizes; the v2 dialect passes first-try greedy on both. Nothing about
the fix was 3B-specific — it is simply closer to the distribution both coders were trained on.</p>

<h2>8&nbsp;&nbsp;Conclusions</h2>
<p>What do four billion extra parameters buy on this task? Not the first attempt: the greedy cliff sits at
the same rung, with the same missing-commission signature. Not knowledge: both sizes already rebuild the
tables from prose perfectly. What scale buys is <i>tail probability</i> — 12/12 exists in the 7B's sample
distribution where the 3B's tail ends at 6 — and, decisively, <i>repairability</i>: enough
instruction-following headroom that a white-box loop with fresh regeneration converges every prose rung in
a handful of iterations. The practical recipe is therefore two-tier: <b>engineer the spec and the smallest
model passes on the first deterministic attempt; keep the prose, and buy the 7B <i>plus a repair loop</i> —
not the 7B alone.</b> And one caution travels with it: model-specific trap-proofing does not transfer —
each size found its own way to break the natural tier phrasing, and only the explicitly decomposed additive
form survived both. The lever, at every size we can fit on this laptop, remains the words.</p>

<div class="foot">Models: <code>mlx-community/Qwen2.5-Coder-3B-Instruct-4bit</code> and
<code>…-7B-Instruct-4bit</code> via <code>mlx-lm 0.29.1</code> (Python&nbsp;3.9, Apple&nbsp;Silicon;
16&nbsp;GB M2&nbsp;Pro — the 4-bit 7B (~4.3&nbsp;GB) also fits an 8&nbsp;GB machine, one model resident at
a time). Companion to <code>slm-tiny-ai-report.pdf</code> (the round-1 paper, whose §6 this report
expands). All artifacts re-score offline: <code>experiments/sweet-spot/{{3b,7b}}/outputs/</code> via
<code>prove_ladder.py</code>, and <code>experiments/10-rule-v2/</code> via <code>prove_v2.py</code>.
Generated by <code>docs/build_report_7b.py</code>.</div>

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
