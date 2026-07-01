# Simplified pricing spec — 10 rules (small-model dialect)

Build `process_calculations(csv_path)`. It reads a CSV (header names may have extra
spaces; cells may be empty) and returns a list of dicts, one per row, each containing
the key `total_receivables`.

General rules for reading the CSV:
- Strip surrounding spaces from every header name and every cell value.
- Treat an empty cell as its stated default.
- Convert `volume` and `productid` to numbers.
- Compare all text fields in lower case.

## Input columns
- `productid` : the text "1", "2", or "3"
- `status` : the text "individual" or "corporate"
- `volume` : an integer
- `season` : the text "spring", "summer", "winter", or "autumn"
- `customer` : the text "strategic" or "non-strategic"
- `region` : the text "emea" or "non-emea"
- `payment type` : the text "ach/wire" or "credit-card"
- `transaction type` : the text "domestic", "international", or "cross-border"
- `product category` : the text "electronics", "groceries", or "luxury"
- `tax verified` : the text "yes" or "no" (an empty cell counts as "no")

## Lookup tables (copy these exactly)
```
PRODUCT_RATES = {
    1: {"individual": 1000, "corporate": 900},
    2: {"individual": 1500, "corporate": 1200},
    3: {"individual": 2000, "corporate": 1700},
}

CATEGORY_MULTIPLIER = {
    "electronics": 1.2,
    "groceries": 0.8,
    "luxury": 1.5,
}
```

## The 10 rules (apply in this exact order)

1. **Rate.** Look up `rate = PRODUCT_RATES[productid][status]`.

2. **Base.** `receivable_before_discount = volume * rate`.

3. **Spring discount rate.**
   Start `spring_rate = 0.0`.
   If `season` is "spring", set `spring_rate = 0.05`.

4. **Volume discount rate.** Build it up with two independent checks (do NOT use elif):
   Start `volume_rate = 0.0`.
   If `volume >= 100`, add `0.05` to `volume_rate`.
   If `volume >= 1000`, add another `0.05` to `volume_rate`.
   (So volume under 100 gives 0.0, 100–999 gives 0.05, 1000 or more gives 0.10.)

5. **Strategic discount rate.**
   Start `strategic_rate = 0.0`.
   If `customer` is "strategic", set `strategic_rate = 0.05`.

6. **Apply discounts.**
   `total_discount_rate = spring_rate + volume_rate + strategic_rate`.
   `receivable_after_discount = receivable_before_discount * (1 - total_discount_rate)`.

7. **Region loading.**
   Start `region_loading = 0.0`.
   If `region` is "emea", set `region_loading = 0.10 * receivable_after_discount`.

8. **Payment loading.**
   Start `payment_loading = 0.0`.
   If `payment type` is "credit-card", set `payment_loading = 0.025 * receivable_after_discount`.

9. **Commission.**
   Look up `multiplier = CATEGORY_MULTIPLIER[product category]`.
   `commission = (region_loading + payment_loading) * multiplier`.

10. **Tax withholding and total.**
    `subtotal = receivable_after_discount + commission`.
    Start `withholding = 0.0`.
    If `tax verified` is "no" (or the cell was empty), set `withholding = 0.03 * subtotal`.
    If `tax verified` is "yes", leave `withholding = 0.0`.
    `total_receivables = subtotal - withholding`.

Output: a list of dicts, one per input row, each with the key `total_receivables`.
