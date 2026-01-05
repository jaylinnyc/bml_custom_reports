#!/usr/bin/env python3
"""
Get detailed field information for the fields we need to hide/migrate
"""
import json
from odoo_client import OdooClient


def main():
    print("=" * 60)
    print("Field Details for Accounting Date & TaxInvoice Date")
    print("=" * 60)
    
    client = OdooClient()
    
    fields = client.get_fields('account.move')
    
    target_fields = ['date', 'x_studio_taxinvoice_date', 'invoice_date', 'delivery_date']
    
    print("\n📋 Field Details:\n")
    for field_name in target_fields:
        if field_name in fields:
            info = fields[field_name]
            print(f"Field: {field_name}")
            print(f"  Type: {info.get('type')}")
            print(f"  String: {info.get('string')}")
            print(f"  Required: {info.get('required')}")
            print(f"  Readonly: {info.get('readonly')}")
            print(f"  Store: {info.get('store')}")
            print(f"  Help: {info.get('help')}")
            print()
    
    # Check if there's data in x_studio_taxinvoice_date
    print("\n🔍 Checking for records with TaxInvoice Date set...")
    count = client.search_count('account.move', [('x_studio_taxinvoice_date', '!=', False)])
    print(f"   Records with x_studio_taxinvoice_date: {count}")
    
    if count > 0:
        print("\n📄 Sample records with TaxInvoice Date:")
        samples = client.search_read(
            'account.move',
            [('x_studio_taxinvoice_date', '!=', False)],
            ['name', 'move_type', 'date', 'invoice_date', 'x_studio_taxinvoice_date'],
            limit=5
        )
        for rec in samples:
            print(f"   {rec['name']}: date={rec.get('date')}, invoice_date={rec.get('invoice_date')}, taxinvoice_date={rec.get('x_studio_taxinvoice_date')}")


if __name__ == '__main__':
    main()
