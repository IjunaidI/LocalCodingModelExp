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
            # Convert productid and volume to numbers
            row['productid'] = int(row['productid'])
            row['volume'] = int(row['volume'])
            # Convert status, customer, region, payment type, and season to lowercase
            row['status'] = row['status'].strip().lower()
            row['customer'] = row['customer'].strip().lower()
            row['region'] = row['region'].strip().lower()
            row['payment type'] = row['payment type'].strip().lower()
            row['season'] = row['season'].strip().lower()
            # Convert tax verified to boolean
            row['tax verified'] = row['tax verified'].strip().lower() == 'true'
            
            # Calculate the base receivable
            base_receivable = row['volume'] * PRODUCT_RATES[row['productid']][row['status']]
            
            # Calculate the spring rate
            spring_rate = 0.05 if row['season'] == 'spring' else 0.0
            
            # Calculate the volume rate
            volume_rate = 0.05 if row['volume'] >= 100 else 0.0
            volume_rate += 0.05 if row['volume'] >= 1000 else 0.0
            
            # Calculate the strategic rate
            strategic_rate = 0.05 if row['customer'] == 'strategic' else 0.0
            
            # Calculate the total discount rate
            total_discount_rate = spring_rate + volume_rate + strategic_rate
            
            # Calculate the receivable after discount
            receivable_after_discount = base_receivable * (1 - total_discount_rate)
            
            # Calculate the region loading
            region_loading = 0.10 * receivable_after_discount if row['region'] == 'emea' else 0.0
            
            # Calculate the payment loading
            payment_loading = 0.025 * receivable_after_discount if row['payment type'] == 'credit-card' else 0.0
            
            # Calculate the commission
            commission = (region_loading + payment_loading) * CATEGORY_MULTIPLIER[row['product category']]
            
            # Calculate the subtotal
            subtotal = receivable_after_discount + commission
            
            # Calculate the withholding
            withholding = 0.03 * subtotal if not row['tax verified'] else 0.0
            
            # Calculate the total receivables
            total_receivable = subtotal - withholding
            
            # Add the result to the list
            total_receivables.append({
                'total_receivables': total_receivable
            })
    
    return total_receivables
