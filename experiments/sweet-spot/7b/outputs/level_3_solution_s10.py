import csv

def process_calculations(csv_path):
    results = []
    with open(csv_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            row = {key.strip(): value.strip().lower() for key, value in row.items()}
            productid = int(row['productid'])
            volume = int(row.get('volume', 0))
            customer = row['customer']
            region = row['region']
            payment_type = row['payment type']
            product_category = row['product category']
            tax_verified = row.get('tax verified', 'no').lower()

            # Calculate per-unit price
            if productid == 1:
                per_unit_price = 1000 if row['status'] == 'individual' else 900
            elif productid == 2:
                per_unit_price = 1500 if row['status'] == 'individual' else 1200
            elif productid == 3:
                per_unit_price = 2000 if row['status'] == 'individual' else 1700

            # Calculate base receivable
            base_receivable = volume * per_unit_price

            # Calculate discounts
            discount = 0
            if row['season'] == 'spring':
                discount += 0.05
            if volume >= 100:
                discount += 0.05
            if volume >= 1000:
                discount += 0.05
            if row['customer'] == 'strategic':
                discount += 0.05

            # Calculate receivable after discount
            receivable_after_discount = base_receivable * (1 - discount)

            # Calculate surcharges
            surcharge_region = 0.10 if region == 'emea' else 0
            surcharge_payment_type = 0.025 if payment_type == 'credit-card' else 0
            commission = (surcharge_region + surcharge_payment_type) * receivable_after_discount * {
                'electronics': 1.2,
                'groceries': 0.8,
                'luxury': 1.5
            }[product_category]

            # Calculate subtotal
            subtotal = receivable_after_discount + commission

            # Calculate withholding
            withholding = 0 if tax_verified == 'yes' else 0.03 * subtotal

            # Calculate total receivables
            total_receivables = subtotal - withholding

            results.append({'total_receivables': total_receivables})
    return results
