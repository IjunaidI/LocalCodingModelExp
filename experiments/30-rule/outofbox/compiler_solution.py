CAPS = {'lahore', 'karachi', 'quetta', 'islamabad', 'peshawar'}

def product_rate(productid, status):
    """productid is the text "1","2","3"; status is "individual" or "corporate". Return the unit rate from this table: product "1" is 1000 for individual and 900 for corporate; product "2" is 1500 for individual and 1200 for corporate; product "3" is 2000 for individual and 1700 for corporate."""
    if productid == "1":
        if status == "individual":
            return 1000
        elif status == "corporate":
            return 900
    elif productid == "2":
        if status == "individual":
            return 1500
        elif status == "corporate":
            return 1200
    elif productid == "3":
        if status == "individual":
            return 2000
        elif status == "corporate":
            return 1700
    else:
        return "Invalid product id"

def spring_rate(season):
    """Return 0.05 if season == "spring", else 0.0."""
    return 0.05 if season == "spring" else 0.0

def volume_rate(volume):
    """Return 0.0 if volume < 100, 0.05 if 100 <= volume < 1000, 0.10 if volume >= 1000."""
    if volume < 100:
        return 0.0
    elif 100 <= volume < 1000:
        return 0.05
    else:
        return 0.10

def strategic_rate(customer):
    """Return 0.05 if customer == "strategic", else 0.0."""
    return 0.05 if customer == "strategic" else 0.0

def loyalty_status(seller_years):
    """Return "platinum" if seller_years >= 5, "gold" if seller_years >= 2, else "none"."""
    if seller_years >= 5:
        return "platinum"
    elif seller_years >= 2:
        return "gold"
    else:
        return "none"

def loyalty_rate(seller_years):
    """Return 0.15 if seller_years >= 5, 0.10 if seller_years >= 2, else 0.0."""
    if seller_years >= 5:
        return 0.15
    elif seller_years >= 2:
        return 0.10
    else:
        return 0.0

def region_loading_rate(region):
    """Return 0.10 if region == "emea", else 0.0."""
    return 0.10 if region == "emea" else 0.0

def payment_loading_rate(payment_type):
    """Return 0.025 if payment_type == "credit-card", else 0.0."""
    return 0.025 if payment_type == "credit-card" else 0.0

def quarter_loading_rate(quarter):
    """quarter is upper-case. Return 0.02 if quarter == "Q1", -0.01 if quarter== "Q4", else 0.0."""
    if quarter == "Q1":
        return 0.02
    elif quarter == "Q4":
        return -0.01
    else:
        return 0.0

def zone_loading_rate(transaction_type):
    """Return 0.05 for domestic, 0.08 for international, 0.10 for cross-border, else 0.0."""
    if transaction_type == "domestic":
        return 0.05
    elif transaction_type == "international":
        return 0.08
    elif transaction_type == "cross-border":
        return 0.10
    else:
        return 0.0

def speed_loading_rate(processing_speed):
    """Return 0.15 for same-day, 0.10 for next-day, 0.0 for standard."""
    if processing_speed == "same-day":
        return 0.15
    elif processing_speed == "next-day":
        return 0.10
    else:
        return 0.0

def category_multiplier(category):
    """Return 1.2 for electronics, 0.8 for groceries, 1.5 for luxury, else 1.0."""
    if category == "electronics":
        return 1.2
    elif category == "groceries":
        return 0.8
    elif category == "luxury":
        return 1.5
    else:
        return 1.0

def risk_fee_rate(is_high_risk):
    """is_high_risk is "yes"/"no". Return 0.015 if it is "yes", else 0.0."""
    return 0.015 if is_high_risk == "yes" else 0.0

def referral_credit_rate(referral_active, remaining):
    """Return 0.0025 if referral_active == "yes" AND remaining > 0, else 0.0."""
    return 0.0025 if referral_active == "yes" and remaining > 0 else 0.0

def correction_fee(requires_correction):
    """Return 5.0 if requires_correction == "yes", else 0.0."""
    return 5.0 if requires_correction == "yes" else 0.0

def min_fee(base_amount):
    """Return 2.50 if base_amount < 50, else 0.0."""
    return 2.50 if base_amount < 50 else 0.0

def _fallback_withhold(tv): return 0.0 if tv == "yes" else 0.03

withholding_rate = _fallback_withhold


def capital_city_rate(city):
    """Return 0.10 if city is one of karachi, lahore, islamabad, peshawar, quetta, else 0.0."""
    return 0.10 if city in ["karachi", "lahore", "islamabad", "peshawar", "quetta"] else 0.0

def senior_rate(senior_citizen):
    """Return 0.02 if senior_citizen == "yes", else 0.0."""
    return 0.02 if senior_citizen == "yes" else 0.0

def first_order_rate(first_order):
    """Return 0.05 if first_order == "yes", else 0.0."""
    return 0.05 if first_order == "yes" else 0.0

def luxury_tax_rate(category):
    """Return 0.04 if category == "luxury", else 0.0."""
    return 0.04 if category == "luxury" else 0.0

def heavy_weight_rate(weight):
    """Return 0.03 if weight > 20, else 0.0."""
    return 0.03 if weight > 20 else 0.0

def accelerator_rate(customer, loyalty_status, volume, correction_fee):
    return 0.07 if customer == "strategic" and loyalty_status == "platinum" and volume >= 1000 and correction_fee == 0.0 else 0.0

def bundle_rate(season, category, processing_speed):
    """Return 0.06 if season == "spring" AND category == "luxury" AND processing_speed == "same-day", else 0.0."""
    return 0.06 if season == "spring" and category == "luxury" and processing_speed == "same-day" else 0.0

def corp_incentive_rate(status, city, payment_type, tax_verified):
    """Return 0.04 if status == "corporate" AND city is a capital city (karachi, lahore, islamabad, peshawar, quetta) AND payment_type != "credit-card" AND tax_verified == "yes", else 0.0."""
    if status == "corporate" and city in ["karachi", "lahore", "islamabad", "peshawar", "quetta"] and payment_type != "credit-card" and tax_verified == "yes":
        return 0.04
    return 0.0

def global_expansion_rate(transaction_type, customer, first_order, volume):
    """Return 0.08 if transaction_type == "international" AND customer == "strategic" AND first_order != "yes" AND volume > 5000, else 0.0."""
    return 0.08 if transaction_type == "international" and customer == "strategic" and first_order != "yes" and volume > 5000 else 0.0

def elite_rate(loyalty_status, referral_active, is_high_risk, tax_verified):
    return 0.05 if loyalty_status == "platinum" and referral_active == "yes" and is_high_risk != "yes" and tax_verified == "yes" else 0.0

def escrow_amount(receivable_before_discount):
    """Return 0.01 * receivable_before_discount."""
    return 0.01 * receivable_before_discount


def process_calculations(csv_path):
    import csv as _csv
    results = []
    with open(csv_path, newline="") as f:
        for raw in _csv.DictReader(f):
            r = {(k.strip() if k else k): (v.strip() if isinstance(v, str) else v) for k, v in raw.items()}
            def t(k): return str(r.get(k, "")).strip()
            def tl(k): return t(k).lower()
            def num(k):
                try: return float(t(k))
                except Exception: return 0.0
            pid = t("productid"); status = tl("status"); customer = tl("customer")
            season = tl("season"); category = tl("product category"); city = tl("city")
            region = tl("region"); pay = tl("payment type"); txn = tl("transaction type")
            speed = tl("processing speed"); quarter = t("quarter").upper()
            volume = num("volume"); years = num("seller years"); weight = num("weight")
            remaining = num("referral invoices remaining")
            hr = tl("is high risk"); corr_flag = tl("requires correction")
            ref = tl("referral active"); senior = tl("senior citizen")
            first = tl("first order"); tax = tl("tax verified")

            rate = product_rate(pid, status)
            rbd = volume * rate
            disc = spring_rate(season) + volume_rate(volume) + strategic_rate(customer) + loyalty_rate(years)
            rad = rbd * (1 - disc)
            base = (region_loading_rate(region) + payment_loading_rate(pay)
                    + quarter_loading_rate(quarter) + zone_loading_rate(txn)
                    + speed_loading_rate(speed)) * rad
            adj = base * category_multiplier(category)
            adj *= (1 - risk_fee_rate(hr))
            adj *= (1 + referral_credit_rate(ref, remaining))
            corr = correction_fee(corr_flag)
            mf = min_fee(rad + adj)
            pre = rad + adj + corr + mf
            total = pre - withholding_rate(tax) * pre
            ls = loyalty_status(years)
            total *= (1 - capital_city_rate(city))
            total *= (1 - senior_rate(senior))
            total *= (1 - first_order_rate(first))
            total *= (1 - luxury_tax_rate(category))
            total *= (1 - heavy_weight_rate(weight))
            total *= (1 - accelerator_rate(customer, ls, volume, corr))
            total *= (1 - bundle_rate(season, category, speed))
            total *= (1 - corp_incentive_rate(status, city, pay, tax))
            total *= (1 - global_expansion_rate(txn, customer, first, volume))
            total *= (1 - elite_rate(ls, ref, hr, tax))
            results.append({"total_receivables": total, "escrow": escrow_amount(rbd)})
    return results
