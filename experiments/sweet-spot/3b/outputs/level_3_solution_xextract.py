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

DISCOUNT_SPRING = 0.05
DISCOUNT_VOLUME_100 = 0.05
DISCOUNT_VOLUME_1000 = 0.10
DISCOUNT_STRATEGIC = 0.05

SURCHARGE_EMEA = 0.10
SURCHARGE_CREDIT_CARD = 0.025

WITHHOLDING_NO = 0.03
WITHHOLDING_YES = 0.00

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
            
            # Calculate the per-unit price
            product_id = row['productid']
            status = row['status']
            per_unit_price = PRODUCT_RATES[product_id][status]
            
            # Calculate the base receivable
            base_receivable = row['volume'] * per_unit_price
            
            # Calculate the discounts
            discount_spring = DISCOUNT_SPRING if row['season'] == 'spring' else 0
            discount_volume_100 = DISCOUNT_VOLUME_100 if row['volume'] >= 100 else 0
            discount_volume_1000 = DISCOUNT_VOLUME_1000 if row['volume'] >= 1000 else 0
            discount_strategic = DISCOUNT_STRATEGIC if row['customer'] == 'strategic' else 0
            total_discount = discount_spring + discount_volume_100 + discount_volume_1000 + discount_strategic
            
            # Calculate the receivable after discount
            receivable_after_discount = base_receivable * (1 - total_discount)
            
            # Calculate the surcharges
            surcharge_emea = SURCHARGE_EMEA if row['region'] == 'emea' else 0
            surcharge_credit_card = SURCHARGE_CREDIT_CARD if row['payment type'] == 'credit-card' else 0
            total_surcharges = surcharge_emea + surcharge_credit_card
            
            # Calculate the commission
            commission = total_surcharges * CATEGORY_MULTIPLIER[row['product category']]
            
            # Calculate the subtotal
            subtotal = receivable_after_discount + commission
            
            # Calculate the withholding
            withholding = WITHHOLDING_NO if row['tax verified'] == 'no' else WITHHOLDING_YES
            
            # Calculate the total receivables
            total_receivables = subtotal - (subtotal * withholding)
            
            # Add the result to the list
            results.append({
                'total_receivables': total_receivables
            })
    
    return results
