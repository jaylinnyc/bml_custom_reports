#!/usr/bin/env python3
"""Trace exactly what the converter sees and processes"""
import sys
import os
import types
import io

sys.path.insert(0, '.')

# Mock Odoo
odoo_mock = types.ModuleType('odoo')
odoo_exceptions_mock = types.ModuleType('odoo.exceptions')
odoo_exceptions_mock.UserError = Exception
odoo_mock.exceptions = odoo_exceptions_mock
sys.modules['odoo'] = odoo_mock
sys.modules['odoo.exceptions'] = odoo_exceptions_mock

from utils.thai_bank_converter import ThaiBankStatementConverter
import pandas as pd

converter = ThaiBankStatementConverter()

with open('demo_data/Petty Cash 01-080126.xlsx', 'rb') as f:
    file_data = f.read()

# Simulate what convert_file does
df_raw = pd.read_excel(io.BytesIO(file_data), header=None)

print('Step 1: Find header row')
header_idx = converter.find_header_row(df_raw)
print(f'Header index: {header_idx}')
print()

print('Step 2: Read with correct header')
df = pd.read_excel(io.BytesIO(file_data), header=header_idx)
df.columns = df.columns.str.strip()

print(f'Columns after reading: {df.columns.tolist()}')
print(f'Total rows after header: {len(df)}')
print()

print('First 5 rows:')
for i in range(min(5, len(df))):
    print(f'Row {i}: {df.iloc[i].to_dict()}')
print()

print('Last 3 rows:')
for i in range(max(0, len(df)-3), len(df)):
    print(f'Row {i}: {df.iloc[i].to_dict()}')
print()

# Now check validation for each row
date_col = converter.find_column_by_keywords(df.columns, [
    'date', 'transaction date', 'effective date'
])
desc_cols = converter.find_all_columns_by_keywords(df.columns, [
    'description', 'detail', 'transaction description', 'tr description',
    'memo', 'label', 'additional', 'enrichment', 'remarks'
])
debit_col = converter.find_column_by_keywords(df.columns, ['withdrawal', 'debit'])
credit_col = converter.find_column_by_keywords(df.columns, ['deposit', 'credit'])

print(f'Date column: {date_col}')
print(f'Desc columns: {desc_cols}')
print(f'Debit column: {debit_col}')
print(f'Credit column: {credit_col}')
print()

desc_col = desc_cols[0] if desc_cols else None

print('Checking validation for each row:')
print('='*80)

valid_count = 0
for idx, row in df.iterrows():
    is_valid = converter.is_valid_transaction_row(row, date_col, debit_col, credit_col, desc_col)
    
    if desc_col:
        desc_val = str(row.get(desc_col, ''))
        
        if not is_valid:
            print(f'Row {idx} SKIPPED: {desc_val[:70]}')
        else:
            valid_count += 1

print()
print(f'Valid transactions: {valid_count}')
print(f'Expected: 36 (rows 1-36 after skipping opening balance row 0 and total row 37)')
