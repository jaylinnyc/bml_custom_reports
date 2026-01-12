#!/usr/bin/env python3
"""Quick debug test"""
import pandas as pd
import base64
import sys
sys.path.insert(0, '/Users/Jay/development/git/nexus/panya19prod/jaylinnyc/bml_custom_reports')

from utils.thai_bank_converter import ThaiBankStatementConverter

# Read CSV
with open('demo_data/CSV 1-NOV 2025 StatementInquiry_01122025_154324.csv', 'rb') as f:
    file_data = f.read()

file_base64 = base64.b64encode(file_data).decode('utf-8')

converter = ThaiBankStatementConverter()
result = converter.convert_file(file_base64, 'test.csv')

print(f"Result type: {type(result)}")
print(f"Result length: {len(result) if isinstance(result, list) else 'N/A'}")
print(f"Result: {result}")
