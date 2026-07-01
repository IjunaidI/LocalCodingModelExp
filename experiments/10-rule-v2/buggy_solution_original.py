# The article's actual 7B "solution_best.py" — architecture right, two killer bugs.
import csv

PRODUCT_RATES = {
    1: {"individual": 1000, "corporate": 900},
    2: {"individual": 1500, "corporate": 1200},
    3: {"individual": 2000, "corporate": 1700},
}

def process_calculations(csv_path):
    results = []
    with open(csv_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            row = {k.strip(): v.strip() for k, v in row.items()}
            row = {k: v if v else None for k, v in row.items()}
            for key in ['volume']:
                if row[key]:
                    row[key] = int(row[key])

            rate = PRODUCT_RATES.get(int(row['productid']), {}).get(row['status'].lower(), 0)
            receivable_before_discount = row['volume'] * rate if rate else 0

            spring_discount = 0.05 if row['season'].lower() == 'spring' else 0
            # BUG 1: both branches yield 0.1 (and <100 never yields 0). Spec is 0/5/10%.
            volume_discount = 0.05 if row['volume'] < 100 else (0.1 if row['volume'] < 1000 else 0.1)
            strategic_discount = 0.05 if row['customer'].lower() == 'strategic' else 0
            total_discount_rate = spring_discount + volume_discount + strategic_discount
            receivable_after_discount = receivable_before_discount * (1 - total_discount_rate)

            region_loading = 0.1 * receivable_after_discount if row['region'].lower() == 'emea' else 0
            payment_loading = 0.025 * receivable_after_discount if row['payment type'].lower() == 'credit-card' else 0
            commission = (region_loading + payment_loading) * 1.2 if row['product category'].lower() == 'electronics' else \
                         (region_loading + payment_loading) * 0.8 if row['product category'].lower() == 'groceries' else \
                         (region_loading + payment_loading) * 1.5 if row['product category'].lower() == 'luxury' else 0

            subtotal = receivable_after_discount + commission
            # BUG 2: the cell is the STRING "False" (truthy), so withholding is skipped when it should apply.
            withholding = 0.03 * subtotal if not row['tax verified'] else 0
            total_receivables = subtotal - withholding

            results.append({'total_receivables': total_receivables})
    return results
