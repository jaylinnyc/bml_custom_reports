# Bill Date Sync Script

## Purpose

One-time utility script to synchronize accounting dates with invoice dates for vendor bills in Odoo 19.

**Status:** ✅ Completed on December 4, 2025

---

## Background

Previously, vendor bills could have mismatched dates:
- **Bill Date** (`invoice_date`) - The date on the vendor's invoice
- **Accounting Date** (`date`) - The date used in journal entries

This mismatch caused reporting inconsistencies and confusion.

---

## Solution Implemented

### 1. **Automatic Prevention (Permanent)**
The `bml_custom_reports` module now automatically syncs these dates:
- New bills: Accounting date auto-copies from bill date on creation
- Existing bills: When bill date changes, accounting date updates automatically
- UI: Accounting date field is readonly for vendor bills

**Location:** `models/account_move.py` and `views/account_move_views.xml`

### 2. **One-Time Cleanup (This Script)**
This script fixed existing bills with mismatched dates while preserving:
- ✅ Payment reconciliations
- ✅ Payment states (paid/in_payment/not_paid)
- ✅ Accounting integrity (balanced entries)

---

## What the Script Does

### For Draft Bills:
- Simply updates the accounting date to match bill date
- Fast and straightforward

### For Posted Bills:
1. Identifies payment reconciliations
2. Unlinks payments temporarily
3. Resets bill to draft
4. Updates accounting date to match bill date
5. Re-posts the bill
6. Restores all payment reconciliations
7. Verifies payment state and accounting balance

---

## Usage

**⚠️ This script should only be run ONCE for cleanup of existing data.**

```bash
# From Odoo shell
odoo-bin shell -d your_database

# Run the script
exec(open('/path/to/sync_bill_accounting_dates.py').read())
```

### Configuration
Edit line 5 in the script:
```python
dry_run = False  # Set to True for testing, False for execution
```

---

## Results from Last Run

- **Processed:** 119 posted bills + draft bills
- **Success Rate:** 100%
- **Errors:** 0
- **Warnings:** 0

All vendor bills now have synchronized dates.

---

## Edge Cases Handled

1. ✅ Multiple payable lines (multi-currency, rounding)
2. ✅ Fiscal year/period locks
3. ✅ Asset-linked bills
4. ✅ Archived bank accounts
5. ✅ Multiple partial payments
6. ✅ Invalid/deleted payment lines
7. ✅ Reconciliation failures with fallback logic
8. ✅ Payment state verification
9. ✅ Accounting entry balance validation
10. ✅ Non-posted payment moves
11. ✅ Odoo 19 account type changes (`payable` → `liability_payable`)

---

## Future Maintenance

**This script is no longer needed!**

The module now prevents date mismatches automatically. All new vendor bills will have synchronized dates by default.

---

## Technical Details

### Files Modified by Script:
- `account.move` records (journal entries)
- `account.move.line` records (journal items)
- `account.partial.reconcile` records (payment reconciliations)

### Safety Features:
- Uses database savepoints (auto-rollback on errors)
- Dry-run mode for testing
- Detailed logging for each bill
- Individual bill error handling (one failure doesn't stop others)

### Performance:
- Processes one bill at a time for safety
- ~119 bills processed successfully
- Average time: ~1-2 seconds per posted bill, <1 second per draft bill

---

## Support

For questions or issues, refer to:
- Main module: `bml_custom_reports`
- Model: `models/account_move.py`
- View: `views/account_move_views.xml`
