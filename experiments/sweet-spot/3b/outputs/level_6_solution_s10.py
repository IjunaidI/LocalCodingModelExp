import csv

PRODUCT_RATES = {
    1: {"individual": 1000, "corporate": 900},
    2: {"individual": 1500, "corporate": 1200},
    3: {"individual": 2000, "corporate": 1700},
}
CATEGORY_MULTIPLIER = {"electronics": 1.2, "groceries": 0.8, "luxury": 1.5}

def process_calculations(csv_path):
    total_receivables = []
    
    with open(csv_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Normalize the row
            row = {key.strip(): value.strip().lower() for key, value in row.items()}
            
            # Convert to numbers
            row['volume'] = int(row['volume']) if row['volume'] else 0
            row['productid'] = int(row['productid'])
            
            # Calculate base receivable
            base_receivable = row['volume'] * PRODUCT_RATES[row['productid']][row['status']]
            
            # Calculate discount rates
            spring_rate = 0.05 if row['season'] == 'spring' else 0.0
            volume_rate = 0.0
            if row['volume'] < 100:
                volume_rate = 0.0
            elif row['volume'] < 1000:
                volume_rate = 0.05
            else:
                volume_rate = 0.10
            
            strategic_rate = 0.05 if row['customer'] == 'strategic' else 0.0
            
            # Calculate receivable after discount
            discount_rate = spring_rate + volume_rate + strategic_rate
            receivable_after_discount = base_receivable * (1 - discount_rate)
            
            # Calculate loadings
            region_loading = 0.10 * receivable_after_discount if row['region'] == 'emea' else 0.0
            payment_loading = 0.025 * receivable_after_discount if row['payment type'] == 'credit-card' else 0.0
            
            # Calculate commission
            commission = (region_loading + payment_loading) * CATEGORY_MULTIPLIER[row['product category']]
            
            # Calculate subtotal
            subtotal = receivable_after_discount + commission
            
            # Calculate withholding
            withholding = 0.03 * subtotal if row['tax verified'] == 'no' else 0.0
            
            # Calculate total receivables
            total_receivables.append({
                'total_receivables': subtotal - withholding
            })
    
    return total_receivables
