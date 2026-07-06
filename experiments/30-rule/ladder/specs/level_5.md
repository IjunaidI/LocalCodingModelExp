# Requirement

Build a python program that has a function `process_calculations` that takes a csv path as
input. The csv field names can have extra spaces. It has the fields: customer
(strategic/non-strategic), productid (1, 2, or 3), season, volume (integer), region
(EMEA/non-EMEA), quarter (Q1–Q4), payment type (ach/wire or credit-card), transaction type
(domestic/international/cross-border), product category (electronics/groceries/luxury),
seller years (integer), processing speed (same-day/next-day/standard), tax verified
(boolean True/False), is high risk (boolean), requires correction (boolean), status
(individual/corporate), referral active (True/False), referral invoices remaining (integer),
city, senior citizen (boolean), first order (boolean), weight (kg). Values can be empty.

The product rates (rule D) are:
```
PRODUCT_RATES = {
    1: {"individual": 1000, "corporate": 900},
    2: {"individual": 1500, "corporate": 1200},
    3: {"individual": 2000, "corporate": 1700},
}
```
- receivable before discount = volume * individual-or-corporate rate
- total discounts = rule A, rule B, rule C, and rule I applied
- receivable after discount = receivable before discount − total discounts
- all loadings are calculated strictly on receivable after discount
- base commission total = sum of region loading (E), payment loading (F), seasonal/quarter
  loading (G), geographic zone loading (H), processing speed loading (L)
- adjusted commission total = base commission total * product category multiplier (J)
- total receivables = receivable after discount + adjusted commission total + correction fee
  − tax withholding amount
- escrow is tracked separately and not included in total receivables

Rules:
- Rule A: Spring season has a 5% discount.
- Rule B: Volume under 100 has 0% discount, volume under 1000 has 5% discount, volume of
  1000 and above have 10% discount.
- Rule C: Strategic customer gets 5% discount.
- Rule D: Each product has an individual rate and corporate rate (above).
- Rule E: EMEA is charged 10% extra on the receivable after discount.
- Rule F: Credit-card payments add 2.5% processing on the receivable after discount.
- Rule G: rates vary by quarter (Q1: +2%, Q4: −1%).
- Rule H: Geographic zone pricing by transaction type: domestic 5%, international 8%,
  cross-border 10%.
- Rule I: Loyalty status: Gold sellers (2+ years) get 10% discount; Platinum sellers (5+
  years) get 15% discount.
- Rule J: Product category multipliers: electronics 1.2x, groceries 0.8x, luxury 1.5x.
- Rule K: Invoices under $50 incur a flat $2.50 fee, applied on receivable after discount
  and adjusted commission total.
- Rule L: Processing speed premium: same-day +15%, next-day +10%, standard 0%.
- Rule M: Escrow — 1% of gross invoice held for 30 days (tracked separately).
- Rule N: Sellers with an active referral credit get a 0.25% commission credit applied to
  the adjusted commission total (only for the next 10 invoices).
- Rule O: Sellers without verified tax documentation have an additional 3% withholding
  applied on total receivables after all calculations.
- Rule P: High-risk transactions incur an additional 1.5% fee subtracted from the adjusted
  commission total (commission only, not receivables).
- Rule Q: Any invoice requiring manual correction incurs a flat $5 administrative fee,
  included in total receivables before tax withholding.
- Rule R: Customers ordering from capital cities (karachi, lahore, islamabad, peshawar,
  quetta) receive a 10% discount on total receivables.
- Rule S: Senior citizens get a 2% discount, applied on total receivables after the capital
  city discount.
- Rule T: First orders receive a 5% discount, applied after the senior citizen discount.
- Rule U: Luxury products incur a 4% tax on total receivables after the senior citizen
  discount.
- Rule V: Orders over 20 kg incur a 3% handling fee, applied after the luxury tax.
- Rule X: 7% discount on total receivables for a strategic customer with Platinum loyalty,
  volume ≥ 1000, and no correction fee; applied after the heavy weight fee.
- Rule Y: 6% discount for spring season, luxury category, and same-day processing; applied
  after the heavy weight fee.
- Rule Z: 4% discount for a corporate customer, an approved capital city, non credit-card
  payment, and verified tax documentation; applied after the heavy weight fee.
- Rule AA: 8% discount for an international transaction, strategic customer, non first-time
  customer, and volume > 5000; applied after the heavy weight fee.
- Rule AB: 5% discount for Platinum loyalty, active referral credit, non high-risk
  transaction, and verified tax documentation; applied after the heavy weight fee.

Output a list of dictionaries with `total_receivables` and `escrow`; keys must match exactly.
