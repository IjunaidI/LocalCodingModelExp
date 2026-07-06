"""
A passing reference solution written ONLY from spec_30.md (not from reference_30.py).

If this scores a full pass via prove_30.py, the spec is sufficient — a reader can produce
correct code from the spec alone. That is the pre-condition for handing the spec to the
model. This mirrors 10-rule-v2/model_solution_v2.py.
"""

import csv

PRODUCT_RATES = {
    "1": {"individual": 1000, "corporate": 900},
    "2": {"individual": 1500, "corporate": 1200},
    "3": {"individual": 2000, "corporate": 1700},
}
CATEGORY_MULTIPLIER = {"electronics": 1.2, "groceries": 0.8, "luxury": 1.5}
ZONE_LOADING = {"domestic": 0.05, "international": 0.08, "cross-border": 0.10}
SPEED_PREMIUM = {"same-day": 0.15, "next-day": 0.10, "standard": 0.0}
QUARTER_LOADING = {"q1": 0.02, "q2": 0.0, "q3": 0.0, "q4": -0.01}
CAPITAL_CITIES = {"karachi", "lahore", "islamabad", "peshawar", "quetta"}


def _to_num(v, default=0.0):
    try:
        return float(str(v).strip())
    except (ValueError, AttributeError, TypeError):
        return default


def process_calculations(csv_path):
    results = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            row = {(k.strip() if k else k): (v.strip() if isinstance(v, str) else v)
                   for k, v in raw.items()}

            def txt(key):
                return str(row.get(key, "")).strip().lower()

            productid = str(row.get("productid", "")).strip()
            status = txt("status")
            volume = _to_num(row.get("volume"))
            seller_years = _to_num(row.get("seller years"))

            # 1-2
            rate = PRODUCT_RATES[productid][status]
            receivable_before_discount = volume * rate

            # 3-6
            spring_rate = 0.05 if txt("season") == "spring" else 0.0
            volume_rate = 0.0
            if volume >= 100:
                volume_rate += 0.05
            if volume >= 1000:
                volume_rate += 0.05
            strategic_rate = 0.05 if txt("customer") == "strategic" else 0.0
            if seller_years >= 5:
                loyalty_status, loyalty_rate = "platinum", 0.15
            elif seller_years >= 2:
                loyalty_status, loyalty_rate = "gold", 0.10
            else:
                loyalty_status, loyalty_rate = "none", 0.0

            # 7
            total_discount_rate = spring_rate + volume_rate + strategic_rate + loyalty_rate
            receivable_after_discount = receivable_before_discount * (1 - total_discount_rate)

            # 8-12
            region_loading = 0.10 * receivable_after_discount if txt("region") == "emea" else 0.0
            payment_loading = 0.025 * receivable_after_discount if txt("payment type") == "credit-card" else 0.0
            quarter_loading = QUARTER_LOADING.get(txt("quarter"), 0.0) * receivable_after_discount
            zone_loading = ZONE_LOADING.get(txt("transaction type"), 0.0) * receivable_after_discount
            speed_loading = SPEED_PREMIUM.get(txt("processing speed"), 0.0) * receivable_after_discount

            # 13-16
            base_commission_total = (region_loading + payment_loading + quarter_loading
                                     + zone_loading + speed_loading)
            adjusted_commission_total = base_commission_total * CATEGORY_MULTIPLIER.get(
                txt("product category"), 1.0)
            if txt("is high risk") == "yes":
                adjusted_commission_total = adjusted_commission_total * (1 - 0.015)
            if txt("referral active") == "yes" and _to_num(row.get("referral invoices remaining")) > 0:
                adjusted_commission_total = adjusted_commission_total * (1 + 0.0025)

            # 17-20
            correction_fee = 5.0 if txt("requires correction") == "yes" else 0.0
            minimum_transaction_fee = 2.50 if (receivable_after_discount
                                               + adjusted_commission_total) < 50 else 0.0
            pre_withholding_total = (receivable_after_discount + adjusted_commission_total
                                     + correction_fee + minimum_transaction_fee)
            tax_withholding_amount = 0.0
            if txt("tax verified") != "yes":  # "no" or empty
                tax_withholding_amount = 0.03 * pre_withholding_total
            total_receivables = pre_withholding_total - tax_withholding_amount

            # 22-31 — final discounts (all multiplicative)
            city = txt("city")
            category = txt("product category")
            if city in CAPITAL_CITIES:
                total_receivables *= (1 - 0.10)
            if txt("senior citizen") == "yes":
                total_receivables *= (1 - 0.02)
            if txt("first order") == "yes":
                total_receivables *= (1 - 0.05)
            if category == "luxury":
                total_receivables *= (1 - 0.04)
            if _to_num(row.get("weight")) > 20:
                total_receivables *= (1 - 0.03)
            if (txt("customer") == "strategic" and loyalty_status == "platinum"
                    and volume >= 1000 and correction_fee == 0.0):
                total_receivables *= (1 - 0.07)
            if (txt("season") == "spring" and category == "luxury"
                    and txt("processing speed") == "same-day"):
                total_receivables *= (1 - 0.06)
            if (status == "corporate" and city in CAPITAL_CITIES
                    and txt("payment type") != "credit-card" and txt("tax verified") == "yes"):
                total_receivables *= (1 - 0.04)
            if (txt("transaction type") == "international" and txt("customer") == "strategic"
                    and txt("first order") != "yes" and volume > 5000):
                total_receivables *= (1 - 0.08)
            if (loyalty_status == "platinum" and txt("referral active") == "yes"
                    and txt("is high risk") != "yes" and txt("tax verified") == "yes"):
                total_receivables *= (1 - 0.05)

            # 32
            escrow = 0.01 * receivable_before_discount

            results.append({
                "loyalty_status": loyalty_status,
                "receivable_before_discount": receivable_before_discount,
                "receivable_after_discount": receivable_after_discount,
                "base_commission_total": base_commission_total,
                "adjusted_commission_total": adjusted_commission_total,
                "correction_fee": correction_fee,
                "tax_withholding_amount": tax_withholding_amount,
                "total_receivables": total_receivables,
                "escrow": escrow,
            })
    return results
