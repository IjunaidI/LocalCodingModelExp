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
        result = []
        
        for row in reader:
            # Normalize the row
            row = {key.strip(): value.strip().lower() for key, value in row.items()}
            
            # Convert numeric values
            row['volume'] = int(row['volume']) if row['volume'] else 0
            row['productid'] = int(row['productid'])
            
            # Calculate the per-unit price
            product_rate = PRODUCT_RATES[str(row['productid'])][row['status']]
            per_unit_price = product_rate
            
            # Calculate the volume discount
            volume_discount = DISCOUNT_RATE_VOLUME.get(str(row['volume']), 0)
            
            # Calculate the total receivable before discounts
            base_receivable = row['volume'] * per_unit_price
            
            # Calculate the total receivable after discounts
            total_receivable = base_receivable * (1 - DISCOUNT_RATE_SPRING - volume_discount - DISCOUNT_RATE_STRATEGIC)
            
            # Calculate the surcharges
            surcharge_region = total_receivable * SURCHARGE_REGION_EMEA if row['region'] == 'emea' else 0
            surcharge_payment_type = total_receivable * SURCHARGE_PAYMENT_TYPE_CREDIT_CARD if row['payment type'] == 'credit-card' else 0
            
            # Calculate the commission
            commission = (surcharge_region + surcharge_payment_type) * CATEGORY_MULTIPLIER[row['product category']]
            
            # Calculate the subtotal
            subtotal = total_receivable + commission
            
            # Calculate the withholding
            withholding = subtotal * WITHHOLDING_RATE if row['tax verified'] == 'no' else 0
            
            # Calculate the total receivables
            total_receivables = subtotal - withholding
            
            # Append the result to the list
            result.append({
                'total_receivables': total_receivables
            })
        
        return result
