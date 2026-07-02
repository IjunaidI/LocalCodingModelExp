import csv

def process_calculations(csv_path):
    results = []
    with open(csv_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            row = {key.strip(): value.strip().lower() for key, value in row.items()}
            productid = int(row['productid'])
            volume = int(row.get('volume', 0))
            season = row['season']
            customer = row['customer']
            region = row['region']
            payment_type = row['payment type']
            product_category = row['product category']
            tax_verified = row.get('tax verified', 'no')

            # Calculate receivable before discount
            if productid == 1:
                per_unit_price = 1000 if row['status'] == 'individual' else 900
            elif productid == 2:
                per_unit_price = 1500 if row['status'] == 'individual' else 1200
            elif productid == 3:
                per_unit_price = 2000 if row['status'] == 'individual' else 1700
            receivable_before_discount = volume * per_unit_price

            # Calculate spring rate
            spring_rate = 0.05 if season == 'spring' else 0

            # Calculate volume rate
            if volume >= 1000:
                volume_rate = 0.10
            elif volume >= 100:
                volume_rate = 0.05
            else:
                volume_rate = 0

            # Calculate strategic rate
            strategic_rate = 0.05 if customer == 'strategic' else 0

            # Calculate total discount rate
            total_discount_rate = spring_rate + volume_rate + strategic_rate

            # Calculate receivable after discount
            receivable_after_discount = receivable_before_discount * (1 - total_discount_rate)

            # Calculate region loading
            region_loading = 0.10 if region == 'emea' else 0

            # Calculate payment loading
            payment_loading = 0.025 if payment_type == 'credit-card' else 0

            # Calculate commission
            commission = (region_loading + payment_loading) * receivable_after_discount * {
                'electronics': 1.2,
                'groceries': 0.8,
                'luxury': 1.5
            }[product_category]

            # Calculate subtotal
            subtotal = receivable_after_discount + commission

            # Calculate withholding
            withholding = 0.03 * subtotal if tax_verified == 'no' else 0

            # Calculate total receivables
            total_receivables = subtotal - withholding

            # Append the result with intermediate values
            results.append({
                'rate': receivable_after_discount,
                'receivable_before_discount': receivable_before_discount,
                'spring_rate': spring_rate,
                'volume_rate': volume_rate,
                'strategic_rate': strategic_rate,
                'total_discount_rate': total_discount_rate,
                'receivable_after_discount': receivable_after_discount,
                'region_loading': region_loading,
                'payment_loading': payment_loading,
                'commission': commission,
                'subtotal': subtotal,
                'withholding': withholding,
                'total_receivables': total_receivables
            })

    return results
