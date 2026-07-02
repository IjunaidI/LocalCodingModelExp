import csv

def process_calculations(csv_path):
    results = []
    
    with open(csv_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        
        for row in reader:
            # Normalize the row
            row = {key.strip(): value.strip().lower() for key, value in row.items()}
            
            # Convert volume and productid to numbers
            row['volume'] = int(row['volume']) if row['volume'] else 0
            row['productid'] = int(row['productid']) if row['productid'] else 0
            
            # Determine the base per-unit price
            if row['productid'] == 1:
                per_unit_price = 1000 if row['status'] == 'individual' else 900
            elif row['productid'] == 2:
                per_unit_price = 1500 if row['status'] == 'individual' else 1200
            elif row['productid'] == 3:
                per_unit_price = 2000 if row['status'] == 'individual' else 1700
            
            # Calculate the base receivable
            receivable_before_discount = row['volume'] * per_unit_price
            
            # Calculate the spring rate
            spring_rate = 0.05 if row['season'] == 'spring' else 0
            
            # Calculate the volume rate
            if row['volume'] < 100:
                volume_rate = 0
            elif row['volume'] < 1000:
                volume_rate = 0.05
            else:
                volume_rate = 0.10
            
            # Calculate the strategic rate
            strategic_rate = 0.05 if row['customer'] == 'strategic' else 0
            
            # Calculate the total discount rate
            total_discount_rate = spring_rate + volume_rate + strategic_rate
            
            # Calculate the receivable after discount
            receivable_after_discount = receivable_before_discount * (1 - total_discount_rate)
            
            # Calculate the region loading
            region_loading = 0.10 if row['region'] == 'emea' else 0
            
            # Calculate the payment loading
            payment_loading = 0.025 if row['payment type'] == 'credit-card' else 0
            
            # Calculate the commission
            commission = (region_loading + payment_loading) * receivable_after_discount * {
                'electronics': 1.2,
                'groceries': 0.8,
                'luxury': 1.5
            }[row['product category']]
            
            # Calculate the subtotal
            subtotal = receivable_after_discount + commission
            
            # Calculate the withholding
            withholding = 0.03 * subtotal if not row['tax verified'].lower() == 'true' else 0
            
            # Calculate total receivables
            total_receivables = subtotal - withholding
            
            # Create the result dictionary
            result = {
                'rate': 1000.0000,  # Fixed rate as per requirement
                'receivable_before_discount': receivable_before_discount,
                'spring_rate': spring_rate,
                'volume_rate': volume_rate,
                'strategic_rate': strategic_rate,
                'total_discount_rate': total_discount_rate,
                'receivable_after_discount': receivable_after_discount,
                'region_loading': region_loading,
                'payment_loading': payment_loading,
                'commission': commission,
                'subtotal': subtotal,
                'withholding': withholding,
                'total_receivables': total_receivables
            }
            
            results.append(result)
    
    return results
