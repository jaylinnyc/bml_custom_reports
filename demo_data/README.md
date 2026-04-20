# Demo Data Test Files

This directory contains sample Thai bank statement files used for testing the bank statement parser.

## Test Files

Each file represents a different bank statement format that the parser should handle:

1. **2601 22 CA.xls** - Single transaction withdrawal (SMS Alert Fee)
2. **ACCHIST_260112122148.xlsx** - Account history with 2 transactions
3. **CSV 1-NOV 2025 StatementInquiry_01122025_154324.csv** - CSV format with 3 transactions
4. **HISTSTMT_RPT2601121214393550_260112121449101 1-11 Jan 2026.xlsx** - Historical statement with 3 transactions
5. **PC6901-001.xlsx** - Petty cash format with 11 transactions
6. **Petty Cash 01-080126.xlsx** - Detailed petty cash with 35 transactions
7. **StatementInquiry_05112025_163844 (SAVING Oct 2025).xlsx** - Savings account with 5 transactions
8. **StatementInquiry_12012026_121809 BAY Saving 1-12 Jan 2026.xlsx** - BAY bank savings with 4 transactions
9. **XLS-0538541974 CA-0101 to 100126.xls** - Current account with 48 transactions
10. **XLS-0538547468 SA-0101 to 100126.xls** - Savings account with 25 transactions

## Running Tests

### Quick Test (Recommended)

To test the parser against all demo files and verify backward compatibility:

```bash
# Activate the virtual environment
cd /path/to/jaylinnyc/bml_custom_reports
source .test_venv/bin/activate

# Run the validation test (compares against expected results)
python scripts/test_with_validation.py
```

This test will:
- Load each file in demo_data/
- Parse it using the actual converter (utils/thai_bank_converter.py)
- Compare transaction counts against expected values in `expected_test_results.json`
- Report any failures or regressions
- **Exit with code 1 if any test fails or regression is detected**

### Alternative Tests

```bash
# Simple test without validation (just checks for errors)
python scripts/test_all_with_actual_converter.py

# Test individual file
python scripts/quick_test_fix.py  # Tests only 2601 22 CA.xls
```

### Expected Results

The file `expected_test_results.json` contains the ground truth for each test file, including:
- Expected transaction count
- Total debit amount
- Total credit amount
- Net balance change

**Always update `expected_test_results.json` after verifying that parser changes are correct and intentional.**

## Adding New Test Files

1. Add your new bank statement file to this directory
2. Run the test script to see the parsed results
3. If results are correct, update `expected_test_results.json` with the new file's expected values
4. Commit both the new file and updated expected results

## Notes

- All tests must pass before committing changes to the parser
- If transaction counts change, investigate whether it's a fix (intended) or a regression (bug)
- The parser should gracefully handle various Thai bank formats (SCB, BAY, KBank, etc.)
