PRODUCT_RATES = {
    "1": {"individual": 1000, "corporate": 900},
    "2": {"individual": 1500, "corporate": 1200},
    "3": {"individual": 2000, "corporate": 1700}
}

CATEGORY_MULTIPLIER = {
    "electronics": 1.2,
    "groceries": 0.8,
    "luxury": 1.5
}

DISCOUNT_RATE = 0.05
VOLUME_DISCOUNT_RATE = 0.05
STRATEGIC_CUSTOMER_DISCOUNT_RATE = 0.05
REGION_DISCOUNT_RATE = 0.10
PAYMENT_TYPE_DISCOUNT_RATE = 0.025
COMMISSION_MULTIPLIER = 1.0
TAX_WITHHOLDING_RATE = 0.03

import csv

def process_calculations(csv_path):
    # Read the CSV file
    with open(csv_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        
        # Process each row
        results = []
        for row in reader:
            # Normalize the row
            row = {key.strip(): value.strip().lower() for key, value in row.items()}
            
            # Convert numeric values
            row['volume'] = int(row['volume']) if row['volume'] else 0
            
            # Calculate the per-unit price
            product_id = row['productid']
            status = row['status']
            per_unit_price = PRODUCT_RATES[product_id][status]
            
            # Calculate the base receivable
            base_receivable = row['volume'] * per_unit_price
            
            # Calculate the volume discount
            volume_discount = 0
            if row['volume'] >= 1000:
                volume_discount += VOLUME_DISCOUNT_RATE
            if row['volume'] >= 100:
                volume_discount += VOLUME_DISCOUNT_RATE
            
            # Calculate the strategic customer discount
            strategic_customer_discount = STRATEGIC_CUSTOMER_DISCOUNT_RATE
            
            # Calculate the total discount
            total_discount = DISCOUNT_RATE + volume_discount + strategic_customer_discount
            
            # Calculate the receivable after discount
            receivable_after_discount = base_receivable * (1 - total_discount)
            
            # Calculate the surcharges
            region_discount = REGION_DISCOUNT_RATE if row['region'] == 'emea' else 0
            payment_type_discount = PAYMENT_TYPE_DISCOUNT_RATE if row['payment type'] == 'credit-card' else 0
            
            # Calculate the subtotal
            subtotal = receivable_after_discount + (region_discount + payment_type_discount) * receivable_after_discount
            
            # Calculate the commission
            commission = subtotal * CATEGORY_MULTIPLIER[row['product category']]
            
            # Calculate the withholding
            withholding = subtotal * TAX_WITHHOLDING_RATE if row['tax verified'] == 'yes' else 0
            
            # Calculate the total receivables
            total_receivables = subtotal - withholding
            
            # Add the result to the list
            results.append({
                'total_receivables': total_receivables
            })
    
    return results
