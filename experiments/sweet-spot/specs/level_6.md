<!-- LEVEL 6 — Tables kept + natural volume-tier (control for the tier trap). Branches
     from level 2 (literal dicts, declarative prose, yes/no) but states the volume rule
     as natural tiered bands (the L4 phrasing). Isolates: does the tier phrasing break
     the model when the lookup tables are still handed over? Dataset: yes/no. -->
# Pricing & commission calculation spec

`process_calculations(csv_path)` reads a CSV and returns one dict per row, each with the
key `total_receivables`.

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

## Lookup tables
```
PRODUCT_RATES = {
    1: {"individual": 1000, "corporate": 900},
    2: {"individual": 1500, "corporate": 1200},
    3: {"individual": 2000, "corporate": 1700},
}
CATEGORY_MULTIPLIER = {"electronics": 1.2, "groceries": 0.8, "luxury": 1.5}
```

## The calculation

The base receivable is `volume * PRODUCT_RATES[productid][status]`.

Three discount rates then apply, and they add together:
- a spring rate of `0.05` when `season` is "spring", otherwise `0.0`;
- a volume rate based on how much was ordered: `0.0` under 100 units, `0.05` from 100 to
  999 units, and `0.10` at 1000 units or more;
- a strategic rate of `0.05` when `customer` is "strategic", otherwise `0.0`.

The receivable after discount is the base times `(1 - sum of those three rates)`.

Two loadings are computed from the receivable after discount:
- a region loading of `0.10 * receivable_after_discount` when `region` is "emea", else `0.0`;
- a payment loading of `0.025 * receivable_after_discount` when `payment type` is
  "credit-card", else `0.0`.

The commission is `(region_loading + payment_loading) * CATEGORY_MULTIPLIER[product category]`.

The subtotal is `receivable_after_discount + commission`. Tax withholding is
`0.03 * subtotal` when `tax verified` is "no" (or empty), and `0.0` when it is "yes".

`total_receivables = subtotal - withholding`.
