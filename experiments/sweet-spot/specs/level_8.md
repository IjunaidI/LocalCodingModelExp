<!-- LEVEL 8 — Tables kept + natural tier + True/False (both traps re-armed, tables kept).
     Branches from level 2 but uses BOTH the L4 natural volume-tier phrasing and the L5
     True/False boolean. This is "keep the lookup table, but use the L4 and L5 dialect."
     Tests whether the two traps together break the model while the tables are retained.
     Dataset: True/False. -->
# Pricing & commission calculation spec

`process_calculations(csv_path)` reads a CSV and returns one dict per row, each with the
key `total_receivables`.

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
- `tax verified` : True or False (an empty cell counts as False)

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

The subtotal is `receivable_after_discount + commission`. The `tax verified` column is
True or False: withhold `0.03 * subtotal` when the sale has not been tax-verified, and
`0.0` when it has been verified.

`total_receivables = subtotal - withholding`.
