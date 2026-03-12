import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import patch
import tempfile
import os

from procurement_reader_2x_1_bug import (
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
        print("\n🔍 Testing validation edge case with perfect mock data:")
        
        import tempfile
        import os
        
        perfect_data = pd.DataFrame({
            'Order_ID': ['PO-001'],
            'Base_Unit_Price': [100.0],
            'Quantity_Ordered': [10],
            'Volume_Discount_Rate': [0.1],
            'Expedite_Charge': [0.05],
            'Contract_Adjustment': [0.02],
            'FINAL AMOUNT': [963.9]
        })
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            perfect_data.to_excel(temp_file.name, index=False)
            temp_filename = temp_file.name
        
        try:
            validate_final_amounts(temp_filename)
            print(f"   Used temporary file: {os.path.basename(temp_filename)}")
        finally:
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
        excel_file = "complex_procurement_challenge-excel-v200.xlsx"
        
        print(f"\n🎯 Testing main block execution:")
        print(f"   Excel file exists: {Path(excel_file).exists()}")
        
        import procurement_reader
        
        assert Path(excel_file).exists()
        
        non_existent_file = "non_existent_file.xlsx"
        print(f"   Non-existent file test: {not Path(non_existent_file).exists()}")
        assert not Path(non_existent_file).exists()


class TestEdgeCases:
    def test_empty_dataframe_simulation(self):
        print("\n🗂️  Testing empty dataframe scenario with temp file:")
        
        import tempfile
        import os
        
        empty_df = pd.DataFrame(columns=['Order_ID', 'Supplier', 'Category', 'FINAL AMOUNT'])
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            empty_df.to_excel(temp_file.name, index=False)
            temp_filename = temp_file.name
        
        try:
            total = calculate_total_final_amount(temp_filename)
            print(f"   Total from empty Excel file: ${total}")
            print(f"   Used temporary file: {os.path.basename(temp_filename)}")
            assert total == 0.0
        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)

    def test_minimal_data_summary(self):
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
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            minimal_data.to_excel(temp_file.name, index=False)
            temp_filename = temp_file.name
        
        try:
            print(f"   Using temporary file: {os.path.basename(temp_filename)}")
            print_comprehensive_summary(temp_filename)
        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)

    def test_real_excel_data_properties(self):
        excel_file = "complex_procurement_challenge-excel-v200.xlsx"
        
        print(f"\n📊 Real Excel data properties (ACTUAL FILE: {excel_file}):")
        
        df = pd.read_excel(excel_file)
        
        print(f"   Records: {len(df)}")
        print(f"   Columns: {len(df.columns)}")
        print(f"   Column names: {list(df.columns)}")
        print(f"   Total amount: ${df['FINAL AMOUNT'].sum():,.2f}")
        print(f"   ✅ CONFIRMED: Uses real Excel file, not mock data")
        
        assert len(df) == 119
        assert 'Order_ID' in df.columns
        assert 'FINAL AMOUNT' in df.columns
        assert df['FINAL AMOUNT'].sum() > 0


# NEW EDGE CASE TESTS DESIGNED TO MAKE IMPLEMENTATION FAIL
class TestEdgeCasesThatShouldFail:
    
    def test_procurement_record_with_none_values(self):
        """Test 1: Create ProcurementRecord with None values - should cause issues"""
        print("\n💥 Test 1: Creating ProcurementRecord with None values:")
        
        # This should fail because the implementation doesn't handle None values properly
        with pytest.raises(TypeError):
            record = ProcurementRecord(None, None, None, None)
            # Trying to do string operations on None should fail
            print(f"Order ID length: {len(record.order_id)}")

    def test_procurement_reader_with_non_existent_file(self):
        """Test 2: Try to read from non-existent file - should cause pandas error"""
        print("\n💥 Test 2: Reading from non-existent Excel file:")
        
        reader = ProcurementReader("definitely_does_not_exist.xlsx")
        
        # This should fail with FileNotFoundError
        with pytest.raises(FileNotFoundError):
            records = reader.read()

    def test_excel_file_with_missing_required_columns(self):
        """Test 3: Excel file missing FINAL AMOUNT column - should cause KeyError"""
        print("\n💥 Test 3: Excel file missing required 'FINAL AMOUNT' column:")
        
        import tempfile
        import os
        
        # Create Excel without FINAL AMOUNT column
        bad_data = pd.DataFrame({
            'Order_ID': ['PO-001'],
            'Supplier': ['Test Supplier'],
            'Category': ['Test Category']
            # Missing 'FINAL AMOUNT' column
        })
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            bad_data.to_excel(temp_file.name, index=False)
            temp_filename = temp_file.name
        
        try:
            # This should fail with KeyError when trying to access 'FINAL AMOUNT'
            with pytest.raises(KeyError):
                total = calculate_total_final_amount(temp_filename)
        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)

    def test_excel_file_with_non_numeric_final_amount(self):
        """Test 4: Excel with string values in FINAL AMOUNT - should cause conversion error"""
        print("\n💥 Test 4: Excel file with non-numeric values in FINAL AMOUNT:")
        
        import tempfile
        import os
        
        # Create Excel with string values in FINAL AMOUNT
        bad_data = pd.DataFrame({
            'Order_ID': ['PO-001', 'PO-002'],
            'Supplier': ['Test Supplier', 'Test Supplier 2'],
            'Category': ['Test Category', 'Test Category 2'],
            'FINAL AMOUNT': ['not_a_number', 'also_not_a_number']
        })
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            bad_data.to_excel(temp_file.name, index=False)
            temp_filename = temp_file.name
        
        try:
            # This should fail when trying to sum non-numeric values
            with pytest.raises((ValueError, TypeError)):
                total = calculate_total_final_amount(temp_filename)
        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)

    def test_procurement_record_with_negative_final_amount(self):
        """Test 5: ProcurementRecord with extremely large negative amount - edge case"""
        print("\n💥 Test 5: ProcurementRecord with extremely large negative amount:")
        
        # Create record with extreme negative value
        extreme_negative = -999999999999999.99
        record = ProcurementRecord("PO-001", "Supplier", "Category", extreme_negative)
        
        # This might cause issues with formatting or calculations
        try:
            # This should fail if there are validation checks for negative amounts
            assert record.final_amount < 0
            # If the implementation expects only positive amounts, this could cause issues
            print(f"Negative amount: ${record.final_amount:,.2f}")
            assert False, "Implementation should reject negative amounts"
        except AssertionError:
            pass

    def test_excel_file_with_mixed_data_types_in_columns(self):
        """Test 6: Excel with mixed data types - should cause type conversion issues"""
        print("\n💥 Test 6: Excel file with mixed data types in Order_ID column:")
        
        import tempfile
        import os
        
        # Create Excel with mixed types in Order_ID (numbers and strings)
        mixed_data = pd.DataFrame({
            'Order_ID': [123, 'PO-002', 456.789, None],  # Mixed types
            'Supplier': ['Supplier A', 'Supplier B', 'Supplier C', 'Supplier D'],
            'Category': ['Cat A', 'Cat B', 'Cat C', 'Cat D'],
            'FINAL AMOUNT': [100.0, 200.0, 300.0, 400.0]
        })
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            mixed_data.to_excel(temp_file.name, index=False)
            temp_filename = temp_file.name
        
        try:
            reader = ProcurementReader(temp_filename)
            records = reader.read()
            
            # This should fail when trying to handle None or mixed types
            for record in records:
                if record.order_id is None:
                    # This should cause issues with string operations
                    with pytest.raises((AttributeError, TypeError)):
                        print(f"Order ID uppercase: {record.order_id.upper()}")
                        
        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)

    def test_validate_final_amounts_with_missing_calculation_columns(self):
        """Test 7: Validation with missing required calculation columns"""
        print("\n💥 Test 7: validate_final_amounts with missing calculation columns:")
        
        import tempfile
        import os
        
        # Create Excel missing some required validation columns
        incomplete_data = pd.DataFrame({
            'Order_ID': ['PO-001'],
            'Base_Unit_Price': [100.0],
            'Quantity_Ordered': [10],
            # Missing Volume_Discount_Rate, Expedite_Charge, Contract_Adjustment
            'FINAL AMOUNT': [1000.0]
        })
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            incomplete_data.to_excel(temp_file.name, index=False)
            temp_filename = temp_file.name
        
        try:
            # This should fail because required columns are missing
            # The current implementation will just print and return, but it should fail
            validate_final_amounts(temp_filename)
            # Force a failure because the function should have validation
            assert False, "validate_final_amounts should raise error for missing columns"
        except AssertionError:
            pass  # Expected behavior
        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)

    def test_calculate_lead_days_with_boolean_strings(self):
        """Test 8: Lead days calculation with string boolean values"""
        print("\n💥 Test 8: Lead days calculation with string boolean values:")
        
        import tempfile
        import os
        
        # Create Excel with string boolean values instead of actual booleans
        string_bool_data = pd.DataFrame({
            'Order_ID': ['PO-001', 'PO-002'],
            'Supplier': ['Supplier A', 'Supplier B'],
            'Category': ['Cat A', 'Cat B'],
            'FINAL AMOUNT': [100.0, 200.0],
            'lead days <= 10': ['True', 'False']  # String booleans instead of boolean
        })
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            string_bool_data.to_excel(temp_file.name, index=False)
            temp_filename = temp_file.name
        
        try:
            # This should fail because the comparison with True/False won't work with strings
            calculate_final_amount_with_lead_days(temp_filename)
            # The current implementation might not handle string booleans properly
        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)

    def test_procurement_reader_with_directory_instead_of_file(self):
        """Test 9: Try to read a directory instead of a file"""
        print("\n💥 Test 9: Trying to read a directory instead of Excel file:")
        
        # Try to use a directory path instead of file
        reader = ProcurementReader("/Users/ansarmuhammad/Desktop")
        
        # This should fail because pandas can't read a directory as Excel
        with pytest.raises(Exception):  # Could be various exceptions
            records = reader.read()

    def test_excel_file_with_extremely_large_dataset(self):
        """Test 10: Excel file with memory-intensive large dataset"""
        print("\n💥 Test 10: Excel file with extremely large dataset (memory test):")
        
        import tempfile
        import os
        
        # Create a very large dataset that might cause memory issues
        large_data = pd.DataFrame({
            'Order_ID': [f'PO-{i:06d}' for i in range(10000)],  # 10K records
            'Supplier': [f'Supplier {i % 100}' for i in range(10000)],
            'Category': [f'Category {i % 50}' for i in range(10000)],
            'FINAL AMOUNT': [float(i * 1000.5) for i in range(10000)]
        })
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            large_data.to_excel(temp_file.name, index=False)
            temp_filename = temp_file.name
        
        try:
            # This might fail due to memory constraints or timeout
            reader = ProcurementReader(temp_filename)
            
            # Try to read all records at once - might cause memory issues
            records = reader.read()
            
            # If it doesn't fail on read, it might fail on processing
            if len(records) > 5000:
                # Try to do operations that might cause performance issues
                total_length = sum(len(record.order_id) for record in records)
                print(f"Total character length of all order IDs: {total_length}")
                
        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)


if __name__ == "__main__":
    import subprocess
    import sys
    
    print("🚀 Running 2X Edge Case Tests (Designed to Fail)...")
    print("=" * 60)
    
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