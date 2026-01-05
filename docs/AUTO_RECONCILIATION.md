# Auto-Reconciliation Guide

## Overview

The **Auto Reconcile** button in the bank reconciliation widget triggers an intelligent 4-strategy matching process to automatically match bank statement lines with journal entries.

---

## Matching Strategies (Priority Order)

### Strategy 1: Exact Match with Reference ⭐ Highest Priority

| Criteria | Description |
|----------|-------------|
| Journal | Same bank journal |
| Date | Exact date match |
| Amount | Exact amount match |
| Reference | Statement `payment_ref` contains invoice number |

**Use case**: When bank description includes invoice number like "Payment for INV/2026/001"

---

### Strategy 2: Exact Date Match

| Criteria | Description |
|----------|-------------|
| Journal | Same bank journal |
| Date | Exact date match |
| Amount | Exact amount match |

**Use case**: Clean matches where only one entry exists for that amount on that date

---

### Strategy 3: Amount Match with Date Tolerance (±7 days)

| Criteria | Description |
|----------|-------------|
| Journal | Same bank journal |
| Date | Within ±7 days |
| Amount | Exact amount match |

**Prioritization** (when multiple same-amount entries exist):
1. **Reference match** first (if `payment_ref` contains invoice number)
2. **Closest date** second
3. **Oldest entry (FIFO)** as tiebreaker

---

### Strategy 4: Combined/Partial Match (±30 days)

| Criteria | Description |
|----------|-------------|
| Journal | Same bank journal |
| Date | Within ±30 days |
| Amount | Sum of multiple items = statement amount |

- Searches up to **15 candidate entries**
- Tries combinations of 1, 2, 3 items, then greedy algorithm for 4+
- Prioritizes combinations with reference matches

---

## Reference Matching Logic

The system extracts and matches invoice numbers using these patterns:

| Pattern | Examples |
|---------|----------|
| `INV-xxx` | INV-001, INV/2026/001 |
| `SI-xxx` | SI-001, SI/2026/001 |
| `Numeric (4+ digits)` | 20260001, 123456 |

Reference matching checks:
- Statement `payment_ref` contains journal entry's `move_name`
- Statement `payment_ref` contains journal entry's `ref`
- Journal entry's reference contains statement's `payment_ref`

---

## What Gets Matched

✅ **Included:**
- Journal items with matching `journal_id` (same bank account)
- Unreconciled items only
- Items in `draft` or `posted` state
- Accounts marked as reconcilable

❌ **Excluded:**
- Statement lines themselves (prevents self-reconciliation)
- Cash/bank suspense accounts
- Already reconciled items

---

## Score-Based Selection

When multiple candidates have the same amount, the system scores them:

| Factor | Weight | Description |
|--------|--------|-------------|
| Reference match | Highest | Invoice number found in payment_ref |
| Date proximity | Medium | Closer dates preferred |
| FIFO | Lowest | Older entries preferred (tiebreaker) |

---

## Technical Details

### Files
- **Button UI**: `static/src/js/bank_rec_auto_reconcile.js`
- **Button Template**: `static/src/xml/bank_rec_auto_reconcile.xml`
- **Logic**: `models/account_bank_statement.py`

### Key Methods
- `action_manual_auto_reconcile()` - Entry point from button click
- `_try_auto_reconcile_statement_lines()` - Main matching logic
- `_process_auto_reconcile_matches()` - Process SQL results
- `_find_matching_combination()` - Combined match algorithm

### SQL Joins
The `date` field is accessed via join with `account_move` table because `account.bank.statement.line` inherits from `account.move`:

```sql
JOIN account_move st_move ON st_line.move_id = st_move.id
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 19.0.1.5.0 | 2026-01-05 | Added reference matching, score-based selection, improved combined matching |
| 19.0.1.4.0 | 2026-01-04 | Fixed SQL date field issue, added Auto Reconcile button |
