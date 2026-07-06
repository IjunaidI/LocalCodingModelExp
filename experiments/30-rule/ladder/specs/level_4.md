# Pricing & commission rules

Write `process_calculations(csv_path)` that reads the CSV (headers may have extra spaces,
cells may be empty) and returns one dict per row with `total_receivables` and `escrow`.
Boolean columns read "yes" or "no".

The receivable before discount is the volume times the product's rate. Product 1 costs 1000
for individuals and 900 for corporates, product 2 costs 1500 and 1200, and product 3 costs
2000 and 1700.

Apply these discounts to get the receivable after discount:
- Spring season has a 5% discount.
- Volume under 100 has no discount, volume under 1000 has a 5% discount, and volume of 1000
  and above has a 10% discount.
- Strategic customers get a 5% discount.
- Loyalty: sellers with 2 or more years are Gold and get 10%; sellers with 5 or more years
  are Platinum and get 15%.

All loadings are charged on the receivable after discount:
- EMEA is charged 10% extra.
- Credit-card payments add 2.5%.
- Quarter rates vary: Q1 adds 2%, Q4 removes 1%.
- Geographic zone by transaction type: domestic 5%, international 8%, cross-border 10%.
- Processing speed premium: same-day 15%, next-day 10%, standard 0%.

The base commission total is the sum of those five loadings. Multiply it by the product
category multiplier (electronics 1.2x, groceries 0.8x, luxury 1.5x) to get the adjusted
commission total. High-risk transactions then take an extra 1.5% fee off the adjusted
commission total. A seller with an active referral credit and referral invoices remaining
gets a 0.25% commission credit added to the adjusted commission total.

Invoices requiring correction incur a flat $5 fee, and invoices under $50 (counting the
receivable after discount plus the adjusted commission total) incur a flat $2.50 fee; both
are included before withholding. The total receivables is the receivable after discount plus
the adjusted commission total plus the correction fee, and sellers without verified tax
documentation have an additional 3% withholding taken from it.

Then apply these discounts to the total receivables (each on the running total):
- Capital cities (karachi, lahore, islamabad, peshawar, quetta) get 10% off.
- Senior citizens get 2% off.
- First orders get 5% off.
- Luxury products are taxed 4%.
- Shipments over 20 kg have a 3% handling fee.
- A strategic customer with Platinum loyalty, volume of at least 1000, and no correction fee
  gets a 7% discount.
- Spring + luxury + same-day gets a 6% discount.
- A corporate customer in a capital city paying by a non-credit-card method with verified tax
  gets a 4% discount.
- An international, strategic, non-first-time customer with volume over 5000 gets 8% off.
- A Platinum seller with an active referral, no high risk, and verified tax gets 5% off.

Escrow is 1% of the gross invoice (the receivable before discount), tracked separately and
not part of the total receivables.
