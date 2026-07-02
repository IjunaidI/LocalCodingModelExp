import csv

def process_calculations(csv_path):
    with open(csv_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        results = []
        for row in reader:
            row = {key.strip(): value.strip().lower() for key, value in row.items()}
            productid = int(row['productid'])
            volume = int(row['volume']) if row['volume'] else 0
            status = row['status']
            season = row['season']
            customer = row['customer']
            region = row['region']
            payment_type = row['payment type']
            transaction_type = row['transaction type']
            product_category = row['product category']
            tax_verified = True if row['tax verified'] == 'true' else False
            
            # Calculate per-unit price
            if productid == 1:
                per_unit_price = 1000 if status == 'individual' else 900
            elif productid == 2:
                per_unit_price = 1500 if status == 'individual' else 1200
            elif productid == 3:
                per_unit_price = 2000 if status == 'individual' else 1700
            
            # Calculate base receivable
            base_receivable = volume * per_unit_price
            
            # Calculate discounts
            discounts = 0
            if season == 'spring':
                discounts += 0.05 * base_receivable
            if volume >= 1000:
                discounts += 0.10 * base_receivable
            elif volume >= 100:
                discounts += 0.05 * base_receivable
            if customer == 'strategic':
                discounts += 0.05 * base_receivable
            
            receivable_after_discount = base_receivable - discounts
            
            # Calculate surcharges
            surcharges = 0
            if region == 'emea':
                surcharges += 0.10 * receivable_after_discount
            if payment_type == 'credit-card':
                surcharges += 0.025 * receivable_after_discount
            
            commission = surcharges * (1.2 if product_category == 'electronics' else 0.8 if product_category == 'groceries' else 1.5)
            
            subtotal = receivable_after_discount + commission
            
            # Calculate withholding
            withholding = 0 if tax_verified else 0.03 * subtotal
            
            total_receivables = subtotal - withholding
            
            results.append({'total_receivables': total_receivables})
    
    return results
