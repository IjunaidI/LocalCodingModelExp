<!-- LEVEL 2 — Declarative spec. Diff vs level 1: rules state WHAT to compute, not
     step-by-step pseudocode (no "Start x = 0.0", no "do NOT use elif", no "apply in
     this exact order"). Kept: constant Input-columns block, literal dicts, additive
     volume wording, yes/no boolean, bare decimals. Dataset: yes/no. -->
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
- a volume rate that is `0.05` for `volume >= 100` plus an additional `0.05` for
  `volume >= 1000` (the two thresholds are independent and stack, so `volume >= 1000`
  earns the full `0.10`);
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
