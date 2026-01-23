"""
Test Petty Cash file using convert_file (like the test does) vs direct read
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import MagicMock
sys.modules['odoo'] = MagicMock()
sys.modules['odoo.exceptions'] = MagicMock()

import pandas as pd
from utils.thai_bank_converter import ThaiBankStatementConverter

file_path = 'demo_data/Petty Cash 01-080126.xlsx'

print("="*70)
print("METHOD 1: Using convert_file (like the test does)")
print("="*70)
converter1 = ThaiBankStatementConverter()
with open(file_path, 'rb') as f:
    file_data = f.read()

transactions1 = converter1.convert_file(file_data, 'Petty Cash 01-080126.xlsx')
print(f"Transactions found: {len(transactions1)}")

# Check for Children's Day
found1 = False
for t in transactions1:
    if 'ของขวัญวันเด็ก' in t.get('payment_ref', ''):
        found1 = True
        print(f"✅ Children's Day transaction found")
        break
if not found1:
    print(f"❌ Children's Day transaction NOT found")

print("\n" + "="*70)
print("METHOD 2: Direct read with header=2 (manual)")
print("="*70)
converter2 = ThaiBankStatementConverter()
df = pd.read_excel(file_path, header=2)
df.columns = df.columns.str.strip()
transactions2 = converter2.convert_generic(df)
print(f"Transactions found: {len(transactions2)}")

# Check for Children's Day
found2 = False
for t in transactions2:
    if 'ของขวัญวันเด็ก' in t.get('payment_ref', ''):
        found2 = True
        print(f"✅ Children's Day transaction found")
        break
if not found2:
    print(f"❌ Children's Day transaction NOT found")

print("\n" + "="*70)
print("METHOD 3: Check what header row convert_file detects")
print("="*70)

# Read raw to detect header
df_raw = pd.read_excel(file_path, header=None)
converter3 = ThaiBankStatementConverter()
header_idx = converter3.find_header_row(df_raw)
print(f"Detected header row index: {header_idx}")

# Read with detected header
df3 = pd.read_excel(file_path, header=header_idx)
df3.columns = df3.columns.str.strip()
print(f"Rows after reading with header={header_idx}: {len(df3)}")
print(f"Columns: {list(df3.columns)}")

transactions3 = converter3.convert_generic(df3)
print(f"Transactions found: {len(transactions3)}")

# Check for Children's Day
found3 = False
for t in transactions3:
    if 'ของขวัญวันเด็ก' in t.get('payment_ref', ''):
        found3 = True
        print(f"✅ Children's Day transaction found")
        break
if not found3:
    print(f"❌ Children's Day transaction NOT found")
