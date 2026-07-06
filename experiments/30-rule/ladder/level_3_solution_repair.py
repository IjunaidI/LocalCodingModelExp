import csv

def process_calculations(csv_path):
    def calculate_rate(customer_status, product):
        if product == 1:
            return 1000 if customer_status == 'individual' else 900
        elif product == 2:
            return 1500 if customer_status == 'individual' else 1200
        elif product == 3:
            return 2000 if customer_status == 'individual' else 1700

    def calculate_discount(receivable_before_discount):
        spring_season = 0.05
        volume = 0.05 if receivable_before_discount < 100 else 0.10 if receivable_before_discount < 1000 else 0
        strategic_customer = 0.05
        loyalty = 0.15 if customer_years >= 5 else 0.10 if customer_years >= 2 else 0
        return spring_season + volume + strategic_customer + loyalty

    def calculate_loadings(receivable_after_discount):
        region_loading = 0.10
        payment_loading = 0.025 if payment_method == 'credit-card' else 0
        quarter_loading = 0.02 if quarter == 'Q1' else -0.01 if quarter == 'Q4' else 0
        zone_loading = 0.05 if zone == 'domestic' else 0.08 if zone == 'international' else 0.10 if zone == 'cross-border' else 0
        speed_loading = 0.15 if speed == 'same-day' else 0.10 if speed == 'next-day' else 0
        return region_loading + payment_loading + quarter_loading + zone_loading + speed_loading

    def calculate_adjusted_commission(base_commission_total, product_category):
        product_category_multiplier = 1.2 if product_category == 'electronics' else 0.8 if product_category == 'groceries' else 1.5 if product_category == 'luxury' else 1
        high_risk = 0.15 if high_risk_transaction else 1
        active_referral = 0.25 if active_referral and referral_invoices_remaining > 0 else 1
        return base_commission_total * product_category_multiplier * high_risk * active_referral

    def calculate_fees(pre_withholding_total):
        correction_fee = 5
        minimum_transaction_fee = 2.5 if pre_withholding_total < 50 else 0
        return pre_withholding_total + correction_fee + minimum_transaction_fee

    def calculate_withholding(pre_withholding_total):
        return 0.03 * pre_withholding_total if not tax_verified else 0

    def calculate_total_receivables(pre_withholding_total, withholding):
        return pre_withholding_total - withholding

    def calculate_escrow(receivable_before_discount):
        return 0.01 * receivable_before_discount

    results = []
    with open(csv_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            customer_status = row['customer status'].strip()
            product = int(row['product'])
            volume = int(row['volume'])
            customer_years = int(row['customer years'])
            payment_method = row['payment method'].strip()
            quarter = row['quarter'].strip()
            zone = row['zone'].strip()
            speed = row['speed'].strip()
            high_risk_transaction = row['high risk transaction'].strip() == 'yes'
            active_referral = row['active referral'].strip() == 'yes'
            referral_invoices_remaining = int(row['referral invoices remaining'])
            tax_verified = row['tax verified'].strip() == 'yes'

            receivable_before_discount = volume * calculate_rate(customer_status, product)
            discount = calculate_discount(receivable_before_discount)
            receivable_after_discount = receivable_before_discount * (1 - discount)
            loadings = calculate_loadings(receivable_after_discount)
            base_commission_total = receivable_after_discount * loadings
            adjusted_commission_total = calculate_adjusted_commission(base_commission_total, product_category)
            pre_withholding_total = calculate_fees(adjusted_commission_total)
            withholding = calculate_withholding(pre_withholding_total)
            total_receivables = calculate_total_receivables(pre_withholding_total, withholding)
            escrow = calculate_escrow(receivable_before_discount)

            results.append({
                'total_receivables': total_receivables,
                'escrow': escrow
            })

    return results
