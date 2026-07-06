import csv

PRODUCT_RATES = {
    1: {"individual": 1000, "corporate": 900},
    2: {"individual": 1500, "corporate": 1200},
    3: {"individual": 2000, "corporate": 1700},
}

def process_calculations(csv_path):
    def calculate_discount(volume, product_id, customer_type, season, region, quarter, payment_type, transaction_type, product_category, seller_years, processing_speed, tax_verified, is_high_risk, requires_correction, status, referral_active, referral_invoices_remaining, city, senior_citizen, first_order, weight):
        # Calculate receivable before discount
        receivable_before_discount = volume * PRODUCT_RATES[product_id][customer_type]

        # Apply rules
        total_discount = 0
        if season == "Spring":
            total_discount += receivable_before_discount * 0.05
        if volume < 100:
            total_discount += receivable_before_discount * 0.00
        elif volume < 1000:
            total_discount += receivable_before_discount * 0.05
        elif volume >= 1000:
            total_discount += receivable_before_discount * 0.10
        if customer_type == "strategic":
            total_discount += receivable_before_discount * 0.05
        if product_category == "electronics":
            product_category_multiplier = 1.2
        elif product_category == "groceries":
            product_category_multiplier = 0.8
        elif product_category == "luxury":
            product_category_multiplier = 1.5
        if tax_verified == "True":
            total_discount += receivable_before_discount * 0.10
        if is_high_risk == "True":
            total_discount += receivable_before_discount * 0.15
        if requires_correction == "True":
            total_discount += 5
        if status == "individual":
            region_loading = 0.10
            payment_loading = 0.025 if payment_type == "credit-card" else 0
            seasonal_loading = 0.02 if quarter == "Q1" else -0.01 if quarter == "Q4" else 0
            geographic_zone_loading = 0.05 if transaction_type == "domestic" else 0.08 if transaction_type == "international" else 0.10
            processing_speed_loading = 0.15 if processing_speed == "same-day" else 0.10 if processing_speed == "next-day" else 0
        elif status == "corporate":
            region_loading = 0.05
            payment_loading = 0.025 if payment_type == "credit-card" else 0
            seasonal_loading = 0.02 if quarter == "Q1" else -0.01 if quarter == "Q4" else 0
            geographic_zone_loading = 0.05 if transaction_type == "domestic" else 0.08 if transaction_type == "international" else 0.10
            processing_speed_loading = 0.15 if processing_speed == "same-day" else 0.10 if processing_speed == "next-day" else 0
        # Calculate base commission total
        base_commission_total = (region_loading + payment_loading + seasonal_loading + geographic_zone_loading + processing_speed_loading) * receivable_before_discount

        # Calculate adjusted commission total
        adjusted_commission_total = base_commission_total * product_category_multiplier

        # Calculate total receivables
        total_receivables = receivable_before_discount - total_discount + adjusted_commission_total
        if requires_correction == "True":
            total_receivables += 5

        # Calculate escrow
        escrow = 0.01 * total_receivables

        # Apply additional discounts and fees
        if customer_type == "strategic" and seller_years >= 5 and not requires_correction:
            total_receivables *= 0.85
        if referral_active == "True" and referral_invoices_remaining > 0:
            adjusted_commission_total *= 0.95
        if not tax_verified:
            total_receivables *= 1.03
        if is_high_risk:
            adjusted_commission_total *= 0.85
        if requires_correction:
            total_receivables += 5
        if product_category == "luxury":
            total_receivables *= 1.04
        if weight > 20:
            total_receivables *= 1.03
        if customer_type == "strategic" and seller_years == 5 and volume >= 1000 and not requires_correction:
            total_receivables *= 0.90
        if customer_type == "corporate" and status == "corporate" and city in ["karachi", "lahore", "islamabad", "peshawar", "quetta"] and not payment_type == "credit-card" and tax_verified == "True":
            total_receivables *= 0.95
        if customer_type == "strategic" and status == "individual" and volume > 5000 and not requires_correction:
            total_receivables *= 0.92
        if customer_type == "strategic" and status == "individual" and not high_risk and tax_verified == "True":
            total_receivables *= 0.95

        return {
            "total_receivables": total_receivables,
            "escrow": escrow,
        }

    results = []
    with open(csv_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Strip leading/trailing whitespace from header names
            for key in row:
                row[key] = row[key].strip()
            results.append(calculate_discount(**row))

    return results
