#!/usr/bin/env python3
"""
Simple test runner that always shows output by default.
Run this file to see all test results with detailed output.
"""

import subprocess
import sys
from pathlib import Path

def main():
    print("🚀 Running Procurement Reader Tests with Full Output...")
    print("=" * 60)
    
    # Find the test file
    test_file = Path("test_procurement_reader.py")
    
    if not test_file.exists():
        print("❌ Error: test_procurement_reader.py not found!")
        sys.exit(1)
    
    # Run pytest with verbose output and no capture
    cmd = [
        sys.executable, "-m", "pytest",
        str(test_file),
        "-v",           # verbose
        "-s",           # no capture (show print statements)
        "--tb=short"    # shorter traceback format
    ]
    
    try:
        result = subprocess.run(cmd, cwd=".")
        print("=" * 60)
        
        if result.returncode == 0:
            print("🎉 All tests passed successfully!")
        else:
            print("❌ Some tests failed. Check output above for details.")
        
        return result.returncode
        
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())