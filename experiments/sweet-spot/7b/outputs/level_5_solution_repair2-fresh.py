import csv

def process_calculations(csv_path):
    with open(csv_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        results = []
        for row in reader:
            row = {key.strip(): value.strip().lower() for key, value in row.items()}
            productid = int(row['productid'])
            status = row['status']
            volume = int(row['volume'])
            season = row['season']
            customer = row['customer']
            region = row['region']
            payment_type = row['payment type']
            transaction_type = row['transaction type']
            product_category = row['product category']
            tax_verified = row['tax verified'] == 'true' if row['tax verified'] else False

            # Calculate rate
            if productid == 1:
                rate = 1000 if status == 'individual' else 900
            elif productid == 2:
                rate = 1500 if status == 'individual' else 1200
            elif productid == 3:
                rate = 2000 if status == 'individual' else 1700

            # Calculate receivable before discount
            receivable_before_discount = volume * rate

            # Calculate spring_rate
            spring_rate = 0.05 if season == 'spring' else 0.0

            # Calculate volume_rate
            if volume < 100:
                volume_rate = 0.0
            elif volume < 1000:
                volume_rate = 0.05
            else:
                volume_rate = 0.1

            # Calculate strategic_rate
            strategic_rate = 0.05 if customer == 'strategic' else 0.0

            # Calculate total_discount_rate
            total_discount_rate = spring_rate + volume_rate + strategic_rate

            # Calculate receivable after discount
            receivable_after_discount = receivable_before_discount * (1 - total_discount_rate)

            # Calculate region_loading and payment_loading
            region_loading = 0.1 if region == 'emea' else 0.0
            payment_loading = 0.025 if payment_type == 'credit-card' else 0.0

            # Calculate commission
            commission = (region_loading + payment_loading) * receivable_after_discount * {
                'electronics': 1.2,
                'groceries': 0.8,
                'luxury': 1.5
            }[product_category]

            # Calculate subtotal
            subtotal = receivable_after_discount + commission

            # Calculate withholding
            withholding = 0.03 * subtotal if not tax_verified else 0.0

            # Calculate total_receivables
            total_receivables = subtotal - withholding

            results.append({
                'rate': rate,
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
