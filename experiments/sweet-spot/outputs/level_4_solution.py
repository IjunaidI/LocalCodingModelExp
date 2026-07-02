import csv

def process_calculations(csv_path):
    result = []
    with open(csv_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Normalize the row
            row = {key.strip(): value.strip().lower() for key, value in row.items()}
            
            # Convert numeric values
            row['volume'] = int(row['volume']) if row['volume'] else 0
            
            # Calculate per-unit price based on productid and status
            if row['productid'] == '1':
                per_unit_price = 1000 if row['status'] == 'individual' else 900
            elif row['productid'] == '2':
                per_unit_price = 1500 if row['status'] == 'individual' else 1200
            elif row['productid'] == '3':
                per_unit_price = 2000 if row['status'] == 'individual' else 1700
            else:
                raise ValueError(f"Invalid productid: {row['productid']}")
            
            # Calculate base receivable
            base_receivable = row['volume'] * per_unit_price
            
            # Apply discounts
            discount = 0
            if row['season'] == 'spring':
                discount += 0.05
            if 0 < row['volume'] < 1000:
                discount += 0.05
            elif row['volume'] >= 1000:
                discount += 0.10
            if row['customer'] == 'strategic':
                discount += 0.05
            
            # Calculate receivable after discount
            receivable_after_discount = base_receivable * (1 - discount)
            
            # Apply surcharges
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
            
            # Add to result list
            result.append({
                'total_receivables': total_receivables
            })
    
    return result
