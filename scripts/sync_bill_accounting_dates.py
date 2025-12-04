import logging
from odoo.exceptions import UserError, ValidationError

# --- CONFIGURATION ---
dry_run = False
# ---------------------

print(f"\n{'='*20} ROBUST SYNC (ID-BASED) {'='*20}")

# Get both posted and draft bills
posted_bills = env['account.move'].search([
    ('move_type', '=', 'in_invoice'),
    ('state', '=', 'posted'),
    ('invoice_date', '!=', False)
]).filtered(lambda b: b.date != b.invoice_date)

draft_bills = env['account.move'].search([
    ('move_type', '=', 'in_invoice'),
    ('state', '=', 'draft'),
    ('invoice_date', '!=', False)
]).filtered(lambda b: b.date != b.invoice_date)

print(f"Found {len(posted_bills)} posted bills and {len(draft_bills)} draft bills to process.\n")

success_count = 0
error_count = 0
warning_count = 0
skip_count = 0

# Process draft bills first (simpler - just update date)
for bill in draft_bills:
    bill_name = bill.name
    target_date = bill.invoice_date
    original_date = bill.date

    print(f"[{bill.id}] {bill_name} (DRAFT):")

    try:
        if dry_run:
            print(f"   > [Plan] Would update from {original_date} to {target_date}")
            print("   > [Plan] Dry Run - skipping execution.")
            continue

        bill.write({'date': target_date})
        print(f"   > [Action] Updated from {original_date} to {target_date}")
        success_count += 1
        
    except Exception as e:
        print(f"   !!! FAILED: {e}")
        import traceback
        print(f"   !!! Traceback: {traceback.format_exc()}")
        error_count += 1

# Process posted bills (complex - handle payments)
bills = posted_bills

for bill in bills:
    bill_name = bill.name
    target_date = bill.invoice_date
    initial_payment_state = bill.payment_state 
    bank_account = bill.partner_bank_id
    bank_needs_unarchiving = bank_account and not bank_account.active

    print(f"[{bill.id}] {bill_name}:")

    with env.cr.savepoint():
        try:
            # --- EDGE CASE: Check if bill is locked by fiscal year ---
            if hasattr(bill, 'fiscal_position_id') and bill.fiscal_position_id:
                lock_date = bill.company_id.fiscalyear_lock_date or bill.company_id.period_lock_date
                if lock_date and target_date <= lock_date:
                    print(f"   !!! SKIP: Target date {target_date} is locked by fiscal year/period (lock date: {lock_date})")
                    skip_count += 1
                    continue

            # --- EDGE CASE: Check for asset entries or recurring entries ---
            # Check if account.asset module is installed and has asset lines
            has_asset_lines = False
            if 'asset_ids' in bill.line_ids._fields:
                has_asset_lines = bill.line_ids.filtered(lambda l: l.asset_ids)
                if has_asset_lines:
                    print(f"   !!! WARNING: Bill has {len(has_asset_lines)} asset line(s). Asset entries may need manual review.")
                    warning_count += 1
            
            # --- STEP 1: BANK ---
            if bank_needs_unarchiving:
                if not dry_run: bank_account.active = True
                print(f"   > [Bank] Un-archived temporarily.")

            # --- STEP 2: IDENTIFY PAYMENTS (THE FIX) ---
            # EDGE CASE: Multiple payable lines (e.g., multi-currency, rounding)
            payable_lines = bill.line_ids.filtered(lambda l: l.account_id.account_type == 'liability_payable')
            
            if not payable_lines:
                print(f"   !!! WARNING: No payable lines found. Checking deprecated account type...")
                # Fallback for older Odoo versions or custom configurations
                payable_lines = bill.line_ids.filtered(lambda l: l.account_id.account_type in ('payable', 'liability_payable'))
            
            if not payable_lines:
                print(f"   !!! ERROR: No payable account lines found. Skipping.")
                skip_count += 1
                continue
            
            if len(payable_lines) > 1:
                print(f"   > [Info] Multiple payable lines detected ({len(payable_lines)}). Processing all.")
            
            # Collect all partial reconciliations from all payable lines
            all_partials = env['account.partial.reconcile']
            payment_line_ids = []
            
            for payable_line in payable_lines:
                partials = payable_line.matched_debit_ids | payable_line.matched_credit_ids
                all_partials |= partials
                linked_lines = partials.mapped('debit_move_id') | partials.mapped('credit_move_id')
                payment_lines = linked_lines - payable_line
                payment_line_ids.extend(payment_lines.ids)
            
            # Remove duplicates while preserving order
            payment_line_ids = list(dict.fromkeys(payment_line_ids))
            num_payments = len(payment_line_ids)

            if num_payments > 0:
                print(f"   > [Payments] Found {num_payments} payment line(s) (IDs: {payment_line_ids})")

            # --- EDGE CASE: Check if payments are from locked period ---
            if num_payments > 0 and not dry_run:
                payment_lines = env['account.move.line'].browse(payment_line_ids)
                locked_payments = payment_lines.filtered(lambda l: l.move_id.state != 'posted')
                if locked_payments:
                    print(f"   !!! WARNING: {len(locked_payments)} payment line(s) are from non-posted moves. This may cause issues.")

            if dry_run:
                print("   > [Plan] Dry Run - skipping execution.")
                continue 

            # --- STEP 3: UNLINK ---
            if num_payments > 0:
                # EDGE CASE: Store partial reconciliation details for audit trail
                partial_details = [(p.debit_move_id.id, p.credit_move_id.id, p.amount) for p in all_partials]
                print(f"   > [Info] Unlinking {len(all_partials)} partial reconciliation(s)")
                
                for payable_line in payable_lines:
                    if payable_line.matched_debit_ids or payable_line.matched_credit_ids:
                        payable_line.remove_move_reconcile()
                
                print("   > [Action] Payments Unlinked.")

            # --- STEP 4: UPDATE ---
            # EDGE CASE: Store original values for rollback capability
            original_name = bill.name
            original_date = bill.date
            
            bill.button_draft()
            
            # EDGE CASE: Check if target date would cause sequencing issues
            same_date_bills = env['account.move'].search([
                ('move_type', '=', 'in_invoice'),
                ('date', '=', target_date),
                ('id', '!=', bill.id),
                ('company_id', '=', bill.company_id.id)
            ], limit=1)
            
            if same_date_bills:
                print(f"   > [Info] Other bills exist with date {target_date}. Sequence will auto-adjust.")
            
            bill.write({'name': '/', 'date': target_date})
            bill.action_post()
            print(f"   > [Action] Updated from {original_date} to {target_date}. Ref: {original_name} → {bill.name}")

            # --- STEP 5: RELINK (THE FIX) ---
            if num_payments > 0:
                # 1. Fetch fresh Bill Payable Lines
                new_payable_lines = bill.line_ids.filtered(lambda l: l.account_id.account_type in ('liability_payable', 'payable'))
                
                if not new_payable_lines:
                    raise ValidationError("Payable lines disappeared after re-posting. This should not happen.")
                
                # 2. Fetch fresh Payment Lines using the IDs we saved
                lines_to_relink = env['account.move.line'].browse(payment_line_ids)
                
                # EDGE CASE: Verify payment lines still exist and are valid
                invalid_lines = lines_to_relink.filtered(lambda l: not l.exists() or l.reconciled)
                if invalid_lines:
                    print(f"   !!! WARNING: {len(invalid_lines)} payment line(s) are invalid or already reconciled")
                    lines_to_relink = lines_to_relink - invalid_lines
                
                if not lines_to_relink:
                    print(f"   !!! WARNING: No valid payment lines to relink")
                else:
                    # 3. Reconcile
                    try:
                        (new_payable_lines | lines_to_relink).reconcile()
                        print(f"   > [Action] {len(lines_to_relink)} payment line(s) relinked successfully.")
                    except Exception as reconcile_error:
                        # EDGE CASE: Partial reconciliation might fail, try manual reconciliation
                        print(f"   !!! WARNING: Auto-reconcile failed ({reconcile_error}). Attempting manual reconciliation...")
                        for pline in new_payable_lines:
                            for payment_line in lines_to_relink:
                                if pline.account_id == payment_line.account_id and not payment_line.reconciled:
                                    try:
                                        (pline | payment_line).reconcile()
                                        print(f"   > [Action] Manually reconciled line {payment_line.id}")
                                    except Exception as e:
                                        print(f"   !!! WARNING: Failed to reconcile line {payment_line.id}: {e}")

            # --- STEP 6: VERIFY ---
            bill.invalidate_recordset(['payment_state'])  # EDGE CASE: Force recompute
            
            if bill.payment_state == 'not_paid' and initial_payment_state != 'not_paid':
                 print(f"   !!! WARNING: Bill dropped to 'not_paid' (Expected: {initial_payment_state}) !!!")
                 warning_count += 1
            else:
                 print(f"   > [Check] State OK ({bill.payment_state})")

            # --- EDGE CASE: Verify accounting entries integrity ---
            debit_total = sum(bill.line_ids.mapped('debit'))
            credit_total = sum(bill.line_ids.mapped('credit'))
            if abs(debit_total - credit_total) > 0.01:  # Allow for minor rounding
                print(f"   !!! WARNING: Unbalanced entry! Debit: {debit_total}, Credit: {credit_total}")
                warning_count += 1

            success_count += 1
            
        except Exception as e:
            print(f"   !!! FAILED: {e}")
            import traceback
            print(f"   !!! Traceback: {traceback.format_exc()}")
            error_count += 1
            
        finally:
            if bank_needs_unarchiving and bank_account.active:
                if not dry_run: bank_account.active = False
                print(f"   > [Bank] Re-archived.")

print(f"\n{'='*60}")
print(f"SUMMARY:")
print(f"  ✓ Success: {success_count}")
print(f"  ✗ Errors:  {error_count}")
print(f"  ⚠ Warnings: {warning_count}")
print(f"  ⊘ Skipped: {skip_count}")
print(f"{'='*60}\n")

if not dry_run:
    env.cr.commit()
    print("Changes committed.")
else:
    print("DRY RUN - No changes committed.")