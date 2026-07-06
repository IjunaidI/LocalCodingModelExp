import csv

def process_calculations(csv_path):
    PRODUCT_RATES = {
        "1": {"individual": 1000, "corporate": 900},
        "2": {"individual": 1500, "corporate": 1200},
        "3": {"individual": 2000, "corporate": 1700},
    }
    CATEGORY_MULTIPLIER = {
        "electronics": 1.2,
        "groceries": 0.8,
        "luxury": 1.5,
    }
    ZONE_LOADING = {
        "domestic": 0.05,
        "international": 0.08,
        "cross-border": 0.10,
    }
    SPEED_PREMIUM = {
        "same-day": 0.15,
        "next-day": 0.10,
        "standard": 0.0,
    }
    CAPITAL_CITIES = {"karachi", "lahore", "islamabad", "peshawar", "quetta"}

    def process_row(row):
        productid = row['productid'].strip()
        status = row['status'].strip().lower()
        customer = row['customer'].strip().lower()
        season = row['season'].strip().lower()
        volume = int(row['volume']) if row['volume'] else 0
        region = row['region'].strip().lower()
        quarter = row['quarter'].strip().upper()
        payment_type = row['payment type'].strip().lower()
        transaction_type = row['transaction type'].strip().lower()
        product_category = row['product category'].strip().lower()
        seller_years = int(row['seller years']) if row['seller years'] else 0
        processing_speed = row['processing speed'].strip().lower()
        tax_verified = row['tax verified'].strip().lower() if row['tax verified'] else 'no'
        is_high_risk = row['is high risk'].strip().lower() if row['is high risk'] else 'no'
        requires_correction = row['requires correction'].strip().lower() if row['requires correction'] else 'no'
        referral_active = row['referral active'].strip().lower() if row['referral active'] else 'no'
        referral_invoices_remaining = int(row['referral invoices remaining']) if row['referral invoices remaining'] else 0
        city = row['city'].strip() if row['city'] else ''
        senior_citizen = row['senior citizen'].strip().lower() if row['senior citizen'] else 'no'
        first_order = row['first order'].strip().lower() if row['first order'] else 'no'
        weight = float(row['weight']) if row['weight'] else 0.0

        # Calculate rate
        rate = PRODUCT_RATES[productid][status]

        # Base receivable
        receivable_before_discount = volume * rate

        # Spring discount
        spring_rate = 0.05 if season == "spring" else 0.0

        # Volume discount
        volume_rate = 0.05 if volume >= 100 else 0.0
        volume_rate += 0.05 if volume >= 1000 else 0.0

        # Strategic discount
        strategic_rate = 0.05 if customer == "strategic" else 0.0

        # Loyalty status
        loyalty_status = "none"
        loyalty_rate = 0.0
        if seller_years >= 5:
            loyalty_status = "platinum"
            loyalty_rate = 0.15
        elif seller_years >= 2:
            loyalty_status = "gold"
            loyalty_rate = 0.10

        # Total discount rate
        total_discount_rate = spring_rate + volume_rate + strategic_rate + loyalty_rate

        # Receivable after discount
        receivable_after_discount = receivable_before_discount * (1 - total_discount_rate)

        # Region loading
        region_loading = 0.10 * receivable_after_discount if region == "emea" else 0.0

        # Payment loading
        payment_loading = 0.025 * receivable_after_discount if payment_type == "credit-card" else 0.0

        # Quarter loading
        quarter_rate = 0.02 if quarter == "Q1" else 0.0
        quarter_rate -= 0.01 if quarter == "Q4" else 0.0
        quarter_loading = quarter_rate * receivable_after_discount

        # Zone loading
        zone_loading = ZONE_LOADING[transaction_type] * receivable_after_discount

        # Speed loading
        speed_loading = SPEED_PREMIUM[processing_speed] * receivable_after_discount

        # Base commission total
        base_commission_total = region_loading + payment_loading + quarter_loading + zone_loading + speed_loading

        # Category multiplier
        multiplier = CATEGORY_MULTIPLIER[product_category]
        adjusted_commission_total = base_commission_total * multiplier

        # High-risk fee
        if is_high_risk == "yes":
            adjusted_commission_total *= 0.985

        # Referral credit
        if referral_active == "yes" and referral_invoices_remaining > 0:
            adjusted_commission_total *= 1.0025

        # Correction fee
        correction_fee = 5.0 if requires_correction == "yes" else 0.0

        # Minimum transaction fee
        minimum_transaction_fee = 2.50 if (receivable_after_discount + adjusted_commission_total) < 50 else 0.0

        # Tax withholding
        pre_withholding_total = receivable_after_discount + adjusted_commission_total + correction_fee + minimum_transaction_fee
        tax_withholding_amount = 0.03 * pre_withholding_total if tax_verified == "no" else 0.0

        # Total receivables
        total_receivables = pre_withholding_total - tax_withholding_amount

        # Final discounts
        total_receivables *= (1 - 0.01 if city in CAPITAL_CITIES else 1)
        total_receivables *= (1 - 0.02 if senior_citizen == "yes" else 1)
        total_receivables *= (1 - 0.05 if first_order == "yes" else 1)
        total_receivables *= (1 - 0.04 if product_category == "luxury" else 1)
        total_receivables *= (1 - 0.03 if weight > 20 else 1)
        total_receivables *= (1 - 0.07 if customer == "strategic" and loyalty_status == "platinum" and volume >= 1000 and correction_fee == 0.0 else 1)
        total_receivables *= (1 - 0.06 if season == "spring" and product_category == "luxury" and processing_speed == "same-day" else 1)
        total_receivables *= (1 - 0.04 if status == "corporate" and city in CAPITAL_CITIES and payment_type != "credit-card" and tax_verified == "yes" else 1)
        total_receivables *= (1 - 0.08 if transaction_type == "international" and customer == "strategic" and first_order != "yes" and volume > 5000 else 1)
        total_receivables *= (1 - 0.05 if loyalty_status == "platinum" and referral_active == "yes" and is_high_risk != "yes" and tax_verified == "yes" else 1)

        # Escrow
        escrow = 0.01 * receivable_before_discount

        return {
            "total_receivables": total_receivables,
            "escrow": escrow
        }

    with open(csv_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        results = [process_row(row) for row in reader]

    return results
