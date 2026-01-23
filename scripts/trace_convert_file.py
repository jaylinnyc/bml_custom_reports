"""
Trace convert_file step by step for Petty Cash
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import MagicMock
sys.modules['odoo'] = MagicMock()
sys.modules['odoo.exceptions'] = MagicMock()

import pandas as pd
import io
from utils.thai_bank_converter import ThaiBankStatementConverter

file_path = 'demo_data/Petty Cash 01-080126.xlsx'

with open(file_path, 'rb') as f:
    file_data = f.read()

filename = 'Petty Cash 01-080126.xlsx'

print("=== STEP 1: Read raw file ===")
df_raw = pd.read_excel(io.BytesIO(file_data), header=None)
print(f"Raw dataframe shape: {df_raw.shape}")

print("\n=== STEP 2: Detect format ===")
converter = ThaiBankStatementConverter()
format_type = converter.detect_statement_format(df_raw, filename)
print(f"Format type: {format_type}")

print("\n=== STEP 3: Find header row ===")
header_idx = converter.find_header_row(df_raw)
print(f"Header index: {header_idx}")

print("\n=== STEP 4: Try merged headers ===")
df_merged = converter.read_excel_with_merged_headers(file_data, header_idx)
if df_merged is not None:
    print(f"✅ read_excel_with_merged_headers succeeded")
    print(f"   Shape: {df_merged.shape}")
    print(f"   Columns: {list(df_merged.columns)[:7]}")
    df = df_merged
else:
    print(f"❌ read_excel_with_merged_headers returned None")
    df = pd.read_excel(io.BytesIO(file_data), header=header_idx)
    print(f"   Using pandas read_excel with header={header_idx}")
    print(f"   Shape: {df.shape}")

# Clean column names
df.columns = df.columns.str.strip()

print("\n=== STEP 5: Check for Children's Day transaction ===")
children_day_found = False
for idx, row in df.iterrows():
    label = str(row.get('Label', ''))
    if 'ของขวัญวันเด็ก' in label:
        children_day_found = True
        print(f"✅ Found at row {idx}: {label[:50]}...")
        break

if not children_day_found:
    print("❌ Children's Day transaction NOT in dataframe!")

print("\n=== STEP 6: Run convert_generic ===")
transactions = converter.convert_generic(df)
print(f"Transactions found: {len(transactions)}")

# Check if Children's Day is in results
found_in_results = False
for t in transactions:
    if 'ของขวัญวันเด็ก' in t.get('payment_ref', ''):
        found_in_results = True
        print(f"✅ Children's Day transaction in final results")
        break

if not found_in_results:
    print(f"❌ Children's Day transaction NOT in final results")
