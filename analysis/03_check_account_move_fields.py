#!/usr/bin/env python3
"""
Check account.move fields - useful for understanding the invoice/bill model
"""
import json
from odoo_client import OdooClient


def main():
    print("=" * 60)
    print("Checking account.move fields")
    print("=" * 60)
    
    client = OdooClient()
    
    # Get all fields on account.move
    print("\n📋 Getting account.move fields...")
    fields = client.get_fields('account.move')
    
    # Categorize fields by type
    field_types = {}
    for name, info in fields.items():
        ftype = info.get('type', 'unknown')
        if ftype not in field_types:
            field_types[ftype] = []
        field_types[ftype].append({
            'name': name,
            'string': info.get('string'),
            'required': info.get('required', False),
            'readonly': info.get('readonly', False)
        })
    
    print(f"\n📊 Total fields: {len(fields)}")
    print("\nFields by type:")
    for ftype, flist in sorted(field_types.items()):
        print(f"   {ftype}: {len(flist)}")
    
    # Show key fields
    key_fields = ['name', 'move_type', 'state', 'partner_id', 'invoice_date', 
                  'delivery_date', 'date', 'amount_total', 'amount_untaxed',
                  'currency_id', 'company_id', 'journal_id']
    
    print("\n🔑 Key fields:")
    for fname in key_fields:
        if fname in fields:
            f = fields[fname]
            print(f"   {fname}: {f.get('type')} - {f.get('string')}")
        else:
            print(f"   {fname}: ❌ NOT FOUND")
    
    # Save to file
    with open('account_move_fields.json', 'w') as f:
        json.dump(fields, f, indent=2, default=str)
    print(f"\n💾 Saved all fields to account_move_fields.json")


if __name__ == '__main__':
    main()
