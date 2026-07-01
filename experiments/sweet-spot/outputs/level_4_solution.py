import csv

def process_calculations(csv_path):
    def calculate_price(productid, status):
        if productid == "1":
            return 1000 if status == "individual" else 900
        elif productid == "2":
            return 1500 if status == "individual" else 1200
        elif productid == "3":
            return 2000 if status == "individual" else 1700

    def calculate_discount(volume, season, customer):
        discount = 0
        if season == "spring":
            discount += 0.05
        if 100 <= volume < 1000:
            discount += 0.05
        elif volume >= 1000:
            discount += 0.10
        if customer == "strategic":
            discount += 0.05
        return discount

    def calculate_receivable(volume, productid, status, season, customer, region, payment_type, product_category, tax_verified):
        price = calculate_price(productid, status)
        base_receivable = volume * price
        discount = calculate_discount(volume, season, customer)
        receivable_after_discount = base_receivable * (1 - discount)
        surcharge_eMEA = 0.10 if region == "emea" else 0
        surcharge_credit_card = 0.025 if payment_type == "credit-card" else 0
        total_receivable = receivable_after_discount + (surcharge_eMEA + surcharge_credit_card) * receivable_after_discount
        commission = (surcharge_eMEA + surcharge_credit_card) * total_receivable
        subtotal = total_receivable + commission
        withholding = 0.03 if tax_verified.lower() == "no" else 0
        total_receivables = subtotal - withholding
        return total_receivables

    results = []
    with open(csv_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            total_receivables = calculate_receivable(
                int(row['volume']),
                row['productid'],
                row['status'],
                row['season'],
                row['customer'],
                row['region'],
                row['payment type'],
                row['product category'],
                row['tax verified']
            )
            results.append({'total_receivables': total_receivables})
    return results
