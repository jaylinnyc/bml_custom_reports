#!/usr/bin/env python3
"""Find which transaction is being skipped"""
import pandas as pd
import sys
import os
import types

sys.path.insert(0, '.')

# Mock Odoo
odoo_mock = types.ModuleType('odoo')
odoo_exceptions_mock = types.ModuleType('odoo.exceptions')
odoo_exceptions_mock.UserError = Exception
odoo_mock.exceptions = odoo_exceptions_mock
sys.modules['odoo'] = odoo_mock
sys.modules['odoo.exceptions'] = odoo_exceptions_mock

from utils.thai_bank_converter import ThaiBankStatementConverter

# Read raw file
df = pd.read_excel('demo_data/Petty Cash 01-080126.xlsx')

print('Raw file analysis:')
print(f'Total rows: {len(df)}')
print()

# Expected structure based on inspection
print('Row 2 should be opening balance "ยอดยกมา"')
if len(df) > 2:
    print(f'Row 2 Label: {df.iloc[2]["บริษัท ปัญญารักษา จำกัด"]}')
print()

print('Row 39 should be "Total" summary')
if len(df) > 39:
    print(f'Row 39 Label: {df.iloc[39]["บริษัท ปัญญารักษา จำกัด"]}')
print()

# Rows 3-38 should be transactions = 36 transactions
print('Transaction rows should be 3-38 = 36 transactions')
print()

# Now check what converter finds
converter = ThaiBankStatementConverter()
with open('demo_data/Petty Cash 01-080126.xlsx', 'rb') as f:
    file_data = f.read()

result = converter.convert_file(file_data, 'Petty Cash 01-080126.xlsx')
print(f'Converter found: {len(result)} transactions')
print()

print('Expected: 36 (rows 3-38 excluding opening balance and total)')
print(f'Actual: {len(result)}')
print(f'Missing: {36 - len(result)} transaction(s)')
