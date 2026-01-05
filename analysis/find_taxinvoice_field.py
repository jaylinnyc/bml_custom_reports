#!/usr/bin/env python3
"""
Find TaxInvoice Date field on account.move model
"""
import json
from odoo_client import OdooClient


def main():
    print("=" * 60)
    print("Searching for TaxInvoice Date field")
    print("=" * 60)
    
    client = OdooClient()
    
    # Get all fields on account.move
    print("\n📋 Getting account.move fields...")
    fields = client.get_fields('account.move')
    
    # Search for fields containing 'tax' and 'date' (case insensitive)
    print("\n🔍 Fields containing 'tax' and 'date':")
    tax_date_fields = {}
    for name, info in fields.items():
        name_lower = name.lower()
        string_lower = (info.get('string') or '').lower()
        
        if ('tax' in name_lower or 'tax' in string_lower) and \
           ('date' in name_lower or 'date' in string_lower):
            tax_date_fields[name] = info
            print(f"   {name}: {info.get('type')} - {info.get('string')}")
    
    # Search for all x_studio fields
    print("\n🎨 All Studio fields (x_studio_*):")
    studio_fields = {}
    for name, info in fields.items():
        if name.startswith('x_studio_'):
            studio_fields[name] = info
            print(f"   {name}: {info.get('type')} - {info.get('string')}")
    
    # Search for 'date' field (Accounting Date)
    print("\n📅 Standard date fields:")
    for field_name in ['date', 'invoice_date', 'invoice_date_due', 'delivery_date']:
        if field_name in fields:
            f = fields[field_name]
            print(f"   {field_name}: {f.get('type')} - {f.get('string')}")
    
    # Save results
    results = {
        'tax_date_fields': tax_date_fields,
        'studio_fields': studio_fields,
        'all_date_fields': {k: v for k, v in fields.items() 
                            if v.get('type') == 'date' or 'date' in k.lower()}
    }
    
    with open('taxinvoice_field_search.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n💾 Saved detailed results to taxinvoice_field_search.json")
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"   Tax+Date fields found: {len(tax_date_fields)}")
    print(f"   Studio fields found: {len(studio_fields)}")
    print(f"   Total date fields: {len(results['all_date_fields'])}")


if __name__ == '__main__':
    main()
