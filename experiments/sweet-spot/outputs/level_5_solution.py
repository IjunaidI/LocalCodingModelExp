import csv

def process_calculations(csv_path):
    def calculate_receivable(row):
        productid = int(row['productid'])
        status = row['status'].strip()
        volume = int(row['volume'])
        season = row['season'].strip()
        customer = row['customer'].strip()
        region = row['region'].strip()
        payment_type = row['payment type'].strip()
        product_category = row['product category'].strip()
        tax_verified = row['tax verified'] == 'True'

        # Calculate per-unit price
        if productid == 1:
            per_unit_price = 1000 if status == 'individual' else 900
        elif productid == 2:
            per_unit_price = 1500 if status == 'individual' else 1200
        elif productid == 3:
            per_unit_price = 2000 if status == 'individual' else 1700
        else:
            raise ValueError(f"Invalid productid: {productid}")

        # Calculate base receivable
        base_receivable = volume * per_unit_price

        # Calculate discounts
        total_discount = 0
        if season == 'spring':
            total_discount += 0.05
        if 100 < volume < 1000:
            total_discount += 0.05
        elif volume >= 1000:
            total_discount += 0.10
        if customer == 'strategic':
            total_discount += 0.05

        # Apply combined discount
        receivable_after_discount = base_receivable * (1 - total_discount)

        # Calculate surcharges
        surcharge_region = 0.10 if region == 'emea' else 0
        surcharge_payment_type = 0.025 if payment_type == 'credit-card' else 0
        total_surcharges = surcharge_region + surcharge_payment_type

        # Calculate commission
        commission = total_surcharges * {
            'electronics': 1.2,
            'groceries': 0.8,
            'luxury': 1.5
        }.get(product_category, 1)

        # Calculate subtotal
        subtotal = receivable_after_discount + commission

        # Calculate withholding
        withholding = subtotal * 0.03 if not tax_verified else 0

        # Calculate total receivables
        total_receivables = subtotal - withholding

        return {
            'total_receivables': total_receivables
        }

    with open(csv_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        return [calculate_receivable(row) for row in reader]
