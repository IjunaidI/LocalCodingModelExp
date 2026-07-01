<!-- LEVEL 3 — Business prose. Diff vs level 2: rates/multipliers given as prose with
     $ and %, so the model must build its own data structures and convert percentages
     (no literal Python dicts, no bare decimals). Rates are tied to the real column
     names (productid, status) to avoid label/column confusion. Kept: constant
     Input-columns block, additive volume wording, yes/no boolean. Dataset: yes/no. -->
# Pricing & commission calculation spec

Write `process_calculations(csv_path)` that reads the CSV and returns one dict per row
with the key `total_receivables`.

## Input columns
Each row has these columns (header names may have extra surrounding spaces (strip leading/trailing whitespace only, and keep inner spaces like in `payment type`); compare text in lower
case; convert `volume` and `productid` to numbers; an empty cell means the stated default):
- `productid` : "1", "2", or "3"
- `status` : "individual" or "corporate"
- `volume` : an integer
- `season` : "spring", "summer", "winter", or "autumn"
- `customer` : "strategic" or "non-strategic"
- `region` : "emea" or "non-emea"
- `payment type` : "ach/wire" or "credit-card"
- `transaction type` : "domestic", "international", or "cross-border"
- `product category` : "electronics", "groceries", or "luxury"
- `tax verified` : "yes" or "no" (an empty cell counts as "no")

## The calculation

The per-unit price depends on `productid` and `status`. For productid 1 it is $1,000 when
status is individual and $900 when corporate; for productid 2 it is $1,500 / $1,200; for
productid 3 it is $2,000 / $1,700. The base receivable is `volume` times that per-unit price.

Then three discounts come off, and they stack (add together):
- **5%** if the `season` is spring;
- a volume discount of **5%** once `volume` reaches 100, plus a further **5%** once
  `volume` reaches 1000 (so 100–999 is 5% and 1000-or-more is 10%);
- **5%** if the `customer` is strategic.

Apply the combined discount to get the receivable after discount.

Two surcharges are then figured from the receivable after discount:
- **10%** if the `region` is EMEA;
- **2.5%** if the `payment type` is credit-card.

Commission is the sum of those two surcharge amounts, scaled by a factor that depends on
`product category`: electronics ×1.2, groceries ×0.8, luxury ×1.5.

The subtotal is the receivable after discount plus the commission. If `tax verified` is
"no" (or blank), withhold **3%** of the subtotal; if it is "yes", withhold nothing.

`total_receivables` is the subtotal minus the withholding.
