#!/usr/bin/env python3
"""
Standalone test for Thai Bank Statement Converter
Tests without requiring Odoo installation
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import base64
import pandas as pd
import io

# Minimal UserError replacement for testing
class UserError(Exception):
    pass

# Copy of the converter class without Odoo dependencies
class ThaiBankStatementConverter:
    """Converter for Thai bank statements to Odoo format"""
    
    def __init__(self):
        self.dataframes = []
    
    def find_column_by_keywords(self, columns, keywords):
        """Find a column that matches any of the keywords (substring match)"""
        for col in columns:
            col_lower = str(col).lower()
            for keyword in keywords:
                if keyword in col_lower:
                    return col
        return None
    
    def parse_date(self, date_str):
        """Parse various date formats and return Python date object"""
        if pd.isna(date_str) or date_str == '':
            return None
        
        date_str = str(date_str).strip()
        
        # List of date formats to try
        formats = [
            '%d-%b-%y',      # 01-Nov-25
            '%d/%m/%Y',      # 07/10/2025
            '%d/%m/%y',      # 07/10/25
            '%d-%m-%Y',      # 01-11-2025
            '%d-%m-%y',      # 01-11-25
            '%Y-%m-%d',      # 2025-11-01
            '%Y/%m/%d',      # 2025/11/01
            '%d.%m.%Y',      # 01.11.2025
            '%d.%m.%y',      # 01.11.25
            '%d %b %Y',      # 01 Nov 2025
            '%d %B %Y',      # 01 November 2025
        ]
        
        for fmt in formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                return parsed_date.date()
            except ValueError:
                continue
        
        # Try to handle Thai Buddhist year (BE) - convert to AD
        try:
            if '/' in date_str or '-' in date_str:
                parts = date_str.replace('-', '/').split('/')
                if len(parts) >= 3:
                    day, month, year = parts[0], parts[1], parts[2]
                    year_int = int(year)
                    # Thai year is 543 years ahead of AD
                    if year_int > 2500:
                        year_int -= 543
                    parsed_date = datetime(int(year_int), int(month), int(day))
                    return parsed_date.date()
        except:
            pass
        
        raise UserError(f"Could not parse date '{date_str}'")
    
    def clean_float_value(self, value):
        """Clean and convert a value to float, handling various formats"""
        if pd.isna(value) or value == '':
            return 0.0
        
        value_str = str(value).strip()
        if not value_str or value_str.lower() == 'nan':
            return 0.0
        
        # Remove commas and spaces
        value_str = value_str.replace(',', '').replace(' ', '')
        
        try:
            return float(value_str)
        except:
            return 0.0
    
    def is_valid_transaction_row(self, row, date_col, debit_col, credit_col, desc_col):
        """Check if a row is a valid transaction"""
        # Must have a valid date
        date_value = row.get(date_col, '') if date_col else ''
        if pd.isna(date_value) or str(date_value).strip() == '':
            return False
        
        # Check if date can be parsed
        try:
            self.parse_date(date_value)
        except:
            return False
        
        # Must have at least one amount (debit or credit)
        debit = self.clean_float_value(row.get(debit_col, 0)) if debit_col else 0
        credit = self.clean_float_value(row.get(credit_col, 0)) if credit_col else 0
        
        if not debit_col and not credit_col:
            return False
        
        if debit == 0 and credit == 0:
            return False
        
        # Skip common summary/total rows by checking description
        if desc_col:
            desc = str(row.get(desc_col, '')).lower()
            skip_keywords = ['total', 'subtotal', 'summary', 'balance', 'closing', 'opening',
                           'รวม', 'ยอดรวม', 'ยอด', 'สรุป', 'ปิด', 'เปิด']
            for keyword in skip_keywords:
                if keyword in desc:
                    return False
        
        return True
    
    def find_all_columns_by_keywords(self, columns, keywords):
        """Find all columns that match any of the keywords (substring match)"""
        matching_cols = []
        for col in columns:
            col_lower = str(col).lower()
            for keyword in keywords:
                if keyword in col_lower and col not in matching_cols:
                    matching_cols.append(col)
                    break
        return matching_cols
    
    def convert_generic(self, df):
        """Convert any bank statement format to Odoo format"""
        # Find date column
        date_col = self.find_column_by_keywords(df.columns, [
            'date', 'transaction date', 'effective date', 'วันที่', 'วันทำ'
        ])
        
        # Find ALL description/detail columns
        desc_keywords = [
            'description', 'detail', 'transaction description', 'tr description',
            'memo', 'รายละเอียด', 'หมายเหตุ', 'รายการ'
        ]
        desc_cols = self.find_all_columns_by_keywords(df.columns, desc_keywords)
        
        # Find debit/credit columns
        debit_col = self.find_column_by_keywords(df.columns, [
            'debit', 'withdrawal', 'ถอน', 'จ่าย', 'out', 'expense'
        ])
        credit_col = self.find_column_by_keywords(df.columns, [
            'credit', 'deposit', 'ฝาก', 'รับ', 'in', 'income'
        ])
        
        # Try to find account number
        account_col = self.find_column_by_keywords(df.columns, [
            'account', 'account number', 'เลขที่บัญชี', 'account no'
        ])
        account_number = None
        if account_col and not df[account_col].isna().all():
            first_account = df[account_col].dropna().iloc[0] if len(df[account_col].dropna()) > 0 else None
            if first_account:
                account_number = str(first_account).strip()
        
        # Try to find opening/closing balance
        balance_start = None
        balance_end = None
        balance_col = self.find_column_by_keywords(df.columns, [
            'balance', 'ยอดคงเหลือ', 'คงเหลือ'
        ])
        
        if balance_col:
            balance_values = df[balance_col].dropna()
            if len(balance_values) > 0:
                balance_start = self.clean_float_value(balance_values.iloc[0])
                balance_end = self.clean_float_value(balance_values.iloc[-1])
        
        # Build transactions
        transactions = []
        for _, row in df.iterrows():
            if not self.is_valid_transaction_row(row, date_col, debit_col, credit_col, desc_cols[0] if desc_cols else None):
                continue
            
            # Parse date
            try:
                trans_date = self.parse_date(row[date_col]) if date_col else None
            except:
                continue
            
            if not trans_date:
                continue
            
            # Combine all description columns
            description_parts = []
            for desc_col in desc_cols:
                desc_value = row.get(desc_col, '')
                if not pd.isna(desc_value) and str(desc_value).strip():
                    description_parts.append(str(desc_value).strip())
            
            payment_ref = ' | '.join(description_parts) if description_parts else 'Transaction'
            
            # Get amounts
            debit = self.clean_float_value(row.get(debit_col, 0)) if debit_col else 0.0
            credit = self.clean_float_value(row.get(credit_col, 0)) if credit_col else 0.0
            
            # Create transaction
            transaction = {
                'date': trans_date,
                'payment_ref': payment_ref,
                'debit': debit,
                'credit': credit,
                'amount': credit - debit,
            }
            transactions.append(transaction)
        
        return {
            'account_number': account_number,
            'balance_start': balance_start,
            'balance_end': balance_end,
            'transactions': transactions,
        }
    
    def convert_file(self, file_base64, filename):
        """Convert a Thai bank statement file to Odoo format"""
        # Decode the file
        file_data = base64.b64decode(file_base64)
        
        # Determine file type and read accordingly
        if filename.endswith('.csv'):
            # Try different encodings for CSV
            for encoding in ['utf-8', 'tis-620', 'windows-874', 'latin-1']:
                try:
                    df = pd.read_csv(io.BytesIO(file_data), encoding=encoding)
                    break
                except:
                    continue
            else:
                raise UserError("Could not read CSV file with any known encoding")
        elif filename.endswith(('.xlsx', '.xls')):
            # Read Excel file
            df = pd.read_excel(io.BytesIO(file_data))
        else:
            raise UserError(f"Unsupported file format: {filename}")
        
        # Convert using generic converter
        return self.convert_generic(df)


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
        
        # result is a list of transactions
        transactions = result if isinstance(result, list) else []
        
        # Display results
        print(f"\n✅ SUCCESS - Converted successfully!")
        print(f"\nTotal Transactions: {len(transactions)}")
        
        # Show first 5 transactions
        if transactions:
            print(f"\nFirst {min(5, len(transactions))} transactions:")
            print(f"{'Date':<12} {'Description':<40} {'Amount':<15}")
            print("-" * 67)
            for trans in transactions[:5]:
                date_str = trans.get('date', '')
                if isinstance(date_str, datetime):
                    date_str = date_str.strftime('%Y-%m-%d')
                desc = str(trans.get('payment_ref', ''))[:38]
                amount = format_currency(trans.get('amount', 0))
                print(f"{date_str:<12} {desc:<40} {amount:<15}")
        
        # Validation checks
        print("\nValidation:")
        issues = []
        
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
    script_path = Path(__file__).parent
    module_path = script_path.parent
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
                if error:
                    print(f"    Error: {error}")
    
    print("\n" + "="*80)
    
    # Exit with appropriate code
    sys.exit(0 if failed == 0 else 1)

if __name__ == '__main__':
    main()
