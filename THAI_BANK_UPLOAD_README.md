# Thai Bank Statement Upload Feature

## Overview
This feature adds automated Thai bank statement upload functionality to Odoo 19, specifically designed for Thai bank formats that include Thai language columns and various date formats.

## Features
- **Automatic Column Detection**: Detects date, description, debit/credit columns in both English and Thai
- **Thai Date Format Support**: Handles Buddhist Era (BE) dates and various Thai date formats
- **Multi-Format Support**: Supports Excel (.xlsx, .xls) and CSV files
- **Smart Transaction Detection**: Automatically filters out header rows and summary lines
- **Merged Header Support**: Handles Excel files with merged header cells
- **Duplicate Prevention**: Uses unique import IDs to prevent duplicate imports
- **Auto-Reconciliation**: Automatically attempts to match transactions after import

## Usage

1. **Navigate to Bank Statements**:
   - Go to: **Accounting → Bank → Statements**

2. **Click "Upload Thai Statement"**:
   - A wizard will open

3. **Fill in the form**:
   - **Bank Journal**: Select the bank account (required)
   - **Statement Reference**: Optional name for this statement
   - **Starting Balance**: Optional starting balance
   - **Ending Balance**: Optional ending balance
   - **Bank Statement File**: Upload your Thai bank statement file (required)

4. **Click "Upload and Import"**:
   - The system will automatically:
     - Detect columns in Thai or English
     - Parse dates in various formats (including Thai Buddhist calendar)
     - Extract transaction descriptions, cheque numbers, etc.
     - Create bank statement with all transactions
     - Run auto-reconciliation
     - Open the bank reconciliation widget

## Supported File Formats

### Excel Files (.xlsx, .xls)
- Automatically detects header row
- Handles merged header cells
- Supports multiple sheets (uses first sheet)

### CSV Files (.csv)
- UTF-8 encoding
- Comma-separated values

## Supported Column Names

The converter automatically detects columns with these keywords:

### Date Columns
- English: date, transaction date, effective date
- Thai: วันที่, วันที่ทำ, วันทำ

### Description Columns
- English: description, detail, transaction description, memo, label, remarks
- Thai: รายละเอียด, หมายเหตุ, รายการ

### Cheque Columns
- English: cheque, cheque no, check, check no
- Thai: เช็ค, เลขเช็ค

### Debit Columns
- English: debit, withdrawal, pay, paid
- Thai: ถอน, จ่าย, ออก

### Credit Columns
- English: credit, deposit, received
- Thai: ฝาก, รับ, เข้า

## Date Format Support

Supports these date formats:
- `01-Nov-25` (Thai bank standard)
- `07/10/2025` or `07/10/25`
- `01-11-2025` or `01-11-25`
- `2025-11-01`
- `01.11.2025`
- Buddhist Era (BE) years (automatically converts to AD)

## Technical Details

### File Structure
```
bml_custom_reports/
├── utils/
│   └── thai_bank_converter.py    # Core conversion logic
├── wizard/
│   ├── thai_bank_statement_upload_wizard.py       # Wizard model
│   └── thai_bank_statement_upload_wizard_views.xml # Wizard UI
├── models/
│   └── account_journal.py         # Journal extension
└── views/
    └── account_bank_statement_views.xml  # Button in list view
```

### Dependencies
- **Python Libraries**: `pandas`, `openpyxl`
- **Odoo Modules**: `account`, `account_accountant`

### Data Format
The converter transforms Thai bank statements to Odoo's expected format:
```python
{
    'date': date_object,           # Python date
    'payment_ref': 'Description',  # Transaction description
    'amount': 100.50,              # Signed amount (+ deposit, - withdrawal)
    'unique_import_id': 'unique_string',  # For duplicate detection
}
```

## Troubleshooting

### No transactions found
- Ensure the file contains a header row with recognizable column names
- Check that dates are in a supported format
- Verify amounts are in debit/credit or amount columns

### Date parsing errors
- Check if dates are in Buddhist Era (BE) - they should be automatically converted
- Ensure date format is consistent throughout the file

### Duplicate transactions
- The system automatically prevents duplicates using unique import IDs
- Duplicates are reported but not imported

## Future Enhancements
- Support for more bank-specific formats
- Balance validation
- Custom column mapping interface
- Support for additional Thai banks' specific formats
