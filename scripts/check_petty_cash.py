#!/usr/bin/env python3
"""Check Petty Cash file for transaction count discrepancy"""
import pandas as pd
import sys

df = pd.read_excel('demo_data/Petty Cash 01-080126.xlsx')

print(f'Total rows in file: {len(df)}')
print(f'Columns: {list(df.columns)}')
print()

# Find date column
date_cols = [c for c in df.columns if 'date' in str(c).lower()]
if date_cols:
    date_col = date_cols[0]
    print(f'Date column: {date_col}')
    
    # Count rows with non-null dates
    non_null_dates = df[date_col].notna().sum()
    print(f'Rows with non-null dates: {non_null_dates}')
    print()

# Show first and last 5 rows
print('First 5 rows:')
print(df.head())
print()
print('Last 5 rows:')
print(df.tail())
print()

# Look for potential summary rows
desc_cols = [c for c in df.columns if any(k in str(c).lower() for k in ['desc', 'detail', 'label', 'payment'])]
if desc_cols:
    desc_col = desc_cols[0]
    print(f'\nDescription column: {desc_col}')
    
    # Check for summary keywords in all descriptions
    for idx, row in df.iterrows():
        desc = str(row[desc_col]).lower()
        if any(k in desc for k in ['total', 'summary', 'balance', 'subtotal']):
            print(f'Row {idx+1} might be summary: {row[desc_col]}')

# Count transactions that have dates AND amounts
amount_cols = [c for c in df.columns if any(k in str(c).lower() for k in ['debit', 'credit', 'withdrawal', 'deposit', 'amount'])]
if date_cols and amount_cols:
    valid_txns = 0
    for idx, row in df.iterrows():
        if pd.notna(row[date_col]):
            has_amount = any(pd.notna(row[ac]) and row[ac] != 0 for ac in amount_cols)
            if has_amount:
                valid_txns += 1
    
    print(f'\nRows with date AND non-zero amount: {valid_txns}')
