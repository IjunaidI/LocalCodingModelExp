import csv

def process_calculations(csv_path):
    PRODUCT_RATES = {
        1: {"individual": 1000, "corporate": 900},
        2: {"individual": 1500, "corporate": 1200},
        3: {"individual": 2000, "corporate": 1700},
    }
    CATEGORY_MULTIPLIER = {"electronics": 1.2, "groceries": 0.8, "luxury": 1.5}

    def calculate_total_receivables(row):
        productid = int(row['productid'].strip())
        status = row['status'].strip().lower()
        volume = int(row['volume'].strip())
        season = row['season'].strip().lower()
        customer = row['customer'].strip().lower()
        region = row['region'].strip().lower()
        payment_type = row['payment type'].strip().lower()
        transaction_type = row['transaction type'].strip().lower()
        product_category = row['product category'].strip().lower()
        tax_verified = row['tax verified'].strip().lower()

        base_receivable = volume * PRODUCT_RATES[productid][status]

        spring_rate = 0.05 if season == "spring" else 0.0
        volume_rate = 0.05 if volume >= 100 else 0.0
        volume_rate += 0.05 if volume >= 1000 else 0.0
        strategic_rate = 0.05 if customer == "strategic" else 0.0

        discount_rate = spring_rate + volume_rate + strategic_rate
        receivable_after_discount = base_receivable * (1 - discount_rate)

        region_loading = 0.10 * receivable_after_discount if region == "emea" else 0.0
        payment_loading = 0.025 * receivable_after_discount if payment_type == "credit-card" else 0.0

        commission = (region_loading + payment_loading) * CATEGORY_MULTIPLIER[product_category]

        subtotal = receivable_after_discount + commission
        withholding = 0.03 * subtotal if tax_verified == "no" else 0.0

        total_receivables = subtotal - withholding
        return {
            "total_receivables": total_receivables
        }

    with open(csv_path, mode='r', newline='') as file:
        reader = csv.DictReader(file)
        results = [calculate_total_receivables(row) for row in reader]

    return results
