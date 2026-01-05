#!/usr/bin/env python3
"""
Step 2: Import parsed Thai addresses back to Odoo

This script reads the parsed/reviewed CSV and updates partner records in Odoo.
"""
from odoo_client import OdooClient
from config import PROJECTS
import csv
import sys


def main():
    if len(sys.argv) < 2:
        print("Usage: python 02_import_thai_addresses.py <parsed_csv_file> [project_key]")
        print("\nExample:")
        print("   python 02_import_thai_addresses.py partners_export_panya19prod_PARSED_20260105.csv panya19prod")
        sys.exit(1)
    
    input_file = sys.argv[1]
    project_key = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Try to detect project from filename
    if not project_key:
        for key in PROJECTS.keys():
            if key in input_file:
                project_key = key
                break
    
    if not project_key:
        print("❌ Could not detect project. Please specify project_key as second argument.")
        print(f"   Available projects: {list(PROJECTS.keys())}")
        sys.exit(1)
    
    print("=" * 60)
    print("Thai Address Import Tool")
    print("=" * 60)
    print(f"\n📂 File: {input_file}")
    print(f"🎯 Target: {project_key}")
    
    # Connect to Odoo
    client = OdooClient(project=project_key, verbose=False)
    print(f"✅ Connected to {project_key}\n")
    
    # Read CSV
    print("📋 Reading CSV...")
    partners = []
    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        partners = list(reader)
    
    print(f"   Found {len(partners)} partners\n")
    
    # Confirm before importing
    print("⚠️  This will update partner records in Odoo.")
    response = input("   Continue? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("❌ Import cancelled")
        sys.exit(0)
    
    print("\n🔄 Importing Thai addresses...")
    
    success_count = 0
    error_count = 0
    skipped_count = 0
    errors = []
    
    for i, partner in enumerate(partners, 1):
        if i % 50 == 0:
            print(f"   Processed {i}/{len(partners)}...")
        
        partner_id = int(partner['id'])
        
        # Build update values (only include non-empty parsed fields)
        values = {}
        
        if partner.get('parsed_building_name'):
            values['etax_building_name'] = partner['parsed_building_name']
        if partner.get('parsed_floor_number'):
            values['etax_floor_number'] = partner['parsed_floor_number']
        if partner.get('parsed_room_number'):
            values['etax_room_number'] = partner['parsed_room_number']
        if partner.get('parsed_moo'):
            values['etax_moo'] = partner['parsed_moo']
        if partner.get('parsed_soi'):
            values['etax_soi'] = partner['parsed_soi']
        if partner.get('parsed_sub_district'):
            values['etax_sub_district'] = partner['parsed_sub_district']
        if partner.get('parsed_district'):
            values['etax_district'] = partner['parsed_district']
        if partner.get('parsed_province'):
            values['etax_province'] = partner['parsed_province']
        
        # Skip if no values to update
        if not values:
            skipped_count += 1
            continue
        
        # Update partner
        try:
            client.execute('res.partner', 'write', [partner_id], values)
            success_count += 1
        except Exception as e:
            error_count += 1
            errors.append({
                'id': partner_id,
                'name': partner.get('name'),
                'error': str(e)
            })
    
    # Summary
    print("\n" + "=" * 60)
    print("Import Complete")
    print("=" * 60)
    print(f"\n📊 Results:")
    print(f"   Successfully updated: {success_count}")
    print(f"   Skipped (no data): {skipped_count}")
    print(f"   Errors: {error_count}")
    
    if errors:
        print("\n❌ Errors encountered:")
        for err in errors[:10]:  # Show first 10 errors
            print(f"   Partner {err['id']} ({err['name']}): {err['error']}")
        if len(errors) > 10:
            print(f"   ... and {len(errors) - 10} more errors")
    
    if success_count > 0:
        print("\n✅ Import successful!")
        print("\n📝 Recommended next steps:")
        print("   1. Verify a few sample partners in Odoo")
        print("   2. Check partners with needs_review = YES")
        print("   3. Run e-Tax export to test the Thai address fields")


if __name__ == '__main__':
    main()
