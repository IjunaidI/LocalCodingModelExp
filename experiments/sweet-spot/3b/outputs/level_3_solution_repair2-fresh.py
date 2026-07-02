import csv

def process_calculations(csv_path):
    results = []
    
    with open(csv_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        headers = {key.strip().lower(): key for key in reader.fieldnames}
        
        for row in reader:
            # Normalize and convert data types
            row = {key.strip(): value.strip().lower() for key, value in row.items()}
            row['volume'] = int(row.get('volume', 0))
            row['productid'] = int(row.get('productid', 0))
            
            # Calculate per-unit price
            productid = row['productid']
            status = row['status']
            if productid == 1:
                per_unit_price = 1000 if status == 'individual' else 900
            elif productid == 2:
                per_unit_price = 1500 if status == 'individual' else 1200
            elif productid == 3:
                per_unit_price = 2000 if status == 'individual' else 1700
            else:
                raise ValueError(f"Invalid productid: {productid}")
            
            # Calculate base receivable
            receivable_before_discount = row['volume'] * per_unit_price
            
            # Calculate discounts
            total_discount_rate = 0
            if row['season'] == 'spring':
                total_discount_rate += 0.05
            if row['volume'] >= 100:
                total_discount_rate += 0.05
            if row['volume'] >= 1000:
                total_discount_rate += 0.05
            if row['customer'] == 'strategic':
                total_discount_rate += 0.05
            
            # Calculate receivable after discount
            receivable_after_discount = receivable_before_discount * (1 - total_discount_rate)
            
            # Calculate surcharges
            region_loading = 0.10 if row['region'] == 'emea' else 0
            payment_loading = 0.025 if row['payment type'] == 'credit-card' else 0
            commission = (region_loading + payment_loading) * (0.8 if row['product category'] == 'groceries' else 1.2 if row['product category'] == 'electronics' else 1.5)
            
            # Calculate subtotal
            subtotal = receivable_after_discount + commission
            
            # Calculate withholding
            withholding = subtotal * 0.03 if row['tax verified'] == 'no' else 0
            
            # Calculate total receivables
            total_receivables = subtotal - withholding
            
            # Collect results
            result = {
                'total_receivables': total_receivables,
                'rate': total_discount_rate,
                'receivable_before_discount': receivable_before_discount,
                'spring_rate': total_discount_rate if row['season'] == 'spring' else 0,
                'volume_rate': total_discount_rate if row['volume'] >= 100 else 0,
                'strategic_rate': total_discount_rate if row['customer'] == 'strategic' else 0,
                'total_discount_rate': total_discount_rate,
                'receivable_after_discount': receivable_after_discount,
                'region_loading': region_loading,
                'payment_loading': payment_loading,
                'commission': commission,
                'subtotal': subtotal,
                'withholding': withholding
            }
            results.append(result)
    
    return results
