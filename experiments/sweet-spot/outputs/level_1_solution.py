import csv

PRODUCT_RATES = {
    1: {"individual": 1000, "corporate": 900},
    2: {"individual": 1500, "corporate": 1200},
    3: {"individual": 2000, "corporate": 1700},
}
CATEGORY_MULTIPLIER = {"electronics": 1.2, "groceries": 0.8, "luxury": 1.5}

def process_calculations(csv_path):
    total_receivables_list = []
    
    with open(csv_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        
        for row in reader:
            # Normalize the row
            row = {key.strip(): value.strip().lower() for key, value in row.items()}
            
            # Convert numeric values
            row['volume'] = int(row['volume']) if row['volume'] else 0
            
            # Apply the 10 rules
            rate = PRODUCT_RATES[int(row['productid'])][row['status']]
            receivable_before_discount = row['volume'] * rate
            
            spring_rate = 0.05 if row['season'] == 'spring' else 0.0
            volume_rate = 0.05 if row['volume'] >= 100 else 0.0
            volume_rate += 0.05 if row['volume'] >= 1000 else 0.0
            
            strategic_rate = 0.05 if row['customer'] == 'strategic' else 0.0
            
            total_discount_rate = spring_rate + volume_rate + strategic_rate
            receivable_after_discount = receivable_before_discount * (1 - total_discount_rate)
            
            region_loading = 0.10 * receivable_after_discount if row['region'] == 'emea' else 0.0
            payment_loading = 0.025 * receivable_after_discount if row['payment type'] == 'credit-card' else 0.0
            
            multiplier = CATEGORY_MULTIPLIER[row['product category']]
            commission = (region_loading + payment_loading) * multiplier
            
            subtotal = receivable_after_discount + commission
            withholding = 0.03 * subtotal if row['tax verified'] == 'no' else 0.0
            total_receivables = subtotal - withholding
            
            # Add to the list
            total_receivables_list.append({'total_receivables': total_receivables})
    
    return total_receivables_list
