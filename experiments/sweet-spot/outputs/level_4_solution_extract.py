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

DISCOUNT_RATE_SPRING = 0.05
DISCOUNT_RATE_VOLUME = {
    "under 100": 0,
    "100 to 999": 0.05,
    "1000 or more": 0.10
}
DISCOUNT_RATE_STRATEGIC = 0.05
SURCHARGE_REGION_EMEA = 0.10
SURCHARGE_PAYMENT_TYPE_CREDIT_CARD = 0.025
WITHHOLDING_RATE = 0.03

import csv

def process_calculations(csv_path):
    with open(csv_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        results = []

        for row in reader:
            # Normalize the row
            row = {key.strip(): value.strip().lower() for key, value in row.items()}
            
            # Convert numeric values
            row['volume'] = int(row['volume']) if row['volume'] else 0
            row['productid'] = int(row['productid'])
            
            # Calculate the per-unit price
            product_rate = PRODUCT_RATES[row['productid']][row['status']]
            
            # Calculate the base receivable
            base_receivable = row['volume'] * product_rate
            
            # Calculate the volume discount
            if row['volume'] < 100:
                volume_discount = 0
            elif row['volume'] < 1000:
                volume_discount = 0.05
            else:
                volume_discount = 0.10
            
            # Calculate the total discount
            total_discount = (
                DISCOUNT_RATE_SPRING +
                volume_discount +
                DISCOUNT_RATE_STRATEGIC
            )
            
            # Calculate the receivable after discount
            receivable_after_discount = base_receivable * (1 - total_discount)
            
            # Calculate the surcharges
            surcharge_region = SURCHARGE_REGION_EMEA if row['region'] == 'emea' else 0
            surcharge_payment_type = SURCHARGE_PAYMENT_TYPE_CREDIT_CARD if row['payment type'] == 'credit-card' else 0
            
            # Calculate the subtotal
            subtotal = receivable_after_discount + (surcharge_region + surcharge_payment_type)
            
            # Calculate the commission
            commission = subtotal * CATEGORY_MULTIPLIER[row['product category']]
            
            # Calculate the withholding
            withholding = subtotal * WITHHOLDING_RATE if row['tax verified'] == 'yes' else 0
            
            # Calculate total receivables
            total_receivables = subtotal - withholding
            
            # Add the result to the list
            results.append({
                'total_receivables': total_receivables
            })
    
    return results
