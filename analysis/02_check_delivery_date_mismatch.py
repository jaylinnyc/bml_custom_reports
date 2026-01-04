#!/usr/bin/env python3
"""
Check for invoices/bills where delivery_date differs from invoice_date
This helps debug why the Delivery Date Mismatch Report might be empty
"""
import json
from odoo_client import OdooClient


def main():
    print("=" * 60)
    print("Checking for Delivery Date Mismatches")
    print("=" * 60)
    
    client = OdooClient()
    
    # First, let's get ALL invoices/bills with delivery_date field
    print("\n📋 Fetching all invoices/bills with delivery_date...")
    
    invoices = client.search_read(
        'account.move',
        [('move_type', 'in', ['out_invoice', 'in_invoice', 'out_refund', 'in_refund'])],
        ['name', 'move_type', 'state', 'invoice_date', 'delivery_date', 'partner_id', 'amount_total'],
        limit=100,
        order='id desc'
    )
    
    print(f"\n📊 Found {len(invoices)} invoices/bills (showing latest 100)")
    
    # Categorize
    draft_count = 0
    posted_count = 0
    with_delivery_date = 0
    mismatch_count = 0
    mismatches = []
    
    for inv in invoices:
        if inv['state'] == 'draft':
            draft_count += 1
        elif inv['state'] == 'posted':
            posted_count += 1
        
        if inv.get('delivery_date'):
            with_delivery_date += 1
            
            # Check for mismatch
            if inv['delivery_date'] != inv['invoice_date']:
                mismatch_count += 1
                mismatches.append({
                    'id': inv['id'],
                    'name': inv['name'],
                    'move_type': inv['move_type'],
                    'state': inv['state'],
                    'invoice_date': inv['invoice_date'],
                    'delivery_date': inv['delivery_date'],
                    'partner': inv['partner_id'][1] if inv['partner_id'] else 'N/A',
                    'amount': inv['amount_total']
                })
    
    print(f"\n📈 Summary:")
    print(f"   Draft: {draft_count}")
    print(f"   Posted: {posted_count}")
    print(f"   With delivery_date set: {with_delivery_date}")
    print(f"   With date mismatch: {mismatch_count}")
    
    if mismatches:
        print(f"\n🔍 Invoices/Bills with date mismatch:")
        for m in mismatches:
            status = "✅ POSTED" if m['state'] == 'posted' else "📝 DRAFT"
            print(f"   {status} {m['name']}: invoice={m['invoice_date']}, delivery={m['delivery_date']} ({m['move_type']})")
        
        # Check how many are POSTED (these should appear in report)
        posted_mismatches = [m for m in mismatches if m['state'] == 'posted']
        print(f"\n⚠️  POSTED mismatches that SHOULD appear in report: {len(posted_mismatches)}")
        
        if not posted_mismatches:
            print("\n💡 HINT: The report only shows POSTED invoices/bills.")
            print("   Your test bill might still be in DRAFT state.")
            print("   Post/Confirm the bill to see it in the report.")
    else:
        print("\n📭 No date mismatches found.")
        print("   Try creating a bill and setting a different delivery date.")
    
    # Save results
    results = {
        'summary': {
            'total': len(invoices),
            'draft': draft_count,
            'posted': posted_count,
            'with_delivery_date': with_delivery_date,
            'mismatches': mismatch_count
        },
        'mismatches': mismatches,
        'all_invoices': invoices[:20]  # Save first 20 for reference
    }
    
    with open('delivery_date_check_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n💾 Saved results to delivery_date_check_results.json")


if __name__ == '__main__':
    main()
