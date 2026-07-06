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
            productid = row['productid'].strip() if 'productid' in row else ''
            volume = float(row['volume'].strip()) if 'volume' in row and row['volume'].strip() else 0
            seller_years = int(row['seller years'].strip()) if 'seller years' in row and row['seller years'].strip() else 0
            referral_invoices_remaining = int(row['referral invoices remaining'].strip()) if 'referral invoices remaining' in row and row['referral invoices remaining'].strip() else 0
            weight = float(row['weight'].strip()) if 'weight' in row and row['weight'].strip() else 0
            status = row['status'].strip() if 'status' in row else ''
            quarter = row['quarter'].strip() if 'quarter' in row else ''
            requires_correction = row['requires correction'].strip() if 'requires correction' in row else ''
            referral_active = row['referral active'].strip() if 'referral active' in row else ''
            product_category = row['product category'].strip() if 'product category' in row else ''
            transaction_type = row['transaction type'].strip() if 'transaction type' in row else ''
            processing_speed = row['processing speed'].strip() if 'processing speed' in row else ''
            tax_verified = row['tax verified'].strip() if 'tax verified' in row else ''

            # Calculate rate
            rate = PRODUCT_RATES.get(productid, {}).get(status, 0)

            # Calculate receivable_before_discount
            receivable_before_discount = volume * rate if rate else 0

            # Calculate discounts
            spring_rate = 0.05 if quarter == 'spring' else 0
            volume_rate = 0.05 if volume >= 100 else 0
            strategic_rate = 0.05 if row.get('strategic', '').strip() == 'yes' else 0
            loyalty_rate = 0.15 if seller_years >= 5 else 0.10 if seller_years >= 2 else 0
            receivable_after_discount = receivable_before_discount * (1 - (spring_rate + volume_rate + strategic_rate + loyalty_rate))

            # Calculate loadings
            region_loading = 0.10 if transaction_type == 'emea' else 0
            payment_loading = 0.025 if row.get('payment type', '').strip() == 'credit-card' else 0
            quarter_loading = 0.02 if quarter == 'Q1' else -0.01 if quarter == 'Q4' else 0
            zone_loading = ZONE_LOADING.get(transaction_type, 0)
            speed_loading = SPEED_PREMIUM.get(processing_speed, 0)
            base_commission_total = receivable_after_discount * (region_loading + payment_loading + quarter_loading + zone_loading + speed_loading)

            # Calculate commission adjustments
            adjusted_commission_total = base_commission_total * CATEGORY_MULTIPLIER.get(product_category, 1)
            if row.get('high risk', '').strip() == 'yes':
                adjusted_commission_total *= 0.985
            if referral_active.strip() == 'yes' and referral_invoices_remaining > 0:
                adjusted_commission_total *= 1.0025

            # Calculate fees, withholding, and the running total
            correction_fee = 5.0 if row.get('requires correction', '').strip() == 'yes' else 0
            minimum_transaction_fee = 2.5 if receivable_after_discount + adjusted_commission_total < 50 else 0
            pre_withholding_total = receivable_after_discount + adjusted_commission_total + correction_fee + minimum_transaction_fee
            tax_withholding_amount = 0.03 * pre_withholding_total if tax_verified.strip() == 'yes' else 0
            total_receivables = pre_withholding_total - tax_withholding_amount

            # Calculate final discounts
            final_discounts = 1
            if productid in CAPITAL_CITIES:
                final_discounts *= 0.9
            if row.get('senior citizen', '').strip() == 'yes':
                final_discounts *= 0.98
            if row.get('first order', '').strip() == 'yes':
                final_discounts *= 0.95
            if product_category == 'luxury':
                final_discounts *= 0.96
            if weight > 20:
                final_discounts *= 0.97
            if row.get('strategic loyalty accelerator', '').strip() == 'yes' and row.get('strategic', '').strip() == 'yes' and row.get('platinum loyalty', '').strip() == 'yes' and volume >= 1000 and row.get('requires correction', '').strip() == 'no':
                final_discounts *= 0.93
            if row.get('premium seasonal bundle', '').strip() == 'yes' and quarter == 'spring' and product_category == 'luxury' and processing_speed == 'same-day':
                final_discounts *= 0.94
            if row.get('capital-city corporate incentive', '').strip() == 'yes' and row.get('corporate status', '').strip() == 'yes' and productid in CAPITAL_CITIES and row.get('payment type', '').strip() != 'credit-card' and tax_verified.strip() == 'yes':
                final_discounts *= 0.96
            if row.get('global expansion', '').strip() == 'yes' and row.get('strategic', '').strip() == 'yes' and not row.get('first order', '').strip() and volume > 5000:
                final_discounts *= 0.92
            if row.get('elite seller performance', '').strip() == 'yes' and row.get('platinum loyalty', '').strip() == 'yes' and referral_active.strip() == 'yes' and not row.get('high risk', '').strip() and tax_verified.strip() == 'yes':
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
