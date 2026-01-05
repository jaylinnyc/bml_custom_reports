#!/usr/bin/env python3
"""
Migration script: Copy x_studio_taxinvoice_date to taxinvoice_date

Run this AFTER upgrading the module to ensure data is migrated.
Works across multiple projects.
"""
from odoo_client import OdooClient
from config import PROJECTS
import sys


def migrate_project(project_key):
    """Migrate data for a single project"""
    print(f"\n{'=' * 60}")
    print(f"Project: {project_key}")
    print("=" * 60)
    
    client = OdooClient(project=project_key, verbose=False)
    print(f"✅ Connected to {project_key}\n")
    
    # Check for records with x_studio_taxinvoice_date
    print("🔍 Checking for records to migrate...")
    count = client.search_count('account.move', [('x_studio_taxinvoice_date', '!=', False)])
    print(f"   Found {count} records with x_studio_taxinvoice_date set")
    
    if count == 0:
        print("   ✅ No data to migrate for this project!")
        return 0
    
    # Get all records with the studio field set
    records = client.search_read(
        'account.move',
        [('x_studio_taxinvoice_date', '!=', False)],
        ['id', 'name', 'x_studio_taxinvoice_date', 'taxinvoice_date']
    )
    
    print(f"\n📋 Migrating {len(records)} records...")
    
    success_count = 0
    for rec in records:
        try:
            # Copy the value to the new field
            client.execute(
                'account.move', 'write',
                [rec['id']],
                {'taxinvoice_date': rec['x_studio_taxinvoice_date']}
            )
            print(f"   ✅ {rec['name']}: {rec['x_studio_taxinvoice_date']}")
            success_count += 1
        except Exception as e:
            print(f"   ❌ {rec['name']}: Error - {e}")
    
    return success_count


def main():
    print("=" * 60)
    print("Migrating TaxInvoice Date Data - All Projects")
    print("=" * 60)
    
    if len(sys.argv) > 1:
        # Migrate specific project
        project = sys.argv[1]
        if project not in PROJECTS:
            print(f"❌ Unknown project: {project}")
            print(f"   Available: {list(PROJECTS.keys())}")
            return
        migrate_project(project)
    else:
        # Migrate all projects
        total_migrated = 0
        for project_key in PROJECTS.keys():
            migrated = migrate_project(project_key)
            total_migrated += migrated
        
        print(f"\n{'=' * 60}")
        print(f"Migration Complete: {total_migrated} total records migrated")
        print("=" * 60)
        
        if total_migrated > 0:
            print("\n✅ Migration successful!")
            print("\nNext steps:")
            print("   1. Verify the data in Odoo UI")
            print("   2. Check that taxinvoice_date matches x_studio_taxinvoice_date")
            print("   3. Once verified, you can remove x_studio_taxinvoice_date from Studio")


if __name__ == '__main__':
    main()
