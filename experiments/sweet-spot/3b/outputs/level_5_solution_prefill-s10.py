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
            # Normalize the row
            row = {key.strip(): value.strip().lower() for key, value in row.items()}
            
            # Convert numeric fields
            row['volume'] = int(row['volume']) if row['volume'] else 0
            
            # Apply discounts and surcharges
            product_id = int(row['productid'])
            status = row['status']
            season = row['season']
            customer = row['customer']
            region = row['region']
            payment_type = row['payment type']
            product_category = row['product category']
            tax_verified = row['tax verified']
            
            # Calculate per-unit price
            per_unit_price = PRODUCT_RATES[product_id][status]
            
            # Calculate base receivable
            base_receivable = row['volume'] * per_unit_price
            
            # Apply volume discount
            if row['volume'] < 100:
                volume_discount = 0
            elif row['volume'] < 1000:
                volume_discount = 0.05
            else:
                volume_discount = 0.10
            
            # Calculate base receivable after volume discount
            base_receivable_after_volume_discount = base_receivable * (1 - volume_discount)
            
            # Apply additional 5% discount if season is spring
            additional_discount = 0.05 if season == 'spring' else 0
            receivable_after_discount = base_receivable_after_volume_discount * (1 - additional_discount)
            
            # Apply surcharges
            region_surcharge = 0.10 if region == 'emea' else 0
            payment_type_surcharge = 0.025 if payment_type == 'credit-card' else 0
            subtotal = receivable_after_discount * (1 + region_surcharge + payment_type_surcharge)
            
            # Calculate commission
            commission = subtotal * (CATEGORY_MULTIPLIER[product_category])
            
            # Calculate total receivables after withholding
            withholding = subtotal * 0.03 if not tax_verified else 0
            total_receivables = subtotal - withholding
            
            # Add the result to the list
            results.append({
                'total_receivables': total_receivables
            })
    
    return results
