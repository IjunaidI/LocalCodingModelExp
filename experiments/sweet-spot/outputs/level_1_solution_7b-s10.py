import csv

PRODUCT_RATES = {
    1: {"individual": 1000, "corporate": 900},
    2: {"individual": 1500, "corporate": 1200},
    3: {"individual": 2000, "corporate": 1700},
}
CATEGORY_MULTIPLIER = {"electronics": 1.2, "groceries": 0.8, "luxury": 1.5}

def process_calculations(csv_path):
    result = []
    with open(csv_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            row = {key.strip(): value.strip().lower() for key, value in row.items()}
            productid = int(row['productid'])
            status = row['status']
            volume = int(row.get('volume', 0))
            season = row['season']
            customer = row['customer']
            region = row['region']
            payment_type = row['payment type']
            product_category = row['product category']
            tax_verified = row.get('tax verified', '').lower()

            rate = PRODUCT_RATES[productid][status]
            receivable_before_discount = volume * rate
            spring_rate = 0.05 if season == 'spring' else 0.0
            volume_rate = 0.05 * (volume >= 100) + 0.05 * (volume >= 1000)
            strategic_rate = 0.05 if customer == 'strategic' else 0.0
            total_discount_rate = spring_rate + volume_rate + strategic_rate
            receivable_after_discount = receivable_before_discount * (1 - total_discount_rate)
            region_loading = 0.10 * receivable_after_discount if region == 'emea' else 0.0
            payment_loading = 0.025 * receivable_after_discount if payment_type == 'credit-card' else 0.0
            multiplier = CATEGORY_MULTIPLIER[product_category]
            commission = (region_loading + payment_loading) * multiplier
            subtotal = receivable_after_discount + commission
            withholding = 0.03 * subtotal if tax_verified != 'yes' else 0.0
            total_receivables = subtotal - withholding

            result.append({'total_receivables': total_receivables})
    return result
