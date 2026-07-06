# Pricing & commission spec — 30 rules (small-model dialect)

Build `process_calculations(csv_path)`. It reads a CSV (header names may have extra
spaces; cells may be empty) and returns a list of dicts, one per row. Each dict must
contain the keys `total_receivables` and `escrow`.

General rules for reading the CSV:
- Strip surrounding spaces from every header name and every cell value.
- Treat an empty cell as its stated default.
- Convert `volume`, `seller years`, `referral invoices remaining`, and `weight` to numbers.
  Keep `productid` as text ("1", "2", "3") — it is used directly as a `PRODUCT_RATES` key.
- Compare text fields case-insensitively (lower-case them), EXCEPT `quarter`, which is
  upper-case in the data (Q1–Q4) — use it exactly as written.
- Every boolean cell is the text "yes" or "no"; an empty cell counts as "no". Compare the
  literal text (e.g. `== "yes"`); do NOT convert cells to Python `True`/`False`.
- If a value is not found in a lookup table, use `0` for its rate (do not raise an error).

## Input columns
- `productid` : the text "1", "2", or "3"
- `status` : "individual" or "corporate"
- `customer` : "strategic" or "non-strategic"
- `season` : "spring", "summer", "winter", or "autumn"
- `volume` : an integer
- `region` : "emea" or "non-emea"
- `quarter` : "q1", "q2", "q3", or "q4"
- `payment type` : "ach/wire" or "credit-card"
- `transaction type` : "domestic", "international", or "cross-border"
- `product category` : "electronics", "groceries", or "luxury"
- `seller years` : an integer
- `processing speed` : "same-day", "next-day", or "standard"
- `tax verified` : "yes" or "no" (empty counts as "no")
- `is high risk` : "yes" or "no"
- `requires correction` : "yes" or "no"
- `referral active` : "yes" or "no"
- `referral invoices remaining` : an integer
- `city` : a city name
- `senior citizen` : "yes" or "no"
- `first order` : "yes" or "no"
- `weight` : a number (kilograms)

## Lookup tables (copy these exactly)
```
PRODUCT_RATES = {          # keys are the text "1"/"2"/"3", matching the productid cell
    "1": {"individual": 1000, "corporate": 900},
    "2": {"individual": 1500, "corporate": 1200},
    "3": {"individual": 2000, "corporate": 1700},
}

CATEGORY_MULTIPLIER = {
    "electronics": 1.2,
    "groceries": 0.8,
    "luxury": 1.5,
}

ZONE_LOADING = {          # by transaction type
    "domestic": 0.05,
    "international": 0.08,
    "cross-border": 0.10,
}

SPEED_PREMIUM = {         # by processing speed
    "same-day": 0.15,
    "next-day": 0.10,
    "standard": 0.0,
}

CAPITAL_CITIES = {"karachi", "lahore", "islamabad", "peshawar", "quetta"}
```

## The rules (apply in this exact order)

1. **Rate.** `rate = PRODUCT_RATES[productid][status]` (use `productid` as the text "1"/"2"/"3").

2. **Base.** `receivable_before_discount = volume * rate`.

3. **Spring discount rate.** Start `spring_rate = 0.0`. If `season` is "spring", set `spring_rate = 0.05`.

4. **Volume discount rate.** Build it up with two independent checks (do NOT use elif):
   Start `volume_rate = 0.0`.
   If `volume >= 100`, add `0.05` to `volume_rate`.
   If `volume >= 1000`, add another `0.05` to `volume_rate`.

5. **Strategic discount rate.** Start `strategic_rate = 0.0`. If `customer` is "strategic", set `strategic_rate = 0.05`.

6. **Loyalty status and discount rate.** From `seller years`:
   If `seller years >= 5`, set `loyalty_status = "platinum"` and `loyalty_rate = 0.15`.
   Else if `seller years >= 2`, set `loyalty_status = "gold"` and `loyalty_rate = 0.10`.
   Else set `loyalty_status = "none"` and `loyalty_rate = 0.0`.
   (Remember `loyalty_status`; rules 24 and 29 use it.)

7. **Apply discounts.**
   `total_discount_rate = spring_rate + volume_rate + strategic_rate + loyalty_rate`.
   `receivable_after_discount = receivable_before_discount * (1 - total_discount_rate)`.

8. **Region loading.** Start `region_loading = 0.0`. If `region` is "emea", set `region_loading = 0.10 * receivable_after_discount`.

9. **Payment loading.** Start `payment_loading = 0.0`. If `payment type` is "credit-card", set `payment_loading = 0.025 * receivable_after_discount`.

10. **Quarter loading.** Build the rate with independent checks (do NOT use elif):
    Start `quarter_rate = 0.0`.
    If `quarter` is "Q1", set `quarter_rate = 0.02`.
    If `quarter` is "Q4", set `quarter_rate = -0.01`.
    (Q2 and Q3 leave it at 0.0. `quarter` is upper-case like "Q2".)
    `quarter_loading = quarter_rate * receivable_after_discount`.

11. **Zone loading.** `zone_loading = ZONE_LOADING[transaction type] * receivable_after_discount`.

12. **Speed loading.** `speed_loading = SPEED_PREMIUM[processing speed] * receivable_after_discount`.

13. **Base commission total.** `base_commission_total = region_loading + payment_loading + quarter_loading + zone_loading + speed_loading`.

14. **Category multiplier.** `multiplier = CATEGORY_MULTIPLIER[product category]`. `adjusted_commission_total = base_commission_total * multiplier`.

15. **High-risk fee.** If `is high risk` is "yes", set `adjusted_commission_total = adjusted_commission_total * (1 - 0.015)`.

16. **Referral credit.** If `referral active` is "yes" AND `referral invoices remaining > 0`, set `adjusted_commission_total = adjusted_commission_total * (1 + 0.0025)`.

17. **Correction fee.** Start `correction_fee = 0.0`. If `requires correction` is "yes", set `correction_fee = 5.0`.

18. **Minimum transaction fee.** Start `minimum_transaction_fee = 0.0`. If `(receivable_after_discount + adjusted_commission_total) < 50`, set `minimum_transaction_fee = 2.50`.

19. **Tax withholding.**
    `pre_withholding_total = receivable_after_discount + adjusted_commission_total + correction_fee + minimum_transaction_fee`.
    Start `tax_withholding_amount = 0.0`.
    If `tax verified` is "no" (or the cell was empty), set `tax_withholding_amount = 0.03 * pre_withholding_total`.
    If `tax verified` is "yes", leave `tax_withholding_amount = 0.0`.

20. **Total (before the final discounts).** `total_receivables = pre_withholding_total - tax_withholding_amount`.

21. **Final discounts (rules 21–30).** Apply each one that qualifies by MULTIPLYING `total_receivables`. Because every step is a multiply, their order does not matter.

22. **Capital city.** If `city` is in `CAPITAL_CITIES`, set `total_receivables = total_receivables * (1 - 0.10)`.

23. **Senior citizen.** If `senior citizen` is "yes", set `total_receivables = total_receivables * (1 - 0.02)`.

24. **First order.** If `first order` is "yes", set `total_receivables = total_receivables * (1 - 0.05)`.

25. **Luxury tax.** If `product category` is "luxury", set `total_receivables = total_receivables * (1 - 0.04)`.

26. **Heavy weight.** If `weight > 20`, set `total_receivables = total_receivables * (1 - 0.03)`.

27. **Strategic loyalty accelerator.** If `customer` is "strategic" AND `loyalty_status` is "platinum" AND `volume >= 1000` AND `correction_fee == 0.0`, set `total_receivables = total_receivables * (1 - 0.07)`.

28. **Premium seasonal bundle.** If `season` is "spring" AND `product category` is "luxury" AND `processing speed` is "same-day", set `total_receivables = total_receivables * (1 - 0.06)`.

29. **Capital city corporate incentive.** If `status` is "corporate" AND `city` is in `CAPITAL_CITIES` AND `payment type` is not "credit-card" AND `tax verified` is "yes", set `total_receivables = total_receivables * (1 - 0.04)`.

30. **Global expansion.** If `transaction type` is "international" AND `customer` is "strategic" AND `first order` is not "yes" AND `volume > 5000`, set `total_receivables = total_receivables * (1 - 0.08)`.

31. **Elite seller performance.** If `loyalty_status` is "platinum" AND `referral active` is "yes" AND `is high risk` is not "yes" AND `tax verified` is "yes", set `total_receivables = total_receivables * (1 - 0.05)`.

32. **Escrow.** `escrow = 0.01 * receivable_before_discount`. (Escrow is reported separately and is NOT part of `total_receivables`.)

Output: a list of dicts, one per input row, each containing at least the keys
`total_receivables` and `escrow`.
