import csv

def process_calculations(csv_path):
    def calculate_rate(productid, status, season, customer, region, payment_type, product_category):
        base_prices = {
            1: {'individual': 1000, 'corporate': 900},
            2: {'individual': 1500, 'corporate': 1200},
            3: {'individual': 2000, 'corporate': 1700}
        }
        base_price = base_prices[productid][status]
        spring_rate = 0.05 if season == 'spring' else 0.0
        volume_rate = 0.05 if volume < 100 else 0.05 if 100 <= volume < 1000 else 0.1
        strategic_rate = 0.05 if customer == 'strategic' else 0.0
        total_discount_rate = spring_rate + volume_rate + strategic_rate
        receivable_before_discount = volume * base_price
        receivable_after_discount = receivable_before_discount * (1 - total_discount_rate)
        region_loading = 0.1 if region == 'emea' else 0.0
        payment_loading = 0.025 if payment_type == 'credit-card' else 0.0
        commission = (region_loading + payment_loading) * receivable_after_discount * {
            'electronics': 1.2,
            'groceries': 0.8,
            'luxury': 1.5
        }[product_category]
        subtotal = receivable_after_discount + commission
        withholding = subtotal * 0.03 if tax_verified == 'no' else 0.0
        total_receivables = subtotal - withholding
        return {
            'rate': total_discount_rate,
            'receivable_before_discount': receivable_before_discount,
            'spring_rate': spring_rate,
            'volume_rate': volume_rate,
            'strategic_rate': strategic_rate,
            'total_discount_rate': total_discount_rate,
            'receivable_after_discount': receivable_after_discount,
            'region_loading': region_loading,
            'payment_loading': payment_loading,
            'commission': commission,
            'subtotal': subtotal,
            'withholding': withholding,
            'total_receivables': total_receivables
        }

    with open(csv_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        rows = [row for row in reader]

    corrected_rows = []
    for row in rows:
        row = {key.strip(): value.strip().lower() for key, value in row.items()}
        productid = int(row.get('productid', 0))
        status = row.get('status', '').strip().lower()
        volume = int(row.get('volume', 0))
        season = row.get('season', '').strip().lower()
        customer = row.get('customer', '').strip().lower()
        region = row.get('region', '').strip().lower()
        payment_type = row.get('payment type', '').strip().lower()
        product_category = row.get('product category', '').strip().lower()
        tax_verified = row.get('tax verified', '').strip().lower()

        result = calculate_rate(productid, status, season, customer, region, payment_type, product_category)
        corrected_rows.append(result)

    return corrected_rows
