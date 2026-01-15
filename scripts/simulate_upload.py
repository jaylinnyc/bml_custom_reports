#!/usr/bin/env python3
"""
Simulate the Thai bank statement upload process
Run in odoo.sh shell
"""

print("\n" + "="*70)
print("SIMULATING THAI BANK STATEMENT UPLOAD")
print("="*70)

# Get journal 61
journal = env['account.journal'].browse(61)
print(f"\nJournal: {journal.name} (ID: {journal.id})")
print(f"Default Account: {journal.default_account_id.code if journal.default_account_id else 'NOT SET'}")

# Create test transactions (simulating what the wizard does)
transactions = [
    {
        'date': '2026-01-15',
        'payment_ref': 'Test Payment 1',
        'amount': 1000.0,
        'unique_import_id': f"{journal.id}-20260115-1000-0",
    },
    {
        'date': '2026-01-15', 
        'payment_ref': 'Test Payment 2',
        'amount': -500.0,
        'unique_import_id': f"{journal.id}-20260115-500-1",
    }
]

statement_vals = {
    'reference': 'TEST UPLOAD',
    'journal_id': journal.id,
    'balance_start': 0.0,
    'balance_end_real': 500.0,
    'transactions': transactions,
}

print(f"\n📋 Statement values prepared:")
print(f"   Reference: {statement_vals['reference']}")
print(f"   Journal ID: {statement_vals['journal_id']}")
print(f"   Transactions: {len(transactions)}")

# Try to create the statement (same method the wizard uses)
print(f"\n🔄 Calling journal._create_bank_statements()...")
try:
    statement_ids, ignored_qty = journal._create_bank_statements([statement_vals])
    
    print(f"\n✅ Method returned:")
    print(f"   statement_ids: {statement_ids}")
    print(f"   ignored_qty: {ignored_qty}")
    
    if statement_ids:
        print(f"\n📄 Statement created successfully!")
        statements = env['account.bank.statement'].browse(statement_ids)
        
        for stmt in statements:
            print(f"\n   Statement ID: {stmt.id}")
            print(f"   Name: {stmt.name}")
            print(f"   Journal: {stmt.journal_id.code} - {stmt.journal_id.name} (ID: {stmt.journal_id.id})")
            print(f"   Date: {stmt.date}")
            print(f"   Lines count: {len(stmt.line_ids)}")
            
            if stmt.line_ids:
                print(f"\n   Statement lines:")
                for line in stmt.line_ids[:3]:  # Show first 3
                    print(f"     - {line.payment_ref}: {line.amount}")
        
        # Check where we'd redirect to
        print(f"\n🔄 Reconciliation redirect would use:")
        print(f"   Domain: [('statement_id', 'in', {statement_ids})]")
        
        # Test the domain
        lines = env['account.bank.statement.line'].search([('statement_id', 'in', statement_ids)])
        print(f"   Found {len(lines)} line(s) with this domain")
        
        # ROLLBACK - don't save test data
        env.cr.rollback()
        print(f"\n   ⚠️  Transaction rolled back (test only)")
        
    else:
        print(f"\n❌ No statement created!")
        print(f"   This means all {len(transactions)} transactions were ignored as duplicates")
        print(f"   ignored_qty: {ignored_qty}")
        
except Exception as e:
    print(f"\n❌ ERROR during statement creation:")
    print(f"   {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    env.cr.rollback()

print("\n" + "="*70)
print("Now try uploading a real file and compare with these results")
print("="*70 + "\n")
