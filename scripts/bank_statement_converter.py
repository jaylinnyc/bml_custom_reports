import pandas as pd
import openpyxl
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.utils import get_column_letter
from datetime import datetime
import os
from pathlib import Path
import re

class BankStatementConverter:
    def __init__(self):
        self.dataframes = []
    
    def find_column_by_keywords(self, columns, keywords):
        """Find a column that matches any of the keywords (substring match)"""
        for col in columns:
            col_lower = str(col).lower()
            for keyword in keywords:
                if keyword in col_lower:
                    return col
        return None
    
    def parse_date(self, date_str):
        """Parse various date formats and convert to DD-MM-YY"""
        if pd.isna(date_str) or date_str == '':
            return None
        
        date_str = str(date_str).strip()
        
        # List of date formats to try
        formats = [
            '%d-%b-%y',      # 01-Nov-25
            '%d/%m/%Y',      # 07/10/2025
            '%d/%m/%y',      # 07/10/25
            '%d-%m-%Y',      # 01-11-2025
            '%d-%m-%y',      # 01-11-25
            '%Y-%m-%d',      # 2025-11-01
            '%Y/%m/%d',      # 2025/11/01
            '%d.%m.%Y',      # 01.11.2025
            '%d.%m.%y',      # 01.11.25
            '%d %b %Y',      # 01 Nov 2025
            '%d %B %Y',      # 01 November 2025
            '%d/%m',         # 07/10 (will add current year)
        ]
        
        for fmt in formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                return parsed_date.strftime('%d-%m-%y')
            except ValueError:
                continue
        
        # Try to handle Thai Buddhist year (BE) - convert to AD
        try:
            # If the year is > 2500, it might be Thai year (BE)
            if '/' in date_str or '-' in date_str:
                parts = date_str.replace('-', '/').split('/')
                if len(parts) >= 3:
                    day, month, year = parts[0], parts[1], parts[2]
                    year_int = int(year)
                    # Thai year is 543 years ahead of AD
                    if year_int > 2500:
                        year_int -= 543
                    parsed_date = datetime(int(year_int), int(month), int(day))
                    return parsed_date.strftime('%d-%m-%y')
        except:
            pass
        
        # If all formats fail, return the original string
        print(f"Warning: Could not parse date '{date_str}'")
        return date_str
    
    def clean_float_value(self, value):
        """Clean and convert a value to float, handling various formats"""
        if pd.isna(value) or value == '':
            return 0
        
        value_str = str(value).strip()
        if not value_str or value_str.lower() == 'nan':
            return 0
        
        # Remove commas and spaces
        value_str = value_str.replace(',', '').replace(' ', '')
        
        try:
            return float(value_str)
        except:
            return 0
    
    def is_valid_transaction_row(self, row, date_col, debit_col, credit_col, desc_col):
        """Check if a row is a valid transaction"""
        # Must have a valid date
        date_value = row.get(date_col, '') if date_col else ''
        if pd.isna(date_value) or str(date_value).strip() == '':
            return False
        
        # Check if date can be parsed
        if self.parse_date(date_value) is None:
            return False
        
        # Must have at least one amount (debit or credit)
        # If one column is missing, just check the other
        debit = self.clean_float_value(row.get(debit_col, 0)) if debit_col else 0
        credit = self.clean_float_value(row.get(credit_col, 0)) if credit_col else 0
        
        # If both columns are missing, only check if one exists
        if not debit_col and not credit_col:
            return False
        
        if debit == 0 and credit == 0:
            return False
        
        # Skip common summary/total rows by checking description
        if desc_col:
            desc = str(row.get(desc_col, '')).lower()
            skip_keywords = ['total', 'subtotal', 'summary', 'balance', 'closing', 'opening',
                           'รวม', 'ยอดรวม', 'ยอด', 'สรุป', 'ปิด', 'เปิด']
            for keyword in skip_keywords:
                if keyword in desc:
                    return False
        
        return True
    
    def find_all_columns_by_keywords(self, columns, keywords):
        """Find all columns that match any of the keywords (substring match)"""
        matching_cols = []
        for col in columns:
            col_lower = str(col).lower()
            for keyword in keywords:
                if keyword in col_lower and col not in matching_cols:
                    matching_cols.append(col)
                    break
        return matching_cols
    
    def convert_generic(self, df):
        """Convert any bank statement format to Odoo format"""
        # Find date column - expanded Thai keywords
        date_col = self.find_column_by_keywords(df.columns, [
            'date', 'transaction date', 'effective date', 'วันที่', 'วันที่ทำ', 'วันทำ'
        ])
        
        # Find ALL description/detail/cheque related columns - expanded Thai keywords
        desc_keywords = [
            'description', 'detail', 'transaction description', 'tr description',
            'memo', 'รายละเอียด', 'หมายเหตุ', 'รายการ', 'รายละเอียดรายการ',
            'label', 'additional', 'enrichment', 'remarks'
        ]
        desc_cols = self.find_all_columns_by_keywords(df.columns, desc_keywords)
        
        cheque_keywords = [
            'cheque', 'cheque no', 'cheque number', 'check', 'check no',
            'เช็ค', 'เลขเช็ค', 'เล่มเล้ว'
        ]
        cheque_cols = self.find_all_columns_by_keywords(df.columns, cheque_keywords)
        
        # Find debit/withdrawal column - expanded Thai keywords
        debit_col = self.find_column_by_keywords(df.columns, [
            'debit', 'withdrawal', 'debit amount', 'amount', 'pay', 'paid', 'ถอน', 'จ่าย', 'ออก'
        ])
        
        # Find credit/deposit column - expanded Thai keywords
        credit_col = self.find_column_by_keywords(df.columns, [
            'credit', 'deposit', 'credit amount', 'received', 'ฝาก', 'รับ', 'เข้า'
        ])
        
        print(f"Mapped columns:")
        print(f"  Date: {date_col}")
        print(f"  Description: {desc_cols}")
        print(f"  Cheque: {cheque_cols}")
        print(f"  Debit: {debit_col}")
        print(f"  Credit: {credit_col}")
        
        result = []
        skipped_rows = 0
        
        for idx, row in df.iterrows():
            # Validate if this is a transaction row
            if not self.is_valid_transaction_row(row, date_col, debit_col, credit_col, desc_cols[0] if desc_cols else None):
                skipped_rows += 1
                continue
            
            # Parse date
            date_value = row.get(date_col, '') if date_col else ''
            date = self.parse_date(date_value)
            
            # Build comprehensive label from all relevant columns
            label_parts = []
            seen_values = set()  # To avoid duplicates
            
            # Add cheque numbers from all cheque columns
            for cheque_col in cheque_cols:
                cheque = str(row.get(cheque_col, '')).strip()
                if cheque and cheque != '0' and cheque.lower() != 'nan' and cheque not in seen_values:
                    label_parts.append(f"Cheque #{cheque}")
                    seen_values.add(cheque)
            
            # Add descriptions from all description columns
            for desc_col in desc_cols:
                desc = str(row.get(desc_col, '')).strip()
                if desc and desc.lower() != 'nan' and desc not in seen_values:
                    label_parts.append(desc)
                    seen_values.add(desc)
            
            description = ' / '.join(label_parts) if label_parts else ''
            
            # Get debit and credit values using clean float conversion
            # If column doesn't exist, value will be empty/0
            debit = self.clean_float_value(row.get(debit_col, 0)) if debit_col else 0
            credit = self.clean_float_value(row.get(credit_col, 0)) if credit_col else 0
            
            # Handle negative values (convert negative to positive for appropriate column)
            if debit < 0:
                credit = abs(debit)
                debit = 0
            if credit < 0:
                debit = abs(credit)
                credit = 0
            
            # Always output values, even if empty/0
            result.append({
                'date': date,
                'label': description,
                'debit': debit if debit > 0 else '',
                'credit': credit if credit > 0 else ''
            })
        
        if skipped_rows > 0:
            print(f"Skipped {skipped_rows} non-transaction rows")
        
        return pd.DataFrame(result)
        
        print(f"Mapped columns:")
        print(f"  Date: {date_col}")
        print(f"  Description: {desc_cols}")
        print(f"  Cheque: {cheque_cols}")
        print(f"  Debit: {debit_col}")
        print(f"  Credit: {credit_col}")
        
        result = []
        skipped_rows = 0
        
        for idx, row in df.iterrows():
            # Validate if this is a transaction row
            if not self.is_valid_transaction_row(row, date_col, debit_col, credit_col, desc_cols[0] if desc_cols else None):
                skipped_rows += 1
                continue
            
            # Parse date
            date_value = row.get(date_col, '') if date_col else ''
            date = self.parse_date(date_value)
            
            # Build comprehensive label from all relevant columns
            label_parts = []
            seen_values = set()  # To avoid duplicates
            
            # Add cheque numbers from all cheque columns
            for cheque_col in cheque_cols:
                cheque = str(row.get(cheque_col, '')).strip()
                if cheque and cheque != '0' and cheque.lower() != 'nan' and cheque not in seen_values:
                    label_parts.append(f"Cheque #{cheque}")
                    seen_values.add(cheque)
            
            # Add descriptions from all description columns
            for desc_col in desc_cols:
                desc = str(row.get(desc_col, '')).strip()
                if desc and desc.lower() != 'nan' and desc not in seen_values:
                    label_parts.append(desc)
                    seen_values.add(desc)
            
            description = ' / '.join(label_parts) if label_parts else ''
            
            # Get debit and credit values
            debit = row.get(debit_col, 0) if debit_col else 0
            credit = row.get(credit_col, 0) if credit_col else 0
            
            # Clean the values
            try:
                debit = float(debit) if debit and str(debit).strip() else 0
            except:
                debit = 0
            
            try:
                credit = float(credit) if credit and str(credit).strip() else 0
            except:
                credit = 0
            
            result.append({
                'date': date,
                'label': description,
                'debit': debit if debit > 0 else '',
                'credit': credit if credit > 0 else ''
            })
        
        if skipped_rows > 0:
            print(f"Skipped {skipped_rows} non-transaction rows")
        
        return pd.DataFrame(result)
    
    def find_header_row(self, df):
        """Try to find the actual header row in a messy file"""
        # Look for a row that has meaningful column names (not mostly NaN, numbers, or generic names)
        for idx, row in df.iterrows():
            # Skip completely empty rows
            non_null_values = [x for x in row if pd.notna(x) and str(x).strip() != '']
            if len(non_null_values) < 2:
                continue
            
            row_str = ' '.join([str(x).lower() for x in row if pd.notna(x) and x != ''])
            
            # Check if row contains common header keywords
            header_keywords = ['date', 'description', 'detail', 'debit', 'credit', 'withdrawal', 
                             'deposit', 'amount', 'cheque', 'check', 'balance', 'pay',
                             'วัน', 'รายละเอียด', 'จ่าย', 'รับ', 'เบิก', 'วิธี', 'เล่มที่', 'เล่มเล้ว', 'รายการ']
            
            keyword_count = sum(1 for keyword in header_keywords if keyword in row_str)
            
            # If row has at least 1 header keyword, it's likely the header
            if keyword_count > 0:
                return idx
            
            # Also check if the row looks like it has numeric data (transaction data) after column names
            # If we have mixed text and numbers, it might be close to header
            has_text = any(isinstance(x, str) and len(str(x).strip()) > 2 for x in row)
            if has_text:
                # This might be a header row even without keywords
                first_non_empty = None
                for i, val in enumerate(row):
                    if pd.notna(val) and str(val).strip() != '':
                        first_non_empty = val
                        break
                # If first column looks like it could be a date or description column
                if first_non_empty and len(str(first_non_empty).strip()) > 1:
                    return idx
        
        return 0  # Default to first row
    
    def read_excel_with_merged_headers(self, file_path, header_idx):
        """Read Excel file handling merged cells in headers"""
        try:
            wb = openpyxl.load_workbook(file_path)
            ws = wb.active
            
            # Get merged cells info
            merged_ranges = {}
            for merged_range in ws.merged_cells.ranges:
                min_col = merged_range.min_col
                max_col = merged_range.max_col
                min_row = merged_range.min_row
                max_row = merged_range.max_row
                
                for col in range(min_col, max_col + 1):
                    merged_ranges[col] = {
                        'value': ws.cell(min_row, min_col).value,
                        'min_row': min_row,
                        'max_row': max_row
                    }
            
            # Read first header row
            header_row_1 = []
            for col in range(1, ws.max_column + 1):
                cell_value = ws.cell(header_idx + 1, col).value
                header_row_1.append(str(cell_value) if cell_value else '')
            
            # Read second header row (sub-columns)
            header_row_2 = []
            if header_idx + 2 <= ws.max_row:
                for col in range(1, ws.max_column + 1):
                    cell_value = ws.cell(header_idx + 2, col).value
                    header_row_2.append(str(cell_value) if cell_value else '')
            
            # Combine headers
            final_columns = []
            for col_idx, (h1, h2) in enumerate(zip(header_row_1, header_row_2)):
                h1 = h1.strip() if h1 else ''
                h2 = h2.strip() if h2 else ''
                
                # If both exist and are different, combine them
                if h1 and h2 and h1 != h2 and h2.lower() != 'unnamed':
                    combined = f"{h1} {h2}"
                elif h1:
                    combined = h1
                elif h2:
                    combined = h2
                else:
                    combined = f"Unnamed: {col_idx}"
                
                final_columns.append(combined)
            
            # Read data starting from row after headers
            data_rows = []
            for row_idx in range(header_idx + 3, ws.max_row + 1):
                row_data = []
                for col in range(1, ws.max_column + 1):
                    cell_value = ws.cell(row_idx, col).value
                    row_data.append(cell_value)
                data_rows.append(row_data)
            
            # Create DataFrame
            df = pd.DataFrame(data_rows, columns=final_columns)
            wb.close()
            return df
            
        except Exception as e:
            print(f"Warning: Could not read merged headers: {e}")
            return None
    
    def convert_file(self, file_path):
        """Convert a bank statement file"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            print(f"Error: File '{file_path}' not found")
            return None
        
        # Read the file
        if file_path.suffix.lower() == '.csv':
            df = pd.read_csv(file_path, encoding='utf-8')
        elif file_path.suffix.lower() in ['.xlsx', '.xls']:
            # Read without assuming first row is header
            df_raw = pd.read_excel(file_path, header=None)
            
            # Find the actual header row
            header_idx = self.find_header_row(df_raw)
            
            print(f"Scanning for header... trying row {header_idx + 1}")
            
            if header_idx > 0:
                print(f"Found header at row {header_idx + 1}")
                
                # Try to read with merged header handling
                df_merged = self.read_excel_with_merged_headers(str(file_path), header_idx)
                if df_merged is not None:
                    df = df_merged
                    print("Merged headers detected and combined")
                else:
                    df = pd.read_excel(file_path, header=header_idx)
            else:
                print("Using row 1 as header")
                df = pd.read_excel(file_path)
        else:
            print(f"Error: Unsupported file format '{file_path.suffix}'")
            return None
        
        print(f"Detected columns: {', '.join([str(c) for c in df.columns])}")
        
        # Convert using generic format
        result_df = self.convert_generic(df)
        
        if result_df.empty:
            print("Error: No transactions found in the file")
            print("The file might have an unusual structure.")
            print("Try: Remove title rows, keep only header + data rows, then try again.")
            return None
        
        # Convert date column to datetime for sorting
        result_df['date_sort'] = pd.to_datetime(result_df['date'], format='%d-%m-%y', errors='coerce')
        
        # Sort by date
        result_df = result_df.sort_values('date_sort').reset_index(drop=True)
        
        # Drop the temporary sorting column
        result_df = result_df.drop('date_sort', axis=1)
        
        # Rename columns to the standard format
        result_df.columns = ['date', 'label', 'debit', 'credit']
        
        return result_df
    
    def save_to_excel(self, df, output_path):
        """Save dataframe to Excel file"""
        output_path = Path(output_path)
        
        # Create Excel workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        
        # Write header
        headers = ['date', 'label', 'debit', 'credit']
        for col_idx, header in enumerate(headers, 1):
            ws.cell(row=1, column=col_idx, value=header)
        
        # Write data
        for row_idx, row in enumerate(df.values, 2):
            for col_idx, value in enumerate(row, 1):
                ws.cell(row=row_idx, column=col_idx, value=value)
        
        # Adjust column widths
        ws.column_dimensions['A'].width = 12  # date
        ws.column_dimensions['B'].width = 40  # label
        ws.column_dimensions['C'].width = 15  # debit
        ws.column_dimensions['D'].width = 15  # credit
        
        wb.save(output_path)
        print(f"Converted file saved: {output_path}")

def main():
    converter = BankStatementConverter()
    
    print("=" * 60)
    print("Bank Statement Converter for Odoo")
    print("=" * 60)
    print("Converts any bank statement format to Odoo import format")
    print("Output format: date (DD-MM-YY), label, debit, credit\n")
    
    while True:
        file_path = input("Enter the path to the bank statement file (or 'quit' to exit): ").strip()
        
        if file_path.lower() == 'quit':
            print("Exiting...")
            break
        
        if not file_path:
            print("Please enter a valid file path\n")
            continue
        
        # Convert the file
        result_df = converter.convert_file(file_path)
        
        if result_df is not None:
            # Determine output file path
            file_path_obj = Path(file_path)
            output_path = file_path_obj.parent / f"{file_path_obj.stem}_converted.xlsx"
            
            # Save to Excel
            converter.save_to_excel(result_df, output_path)
            
            print(f"Conversion completed successfully!")
            print(f"Total transactions: {len(result_df)}")
            print(f"\nPreview of converted data:")
            print(result_df.head(10).to_string())
        
        print("\n")

if __name__ == "__main__":
    main()
