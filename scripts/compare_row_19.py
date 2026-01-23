"""
Check what row 19 looks like in merged headers dataframe
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import MagicMock
sys.modules['odoo'] = MagicMock()
sys.modules['odoo.exceptions'] = MagicMock()

import io
import pandas as pd
from utils.thai_bank_converter import ThaiBankStatementConverter

with open('demo_data/Petty Cash 01-080126.xlsx', 'rb') as f:
    file_data = f.read()

converter = ThaiBankStatementConverter()
header_idx = 2
df_merged = converter.read_excel_with_merged_headers(file_data, header_idx)
df_merged.columns = df_merged.columns.str.strip()

print(f'Merged headers dataframe has {len(df_merged)} rows')
print()

# Check rows around 19
for idx in [18, 19, 20]:
    row = df_merged.iloc[idx]
    date_val = row.get('Date')
    label_val = str(row.get('Label', ''))
    debit_val = row.get('Debit')
    credit_val = row.get('Credit')
    
    print(f'Row {idx}:')
    print(f'  Date: {date_val} (type: {type(date_val).__name__})')
    print(f'  Label: {label_val[:60] if len(label_val) > 60 else label_val}')
    print(f'  Debit: {debit_val}')
    print(f'  Credit: {credit_val}')
    print(f'  Date is NaT: {pd.isna(date_val)}')
    print()

# Now check with direct read (header=2)
df_direct = pd.read_excel('demo_data/Petty Cash 01-080126.xlsx', header=2)
df_direct.columns = df_direct.columns.str.strip()

print(f'\nDirect read dataframe has {len(df_direct)} rows')
print()

# Check same rows
for idx in [18, 19, 20]:
    row = df_direct.iloc[idx]
    date_val = row.get('Date')
    label_val = str(row.get('Label', ''))
    debit_val = row.get('Debit')
    credit_val = row.get('Credit')
    
    print(f'Row {idx}:')
    print(f'  Date: {date_val} (type: {type(date_val).__name__})')
    print(f'  Label: {label_val[:60] if len(label_val) > 60 else label_val}')
    print(f'  Debit: {debit_val}')
    print(f'  Credit: {credit_val}')
    print(f'  Date is NaT: {pd.isna(date_val)}')
    print()
