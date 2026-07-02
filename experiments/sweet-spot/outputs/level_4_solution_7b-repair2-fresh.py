import csv
import re

def process_calculations(csv_path):
    results = []
    with open(csv_path, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Normalize the row
            row = {key.strip(): value.strip().lower() for key, value in row.items()}
            
            # Convert volume and productid to numbers
            row['volume'] = int(row['volume'] or 0)
            row['productid'] = int(row['productid'] or 0)
            
            # Calculate per-unit price
            if row['productid'] == 1:
                per_unit_price = 1000 if row['status'] == 'individual' else 900
            elif row['productid'] == 2:
                per_unit_price = 1500 if row['status'] == 'individual' else 1200
            elif row['productid'] == 3:
                per_unit_price = 2000 if row['status'] == 'individual' else 1700
            
            # Calculate receivable before discount
            receivable_before_discount = row['volume'] * per_unit_price
            
            # Calculate spring rate
            spring_rate = 0.05 if row['season'] == 'spring' else 0.0
            
            # Calculate volume rate
            volume_rate = 0.05 if 100 <= row['volume'] < 1000 else 0.1 if row['volume'] >= 1000 else 0.0
            
            # Calculate strategic rate
            strategic_rate = 0.05 if row['customer'] == 'strategic' else 0.0
            
            # Calculate total discount rate
            total_discount_rate = spring_rate + volume_rate + strategic_rate
            
            # Calculate receivable after discount
            receivable_after_discount = receivable_before_discount * (1 - total_discount_rate)
            
            # Calculate region loading
            region_loading = 0.1 if row['region'] == 'emea' else 0.0
            
            # Calculate payment loading
            payment_loading = 0.025 if row['payment type'] == 'credit-card' else 0.0
            
            # Calculate commission
            commission = (region_loading + payment_loading) * receivable_after_discount * {
                'electronics': 1.2,
                'groceries': 0.8,
                'luxury': 1.5
            }[row['product category']]
            
            # Calculate subtotal
            subtotal = receivable_after_discount + commission
            
            # Calculate withholding
            withholding = 0.03 * subtotal if row.get('tax verified', '').lower() != 'yes' else 0.0
            
            # Calculate total receivables
            total_receivables = subtotal - withholding
            
            # Append the result to the list
            results.append({
                'total_receivables': total_receivables,
                'rate': per_unit_price,
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
                'withholding': withholding
            })
    
    return results
