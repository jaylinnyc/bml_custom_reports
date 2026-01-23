"""
Simple trace to see what happens to row 19 during conversion
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import MagicMock
sys.modules['odoo'] = MagicMock()
sys.modules['odoo.exceptions'] = MagicMock()

import pandas as pd
from utils.thai_bank_converter import ThaiBankStatementConverter

# Read the file
df = pd.read_excel('demo_data/Petty Cash 01-080126.xlsx', header=2)
df.columns = df.columns.str.strip()

print(f"Total rows in dataframe: {len(df)}")
print(f"Columns: {list(df.columns)}")

# Find the Children's Day row
children_day_idx = None
for idx, row in df.iterrows():
    label = str(row.get('Label', ''))
    if 'ของขวัญวันเด็ก' in label:
        children_day_idx = idx
        print(f"\nFound Children's Day transaction at row {idx}")
        print(f"Label: {label}")
        print(f"Date: {row.get('Date')}")
        print(f"Debit: {row.get('Debit')}")
        print(f"Credit: {row.get('Credit')}")
        break

# Create converter and convert
converter = ThaiBankStatementConverter()

# Manually find columns like convert_generic does
date_col = converter.find_column_by_keywords(df.columns, [
    'date', 'transaction date', 'effective date', 'วันที่', 'วันทำ', 'เวลา'
])

desc_keywords = [
    'description', 'detail', 'transaction description', 'tr description',
    'memo', 'รายละเอียด', 'หมายเหตุ', 'รายการ', 'รายละเอียดรายการ',
    'label', 'additional', 'enrichment', 'remarks'
]
desc_cols = converter.find_all_columns_by_keywords(df.columns, desc_keywords)

debit_col = converter.find_column_by_keywords(df.columns, [
    'withdrawal', 'ถอน', 'จ่าย', 'ออก'
])
if not debit_col:
    for col in df.columns:
        col_lower = str(col).lower().strip()
        if 'debit' in col_lower:
            debit_col = col
            break

credit_col = converter.find_column_by_keywords(df.columns, [
    'deposit', 'ฝาก', 'รับ', 'เข้า'
])
if not credit_col:
    for col in df.columns:
        col_lower = str(col).lower().strip()
        if 'credit' in col_lower:
            credit_col = col
            break

print(f"\nColumn mappings:")
print(f"  Date column: {date_col}")
print(f"  Description columns: {desc_cols}")
print(f"  Debit column: {debit_col}")
print(f"  Credit column: {credit_col}")

# Now check if Children's Day row is valid
if children_day_idx is not None:
    row = df.iloc[children_day_idx]
    is_valid = converter.is_valid_transaction_row(
        row, date_col, debit_col, credit_col, desc_cols[0] if desc_cols else None
    )
    print(f"\nChildren's Day row is_valid_transaction_row: {is_valid}")
    
    if not is_valid:
        print("\n❌ This row is being filtered out by is_valid_transaction_row!")
        
        # Check each validation step
        date_value = row.get(date_col, '')
        print(f"\nDate value: {date_value}")
        print(f"Date is na: {pd.isna(date_value)}")
        
        if desc_cols:
            desc = str(row.get(desc_cols[0], '')).lower()
            print(f"\nDescription (lowercase): {desc}")
            
            skip_keywords = [
                'total', 'subtotal', 'summary', 'closing', 'opening',
                'grand total', 'sum of',
                'ยอดรวม',  # Total amount
                'ยอดยกมา', 'ยอดยกไป',  # Balance carried forward/forward
                'รวมทั้งหมด',  # Total all
                'สรุป',  # Summary
                'ปิดบัญชี', 'เปิดบัญชี',  # Close/open account
            ]
            
            for keyword in skip_keywords:
                if keyword in desc:
                    print(f"  ⚠️  MATCHED skip_keyword: '{keyword}'")

# Now run the full conversion
print(f"\n{'='*60}")
print("Running full conversion...")
print(f"{'='*60}")

transactions = converter.convert_generic(df)
print(f"\nTotal transactions found: {len(transactions)}")

# Check if Children's Day is in results
found = False
for t in transactions:
    if 'ของขวัญวันเด็ก' in t.get('payment_ref', ''):
        found = True
        print(f"\n✅ Children's Day transaction is IN the final results!")
        break

if not found:
    print(f"\n❌ Children's Day transaction is NOT in the final results!")
