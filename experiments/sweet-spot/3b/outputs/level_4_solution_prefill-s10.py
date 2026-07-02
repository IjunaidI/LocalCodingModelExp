import csv

PRODUCT_RATES = {
    1: {"individual": 1000, "corporate": 900},
    2: {"individual": 1500, "corporate": 1200},
    3: {"individual": 2000, "corporate": 1700},
}
CATEGORY_MULTIPLIER = {"electronics": 1.2, "groceries": 0.8, "luxury": 1.5}


def process_calculations(csv_path):
    results = []
    with open(csv_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Normalize row
            row = {key.strip(): value.strip().lower() for key, value in row.items()}
            
            # Convert numeric values
            row['volume'] = int(row['volume']) if row['volume'] else 0
            row['productid'] = int(row['productid'])
            
            # Calculate base receivable
            per_unit_price = PRODUCT_RATES[row['productid']][row['status']]
            base_receivable = row['volume'] * per_unit_price
            
            # Apply discounts
            discount = 0
            if row['season'] == 'spring':
                discount += 0.05
            if row['volume'] < 100:
                volume_discount = 0
            elif row['volume'] < 1000:
                volume_discount = 0.05
            else:
                volume_discount = 0.10
            discount += volume_discount
            discount += 0.05 if row['customer'] == 'strategic' else 0
            
            # Apply combined discount
            receivable_after_discount = base_receivable * (1 - discount)
            
            # Apply surcharges
            domestic_surcharge = 0.10 if row['region'] == 'emea' else 0
            credit_card_surcharge = 0.025 if row['payment type'] == 'credit-card' else 0
            commission = (domestic_surcharge + credit_card_surcharge) * CATEGORY_MULTIPLIER[row['product category']]
            
            # Calculate subtotal
            subtotal = receivable_after_discount + commission
            
            # Apply withholding
            withholding = 0
            if row['tax verified'] == 'no':
                withholding = subtotal * 0.03
            
            # Calculate total receivables
            total_receivables = subtotal - withholding
            
            # Append result
            results.append({
                'total_receivables': total_receivables,
            })
    
    return results
