#!/usr/bin/env python3
"""
Get sample invoices/bills for analysis
"""
import json
from odoo_client import OdooClient


def main():
    print("=" * 60)
    print("Getting Sample Invoices/Bills")
    print("=" * 60)
    
    client = OdooClient()
    
    # Get recent invoices/bills
    print("\n📋 Fetching recent invoices/bills...")
    
    fields = [
        'name', 'move_type', 'state', 'partner_id',
        'invoice_date', 'delivery_date', 'date',
        'amount_total', 'amount_untaxed', 'amount_tax',
        'currency_id', 'company_id', 'journal_id',
        'invoice_line_ids', 'ref', 'narration'
    ]
    
    # Customer Invoices
    print("\n🧾 Customer Invoices (latest 5):")
    invoices = client.search_read(
        'account.move',
        [('move_type', '=', 'out_invoice')],
        fields,
        limit=5,
        order='id desc'
    )
    for inv in invoices:
        print(f"   {inv['name']} - {inv['state']} - {inv['amount_total']}")
    
    # Vendor Bills
    print("\n📄 Vendor Bills (latest 5):")
    bills = client.search_read(
        'account.move',
        [('move_type', '=', 'in_invoice')],
        fields,
        limit=5,
        order='id desc'
    )
    for bill in bills:
        print(f"   {bill['name']} - {bill['state']} - {bill['amount_total']}")
    
    # Summary counts
    print("\n📊 Summary:")
    for move_type, label in [
        ('out_invoice', 'Customer Invoices'),
        ('in_invoice', 'Vendor Bills'),
        ('out_refund', 'Customer Credit Notes'),
        ('in_refund', 'Vendor Credit Notes')
    ]:
        count = client.search_count('account.move', [('move_type', '=', move_type)])
        posted = client.search_count('account.move', [('move_type', '=', move_type), ('state', '=', 'posted')])
        print(f"   {label}: {count} total, {posted} posted")
    
    # Save samples
    samples = {
        'customer_invoices': invoices,
        'vendor_bills': bills
    }
    with open('sample_invoices.json', 'w') as f:
        json.dump(samples, f, indent=2, default=str)
    print(f"\n💾 Saved samples to sample_invoices.json")


if __name__ == '__main__':
    main()
