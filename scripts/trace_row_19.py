"""
Trace why row 19 (Children's Day gift transaction) is being filtered out
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock Odoo modules
from unittest.mock import MagicMock
sys.modules['odoo'] = MagicMock()
sys.modules['odoo.exceptions'] = MagicMock()

import pandas as pd
from utils.thai_bank_converter import ThaiBankStatementConverter

class DebugConverter(ThaiBankStatementConverter):
    """Debug version that prints every step for row 19"""
    
    def is_valid_transaction_row(self, row, idx):
        label = str(row.get('Label', ''))
        if 'ของขวัญวันเด็ก' in label:
            print(f"\n=== CHECKING ROW 19 (Children's Day) ===")
            print(f"Row index: {idx}")
            print(f"Label: {label}")
        
        result = super().is_valid_transaction_row(row, idx)
        
        if 'ของขวัญวันเด็ก' in label:
            print(f"is_valid_transaction_row result: {result}")
            
        return result
    
    def convert_generic(self, df):
        print("\n=== STARTING CONVERSION ===")
        print(f"Dataframe has {len(df)} rows")
        
        # Count how many pass validation
        valid_count = 0
        for idx, row in df.iterrows():
            if self.is_valid_transaction_row(row, idx):
                valid_count += 1
        
        print(f"Rows passing is_valid_transaction_row: {valid_count}")
        
        transactions = super().convert_generic(df)
        
        print(f"\n=== CONVERSION COMPLETE ===")
        print(f"Total transactions: {len(transactions)}")
        
        # Check if Children's Day transaction made it through
        found = False
        for t in transactions:
            if 'ของขวัญวันเด็ก' in t.get('label', ''):
                found = True
                print(f"\n✅ Children's Day transaction FOUND in final results!")
                print(f"   Label: {t['label']}")
                print(f"   Date: {t['date']}")
                print(f"   Debit: {t.get('debit', 0)}")
                break
        
        if not found:
            print(f"\n❌ Children's Day transaction NOT in final results!")
            print(f"\nSearching for it in the dataframe...")
            
            for idx, row in df.iterrows():
                label = str(row.get('Label', ''))
                if 'ของขวัญวันเด็ก' in label:
                    print(f"\nFound at Row {idx}:")
                    print(f"  Date: {row.get('Date')}")
                    print(f"  Date type: {type(row.get('Date'))}")
                    print(f"  Date is NaT: {pd.isna(row.get('Date'))}")
                    print(f"  Label: {label}")
                    print(f"  Credit: {row.get('Credit')}, null={pd.isna(row.get('Credit'))}")
                    print(f"  Debit: {row.get('Debit')}, null={pd.isna(row.get('Debit'))}")
                    print(f"  Balance: {row.get('Balance')}, null={pd.isna(row.get('Balance'))}")
                    
                    # Check validation
                    valid = self.is_valid_transaction_row(row, idx)
                    print(f"  is_valid_transaction_row: {valid}")
                    
                    # Check date parsing
                    try:
                        date_val = row.get('Date')
                        if pd.notna(date_val):
                            date_str = date_val.strftime('%Y-%m-%d')
                            print(f"  Date formats to: {date_str}")
                    except Exception as e:
                        print(f"  Date formatting error: {e}")
                    
                    # Check credit/debit
                    credit = row.get('Credit')
                    debit = row.get('Debit')
                    credit_val = float(credit) if pd.notna(credit) else 0
                    debit_val = float(debit) if pd.notna(debit) else 0
                    print(f"  credit_val: {credit_val}, debit_val: {debit_val}")
                    print(f"  Has amount: {credit_val != 0 or debit_val != 0}")
        
        return transactions

# Test with Petty Cash file
converter = DebugConverter()
file_path = 'demo_data/Petty Cash 01-080126.xlsx'

print(f"Testing: {file_path}")

# Read the file like the converter does
df = pd.read_excel(file_path, header=2)
df.columns = df.columns.str.strip()

transactions = converter.convert_generic(df)

print(f"\n=== FINAL SUMMARY ===")
print(f"Transactions found: {len(transactions)}")
if transactions:
    print(f"Sample transaction keys: {list(transactions[0].keys())}")
