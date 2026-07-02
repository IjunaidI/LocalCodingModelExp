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
VOLUME_DISCOUNT_100_TO_999 = 0.05
VOLUME_DISCOUNT_1000_OR_MORE = 0.10
DISCOUNT_STRATEGIC = 0.05
SURCHARGE_EMEA = 0.10
SURCHARGE_CREDIT_CARD = 0.025
WITHHOLDING_NO = 0.03

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
            
            # Apply discounts
            discount_spring = DISCOUNT_SPRING if row['season'] == 'spring' else 0
            volume_discount = 0
            if row['volume'] < 100:
                volume_discount = 0
            elif row['volume'] < 1000:
                volume_discount = VOLUME_DISCOUNT_100_TO_999
            else:
                volume_discount = VOLUME_DISCOUNT_1000_OR_MORE
            total_discount = discount_spring + volume_discount + DISCOUNT_STRATEGIC
            
            # Apply the combined discount
            receivable_after_discount = base_receivable * (1 - total_discount)
            
            # Apply surcharges
            surcharge_emea = SURCHARGE_EMEA if row['region'] == 'emea' else 0
            surcharge_credit_card = SURCHARGE_CREDIT_CARD if row['payment type'] == 'credit-card' else 0
            total_surcharges = surcharge_emea + surcharge_credit_card
            
            # Calculate the commission
            category = row['product category']
            commission = total_surcharges * CATEGORY_MULTIPLIER[category]
            
            # Calculate the subtotal
            subtotal = receivable_after_discount + commission
            
            # Calculate withholding
            withholding = subtotal * WITHHOLDING_NO if row['tax verified'] == 'no' else 0
            
            # Calculate total receivables
            total_receivables = subtotal - withholding
            
            # Add the result to the list
            results.append({
                'total_receivables': total_receivables
            })
        
        return results
