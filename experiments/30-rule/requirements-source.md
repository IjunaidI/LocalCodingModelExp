# Source requirement — the 30-rule pricing/commission spec (verbatim)

This is the original requirement as received, plus Fahad's raw input CSV
(`INPUT-fahad-updated.csv`). **Provenance only — never edit.** `reference_30.py` transcribes
the input rows from here; the prose below is the authority the reference implements.

> Note: the CSV mixes genuine input columns with pre-computed output/scratch columns Fahad
> filled in (`total Receivable`, `total receiveables after`, per-rule discount %, etc.).
> Those scratch columns are NOT authoritative (they contradict the prose in spots, e.g. a
> 5% luxury tax on a groceries row). The reference computes ground truth from the prose and
> uses Fahad's `total Receivable` column only as a cross-check.

## Prose requirement

Build a python program that has a function `process_calculations` that takes a csv path as
input. The csv field names can have extra spaces. It has the fields:

- customer = can be strategic or non-strategic
- productid = can be any product from the list below

      PRODUCT_RATES = {
          1: {"individual": 1000, "corporate": 900},
          2: {"individual": 1500, "corporate": 1200},
          3: {"individual": 2000, "corporate": 1700},
      }

- season = can be spring, summer, winter, autumn
- volume = will be an integer value
- region = can be EMEA or non-EMEA
- quarter = can be Q1, Q2, Q3, Q4
- payment type = can be ach/wire or credit-card
- transaction type = can be domestic, international, or cross-border
- product category = can be electronics, groceries, or luxury
- seller years = integer value
- processing speed = can be same-day, next-day, or standard
- tax verified = boolean value indicating whether seller tax documentation is verified
- is high risk = boolean indicating whether transaction is high-risk
- requires correction = boolean indicating whether invoice required manual adjustment or resubmission after processing
- discount = calculate using rule A
- volume discount = calculate using rule B
- category discount = calculate using rule C
- status = this is customer status which can be individual or corporate
- referral active = can be True, False - if referral credit is active
- referral invoices remaining = (integer counter) - referral invoices remaining
- city = can be karachi, lahore, islamabad, peshawar, or quetta
- senior citizen = boolean
- first order = boolean value indicating whether this is the customer's first order
- weight = numeric value representing total shipment weight in kg

- individual rate = calculate using rule D
- corporate rate = calculate using rule D
- receivable before discount = Volume * Individual or Corporate Rate
- total discounts = rule A, rule B, rule C, and rule I applied
- receivable after discount = Receivable before discount – Total discounts
- all loadings are calculated strictly on receivable after discount
- region loading = calculate using rule E
- payment method loading = calculate using rule F
- seasonal pricing tier loading = calculate using rule G
- geographic zone loading = calculate using rule H
- loyalty discount = calculate using rule I
- loyalty status = calculate using rule I
- product category multiplier = calculate using rule J
- processing speed premium = calculate using rule L
- minimum transaction fee = calculate using rule K
- escrow = calculate using rule M
- referral credit system = calculate using Rule N
- tax withholding rate = calculate using Rule O
- tax withholding amount = calculate using Rule O
- base commission total = sum of region loading, payment loading, seasonal pricing loading, geographic zone loading, processing speed loading
- risk management fee = calculate using Rule P
- correction fee = calculate using Rule Q
- adjusted commission total = base commission total * product category multiplier
- total receivables = Receivable-after-discount + adjusted commission total + correction fee - tax withholding amount
- capital city discount = calculate using Rule R
- senior citizen discount = calculated using Rule S
- first order discount = calculated using Rule T
- luxury tax amount = calculated using Rule U
- heavy weight fee = calculated using Rule V
- strategic loyalty accelerator discount = calculated using Rule X
- premium seasonal bundle discount = calculated using Rule Y
- capital city corporate incentive discount = calculated using Rule Z
- global expansion discount = calculated using Rule AA
- elite seller performance discount = calculated using Rule AB
- escrow amount is tracked separately and not included in total receivables
- comments

The values in the columns can be empty.

It then processes output based on below rules (output values can be float):

- Rule A: Spring season has a 5% discount
- Rule B: Volume under 100 has 0% discount, volume under 1000 has 5% discount, volume of 1000 and above have 10% discount
- Rule C: Strategic customer gets 5% discount
- Rule D: Each product or item has an individual rate and corporate rate
- Rule E: EMEA is charged 10% extra on the Receivable after discount
- Rule F: Credit card payments add 2.5% processing on the Receivable after discount
- Rule G: rates vary by quarter (Q1: +2%, Q4: -1% for holiday incentives)
- Rule H: Geographic zone pricing varies by transaction type: domestic = 5%, international = 8%, cross-border = 10%
- Rule I: Loyalty status benefits: Gold sellers (2+ years) get 10% discount; Platinum sellers (5+ years) get 15% discount
- Rule J: Product category multipliers: electronics = 1.2x, groceries = 0.8x, luxury = 1.5x
- Rule K: Minimum Transaction Fees — invoices under $50 incur flat $2.50 fee; applied on receivables after discount and adjusted commission total
- Rule L: Processing Speed Premium — same-day = +15%, next-day = +10%, standard = 0%
- Rule M: Escrow — 1% of gross invoice held for 30 days (tracked separately)
- Rule N: Referral Credit System — Sellers who refer new sellers get 0.25% commission credit; applied to adjusted commission total after all calculations and multipliers; only applies for next 10 invoices; a seller has an active referral credit
- Rule O: Tax Compliance Withholding — Sellers without verified tax documentation have additional 3% withholding; withholding is applied on total receivables after all calculations
- Rule P: High-Risk Transaction Adjustment — high-risk transactions incur an additional 1.5% fee; fee is subtracted from adjusted commission total after all commission calculations (including multipliers); fee affects commission only, not invoice receivables
- Rule Q: Invoice Correction Fee — any invoice requiring manual adjustment or resubmission after processing incurs a flat $5 administrative fee; applied after all commission calculations; included in total receivables before tax withholding is calculated
- Rule R: Capital City Discount — customers ordering from designated capital cities receive 10% discount; applicable cities: karachi, lahore, islamabad, peshawar, quetta; applied to total receivables
- Rule S: Senior Citizen Discount — if true → apply 2% discount; if false → no discount; applied on total receivables after Capital City Discount
- Rule T: New Customer Discount — customers placing their first order receive a 5% discount; applied after senior citizen discount
- Rule U: Luxury Tax — luxury product category incurs 4% tax; deducted on total receivables after Senior Citizen Discount
- Rule V: Heavy Weight Handling Fee — orders exceeding 20 kg incur additional handling charges; 3% of total receivables deducted; applied after luxury tax
- Rule X: Strategic Loyalty Accelerator Discount — apply 7% discount on total receivables; requires strategic customer, Platinum loyalty status, volume >= 1000, and no correction fee; applied after Heavy Weight Handling Fee
- Rule Y: Premium Seasonal Bundle Discount — apply 6% discount on total receivables; requires spring season, luxury category, and same-day processing; applied after Heavy Weight Handling Fee
- Rule Z: Capital City Corporate Incentive Discount — apply 4% discount on total receivables; requires corporate customer, approved capital city, non credit-card payment, and verified tax documentation; applied after Heavy Weight Handling Fee
- Rule AA: Global Expansion Discount — apply 8% discount on total receivables; requires international transaction, strategic customer, non first-time customer, and volume > 5000; applied after Heavy Weight Handling Fee
- Rule AB: Elite Seller Performance Discount — apply 5% discount on total receivables; requires Platinum loyalty status, active referral credit, non high-risk transaction, and verified tax documentation; applied after Heavy Weight Handling Fee

Output should be a list of dictionaries with all calculations, `total_receivables` and
`escrow`. The output keys should match exactly.

## Fahad's raw input CSV (`INPUT-fahad-updated.csv`)

```csv
customer name,productid,season,status,individual rate,corporate rate,volume,customer,seller years,region,payment type,quarter,transaction type,processing speed,product category,referral invoices remaining,referral active,is high risk,tax verified,requires correction,total Receivable,city,capital city discount,senoir citizen,senior citizen discount,first order,first order discount,luxury tax,weight,heavy weight fee,total receiveables after ,loyalty_status,Strategic Loyalty Accelerator,Premium Seasonal Bundle,Rule Z Discount %,Rule AA Discount %,Rule AB Discount %,Total New Discounts %
A,1,winter,INDIVIDUAL,1000,900,90,strategic,4,non-EMEA,credit-card,Q2,international,same-day,luxury,0,FALSE,FALSE,,FALSE,102588.4125,karachi,0.1,FALSE,0,0,0,0.04,1,0,88636.39,Gold,0,0,0,0,0,0
B,1,winter,INDIVIDUAL,1000,900,900,strategic,3,non-EMEA,credit-card,Q1,international,standard,groceries,0,FALSE,FALSE,,FALSE,768240,lahore,0.1,FALSE,0,0,0,0,1,0,691416.00,Gold,0,0,0,0,0,0
C,1,winter,INDIVIDUAL,1000,900,90,non-strategic,5,EMEA,credit-card,Q4,international,same-day,luxury,8,TRUE,TRUE,FALSE,TRUE,112129.4839,hyderabad,0,FALSE,0,0,0,0.04,1,0,107644.30,Platinum,0,0,0,0,0,0
D,1,spring,INDIVIDUAL,1000,900,90,non-strategic,0,EMEA,credit-card,Q3,domestic,next-day,electronics,0,FALSE,FALSE,,FALSE,110303.55,sukkur,0,FALSE,0,0,0,0,1,0,110303.55,None,0,0,0,0,0,0
E,1,summer,CORPORATE,1000,900,315,strategic,3,non-EMEA,credit-card,Q1,cross-border,standard,groceries,0,FALSE,FALSE,,FALSE,245515.536,ferozpur,0,FALSE,0,0,0,0,1,0,245515.54,Gold,0,0,0,0,0,0
F,2,summer,CORPORATE,1500,1200,1790,strategic,6,non-EMEA,ach/wire,Q2,cross-border,same-day,groceries,0,FALSE,FALSE,,FALSE,1750190.4,dera ghazi Khan,0,TRUE,0.02,1,0.05,0,22,0.03,1580544.44,Platinum,0.07,0,0,0,0,0.07
G,1,autumn,INDIVIDUAL,1000,900,747,non-strategic,4,non-EMEA,ach/wire,Q1,cross-border,next-day,electronics,0,FALSE,FALSE,,FALSE,778499.496,islamabad,0.1,FALSE,0,1,0.05,0,1,0,665617.07,Gold,0,0,0,0,0,0
H,2,summer,INDIVIDUAL,1500,1200,971,strategic,1,non-EMEA,ach/wire,Q3,domestic,same-day,electronics,0,FALSE,FALSE,,FALSE,1576690.38,faislabad,0,FALSE,0,0,0,0,1,0,1576690.38,None,0,0,0,0,0,0
I,1,winter,INDIVIDUAL,1000,900,1773,strategic,8,EMEA,ach/wire,Q1,international,same-day,electronics,0,FALSE,FALSE,,FALSE,1709491.14,rawalpindi,0,FALSE,0,0,0,0,25,0.03,1658206.41,Platinum,0.07,0,0,0,0,0.07
J,3,spring,INDIVIDUAL,2000,1700,1718,strategic,4,EMEA,credit-card,Q2,cross-border,same-day,luxury,0,FALSE,FALSE,,FALSE,3645381.25,rawalpindi,0,TRUE,0.02,0,0,0.04,1,0,3429574.68,Gold,0,0.06,0,0,0,0.06
K,2,autumn,CORPORATE,1500,1200,170,strategic,2,EMEA,ach/wire,Q1,domestic,standard,luxury,0,FALSE,FALSE,,FALSE,198671.52,peshawar,0.1,TRUE,0.02,1,0.05,0.04,32,0.03,155013.95,Gold,0,0,0,0,0,0
L,3,spring,INDIVIDUAL,2000,1700,86,non-strategic,10,EMEA,ach/wire,Q4,cross-border,next-day,groceries,0,FALSE,FALSE,,FALSE,164437.50400000002,faislabad,0,FALSE,0,0,0,0,1,0,164437.50400000002,Platinum,0,0,0,0,0,0
M,3,autumn,INDIVIDUAL,2000,1700,1826,strategic,8,non-EMEA,ach/wire,Q2,international,standard,groceries,0,FALSE,FALSE,,FALSE,2638409.312,faislabad,0,FALSE,0,0,0,0,1,0,2638409.31,Platinum,0.07,0,0,0,0,0.07
N,3,winter,INDIVIDUAL,2000,1700,850,non-strategic,3,non-EMEA,credit-card,Q4,domestic,standard,luxury,0,FALSE,FALSE,,FALSE,1538310.875,ferozpur,0,FALSE,0,0,0,0.04,1,0,1476778.44,Gold,0,0,0,0,0,0
O,3,spring,INDIVIDUAL,2000,1700,198,strategic,3,EMEA,credit-card,Q3,international,next-day,groceries,0,FALSE,FALSE,,FALSE,358383.96,nawabshah,0,TRUE,0.02,0,0,0,1,0,351216.28,Gold,0,0,0,0,0,0
P,3,spring,CORPORATE,2000,1700,1113,strategic,10,non-EMEA,credit-card,Q1,international,same-day,groceries,0,FALSE,FALSE,,FALSE,1455422.2410000002,sialkot,0,FALSE,0,0,0,0,1,0,1455422.2410000002,Platinum,0.07,0,0,0,0,0.07
Q,3,spring,CORPORATE,2000,1700,449,strategic,3,non-EMEA,ach/wire,Q1,international,standard,electronics,0,FALSE,FALSE,,FALSE,621936.84,karachi,0.1,FALSE,0,0,0,0,1,0,559743.16,Gold,0,0,0,0,0,0
R,2,winter,INDIVIDUAL,1500,1200,12,non-strategic,7,EMEA,credit-card,Q2,cross-border,standard,groceries,0,FALSE,FALSE,,FALSE,17512.38,quetta,0.1,FALSE,0,1,0.05,0,1,0,14973.08,Platinum,0,0,0,0,0,0
S,3,autumn,INDIVIDUAL,2000,1700,1020,strategic,0,non-EMEA,ach/wire,Q2,international,next-day,electronics,0,FALSE,FALSE,,FALSE,2045287.68,larkana,0,TRUE,0.02,0,0,0,1,0,2004381.93,None,0,0,0,0,0,0
```

### Column key (input vs Fahad's scratch outputs)

**Genuine inputs** (the reference reads these): `productid, status, customer, season,
volume, region, quarter, payment type, transaction type, product category, seller years,
processing speed, tax verified, is high risk, requires correction, referral active,
referral invoices remaining, city, senior citizen (`senoir citizen` in the raw header),
first order, weight`. (`customer name` is a row label.)

**Fahad's pre-computed scratch outputs** (advisory only, NOT authoritative): `individual
rate, corporate rate, total Receivable, capital city discount, senior citizen discount,
first order discount, luxury tax, heavy weight fee, total receiveables after, loyalty_status,
Strategic Loyalty Accelerator, Premium Seasonal Bundle, Rule Z/AA/AB Discount %, Total New
Discounts %`. Of these, `total Receivable` = the pre-cascade total and is used as the
reference's cross-check (verified exact on rows A/C/F).
