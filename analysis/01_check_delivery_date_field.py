#!/usr/bin/env python3
"""
Check if delivery_date field exists on account.move model
"""
import json
from odoo_client import OdooClient


def main():
    print("=" * 60)
    print("Checking delivery_date field on account.move")
    print("=" * 60)
    
    client = OdooClient()
    
    # Get all fields on account.move
    print("\n📋 Getting account.move fields...")
    fields = client.get_fields('account.move')
    
    # Check if delivery_date exists
    if 'delivery_date' in fields:
        print("\n✅ delivery_date field EXISTS on account.move")
        print(f"   Type: {fields['delivery_date'].get('type')}")
        print(f"   Label: {fields['delivery_date'].get('string')}")
        print(f"   Help: {fields['delivery_date'].get('help', 'N/A')}")
    else:
        print("\n❌ delivery_date field NOT FOUND on account.move")
        print("   The bml_custom_reports module may not be installed or upgraded.")
    
    # Check invoice_date for comparison
    if 'invoice_date' in fields:
        print("\n📅 invoice_date field:")
        print(f"   Type: {fields['invoice_date'].get('type')}")
        print(f"   Label: {fields['invoice_date'].get('string')}")
    
    # Save all date-related fields to file
    date_fields = {k: v for k, v in fields.items() if v.get('type') == 'date'}
    with open('account_move_date_fields.json', 'w') as f:
        json.dump(date_fields, f, indent=2, default=str)
    print(f"\n💾 Saved date fields to account_move_date_fields.json")
    
    return fields


if __name__ == '__main__':
    main()
