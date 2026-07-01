import csv

def process_calculations(csv_path):
    PRODUCT_RATES = {
        1: {"individual": 1000, "corporate": 900},
        2: {"individual": 1500, "corporate": 1200},
        3: {"individual": 2000, "corporate": 1700},
    }
    CATEGORY_MULTIPLIER = {"electronics": 1.2, "groceries": 0.8, "luxury": 1.5}

    def process_row(row):
        productid = int(row['productid'].strip())
        status = row['status'].strip().lower()
        volume = int(row['volume'].strip()) if row['volume'].strip() else 0
        season = row['season'].strip().lower()
        customer = row['customer'].strip().lower()
        region = row['region'].strip().lower()
        payment_type = row['payment type'].strip().lower()
        transaction_type = row['transaction type'].strip().lower()
        product_category = row['product category'].strip().lower()
        tax_verified = row['tax verified'].strip().lower() if row['tax verified'].strip() else "no"

        rate = PRODUCT_RATES[productid][status]
        receivable_before_discount = volume * rate

        spring_rate = 0.05 if season == "spring" else 0.0
        volume_rate = 0.05 if volume >= 100 else 0.0
        volume_rate += 0.05 if volume >= 1000 else 0.0

        strategic_rate = 0.05 if customer == "strategic" else 0.0

        total_discount_rate = spring_rate + volume_rate + strategic_rate
        receivable_after_discount = receivable_before_discount * (1 - total_discount_rate)

        region_loading = 0.10 * receivable_after_discount if region == "emea" else 0.0
        payment_loading = 0.025 * receivable_after_discount if payment_type == "credit-card" else 0.0

        multiplier = CATEGORY_MULTIPLIER[product_category]
        commission = (region_loading + payment_loading) * multiplier

        subtotal = receivable_after_discount + commission
        withholding = 0.03 * subtotal if tax_verified == "no" else 0.0
        total_receivables = subtotal - withholding

        return {'total_receivables': total_receivables}

    with open(csv_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        return [process_row(row) for row in reader]

# Example usage:
# results = process_calculations('input.csv')
# for result in results:
#     print(result)
