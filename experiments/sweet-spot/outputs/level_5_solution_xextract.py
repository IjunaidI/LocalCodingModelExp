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
WITHHOLDING_NOT_VERIFIED = 0.03

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
            row['tax verified'] = row['tax verified'] == 'true' if row['tax verified'] else False
            
            # Calculate the per-unit price
            product_id = row['productid']
            status = row['status']
            per_unit_price = PRODUCT_RATES[product_id][status]
            
            # Calculate the base receivable
            base_receivable = row['volume'] * per_unit_price
            
            # Calculate the volume discount
            if row['season'] == 'spring':
                base_receivable *= (1 - DISCOUNT_SPRING)
            if 100 <= row['volume'] < 1000:
                base_receivable *= (1 - VOLUME_DISCOUNT_100_TO_999)
            if row['volume'] >= 1000:
                base_receivable *= (1 - VOLUME_DISCOUNT_1000_OR_MORE)
            
            # Apply the strategic discount
            if row['customer'] == 'strategic':
                base_receivable *= (1 - DISCOUNT_STRATEGIC)
            
            # Calculate the receivable after discount
            receivable_after_discount = base_receivable
            
            # Calculate the surcharges
            if row['region'] == 'emea':
                receivable_after_discount *= (1 + SURCHARGE_EMEA)
            if row['payment type'] == 'credit-card':
                receivable_after_discount *= (1 + SURCHARGE_CREDIT_CARD)
            
            # Calculate the commission
            category = row['product category']
            commission = receivable_after_discount * CATEGORY_MULTIPLIER[category]
            
            # Calculate the subtotal
            subtotal = receivable_after_discount + commission
            
            # Calculate the withholding
            withholding = subtotal * WITHHOLDING_NOT_VERIFIED if not row['tax verified'] else 0
            
            # Calculate the total receivables
            total_receivables = subtotal - withholding
            
            # Add the result to the list
            results.append({
                'total_receivables': total_receivables
            })
    
    return results
