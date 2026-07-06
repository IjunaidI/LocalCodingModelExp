# Pricing & commission specification (30 rules)

Implement `process_calculations(csv_path)`. It reads a CSV whose header names may carry
extra spaces and whose cells may be empty, and returns one dict per row containing at least
`total_receivables` and `escrow`. Read numeric fields (`volume`, `seller years`, `referral
invoices remaining`, `weight`) as numbers; keep `productid` as the text "1"/"2"/"3"; treat
text case-insensitively except `quarter`, which stays upper-case (Q1–Q4). Boolean cells hold
the text "yes"/"no" (empty means "no"); compare them as text, and if a value is missing from
a lookup table use a rate of 0.

## Reference tables
```
PRODUCT_RATES = {
    "1": {"individual": 1000, "corporate": 900},
    "2": {"individual": 1500, "corporate": 1200},
    "3": {"individual": 2000, "corporate": 1700},
}
CATEGORY_MULTIPLIER = {"electronics": 1.2, "groceries": 0.8, "luxury": 1.5}
ZONE_LOADING = {"domestic": 0.05, "international": 0.08, "cross-border": 0.10}
SPEED_PREMIUM = {"same-day": 0.15, "next-day": 0.10, "standard": 0.0}
CAPITAL_CITIES = {"karachi", "lahore", "islamabad", "peshawar", "quetta"}
```

## The quantities

**Rate and base.** The `rate` is `PRODUCT_RATES[productid][status]`. The
`receivable_before_discount` is `volume * rate`.

**Discounts.** Four discount rates add together. The spring rate is 0.05 when the season is
spring, else 0. The volume rate is 0.05 once volume reaches 100 and another 0.05 once it
reaches 1000 (so 0.0 / 0.05 / 0.10 across the three bands). The strategic rate is 0.05 for a
strategic customer. Loyalty depends on `seller years`: 5 or more years is "platinum" with a
0.15 rate, 2 or more is "gold" with 0.10, otherwise "none" with 0. The
`receivable_after_discount` is `receivable_before_discount * (1 - (spring + volume +
strategic + loyalty))`.

**Loadings.** Five loadings are each computed on `receivable_after_discount` and summed into
`base_commission_total`: region loading is 0.10 of it when the region is emea; payment
loading is 0.025 of it for a credit-card payment; quarter loading is +0.02 of it in Q1 and
-0.01 of it in Q4 (0 otherwise); zone loading is `ZONE_LOADING[transaction type]` of it; and
speed loading is `SPEED_PREMIUM[processing speed]` of it.

**Commission adjustments.** The `adjusted_commission_total` is `base_commission_total *
CATEGORY_MULTIPLIER[product category]`. A high-risk transaction then reduces it by 1.5%
(multiply by `1 - 0.015`). An active referral (`referral active` is "yes" and `referral
invoices remaining` is above 0) then increases it by 0.25% (multiply by `1 + 0.0025`).

**Fees, withholding, and the running total.** The `correction_fee` is 5.0 when `requires
correction` is "yes", else 0. A `minimum_transaction_fee` of 2.50 applies when
`receivable_after_discount + adjusted_commission_total` is below 50, else 0. The
`pre_withholding_total` is `receivable_after_discount + adjusted_commission_total +
correction_fee + minimum_transaction_fee`. When `tax verified` is not "yes" (i.e. "no" or
empty), `tax_withholding_amount` is 0.03 of that pre-withholding total, otherwise 0. The
`total_receivables` starts as `pre_withholding_total - tax_withholding_amount`.

**Final discounts.** Then the following each MULTIPLY `total_receivables` when they qualify
(order does not matter, since each is a multiply):
- capital city (city in `CAPITAL_CITIES`): factor `1 - 0.10`;
- senior citizen ("yes"): `1 - 0.02`;
- first order ("yes"): `1 - 0.05`;
- luxury tax (category is luxury): `1 - 0.04`;
- heavy weight (`weight > 20`): `1 - 0.03`;
- strategic loyalty accelerator (strategic customer AND platinum loyalty AND `volume >= 1000`
  AND no correction fee): `1 - 0.07`;
- premium seasonal bundle (spring AND luxury AND same-day): `1 - 0.06`;
- capital-city corporate incentive (corporate status AND capital city AND payment not
  credit-card AND tax verified is "yes"): `1 - 0.04`;
- global expansion (international transaction AND strategic AND not a first order AND
  `volume > 5000`): `1 - 0.08`;
- elite seller performance (platinum loyalty AND referral active is "yes" AND not high risk
  AND tax verified is "yes"): `1 - 0.05`.

**Escrow.** `escrow` is `0.01 * receivable_before_discount`, reported separately and not part
of `total_receivables`.
