import csv

def process_calculations(csv_path):
    with open(csv_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        results = []
        for row in reader:
            row = {key.strip(): value.strip().lower() for key, value in row.items()}
            productid = int(row['productid'])
            volume = int(row.get('volume', 0))
            status = row['status']
            season = row['season']
            customer = row['customer']
            region = row['region']
            payment_type = row['payment type']
            transaction_type = row['transaction type']
            product_category = row['product category']
            tax_verified = row.get('tax verified', 'no').lower()
            
            # Pricing
            if productid == 1:
                per_unit_price = 1000 if status == 'individual' else 900
            elif productid == 2:
                per_unit_price = 1500 if status == 'individual' else 1200
            elif productid == 3:
                per_unit_price = 2000 if status == 'individual' else 1700
            
            base_receivable = volume * per_unit_price
            
            # Discounts
            discount = 0
            if season == 'spring':
                discount += 0.05
            if 100 <= volume < 1000:
                discount += 0.05
            elif volume >= 1000:
                discount += 0.10
            if customer == 'strategic':
                discount += 0.05
            
            receivable_after_discount = base_receivable * (1 - discount)
            
            # Surcharges
            surcharge_region = 0.10 if region == 'emea' else 0
            surcharge_payment = 0.025 if payment_type == 'credit-card' else 0
            commission = (surcharge_region + surcharge_payment) * {
                'electronics': 1.2,
                'groceries': 0.8,
                'luxury': 1.5
            }[product_category]
            
            subtotal = receivable_after_discount * (1 + commission)
            
            # Withholding
            withholding = 0 if tax_verified == 'yes' else 0.03 * subtotal
            
            total_receivables = subtotal - withholding
            
            results.append({'total_receivables': total_receivables})
    
    return results
