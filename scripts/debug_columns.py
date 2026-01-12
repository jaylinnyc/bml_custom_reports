#!/usr/bin/env python3
import pandas as pd

# Simulate the converter logic
df = pd.read_csv('demo_data/CSV 1-NOV 2025 StatementInquiry_01122025_154324.csv')
df.columns = df.columns.str.strip()

print('Columns after strip:', list(df.columns))
print()

# Check for date column
date_keywords = ['date', 'transaction date', 'effective date']
date_col = None
for col in df.columns:
    col_lower = str(col).lower()
    for keyword in date_keywords:
        if keyword in col_lower:
            date_col = col
            break
    if date_col:
        break

print(f'Found date column: {date_col}')

# Check for debit/credit
debit_keywords = ['debit', 'withdrawal']
debit_col = None
for col in df.columns:
    col_lower = str(col).lower()
    for keyword in debit_keywords:
        if keyword in col_lower:
            debit_col = col
            break
    if debit_col:
        break

print(f'Found debit column: {debit_col}')

credit_keywords = ['credit', 'deposit']
credit_col = None
for col in df.columns:
    col_lower = str(col).lower()
    for keyword in credit_keywords:
        if keyword in col_lower:
            credit_col = col
            break
    if credit_col:
        break

print(f'Found credit column: {credit_col}')

# Check for amount column
if not debit_col and not credit_col:
    amount_keywords = ['amount']
    amount_col = None
    for col in df.columns:
        col_lower = str(col).lower()
        for keyword in amount_keywords:
            if keyword in col_lower:
                amount_col = col
                break
        if amount_col:
            break
    print(f'Found amount column: {amount_col}')
else:
    print('Skipping amount column search (debit or credit found)')
