import csv

def process_calculations(csv_path):
    results = []
    with open(csv_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Normalize the row
            row = {key.strip(): value.strip().lower() for key, value in row.items()}
            
            # Convert volume and productid to numbers, and treat an empty cell as 0
            row['volume'] = int(row['volume']) if row['volume'] else 0
            row['productid'] = int(row['productid']) if row['productid'] else 0
            
            # Calculate the base receivable
            if row['productid'] == 1:
                per_unit_price = 1000 if row['status'] == 'individual' else 900
            elif row['productid'] == 2:
                per_unit_price = 1500 if row['status'] == 'individual' else 1200
            elif row['productid'] == 3:
                per_unit_price = 2000 if row['status'] == 'individual' else 1700
            base_receivable = row['volume'] * per_unit_price
            
            # Calculate the total discount rate
            total_discount_rate = 0
            if row['season'] == 'spring':
                total_discount_rate += 0.05
            if row['volume'] >= 1000:
                total_discount_rate += 0.05
            if row['volume'] >= 100:
                total_discount_rate += 0.05
            if row['customer'] == 'strategic':
                total_discount_rate += 0.05
            
            # Calculate the receivable after discount
            receivable_after_discount = base_receivable * (1 - total_discount_rate)
            
            # Calculate the surcharges
            region_loading = 0.10 if row['region'] == 'emea' else 0
            payment_loading = 0.025 if row['payment type'] == 'credit-card' else 0
            commission = (region_loading + payment_loading) * (1.2 if row['product category'] == 'electronics' else 0.8 if row['product category'] == 'groceries' else 1.5)
            
            # Calculate the subtotal
            subtotal = receivable_after_discount + commission
            
            # Calculate the withholding
            withholding = subtotal * 0.03 if row['tax verified'] == 'no' else 0
            
            # Calculate total receivables
            total_receivables = subtotal - withholding
            
            # Store the results
            results.append({
                'total_receivables': total_receivables,
                'receivable_before_discount': base_receivable,
                'spring_rate': total_discount_rate,
                'volume_rate': 0.05 if row['volume'] >= 100 else 0,
                'strategic_rate': 0.05 if row['customer'] == 'strategic' else 0,
                'total_discount_rate': total_discount_rate,
                'receivable_after_discount': receivable_after_discount,
                'region_loading': region_loading,
                'payment_loading': payment_loading,
                'commission': commission,
                'subtotal': subtotal,
                'withholding': withholding
            })
    
    return results
