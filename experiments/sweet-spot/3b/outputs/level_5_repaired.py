import csv

def process_calculations(csv_path):
    def calculate_receivable(row):
        # Constants
        product_prices = {
            1: {"individual": 1000, "corporate": 900},
            2: {"individual": 1500, "corporate": 1200},
            3: {"individual": 2000, "corporate": 1700}
        }
        discounts = {
            "spring": 0.05,
            "strategic": 0.05
        }
        surcharges = {
            "emea": 0.10,
            "credit-card": 0.025
        }
        commission_factors = {
            "electronics": 1.2,
            "groceries": 0.8,
            "luxury": 1.5
        }
        
        # Parse input values
        productid = int(row['productid'].strip())
        status = row['status'].strip().lower()
        volume = int(row['volume'].strip())
        season = row['season'].strip().lower()
        customer = row['customer'].strip().lower()
        region = row['region'].strip().lower()
        payment_type = row['payment type'].strip().lower()
        product_category = row['product category'].strip().lower()
        tax_verified = row['tax verified'].strip().lower() == 'true'
        
        # Calculate base receivable
        per_unit_price = product_prices[productid][status]
        base_receivable = volume * per_unit_price
        
        # Calculate volume discount
        if volume < 100:
            volume_discount = 0
        elif volume < 1000:
            volume_discount = 0.05
        else:
            volume_discount = 0.10
        
        # Calculate total discount rate
        total_discount_rate = discounts.get(season, 0) + volume_discount + discounts.get(customer, 0)
        
        # Calculate receivable after discount
        receivable_after_discount = base_receivable * (1 - total_discount_rate)
        
        # Calculate surcharges
        region_surcharge = receivable_after_discount * surcharges.get(region, 0)
        payment_type_surcharge = receivable_after_discount * surcharges.get(payment_type, 0)
        
        # Calculate commission
        commission = (region_surcharge + payment_type_surcharge) * commission_factors.get(product_category, 1)
        
        # Calculate subtotal
        subtotal = receivable_after_discount + commission
        
        # Calculate withholding
        withholding = subtotal * 0.03 if not tax_verified else 0
        
        # Calculate total receivables
        total_receivables = subtotal - withholding
        
        # Return the result with intermediate values
        return {
            "total_receivables": total_receivables,
            "rate": total_discount_rate,
            "receivable_before_discount": base_receivable,
            "spring_rate": discounts.get(season, 0),
            "volume_rate": volume_discount,
            "strategic_rate": discounts.get(customer, 0),
            "receivable_after_discount": receivable_after_discount,
            "region_loading": region_surcharge,
            "payment_loading": payment_type_surcharge,
            "commission": commission,
            "subtotal": subtotal,
            "withholding": withholding
        }
    
    results = []
    with open(csv_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            result = calculate_receivable(row)
            results.append(result)
    
    return results
