#!/usr/bin/env python3
"""
Inspect bank statement files to understand their structure
"""

import pandas as pd
from pathlib import Path

def inspect_file(file_path):
    """Inspect a single file to see its structure"""
    print(f"\n{'='*80}")
    print(f"File: {file_path.name}")
    print('='*80)
    
    try:
        # Read the file
        if file_path.suffix == '.csv':
            # Try different encodings
            for encoding in ['utf-8', 'tis-620', 'windows-874', 'latin-1']:
                try:
                    df = pd.read_csv(file_path, encoding=encoding)
                    print(f"✅ Loaded CSV with encoding: {encoding}")
                    break
                except:
                    continue
            else:
                print("❌ Could not load CSV")
                return
        else:
            df = pd.read_excel(file_path)
            print(f"✅ Loaded Excel file")
        
        print(f"\nShape: {df.shape[0]} rows × {df.shape[1]} columns")
        print(f"\nColumn names:")
        for i, col in enumerate(df.columns, 1):
            print(f"  {i}. {col}")
        
        print(f"\nFirst 10 rows:")
        print(df.head(10).to_string())
        
        print(f"\nColumn data types:")
        print(df.dtypes)
        
        print(f"\nNon-null counts:")
        print(df.count())
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def main():
    demo_data_path = Path(__file__).parent.parent / 'demo_data'
    files = sorted([f for f in demo_data_path.glob('*') if f.is_file() and not f.name.startswith('.')])
    
    print(f"Found {len(files)} files to inspect")
    
    for file_path in files:
        inspect_file(file_path)

if __name__ == '__main__':
    main()
