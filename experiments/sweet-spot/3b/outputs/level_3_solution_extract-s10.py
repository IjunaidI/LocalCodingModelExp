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

def process_calculations(csv_path):
    total_receivables = []
    
    with open(csv_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Normalize row
            row = {key.strip(): value.strip().lower() for key, value in row.items()}
            
            # Convert numeric values
            row['volume'] = int(row['volume']) if row['volume'] else 0
            
            # Calculate per-unit price
            product_rate = PRODUCT_RATES[row['productid']][row['status']]
            
            # Calculate base receivable
            base_receivable = row['volume'] * product_rate
            
            # Calculate discounts
            total_discount = 0
            if row['season'] == 'spring':
                total_discount += DISCOUNT_RATE
            if row['volume'] >= 100:
                total_discount += VOLUME_DISCOUNT_RATE
            if row['volume'] >= 1000:
                total_discount += VOLUME_DISCOUNT_RATE
            if row['customer'] == 'strategic':
                total_discount += STRATEGIC_CUSTOMER_DISCOUNT_RATE
            
            # Apply combined discount
            receivable_after_discount = base_receivable * (1 - total_discount)
            
            # Calculate surcharges
            if row['region'] == 'emea':
                receivable_after_discount *= (1 + REGION_DISCOUNT_RATE)
            if row['payment type'] == 'credit-card':
                receivable_after_discount *= (1 + PAYMENT_TYPE_DISCOUNT_RATE)
            
            # Calculate commission
            commission = receivable_after_discount * CATEGORY_MULTIPLIER[row['product category']]
            
            # Calculate subtotal
            subtotal = receivable_after_discount + commission
            
            # Calculate withholding
            withholding = subtotal * TAX_WITHHOLDING_RATE if row['tax verified'] == 'yes' else 0
            
            # Calculate total receivables
            total_receivable = subtotal - withholding
            
            # Append to list
            total_receivables.append({
                'total_receivables': total_receivable
            })
    
    return total_receivables
