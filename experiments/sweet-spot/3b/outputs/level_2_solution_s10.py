import csv

def process_calculations(csv_path):
    PRODUCT_RATES = {
        1: {"individual": 1000, "corporate": 900},
        2: {"individual": 1500, "corporate": 1200},
        3: {"individual": 2000, "corporate": 1700},
    }
    CATEGORY_MULTIPLIER = {"electronics": 1.2, "groceries": 0.8, "luxury": 1.5}

    def process_row(row):
        # Normalize the row
        row = {key.strip(): value.strip().lower() for key, value in row.items()}
        
        # Convert to numbers and handle empty cells
        row['volume'] = int(row['volume']) if row['volume'] else 0
        row['productid'] = int(row['productid'])
        row['status'] = row['status'].lower()
        row['season'] = row['season'].lower()
        row['customer'] = row['customer'].lower()
        row['region'] = row['region'].lower()
        row['payment type'] = row['payment type'].lower()
        row['transaction type'] = row['transaction type'].lower()
        row['product category'] = row['product category'].lower()
        row['tax verified'] = row['tax verified'].lower()

        # Calculate the base receivable
        base_receivable = row['volume'] * PRODUCT_RATES[row['productid']][row['status']]

        # Calculate the discount rates
        spring_rate = 0.05 if row['season'] == 'spring' else 0.0
        volume_rate = 0.05 * (1 if row['volume'] >= 100 else 0) + 0.05 * (1 if row['volume'] >= 1000 else 0)
        strategic_rate = 0.05 if row['customer'] == 'strategic' else 0.0
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
        withholding = 0.03 * subtotal if row['tax verified'] == 'no' else 0.0

        # Calculate total receivables
        total_receivables = subtotal - withholding

        return {'total_receivables': total_receivables}

    with open(csv_path, mode='r', newline='') as file:
        reader = csv.DictReader(file)
        results = [process_row(row) for row in reader]

    return results
