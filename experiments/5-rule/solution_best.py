import csv
import re

PRODUCT_RATES = {
    1: {"individual": 1000, "corporate": 900},
    2: {"individual": 1500, "corporate": 1200},
    3: {"individual": 2000, "corporate": 1700},
}

def process_calculations(csv_path):
    try:
        with open(csv_path, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            headers = [re.sub(r'\s+', '', header).strip() for header in reader.fieldnames]
            rows = []

            for row in reader:
                productid = int(row.get('productid', 0))
                status = row.get('status', '').lower()
                volume = int(row.get('volume', 0))
                season = row.get('season', '').lower()
                customer = row.get('customer', '').lower()
                tax_verified = row.get('tax verified', '').lower()

                rate = PRODUCT_RATES.get(productid, {}).get(status, 0)
                base = volume * rate

                if season == 'spring':
                    base *= 0.95
                if customer == 'strategic':
                    base *= 0.95

                if tax_verified == 'no':
                    base *= 0.97

                total_receivables = base
                rows.append({'total_receivables': total_receivables})

        return rows
    except FileNotFoundError:
        return []
    except ValueError:
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

# Example usage:
# result = process_calculations('path_to_your_csv.csv')
# print(result)
