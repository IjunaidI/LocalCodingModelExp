# Out-of-the-box experiments — voting vs. decomposition

Two non-standard attacks on the 30-rule problem, chosen to *change the game* rather than
probe it further. They point in opposite directions, and the contrast is the finding.

| Approach | Idea | Result |
|---|---|---|
| **Ensemble voting** | aggregate many *full* attempts, per-row majority | ✗ not viable — can't build a committee |
| **Rule-by-rule compiler** | decompose into atomic functions, assemble deterministically | ✓ **23/23**, 27/28 functions first/second try |

## Experiment 1 — ensemble voting ([`../ensemble_vote.py`](../ensemble_vote.py))

Generate K independent solutions, run the ones that execute, and for each row take the
majority (largest tolerance-cluster) of their numeric outputs. Hypothesis: if the 3B's
near-misses have *independent* bugs, per-row majority could reach a full pass even when no
single program does.

It doesn't work — for a reason more basic than "correlated bugs":

| Regime | Ran | Individual scores | Best single | Majority | Median | Correct value present in committee |
|---|:--:|--|:--:|:--:|:--:|:--:|
| stripped-L1, temp 0.7 | 2/9 | 23, 1 | 23 | 1 | 1 | 23/23 (one member was perfect) |
| stripped-L1, temp 0.4 | 3/12 | 2, 2, 0 | 2 | 2 | 2 | 2/23 |
| **deliverable prompt, temp 0.3** | 3/12 | 5, 5, 0 | 5 | 5 | 9 | 9/23 |

**You cannot assemble a useful committee at 30 rules.** Temperature sampling of a ~120-line
function crashes ≈75% of the time even at temp 0.3, and the few runners score far below
greedy. Voting can only recover a row if the correct value appears in *some* member — and
that held for just 2–9 of 23 rows. Majority never beats the best single; median edged above
it once (9 vs 5) by hitting that ceiling, but the ceiling itself is nowhere near a pass.

This is the **knife-edge finding restated**: the only good 30-rule output is greedy on the
exact deliverable prompt; the instant you sample around it, quality falls off the cliff — so
there is nothing to vote with. Aggregating full attempts is the wrong lever.

## Experiment 2 — rule-by-rule compiler ([`../compiler.py`](../compiler.py))

The ladder showed the 3B can't *assemble* a 27-rule pipeline. So don't ask it to. Ask for
~two dozen tiny **pure** functions (one rule each), **unit-test every function** against the
reference and resample until it passes, then let a **fixed assembler (our code)** wire them
into `process_calculations` in the correct order.

**Result: 27/28 functions pass their unit test — most on the first greedy try — and the
assembled program scores 23/23.** Assembly was the bottleneck; the atomic rules are easy.

The single per-run miss is always a **known dialect trap**, now isolated to one tiny,
independently-testable function:

- `product_rate` (the one 2-level-dict lookup) initially failed 4/4 — at temp 0 it dropped
  the dict's closing brace, and at temp 0.5 it read the micro-spec shorthand **"1000/900" as
  a division**, not "1000 for individual, 900 for corporate". Rewording the micro-spec
  unambiguously fixed it.
- `withholding_rate` slips on the **empty tax cell** (`("",) -> 0.0, expected 0.03`) — it
  withholds only on the literal `"no"` and misses the empty case. That is the *original
  truthy-string boolean trap* that started this whole project, resurfacing atomically.

Because each function carries its own unit test, you always **know which one failed** and can
resample or reword just that micro-spec (the reference fallback used here is a stand-in for
"resample until the unit test passes"). The dialect traps don't disappear under decomposition
— but they shrink to a single localizable function instead of sinking the whole monolith.

## How the assembled "atomic" solution works ([`compiler_solution.py`](compiler_solution.py))

The output file has **two halves**, and the split is the whole idea.

**1. ~27 atomic functions the model wrote.** Each is *pure*, takes primitive arguments, and
returns one rate / multiplier / amount — nothing more. A few, verbatim from the run:

```python
def volume_rate(volume):          # Rule B — the multi-tier conditional
    if volume < 100:   return 0.0
    elif volume < 1000: return 0.05
    else:              return 0.10

def capital_city_rate(city):      # Rule R
    return 0.10 if city in ["karachi","lahore","islamabad","peshawar","quetta"] else 0.0

def accelerator_rate(customer, loyalty_status, volume, correction_fee):   # Rule X
    return 0.07 if customer=="strategic" and loyalty_status=="platinum" \
                   and volume>=1000 and correction_fee==0.0 else 0.0
```

Each one is trivially checkable *on its own*, so the harness ([`../compiler.py`](../compiler.py))
unit-tests every function against the reference and resamples it until it passes. That is why
the model gets 27/28 right first/second try — you never ask it to hold the whole pipeline in
its head, only one rule at a time.

**2. A fixed assembler we wrote** — the `process_calculations` at the bottom of the file. It
does the part the model *couldn't*: read the CSV, normalize each field (strip / lower-case /
to-number, `quarter` upper-cased), then call the atomic functions **in the exact pipeline
order** and thread the data flow:

```python
rate = product_rate(pid, status);           rbd = volume * rate
rad  = rbd * (1 - (spring_rate(season) + volume_rate(volume)
                   + strategic_rate(customer) + loyalty_rate(years)))          # discounts
base = (region_loading_rate(region) + payment_loading_rate(pay)
        + quarter_loading_rate(quarter) + zone_loading_rate(txn)
        + speed_loading_rate(speed)) * rad                                     # loadings
adj  = base * category_multiplier(category)
adj *= (1 - risk_fee_rate(hr));  adj *= (1 + referral_credit_rate(ref, remaining))
pre  = rad + adj + correction_fee(corr_flag) + min_fee(rad + adj)
total = pre - withholding_rate(tax) * pre                                      # master total
for each cascade rule:  total *= (1 - <that rule's rate>)                      # R..AB
escrow = escrow_amount(rbd)                                                    # 1% of rbd, separate
```

The division of labor is the lesson: the **model supplies the per-rule logic** (easy,
independently verifiable) and the **assembler supplies the pipeline wiring** — the multi-step
assembly that broke the monolith at L1→L2. Because each function has its own unit test, you
always know exactly which one to resample; the single reference fallback in this run
(`withholding_rate`, tripped by the empty-tax-cell boolean) is just the harness standing in for
"resample until its test passes."

Regenerate it: `.venv/bin/python experiments/30-rule/compiler.py --retries 4`.

## The takeaway

At 30 rules, leverage comes from **reducing what you ask the model to do in one shot**, not
from **aggregating many full attempts**:

- a full 30-rule attempt is a knife-edge that collapses under sampling → **voting has no
  committee to work with**;
- an atomic one-rule attempt is rock-solid and *verifiable* → **decomposition + per-function
  unit tests turns the impossible monolith into a reliable 23/23 pipeline.**

Repair (localize-and-fix the monolith) rescued nothing; voting (outvote the monolith's bugs)
had nothing to vote on; decomposition (never build the monolith) worked. The consistent
thread: shrink the unit of generation until it is both easy and checkable.

## Files
- [`../ensemble_vote.py`](../ensemble_vote.py) — voting harness (`--k`, `--temp`, `--full-prompt`)
- [`../compiler.py`](../compiler.py) — decompose → per-function unit-test → assemble
- [`compiler_solution.py`](compiler_solution.py) — **the assembled 23/23 program** (27 model
  functions + the fixed assembler); walked through above
- `ensemble_result.json`, `compiler_result.json` — raw result sheets
- `viz_greedy.html`, `viz_outofbox.html` — the two result visualizations (open in a browser)
