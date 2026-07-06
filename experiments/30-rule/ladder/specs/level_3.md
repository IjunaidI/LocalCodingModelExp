# Pricing & commission specification (30 rules)

Implement `process_calculations(csv_path)`. It reads a CSV whose header names may carry
extra spaces and whose cells may be empty, and returns one dict per row containing at least
`total_receivables` and `escrow`. Boolean cells hold "yes"/"no" (empty means "no").

## The quantities

**Rate and base.** Each product has a unit rate that depends on customer status. Product 1
is 1000 for an individual and 900 for a corporate customer; product 2 is 1500 and 1200;
product 3 is 2000 and 1700. The receivable before discount is the volume times that rate.

**Discounts.** Four discounts add together and reduce the receivable before discount to the
receivable after discount. Spring season gives 0.05. Volume gives nothing below 100, 0.05
from 100 up, and 0.10 from 1000 up. A strategic customer gives 0.05. Loyalty is based on
seller years: 5 years or more is platinum and gives 0.15, 2 years or more is gold and gives
0.10, and fewer than 2 years earns nothing. The receivable after discount is the base times
one minus the sum of those four rates.

**Loadings.** Five loadings are each taken on the receivable after discount and summed into
the base commission total. Region loading is 0.10 of it for emea. Payment loading is 0.025
of it for a credit-card payment. Quarter loading is 0.02 of it in Q1 and minus 0.01 of it in
Q4, and nothing in Q2 or Q3. Zone loading is 0.05 for domestic, 0.08 for international, and
0.10 for cross-border, taken on the receivable after discount. Speed loading is 0.15 for
same-day, 0.10 for next-day, and 0 for standard, taken on the receivable after discount.

**Commission adjustments.** The adjusted commission total is the base commission total times
a product-category multiplier: 1.2 for electronics, 0.8 for groceries, and 1.5 for luxury. A
high-risk transaction then reduces the adjusted commission total by 1.5%. An active referral
(the referral is active and referral invoices remaining is above 0) then increases it by
0.25%.

**Fees, withholding, and the running total.** A correction fee of 5 applies when the invoice
requires correction. A minimum transaction fee of 2.50 applies when the receivable after
discount plus the adjusted commission total is below 50. The pre-withholding total is the
receivable after discount plus the adjusted commission total plus the correction fee plus
the minimum transaction fee. A seller without verified tax documentation (tax verified is
not "yes") has 3% withholding taken on that pre-withholding total. The total receivables
starts as the pre-withholding total minus the withholding.

**Final discounts.** Then each of the following reduces the total receivables by its
percentage when it qualifies (they compound multiplicatively, so order does not matter):
- ordering from a capital city (karachi, lahore, islamabad, peshawar, quetta): 10%;
- a senior citizen: 2%;
- a first order: 5%;
- a luxury product: 4%;
- a shipment over 20 kg: 3%;
- strategic loyalty accelerator, for a strategic customer with platinum loyalty, volume of
  at least 1000, and no correction fee: 7%;
- premium seasonal bundle, for spring season with a luxury product and same-day processing:
  6%;
- capital-city corporate incentive, for a corporate customer in a capital city paying by a
  method other than credit-card with verified tax documentation: 4%;
- global expansion, for an international transaction by a strategic, non-first-time customer
  with volume above 5000: 8%;
- elite seller performance, for platinum loyalty with an active referral, a non-high-risk
  transaction, and verified tax documentation: 5%.

**Escrow.** Escrow is 1% of the receivable before discount, reported separately and not part
of the total receivables.
