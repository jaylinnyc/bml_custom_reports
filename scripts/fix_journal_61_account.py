#!/usr/bin/env python3
"""
Check and fix journal 61 account code issue
Copy-paste into odoo.sh shell
"""

print("\n" + "="*70)
print("CHECKING AND FIXING JOURNAL ID 61")
print("="*70)

journal = env['account.journal'].browse(61)
account = journal.default_account_id

print(f"\n❌ PROBLEM FOUND:")
print(f"   Account ID {account.id} has code: '{account.code}'")
print(f"   This is invalid - account codes cannot be 'False'")

print(f"\n📝 FIXING THE ACCOUNT CODE...")

# Generate a proper account code
# Find what code to use based on similar accounts
similar_accounts = env['account.account'].search([
    ('name', 'ilike', 'petty cash'),
    ('code', '!=', 'False')
], limit=5)

print(f"\nSimilar Petty Cash accounts:")
for acc in similar_accounts:
    print(f"  - {acc.code}: {acc.name}")

# Suggest a code
suggested_code = "108500"
print(f"\nSuggested new code: {suggested_code}")
print(f"\nTo fix this issue, you need to:")
print(f"1. Go to: Accounting > Configuration > Chart of Accounts")
print(f"2. Search for account: {account.name} (ID: {account.id})")
print(f"3. Change the Code from 'False' to '{suggested_code}' (or any unique code)")
print(f"4. Save")

# Or fix it directly here:
response = input("\nDo you want to fix it now? (yes/no): ")
if response.lower() == 'yes':
    # Check if code already exists
    existing = env['account.account'].search([('code', '=', suggested_code)])
    if existing:
        print(f"⚠️  Code {suggested_code} already exists, trying alternative...")
        suggested_code = "108600"
    
    account.write({'code': suggested_code})
    env.cr.commit()
    print(f"✅ FIXED! Account code changed to: {suggested_code}")
    
    # Test statement creation now
    print(f"\n\nTesting statement creation with fixed account...")
    try:
        test_vals = {
            'reference': 'TEST',
            'journal_id': journal.id,
            'balance_start': 0.0,
            'balance_end_real': 100.0,
            'transactions': [
                {
                    'date': '2026-01-15',
                    'payment_ref': 'Test transaction',
                    'amount': 100.0,
                    'unique_import_id': 'TEST-12345',
                }
            ],
        }
        
        statement_ids, ignored = journal._create_bank_statements([test_vals])
        
        if statement_ids:
            print(f"✅ SUCCESS! Statement created: {statement_ids}")
            stmt = env['account.bank.statement'].browse(statement_ids[0])
            print(f"   Statement: {stmt.name}")
            print(f"   Journal: {stmt.journal_id.name}")
            print(f"   Lines: {len(stmt.line_ids)}")
            
            # Rollback test
            env.cr.rollback()
            print(f"\n   (Test rolled back - try uploading again in UI)")
        else:
            print(f"⚠️  No statement created")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        env.cr.rollback()
else:
    print(f"\nPlease fix the account code manually as described above.")

print("\n" + "="*70)
