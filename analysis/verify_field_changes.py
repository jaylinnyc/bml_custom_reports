#!/usr/bin/env python3
"""
Verify the field hiding and migration
"""
from odoo_client import OdooClient
import json


def main():
    print("=" * 60)
    print("Verifying Field Changes")
    print("=" * 60)
    
    client = OdooClient()
    
    # Check if new taxinvoice_date field exists
    print("\n📋 Checking fields on account.move...")
    fields = client.get_fields('account.move')
    
    checks = {
        'date': 'Accounting Date (to be hidden)',
        'x_studio_taxinvoice_date': 'Studio TaxInvoice Date (to be hidden)',
        'taxinvoice_date': 'New TaxInvoice Date field',
        'invoice_date': 'Bill/Invoice Date',
        'delivery_date': 'Delivery Date'
    }
    
    print("\n✅ Field Status:")
    for field_name, description in checks.items():
        exists = "✅ EXISTS" if field_name in fields else "❌ NOT FOUND"
        print(f"   {exists} - {field_name}: {description}")
    
    # Check views
    print("\n📋 Checking view modifications...")
    views = client.search_read(
        'ir.ui.view',
        [('name', '=', 'account.move.form.inherit.date.sync')],
        ['name', 'arch_db', 'active']
    )
    
    if views:
        view = views[0]
        arch = view['arch_db']
        print(f"   ✅ View found: {view['name']}")
        print(f"   Active: {view['active']}")
        
        # Check for key elements
        checks = [
            ('column_invisible', 'date field is hidden'),
            ('x_studio_taxinvoice_date', 'Studio field reference exists'),
            ('delivery_date', 'Delivery date field added'),
        ]
        
        print("\n   View contains:")
        for check_str, description in checks:
            if check_str in arch:
                print(f"      ✅ {description}")
            else:
                print(f"      ❌ {description}")
    else:
        print("   ❌ View not found")
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    new_field_exists = 'taxinvoice_date' in fields
    old_field_exists = 'x_studio_taxinvoice_date' in fields
    
    if new_field_exists:
        print("✅ New taxinvoice_date field is available")
    else:
        print("⚠️  New taxinvoice_date field NOT found - module may need upgrade")
    
    if old_field_exists:
        print("✅ Studio field still exists (can migrate data)")
    
    if views:
        print("✅ View customizations are active")
    
    print("\nNext steps:")
    if not new_field_exists:
        print("   1. Upgrade the module: Settings > Apps > bml_custom_reports > Upgrade")
    print("   2. Open an invoice/bill form and verify:")
    print("      - Accounting Date is hidden")
    print("      - TaxInvoice Date is hidden")
    print("      - Delivery Date is visible below Bill/Invoice Date")
    if old_field_exists and new_field_exists:
        print("   3. Run migration script if there's data in x_studio_taxinvoice_date")


if __name__ == '__main__':
    main()
