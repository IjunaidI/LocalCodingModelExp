import csv

PRODUCT_RATES = {
    1: {"individual": 1000, "corporate": 900},
    2: {"individual": 1500, "corporate": 1200},
    3: {"individual": 2000, "corporate": 1700},
}

CATEGORY_MULTIPLIER = {
    "electronics": 1.2,
    "groceries": 0.8,
    "luxury": 1.5,
}

def process_calculations(csv_path):
    results = []
    with open(csv_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Strip spaces from headers and cells
            row = {k.strip(): v.strip() for k, v in row.items()}
            
            # Treat empty cells as defaults
            row['productid'] = int(row.get('productid', 1))
            row['status'] = row.get('status', 'individual').lower()
            row['volume'] = int(row.get('volume', 0))
            row['season'] = row.get('season', 'spring').lower()
            row['customer'] = row.get('customer', 'non-strategic').lower()
            row['region'] = row.get('region', 'emea').lower()
            row['payment type'] = row.get('payment type', 'ach/wire').lower()
            row['transaction type'] = row.get('transaction type', 'domestic').lower()
            row['product category'] = row.get('product category', 'electronics').lower()
            row['tax verified'] = row.get('tax verified', 'no').lower()
            
            # Rule 1: Rate
            rate = PRODUCT_RATES[row['productid']][row['status']]
            
            # Rule 2: Base
            receivable_before_discount = row['volume'] * rate
            
            # Rule 3: Spring discount rate
            spring_rate = 0.05 if row['season'] == 'spring' else 0.0
            
            # Rule 4: Volume discount rate
            volume_rate = 0.0
            if row['volume'] >= 100:
                volume_rate += 0.05
            if row['volume'] >= 1000:
                volume_rate += 0.05
            
            # Rule 5: Strategic discount rate
            strategic_rate = 0.05 if row['customer'] == 'strategic' else 0.0
            
            # Rule 6: Apply discounts
            total_discount_rate = spring_rate + volume_rate + strategic_rate
            receivable_after_discount = receivable_before_discount * (1 - total_discount_rate)
            
            # Rule 7: Region loading
            region_loading = 0.10 * receivable_after_discount if row['region'] == 'emea' else 0.0
            
            # Rule 8: Payment loading
            payment_loading = 0.025 * receivable_after_discount if row['payment type'] == 'credit-card' else 0.0
            
            # Rule 9: Commission
            multiplier = CATEGORY_MULTIPLIER[row['product category']]
            commission = (region_loading + payment_loading) * multiplier
            
            # Rule 10: Tax withholding and total
            subtotal = receivable_after_discount + commission
            withholding = 0.03 * subtotal if row['tax verified'] == 'no' else 0.0
            total_receivables = subtotal - withholding
            
            results.append({'total_receivables': total_receivables})
    
    return results
