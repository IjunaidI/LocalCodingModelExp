import csv

PRODUCT_RATES = {
    1: {"individual": 1000, "corporate": 900},
    2: {"individual": 1500, "corporate": 1200},
    3: {"individual": 2000, "corporate": 1700},
}
CATEGORY_MULTIPLIER = {"electronics": 1.2, "groceries": 0.8, "luxury": 1.5}

def process_calculations(csv_path):
    total_receivables = []
    
    with open(csv_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Normalize the row
            row = {key.strip(): value.strip().lower() for key, value in row.items()}
            
            # Convert numeric values and handle empty cells
            productid = int(row['productid']) if row['productid'] else None
            volume = int(row['volume']) if row['volume'] else None
            status = row['status']
            season = row['season']
            customer = row['customer']
            region = row['region']
            payment_type = row['payment type']
            transaction_type = row['transaction type']
            product_category = row['product category']
            tax_verified = row['tax verified'] == 'true'
            
            # Calculate the base receivable
            base_receivable = volume * PRODUCT_RATES[productid][status]
            
            # Calculate the discount rates
            spring_rate = 0.05 if season == "spring" else 0.0
            volume_rate = 0.0
            if volume < 100:
                volume_rate = 0.0
            elif volume < 1000:
                volume_rate = 0.05
            else:
                volume_rate = 0.10
            
            # Calculate the strategic rate
            strategic_rate = 0.05 if customer == "strategic" else 0.0
            
            # Calculate the receivable after discount
            discount_rate = spring_rate + volume_rate + strategic_rate
            receivable_after_discount = base_receivable * (1 - discount_rate)
            
            # Calculate the region loading
            region_loading = 0.10 * receivable_after_discount if region == "emea" else 0.0
            
            # Calculate the payment loading
            payment_loading = 0.025 * receivable_after_discount if payment_type == "credit-card" else 0.0
            
            # Calculate the commission
            commission = (region_loading + payment_loading) * CATEGORY_MULTIPLIER[product_category]
            
            # Calculate the subtotal
            subtotal = receivable_after_discount + commission
            
            # Calculate the withholding
            withholding = 0.03 * subtotal if not tax_verified else 0.0
            
            # Calculate the total receivables
            total_receivables.append({
                "total_receivables": subtotal - withholding
            })
    
    return total_receivables
