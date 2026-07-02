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
    "under 100": 0.05,
    "100 to 999": 0.05,
    "1000 or more": 0.10
}
DISCOUNT_RATE_STRATEGIC = 0.05
SURCHARGE_REGION_EMEA = 0.10
SURCHARGE_PAYMENT_TYPE_CREDIT_CARD = 0.025
WITHHOLDING_RATE_UNVERIFIED = 0.03

import csv

def process_calculations(csv_path):
    with open(csv_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        rows = [row for row in reader]
    
    def process_row(row):
        # Normalize row
        row = {key.strip(): value.strip().lower() for key, value in row.items()}
        
        # Convert volume and productid to numbers
        row['volume'] = int(row['volume']) if row['volume'].isdigit() else 0
        row['productid'] = int(row['productid'])
        
        # Calculate per-unit price
        product_rate = PRODUCT_RATES[str(row['productid'])][row['status']]
        
        # Calculate base receivable
        base_receivable = row['volume'] * product_rate
        
        # Calculate discounts
        discount_rate = 0
        if row['season'] == 'spring':
            discount_rate += DISCOUNT_RATE_SPRING
        if row['volume'] < 100:
            discount_rate += DISCOUNT_RATE_VOLUME['under 100']
        elif row['volume'] < 1000:
            discount_rate += DISCOUNT_RATE_VOLUME['100 to 999']
        else:
            discount_rate += DISCOUNT_RATE_VOLUME['1000 or more']
        if row['customer'] == 'strategic':
            discount_rate += DISCOUNT_RATE_STRATEGIC
        
        # Apply combined discount
        receivable_after_discount = base_receivable * (1 - discount_rate)
        
        # Calculate surcharges
        surcharge_region = receivable_after_discount * SURCHARGE_REGION_EMEA if row['region'] == 'emea' else 0
        surcharge_payment_type = receivable_after_discount * SURCHARGE_PAYMENT_TYPE_CREDIT_CARD if row['payment type'] == 'credit-card' else 0
        
        # Calculate commission
        commission = (surcharge_region + surcharge_payment_type) * CATEGORY_MULTIPLIER[row['product category']]
        
        # Calculate subtotal
        subtotal = receivable_after_discount + commission
        
        # Apply withholding
        withholding = subtotal * WITHHOLDING_RATE_UNVERIFIED if not row['tax verified'].lower() == 'true' else 0
        
        # Calculate total receivables
        total_receivables = subtotal - withholding
        
        return {'total_receivables': total_receivables}
    
    return [process_row(row) for row in rows]
