import csv

PRODUCT_RATES = {
    "1": {"individual": 1000, "corporate": 900},
    "2": {"individual": 1500, "corporate": 1200},
    "3": {"individual": 2000, "corporate": 1700},
}
CATEGORY_MULTIPLIER = {"electronics": 1.2, "groceries": 0.8, "luxury": 1.5}
ZONE_LOADING = {"domestic": 0.05, "international": 0.08, "cross-border": 0.10}
SPEED_PREMIUM = {"same-day": 0.15, "next-day": 0.10, "standard": 0.0}
CAPITAL_CITIES = {"karachi", "lahore", "islamabad", "peshawar", "quetta"}

def process_calculations(csv_path):
    results = []
    with open(csv_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Process each row
            productid = row['productid'].strip()
            volume = float(row['volume']) if row['volume'] else 0
            seller_years = int(row['seller years']) if row['seller years'] else 0
            referral_invoices_remaining = int(row['referral invoices remaining']) if row['referral invoices remaining'] else 0
            weight = float(row['weight']) if row['weight'] else 0
            status = row['status'].strip()
            quarter = row['quarter'].strip()
            requires_correction = row['requires correction'].strip()
            referral_active = row['referral active'].strip()
            product_category = row['product category'].strip()
            transaction_type = row['transaction type'].strip()
            processing_speed = row['processing speed'].strip()
            tax_verified = row['tax verified'].strip()

            # Calculate rate
            rate = PRODUCT_RATES[productid][status]

            # Calculate receivable_before_discount
            receivable_before_discount = volume * rate

            # Calculate discounts
            spring_rate = 0.05 if quarter == 'spring' else 0
            volume_rate = 0.05 if volume >= 100 else 0
            strategic_rate = 0.05 if row['strategic'] == 'yes' else 0
            loyalty_rate = 0.15 if seller_years >= 5 else 0.10 if seller_years >= 2 else 0
            receivable_after_discount = receivable_before_discount * (1 - (spring_rate + volume_rate + strategic_rate + loyalty_rate))

            # Calculate loadings
            region_loading = 0.10 if transaction_type == 'emea' else 0
            payment_loading = 0.025 if row['payment type'] == 'credit-card' else 0
            quarter_loading = 0.02 if quarter == 'Q1' else -0.01 if quarter == 'Q4' else 0
            zone_loading = ZONE_LOADING[transaction_type]
            speed_loading = SPEED_PREMIUM[processing_speed]
            base_commission_total = receivable_after_discount * (region_loading + payment_loading + quarter_loading + zone_loading + speed_loading)

            # Calculate commission adjustments
            adjusted_commission_total = base_commission_total * CATEGORY_MULTIPLIER[product_category]
            if row['high risk'] == 'yes':
                adjusted_commission_total *= 0.985
            if referral_active == 'yes' and referral_invoices_remaining > 0:
                adjusted_commission_total *= 1.0025

            # Calculate fees, withholding, and running total
            correction_fee = 5.0 if row['requires correction'] == 'yes' else 0
            minimum_transaction_fee = 2.5 if receivable_after_discount + adjusted_commission_total < 50 else 0
            pre_withholding_total = receivable_after_discount + adjusted_commission_total + correction_fee + minimum_transaction_fee
            tax_withholding_amount = 0.03 * pre_withholding_total if tax_verified == 'yes' else 0
            total_receivables = pre_withholding_total - tax_withholding_amount

            # Calculate final discounts
            final_discounts = 1
            if productid in CAPITAL_CITIES:
                final_discounts *= 0.9
            if row['senior citizen'] == 'yes':
                final_discounts *= 0.98
            if row['first order'] == 'yes':
                final_discounts *= 0.95
            if product_category == 'luxury':
                final_discounts *= 0.96
            if weight > 20:
                final_discounts *= 0.97
            if row['strategic loyalty accelerator'] == 'yes' and row['strategic'] == 'yes' and row['platinum loyalty'] == 'yes' and volume >= 1000 and row['requires correction'] == 'no':
                final_discounts *= 0.93
            if row['premium seasonal bundle'] == 'yes' and quarter == 'spring' and product_category == 'luxury' and processing_speed == 'same-day':
                final_discounts *= 0.94
            if row['capital-city corporate incentive'] == 'yes' and row['corporate status'] == 'yes' and productid in CAPITAL_CITIES and row['payment type'] != 'credit-card' and tax_verified == 'yes':
                final_discounts *= 0.96
            if row['global expansion'] == 'yes' and row['strategic'] == 'yes' and not row['first order'] and volume > 5000:
                final_discounts *= 0.92
            if row['elite seller performance'] == 'yes' and row['platinum loyalty'] == 'yes' and referral_active == 'yes' and not row['high risk'] and tax_verified == 'yes':
                final_discounts *= 0.95

            # Calculate escrow
            escrow = 0.01 * receivable_before_discount

            # Create result dictionary
            result = {
                'total_receivables': total_receivables * final_discounts,
                'escrow': escrow
            }
            results.append(result)

    return results
