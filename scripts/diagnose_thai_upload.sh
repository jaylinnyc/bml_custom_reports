#!/bin/bash
# Diagnostic script for Thai Bank Statement Upload Issues
# Usage: ./diagnose_thai_upload.sh <database_name>

if [ -z "$1" ]; then
    echo "Usage: $0 <database_name>"
    exit 1
fi

DB_NAME="$1"

cat << 'PYTHON_SCRIPT' | python3
import sys
import odoo
from odoo import api, SUPERUSER_ID

# Get database name from command line
db_name = sys.argv[1] if len(sys.argv) > 1 else input("Enter database name: ")

print("\n" + "="*70)
print("THAI BANK STATEMENT UPLOAD - DIAGNOSTIC REPORT")
print("="*70)

try:
    registry = odoo.registry(db_name)
    
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        # 1. Check all journals (bank, cash, credit)
        print("\n1. CHECKING ALL BANK/CASH/CREDIT JOURNALS")
        print("-" * 70)
        
        journals = env['account.journal'].search([
            ('type', 'in', ['bank', 'cash', 'credit'])
        ], order='name')
        
        issues_found = []
        for j in journals:
            status = "✅" if j.default_account_id else "❌"
            print(f"\n{status} [{j.code}] {j.name} (ID: {j.id})")
            print(f"   Type: {j.type}")
            if j.default_account_id:
                print(f"   Default Account: {j.default_account_id.code} - {j.default_account_id.name}")
            else:
                print(f"   Default Account: ❌ NOT CONFIGURED")
                issues_found.append((j.id, j.name, j.code))
        
        # 2. Check recent statements
        print("\n\n2. RECENT BANK STATEMENTS (Last 10)")
        print("-" * 70)
        
        statements = env['account.bank.statement'].search([], 
                                                          order='create_date desc', 
                                                          limit=10)
        
        if statements:
            for stmt in statements:
                print(f"\n📄 Statement: {stmt.name}")
                print(f"   Journal: {stmt.journal_id.code} - {stmt.journal_id.name} (ID: {stmt.journal_id.id})")
                print(f"   Date: {stmt.date}")
                print(f"   Lines: {len(stmt.line_ids)}")
                print(f"   Created: {stmt.create_date}")
        else:
            print("\n⚠️  No statements found in database")
        
        # 3. Test journal action context (simulating dashboard click)
        print("\n\n3. TESTING JOURNAL ACTION CONTEXT")
        print("-" * 70)
        
        if journals:
            test_journal = journals[0]
            print(f"\nTesting with journal: {test_journal.name} (ID: {test_journal.id})")
            
            # Simulate dashboard "Statements" link click
            ctx = {
                'action_name': 'action_bank_statement_tree',
                'search_default_journal': True
            }
            
            # This mimics what open_action_with_context does
            result_ctx = dict(ctx, default_journal_id=test_journal.id)
            if result_ctx.get('search_default_journal', False):
                result_ctx['search_default_journal_id'] = test_journal.id
                result_ctx['search_default_journal'] = False
            
            print(f"\nOriginal context (from dashboard): {ctx}")
            print(f"Transformed context (by open_action_with_context): {result_ctx}")
            print(f"\n✅ Journal ID should be available as: default_journal_id={result_ctx.get('default_journal_id')}")
        
        # 4. Summary of issues
        print("\n\n4. ISSUES SUMMARY")
        print("="*70)
        
        if issues_found:
            print(f"\n❌ Found {len(issues_found)} journal(s) missing default_account_id:")
            print("\nTo fix, run in Odoo UI:")
            print("   Accounting > Configuration > Journals")
            print("\nThen for each journal below:")
            for j_id, j_name, j_code in issues_found:
                print(f"\n   • [{j_code}] {j_name} (ID: {j_id})")
                print(f"     1. Open the journal")
                print(f"     2. Go to 'Accounting Information' tab")
                print(f"     3. Set 'Default Account' field")
                print(f"     4. Click Save")
        else:
            print("\n✅ All journals are properly configured!")
        
        # 5. Check wizard model and access
        print("\n\n5. CHECKING WIZARD MODEL")
        print("-" * 70)
        
        try:
            wizard_model = env['ir.model'].search([('model', '=', 'bml.thai.bank.statement.wizard')])
            if wizard_model:
                print(f"✅ Wizard model found: {wizard_model.name}")
                
                # Check access rules
                access_rules = env['ir.model.access'].search([
                    ('model_id', '=', wizard_model.id)
                ])
                if access_rules:
                    print(f"\nAccess rules:")
                    for rule in access_rules:
                        print(f"   • {rule.name}: group={rule.group_id.full_name if rule.group_id else 'All Users'}")
                else:
                    print("⚠️  No access rules found")
            else:
                print("❌ Wizard model not found - module may not be installed")
        except Exception as e:
            print(f"❌ Error checking wizard: {e}")
        
        print("\n" + "="*70)
        print("END OF DIAGNOSTIC REPORT")
        print("="*70 + "\n")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

PYTHON_SCRIPT

echo "$DB_NAME"
