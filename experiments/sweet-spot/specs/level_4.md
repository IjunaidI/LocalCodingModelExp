<!-- LEVEL 4 — Natural rules (re-arm the volume-tier trap). Diff vs level 3: the volume
     discount is stated as natural tiered bands instead of the additive "5% then another
     5%" wording — the phrasing that invites the 3-way-conditional collapse. Kept:
     constant Input-columns block, prose $/% rates, yes/no boolean. Dataset: yes/no. -->
# Pricing & commission calculation spec

Write `process_calculations(csv_path)` that reads the CSV and returns one dict per row
with the key `total_receivables`.

## Reading the CSV
Normalize every row before applying the rules — strip surrounding spaces from the headers
and **lower-case every text value** so comparisons work regardless of case. Copy this exactly:
```
row = {key.strip(): value.strip().lower() for key, value in row.items()}
```
This turns e.g. `EMEA` into `emea` and `non-EMEA` into `non-emea`. Then convert `volume`
and `productid` to numbers, and treat an empty cell as its stated default.

## Input columns
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
- a volume discount based on how much was ordered: under 100 units gets no volume
  discount, 100 to 999 units gets 5%, and 1000 units or more gets 10%;
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
