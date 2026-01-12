#!/usr/bin/env python3
"""
Test script for Thai Bank Statement Converter
Tests all files in demo_data folder to ensure converter handles different formats
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import base64

# Add the module to Python path
module_path = Path(__file__).parent.parent
sys.path.insert(0, str(module_path))

from utils.thai_bank_converter import ThaiBankStatementConverter

def format_currency(amount):
    """Format currency for display"""
    if amount is None:
        return "N/A"
    return f"{amount:,.2f}"

def test_file(file_path):
    """Test a single bank statement file"""
    print(f"\n{'='*80}")
    print(f"Testing: {file_path.name}")
    print('='*80)
    
    try:
        # Read file as binary
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        # Convert to base64 (simulating Odoo binary field)
        file_base64 = base64.b64encode(file_data).decode('utf-8')
        
        # Initialize converter
        converter = ThaiBankStatementConverter()
        
        # Convert the file
        result = converter.convert_file(file_base64, file_path.name)
        
        # Display results
        print(f"\n✅ SUCCESS - Converted successfully!")
        print(f"\nAccount Number: {result.get('account_number', 'Not detected')}")
        print(f"Opening Balance: {format_currency(result.get('balance_start'))}")
        print(f"Closing Balance: {format_currency(result.get('balance_end'))}")
        print(f"Total Transactions: {len(result.get('transactions', []))}")
        
        # Show first 5 transactions
        transactions = result.get('transactions', [])
        if transactions:
            print(f"\nFirst {min(5, len(transactions))} transactions:")
            print(f"{'Date':<12} {'Description':<40} {'Debit':<15} {'Credit':<15}")
            print("-" * 82)
            for trans in transactions[:5]:
                date_str = trans.get('date', '')
                if isinstance(date_str, datetime):
                    date_str = date_str.strftime('%Y-%m-%d')
                desc = trans.get('payment_ref', '')[:38]
                debit = format_currency(trans.get('debit', 0))
                credit = format_currency(trans.get('credit', 0))
                print(f"{date_str:<12} {desc:<40} {debit:<15} {credit:<15}")
        
        # Validation checks
        print("\nValidation:")
        issues = []
        
        if not result.get('account_number'):
            issues.append("⚠️  Account number not detected")
        
        if result.get('balance_start') is None:
            issues.append("⚠️  Opening balance not detected")
        
        if result.get('balance_end') is None:
            issues.append("⚠️  Closing balance not detected")
        
        if not transactions:
            issues.append("❌ No transactions found")
        
        # Check for invalid transactions
        invalid_count = sum(1 for t in transactions if not t.get('date') or not t.get('payment_ref'))
        if invalid_count > 0:
            issues.append(f"⚠️  {invalid_count} transactions missing date or description")
        
        if issues:
            for issue in issues:
                print(issue)
        else:
            print("✅ All validations passed!")
        
        return True, None
        
    except Exception as e:
        print(f"\n❌ FAILED - Error during conversion:")
        print(f"   {type(e).__name__}: {str(e)}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()
        return False, str(e)

def main():
    """Test all files in demo_data folder"""
    demo_data_path = module_path / 'demo_data'
    
    if not demo_data_path.exists():
        print(f"❌ Demo data folder not found: {demo_data_path}")
        return
    
    # Get all files in demo_data folder
    files = list(demo_data_path.glob('*'))
    files = [f for f in files if f.is_file() and not f.name.startswith('.')]
    
    if not files:
        print(f"❌ No files found in {demo_data_path}")
        return
    
    print(f"Found {len(files)} test files")
    
    # Test each file
    results = {}
    for file_path in sorted(files):
        success, error = test_file(file_path)
        results[file_path.name] = (success, error)
    
    # Summary
    print(f"\n\n{'='*80}")
    print("TEST SUMMARY")
    print('='*80)
    
    passed = sum(1 for success, _ in results.values() if success)
    failed = len(results) - passed
    
    print(f"\nTotal Files: {len(results)}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    
    if failed > 0:
        print("\nFailed files:")
        for filename, (success, error) in results.items():
            if not success:
                print(f"  - {filename}")
                print(f"    Error: {error}")
    
    print("\n" + "="*80)
    
    # Exit with appropriate code
    sys.exit(0 if failed == 0 else 1)

if __name__ == '__main__':
    main()
