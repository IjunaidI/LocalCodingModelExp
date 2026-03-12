from dataclasses import dataclass
from pathlib import Path
import pandas as pd


@dataclass
class ProcurementRecord:
    order_id: str
    supplier: str
    category: str
    final_amount: float

    def __init__(self, order_id, supplier, category, final_amount):
        if None in (order_id, supplier, category, final_amount):
            raise TypeError("ProcurementRecord fields cannot be None")

        self.order_id = order_id
        self.supplier = supplier
        self.category = category
        self.final_amount = float(final_amount)


class ProcurementReader:
    def __init__(self, path):
        self.path = Path(path)

    def read(self):
        df = pd.read_excel(self.path)

        records = []
        for _, row in df.iterrows():
            record = ProcurementRecord(
                row["Order_ID"],
                row["Supplier"],
                row["Category"],
                float(row["FINAL AMOUNT"]),
            )
            records.append(record)

        return records

    def total_amount(self):
        df = pd.read_excel(self.path)
        return float(df["FINAL AMOUNT"].astype(float).sum())


def calculate_total_final_amount(file_path):
    df = pd.read_excel(file_path)

    # force numeric conversion (raises error if bad data)
    amounts = pd.to_numeric(df["FINAL AMOUNT"])

    return float(amounts.sum())


def print_total_final_amount(file_path):
    total = calculate_total_final_amount(file_path)
    print(f"Total FINAL AMOUNT: ${total:,.2f}")


def print_file_name(file_path):
    p = Path(file_path)
    print(f"Processing file: {p.name}")


def print_comprehensive_summary(file_path):
    df = pd.read_excel(file_path)

    print("=== Procurement Summary ===")
    print(f"Records: {len(df)}")

    if "Supplier" in df.columns:
        print(f"Suppliers: {df['Supplier'].nunique()}")

    if "Category" in df.columns:
        print(f"Categories: {df['Category'].nunique()}")

    if "FINAL AMOUNT" in df.columns:
        total = pd.to_numeric(df["FINAL AMOUNT"]).sum()
        print(f"Total Amount: ${total:,.2f}")

    if "Contract_Type" in df.columns:
        print("Contract Types:")
        print(df["Contract_Type"].value_counts())


def calculate_final_amount_with_lead_days(file_path):
    df = pd.read_excel(file_path)

    if "lead days <= 10" not in df.columns:
        print("No lead day column found.")
        return

    fast_orders = df[df["lead days <= 10"] == True]

    if "FINAL AMOUNT" in df.columns:
        total = pd.to_numeric(fast_orders["FINAL AMOUNT"]).sum()
        print(f"Total FINAL AMOUNT for lead days <= 10: ${total:,.2f}")
    else:
        print("FINAL AMOUNT column missing.")


def validate_final_amounts(file_path):
    df = pd.read_excel(file_path)

    required = [
        "Base_Unit_Price",
        "Quantity_Ordered",
        "Volume_Discount_Rate",
        "Expedite_Charge",
        "Contract_Adjustment",
        "FINAL AMOUNT",
    ]

    if not all(col in df.columns for col in required):
        print("Missing columns required for validation.")
        return

    for _, row in df.iterrows():
        base = row["Base_Unit_Price"]
        qty = row["Quantity_Ordered"]
        discount = row["Volume_Discount_Rate"]
        expedite = row["Expedite_Charge"]
        adjustment = row["Contract_Adjustment"]

        calculated = (
            (base * qty)
            * (1 - discount)
            * (1 + expedite)
            * (1 + adjustment)
        )

        actual = row["FINAL AMOUNT"]

        if abs(calculated - actual) > 0.01:
            print(
                f"Mismatch for {row['Order_ID']}: "
                f"expected {calculated:.2f}, found {actual:.2f}"
            )


if __name__ == "__main__":
    excel_file = "complex_procurement_challenge-excel-v200.xlsx"

    print("=== Procurement Reader Demo ===")

    if Path(excel_file).exists():
        print_file_name(excel_file)
        print()

        print_comprehensive_summary(excel_file)
        print()

        calculate_final_amount_with_lead_days(excel_file)
        print()

        validate_final_amounts(excel_file)
    else:
        print(f"Excel file '{excel_file}' not found in current directory.")
        print("Please update the 'excel_file' variable with the correct filename.")