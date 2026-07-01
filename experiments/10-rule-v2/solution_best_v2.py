import csv
import re

def process_calculations(csv_path):
    # Define lookup tables
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

    # Read CSV and process each row
    results = []
    with open(csv_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Strip spaces from header names and cell values
            row = {k.strip(): v.strip() for k, v in row.items()}
            
            # Convert numeric strings to numbers
            row['volume'] = int(row['volume']) if row['volume'].isdigit() else 0
            row['productid'] = int(row['productid']) if row['productid'].isdigit() else 0
            
            # Convert text fields to lower case
            row['status'] = row['status'].lower()
            row['season'] = row['season'].lower()
            row['customer'] = row['customer'].lower()
            row['region'] = row['region'].lower()
            row['payment type'] = row['payment type'].lower()
            row['transaction type'] = row['transaction type'].lower()
            row['product category'] = row['product category'].lower()
            row['tax verified'] = row['tax verified'].lower() if row['tax verified'] else 'no'
            
            # Apply rules
            rate = PRODUCT_RATES[row['productid']][row['status']]
            receivable_before_discount = row['volume'] * rate
            
            spring_rate = 0.05 if row['season'] == 'spring' else 0.0
            volume_rate = 0.05 if row['volume'] >= 100 else 0.0
            volume_rate += 0.05 if row['volume'] >= 1000 else 0.0
            strategic_rate = 0.05 if row['customer'] == 'strategic' else 0.0
            
            total_discount_rate = spring_rate + volume_rate + strategic_rate
            receivable_after_discount = receivable_before_discount * (1 - total_discount_rate)
            
            region_loading = 0.10 * receivable_after_discount if row['region'] == 'emea' else 0.0
            payment_loading = 0.025 * receivable_after_discount if row['payment type'] == 'credit-card' else 0.0
            
            multiplier = CATEGORY_MULTIPLIER[row['product category']]
            commission = (region_loading + payment_loading) * multiplier
            
            subtotal = receivable_after_discount + commission
            withholding = 0.03 * subtotal if row['tax verified'] == 'no' else 0.0
            total_receivables = subtotal - withholding
            
            # Append result to list
            results.append({'total_receivables': total_receivables})
    
    return results
