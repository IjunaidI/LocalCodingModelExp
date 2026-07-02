import csv

def process_calculations(csv_path):
    def calculate_receivable(row):
        # Normalize row
        row = {key.strip(): value.strip().lower() for key, value in row.items()}
        
        # Convert volume and productid to numbers
        row['volume'] = int(row['volume']) if row['volume'] else 0
        row['productid'] = int(row['productid'])
        
        # Calculate per-unit price
        per_unit_price = {
            1: 1000 if row['status'] == 'individual' else 900,
            2: 1500 if row['status'] == 'individual' else 1200,
            3: 2000 if row['status'] == 'individual' else 1700
        }.get(row['productid'], 0)
        
        # Calculate base receivable
        base_receivable = row['volume'] * per_unit_price
        
        # Calculate discounts
        discount = 0
        if row['season'] == 'spring':
            discount += 0.05
        if row['volume'] >= 1000:
            discount += 0.05
        if row['volume'] >= 100:
            discount += 0.05
        if row['customer'] == 'strategic':
            discount += 0.05
        
        # Apply combined discount
        receivable_after_discount = base_receivable * (1 - discount)
        
        # Calculate surcharges
        surcharge_emea = 0.10 if row['region'] == 'emea' else 0
        surcharge_credit_card = 0.025 if row['payment type'] == 'credit-card' else 0
        total_surcharges = surcharge_emea + surcharge_credit_card
        
        # Calculate commission
        commission = total_surcharges * {
            'electronics': 1.2,
            'groceries': 0.8,
            'luxury': 1.5
        }.get(row['product category'], 1)
        
        # Calculate subtotal
        subtotal = receivable_after_discount + commission
        
        # Calculate withholding
        withholding = 0.03 if row['tax verified'] == 'no' else 0
        
        # Calculate total receivables
        total_receivables = subtotal - withholding
        
        return {'total_receivables': total_receivables}
    
    with open(csv_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        return [calculate_receivable(row) for row in reader]
