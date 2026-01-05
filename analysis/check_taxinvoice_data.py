#!/usr/bin/env python3
"""
Check for actual TaxInvoice Date data in both projects
"""
from odoo_client import OdooClient
from config import PROJECTS


def main():
    print("=" * 60)
    print("TaxInvoice Date Data Check")
    print("=" * 60)
    
    for project_key in PROJECTS.keys():
        print(f"\n{'=' * 60}")
        print(f"Project: {project_key}")
        print("=" * 60)
        
        client = OdooClient(project=project_key, verbose=False)
        print(f"✅ Connected to {project_key}\n")
        
        # Check for records with x_studio_taxinvoice_date
        print("🔍 Checking x_studio_taxinvoice_date field...")
        
        # Get count
        count = client.search_count('account.move', [('x_studio_taxinvoice_date', '!=', False)])
        print(f"   Records with data: {count}")
        
        if count > 0:
            # Get sample records
            print(f"\n📋 Sample records (first 10):")
            records = client.search_read(
                'account.move',
                [('x_studio_taxinvoice_date', '!=', False)],
                ['id', 'name', 'move_type', 'partner_id', 'invoice_date', 'x_studio_taxinvoice_date'],
                limit=10,
                order='id desc'
            )
            
            for rec in records:
                partner = rec.get('partner_id', [False, 'Unknown'])
                partner_name = partner[1] if isinstance(partner, list) else 'Unknown'
                print(f"   ID {rec['id']}: {rec['name']} - {partner_name}")
                print(f"      Type: {rec.get('move_type')}")
                print(f"      Invoice Date: {rec.get('invoice_date')}")
                print(f"      TaxInvoice Date: {rec.get('x_studio_taxinvoice_date')}")
                print()
        else:
            print("   ✅ No records found with x_studio_taxinvoice_date")
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print("If data exists, we NEED the migration script!")


if __name__ == '__main__':
    main()
