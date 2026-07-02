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
            # Normalize the row
            row = {key.strip(): value.strip().lower() for key, value in row.items()}
            
            # Convert numeric values
            row['volume'] = int(row['volume']) if row['volume'] else 0
            
            # Calculate the per-unit price
            product_id = int(row['productid'])
            status = row['status']
            per_unit_price = PRODUCT_RATES[product_id][status]
            
            # Calculate the base receivable
            base_receivable = row['volume'] * per_unit_price
            
            # Apply discounts
            discount = 0
            if row['season'] == 'spring':
                discount += 0.05
            if row['volume'] >= 1000:
                discount += 0.05
            if row['volume'] >= 100:
                discount += 0.05
            if row['customer'] == 'strategic':
                discount += 0.05
            
            # Apply the combined discount
            receivable_after_discount = base_receivable * (1 - discount)
            
            # Apply surcharges
            if row['region'] == 'emea':
                receivable_after_discount *= 1.10
            if row['payment type'] == 'credit-card':
                receivable_after_discount *= 1.025
            
            # Calculate commission
            commission = receivable_after_discount * CATEGORY_MULTIPLIER[row['product category']]
            
            # Calculate the subtotal
            subtotal = receivable_after_discount + commission
            
            # Calculate withholding
            withholding = subtotal * 0.03 if row['tax verified'] == 'no' else 0
            
            # Calculate total receivables
            total_receivables = subtotal - withholding
            
            # Add the result to the list
            results.append({
                'total_receivables': total_receivables
            })
    
    return results
