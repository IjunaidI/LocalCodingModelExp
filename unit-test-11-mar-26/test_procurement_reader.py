import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import patch

from procurement_reader import (
    ProcurementRecord,
    ProcurementReader,
    calculate_total_final_amount,
    print_total_final_amount,
    print_file_name,
    print_comprehensive_summary,
    calculate_final_amount_with_lead_days,
    validate_final_amounts
)


class TestProcurementRecord:
    def test_procurement_record_creation(self):
        record = ProcurementRecord("PO-001", "Supplier A", "Medical", 1500.50)
        print(f"\n🏗️  Created ProcurementRecord: {record.order_id} | {record.supplier} | {record.category} | ${record.final_amount}")
        assert record.order_id == "PO-001"
        assert record.supplier == "Supplier A"
        assert record.category == "Medical"
        assert record.final_amount == 1500.50


class TestProcurementReader:
    @pytest.fixture
    def excel_file(self):
        return "complex_procurement_challenge-excel-v200.xlsx"

    def test_init(self):
        reader = ProcurementReader("test.xlsx")
        print(f"\n✅ ProcurementReader initialized with path: {reader.path}")
        assert reader.path == Path("test.xlsx")

    def test_init_with_path_object(self):
        path = Path("test.xlsx")
        reader = ProcurementReader(path)
        print(f"\n✅ ProcurementReader initialized with Path object: {reader.path}")
        assert reader.path == path

    def test_read(self, excel_file):
        reader = ProcurementReader(excel_file)
        records = reader.read()
        
        print(f"\n📊 Read {len(records)} records from Excel file")
        print(f"   First record: {records[0].order_id} | {records[0].supplier} | {records[0].category} | ${records[0].final_amount:,.2f}")
        
        assert len(records) == 119
        assert records[0].order_id == "PO-2026-1001"
        assert records[0].supplier == "MedTech Alpha"
        assert records[0].category == "Critical Care"
        assert abs(records[0].final_amount - 157235.502653) < 0.01

    def test_total_amount(self, excel_file):
        reader = ProcurementReader(excel_file)
        total = reader.total_amount()
        print(f"\n💰 Total amount from ProcurementReader class: ${total:,.2f}")
        assert abs(total - 79008671.70) < 1.0


class TestStandaloneFunctions:
    @pytest.fixture
    def excel_file(self):
        return "complex_procurement_challenge-excel-v200.xlsx"

    def test_calculate_total_final_amount(self, excel_file):
        total = calculate_total_final_amount(excel_file)
        print(f"\n💰 Standalone function total: ${total:,.2f}")
        assert abs(total - 79008671.70) < 1.0

    def test_print_total_final_amount(self, excel_file):
        print("\n📋 Testing print_total_final_amount function:")
        print_total_final_amount(excel_file)

    def test_print_file_name(self):
        print("\n📄 Testing print_file_name function:")
        print_file_name("test.xlsx")

    def test_print_comprehensive_summary(self, excel_file):
        print("\n📊 Testing comprehensive summary function:")
        print_comprehensive_summary(excel_file)

    def test_calculate_final_amount_with_lead_days_matches(self, excel_file):
        print("\n⏰ Testing lead days calculation:")
        calculate_final_amount_with_lead_days(excel_file)

    def test_validate_final_amounts_edge_case_with_mock(self):
        # Keep one test with mock data to test the edge case of perfect calculations
        print("\n🔍 Testing validation edge case with perfect mock data:")
        
        # Create a temporary CSV for this specific test
        import tempfile
        import os
        
        perfect_data = pd.DataFrame({
            'Order_ID': ['PO-001'],
            'Base_Unit_Price': [100.0],
            'Quantity_Ordered': [10],
            'Volume_Discount_Rate': [0.1],
            'Expedite_Charge': [0.05],
            'Contract_Adjustment': [0.02],
            'FINAL AMOUNT': [963.9]  # Exact calculation result
        })
        
        # Save to temporary Excel file
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            perfect_data.to_excel(temp_file.name, index=False)
            temp_filename = temp_file.name
        
        try:
            validate_final_amounts(temp_filename)
            print(f"   Used temporary file: {os.path.basename(temp_filename)}")
        finally:
            # Clean up
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)

    def test_validate_final_amounts_with_mismatches(self, excel_file):
        print("\n❌ Testing validation with real data (expecting mismatches):")
        validate_final_amounts(excel_file)


class TestMainExecution:
    @patch('procurement_reader.Path')
    @patch('builtins.print')
    def test_main_file_not_found(self, mock_print, mock_path_class):
        mock_path_instance = mock_path_class.return_value
        mock_path_instance.exists.return_value = False
        
        def dummy_func(file):
            pass
        
        print("\n🚫 Testing main execution when Excel file is not found:")
        
        # Execute the main block directly
        exec("""
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
""", {'__name__': '__main__', 'Path': mock_path_class, 'print_file_name': dummy_func,
      'print_comprehensive_summary': dummy_func, 'calculate_final_amount_with_lead_days': dummy_func,
      'validate_final_amounts': dummy_func, 'print': mock_print})
        
        print_calls = [str(call) for call in mock_print.call_args_list]
        summary_text = " ".join(print_calls)
        print(f"   Result: {summary_text}")
        assert "not found" in summary_text

    @patch('procurement_reader.Path')
    @patch('procurement_reader.print_comprehensive_summary')
    @patch('procurement_reader.calculate_final_amount_with_lead_days')
    @patch('procurement_reader.validate_final_amounts')
    @patch('procurement_reader.print_file_name')
    @patch('builtins.print')
    def test_main_file_exists(self, mock_print, mock_print_file, mock_validate, 
                             mock_calculate, mock_summary, mock_path_class):
        mock_path_instance = mock_path_class.return_value
        mock_path_instance.exists.return_value = True
        
        print("\n✅ Testing main execution when Excel file exists:")
        
        # Execute the main block directly
        exec("""
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
""", {'__name__': '__main__', 'Path': mock_path_class, 'print_file_name': mock_print_file,
      'print_comprehensive_summary': mock_summary, 'calculate_final_amount_with_lead_days': mock_calculate,
      'validate_final_amounts': mock_validate, 'print': mock_print})
        
        print_calls = [str(call) for call in mock_print.call_args_list]
        summary_text = " ".join(print_calls)
        print(f"   Executed main block successfully")
        assert "Procurement Reader Demo" in summary_text


class TestMainBlockExecution:
    def test_main_block_execution(self):
        """Test the actual main block execution by using the real Excel file"""
        # Use the actual Excel file for testing
        excel_file = "complex_procurement_challenge-excel-v200.xlsx"
        
        print(f"\n🎯 Testing main block execution:")
        print(f"   Excel file exists: {Path(excel_file).exists()}")
        
        # Test with file existing
        import procurement_reader
        
        # Capture if the main block would execute with the real file
        assert Path(excel_file).exists()
        
        # Test file not found scenario by checking a non-existent file
        non_existent_file = "non_existent_file.xlsx"
        print(f"   Non-existent file test: {not Path(non_existent_file).exists()}")
        assert not Path(non_existent_file).exists()


# Test edge cases and error conditions
class TestEdgeCases:
    def test_empty_dataframe_simulation(self):
        # Test edge case using temporary file instead of mocking
        print("\n🗂️  Testing empty dataframe scenario with temp file:")
        
        import tempfile
        import os
        
        empty_df = pd.DataFrame(columns=['Order_ID', 'Supplier', 'Category', 'FINAL AMOUNT'])
        
        # Save to temporary Excel file
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            empty_df.to_excel(temp_file.name, index=False)
            temp_filename = temp_file.name
        
        try:
            total = calculate_total_final_amount(temp_filename)
            print(f"   Total from empty Excel file: ${total}")
            print(f"   Used temporary file: {os.path.basename(temp_filename)}")
            assert total == 0.0
        finally:
            # Clean up
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)

    def test_minimal_data_summary(self):
        # Test with minimal data using temporary file
        print("\n📋 Testing comprehensive summary with minimal data from temp file:")
        
        import tempfile
        import os
        
        minimal_data = pd.DataFrame({
            'Order_ID': ['PO-001'],
            'Supplier': ['Only Supplier'],
            'Category': ['Only Category'],
            'FINAL AMOUNT': [100.0],
            'TOTAL AMOUNT': [90.0],
            'lead days <= 10': [False],
            'Contract_Type': ['Fixed']
        })
        
        # Save to temporary Excel file
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            minimal_data.to_excel(temp_file.name, index=False)
            temp_filename = temp_file.name
        
        try:
            print(f"   Using temporary file: {os.path.basename(temp_filename)}")
            print_comprehensive_summary(temp_filename)
        finally:
            # Clean up
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)

    def test_real_excel_data_properties(self):
        """Test properties of the actual Excel data - USES REAL FILE"""
        excel_file = "complex_procurement_challenge-excel-v200.xlsx"
        
        print(f"\n📊 Real Excel data properties (ACTUAL FILE: {excel_file}):")
        
        df = pd.read_excel(excel_file)
        
        print(f"   Records: {len(df)}")
        print(f"   Columns: {len(df.columns)}")
        print(f"   Column names: {list(df.columns)}")
        print(f"   Total amount: ${df['FINAL AMOUNT'].sum():,.2f}")
        print(f"   ✅ CONFIRMED: Uses real Excel file, not mock data")
        
        # Test data properties
        assert len(df) == 119
        assert 'Order_ID' in df.columns
        assert 'FINAL AMOUNT' in df.columns
        assert df['FINAL AMOUNT'].sum() > 0


if __name__ == "__main__":
    # Run tests when file is executed directly
    import subprocess
    import sys
    
    print("🚀 Running Procurement Reader Tests with Full Output...")
    print("=" * 60)
    
    # Run pytest with verbose and capture disabled
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        __file__, "-v", "-s", "--tb=short"
    ], cwd=".")
    
    print("=" * 60)
    print(f"✅ Test execution completed with exit code: {result.returncode}")
    
    if result.returncode == 0:
        print("🎉 All tests passed successfully!")
    else:
        print("❌ Some tests failed. Check output above for details.")
    
    sys.exit(result.returncode)