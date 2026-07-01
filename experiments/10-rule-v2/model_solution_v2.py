import csv

PRODUCT_RATES = {
    1: {"individual": 1000, "corporate": 900},
    2: {"individual": 1500, "corporate": 1200},
    3: {"individual": 2000, "corporate": 1700},
}

CATEGORY_MULTIPLIER = {
    "electronics": 1.2,
    "groceries": 0.8,
    "luxury": 1.5,
}


def process_calculations(csv_path):
    results = []
    with open(csv_path, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for raw in reader:
            row = {k.strip(): (v.strip() if v else "") for k, v in raw.items()}

            productid = int(row["productid"]) if row["productid"] else 1
            status = row["status"].lower()
            volume = int(row["volume"]) if row["volume"] else 0
            season = row["season"].lower()
            customer = row["customer"].lower()
            region = row["region"].lower()
            payment_type = row["payment type"].lower()
            category = row["product category"].lower()
            tax_verified = row["tax verified"].lower()  # "yes" or "no"

            # 1. Rate
            rate = PRODUCT_RATES[productid][status]

            # 2. Base
            receivable_before_discount = volume * rate

            # 3. Spring discount rate
            spring_rate = 0.0
            if season == "spring":
                spring_rate = 0.05

            # 4. Volume discount rate (two independent checks, no elif)
            volume_rate = 0.0
            if volume >= 100:
                volume_rate += 0.05
            if volume >= 1000:
                volume_rate += 0.05

            # 5. Strategic discount rate
            strategic_rate = 0.0
            if customer == "strategic":
                strategic_rate = 0.05

            # 6. Apply discounts
            total_discount_rate = spring_rate + volume_rate + strategic_rate
            receivable_after_discount = receivable_before_discount * (1 - total_discount_rate)

            # 7. Region loading
            region_loading = 0.0
            if region == "emea":
                region_loading = 0.10 * receivable_after_discount

            # 8. Payment loading
            payment_loading = 0.0
            if payment_type == "credit-card":
                payment_loading = 0.025 * receivable_after_discount

            # 9. Commission
            multiplier = CATEGORY_MULTIPLIER[category]
            commission = (region_loading + payment_loading) * multiplier

            # 10. Tax withholding and total
            subtotal = receivable_after_discount + commission
            withholding = 0.0
            if tax_verified == "no" or tax_verified == "":
                withholding = 0.03 * subtotal
            total_receivables = subtotal - withholding

            results.append({"total_receivables": total_receivables})
    return results
