import csv

PRODUCT_RATES = {
    1: {"individual": 1000, "corporate": 900},
    2: {"individual": 1500, "corporate": 1200},
    3: {"individual": 2000, "corporate": 1700},
}
CATEGORY_MULTIPLIER = {"electronics": 1.2, "groceries": 0.8, "luxury": 1.5}


def process_calculations(csv_path):
    results = []

    with open(csv_path, mode='r', newline='') as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Normalize and convert values
            row = {key.strip(): value.strip().lower() for key, value in row.items()}
            row['volume'] = int(row['volume']) if row['volume'] else 0
            row['productid'] = int(row['productid'])

            # Calculate per-unit price
            per_unit_price = PRODUCT_RATES[row['productid']][row['status']]

            # Calculate base receivable
            base_receivable = row['volume'] * per_unit_price

            # Calculate discounts
            discounts = 0
            if row['season'] == 'spring':
                discounts += 0.05
            if row['volume'] >= 1000:
                discounts += 0.05
            if row['volume'] >= 100:
                discounts += 0.05
            if row['customer'] == 'strategic':
                discounts += 0.05

            # Calculate receivable after discount
            receivable_after_discount = base_receivable * (1 - discounts)

            # Calculate surcharges
            surcharges = 0
            if row['region'] == 'emea':
                surcharges += 0.10
            if row['payment type'] == 'credit-card':
                surcharges += 0.025

            # Calculate commission
            commission = surcharges * CATEGORY_MULTIPLIER[row['product category']]

            # Calculate subtotal
            subtotal = receivable_after_discount + commission

            # Calculate withholding
            withholding = 0
            if row['tax verified'] == 'no':
                withholding = subtotal * 0.03

            # Calculate total receivables
            total_receivables = subtotal - withholding

            # Add result to results list
            results.append({
                'total_receivables': total_receivables
            })

    return results
