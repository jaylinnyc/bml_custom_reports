#!/usr/bin/env python3
"""
Step 1: Export partners to CSV for AI parsing
"""
import sys
sys.path.insert(0, '/Users/Jay/development/git/nexus/panya19prod/jaylinnyc/bml_custom_reports/analysis')

from odoo_client import OdooClient
from config import PROJECTS
import csv
from datetime import datetime


def export_partners(project_key):
    """Export partners from a specific project"""
    print(f"\n{'=' * 60}")
    print(f"Exporting partners from: {project_key}")
    print("=" * 60)
    
    client = OdooClient(project=project_key, verbose=False)
    print(f"✅ Connected to {project_key}\n")
    
    # Get all partners with addresses
    print("🔍 Fetching partners with addresses...")
    
    # First check which Thai e-tax fields exist
    partner_fields = client.execute('ir.model.fields', 'search_read', [
        ('model', '=', 'res.partner'),
        ('name', 'in', ['etax_effective_tax_id', 'etax_building_name', 'etax_floor_number', 
                        'etax_room_number', 'etax_moo', 'etax_soi', 'etax_sub_district',
                        'etax_district', 'etax_province'])
    ], ['name'])
    
    existing_etax_fields = [f['name'] for f in partner_fields]
    
    # Build field list with only existing fields
    fields_to_fetch = [
        'id', 'name', 'vat', 'ref',
        'street', 'street2', 'city', 'state_id', 'zip', 'country_id'
    ]
    fields_to_fetch.extend(existing_etax_fields)
    
    partners = client.search_read(
        'res.partner',
        [
            '|',
            ('street', '!=', False),
            ('street2', '!=', False)
        ],
        fields_to_fetch,
        order='id'
    )
    
    print(f"   Found {len(partners)} partners\n")
    
    # Generate filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"partners_export_{project_key}_{timestamp}.csv"
    
    # Write to CSV
    print(f"💾 Writing to {filename}...")
    
    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow([
            'id', 'name', 'vat', 'ref',
            'street', 'street2', 'city', 'state', 'zip', 'country',
            'etax_effective_tax_id',
            'etax_building_name', 'etax_floor_number', 'etax_room_number',
            'etax_moo', 'etax_soi', 'etax_sub_district',
            'etax_district', 'etax_province',
            'full_address'  # Combined for easy review
        ])
        
        # Data rows
        for partner in partners:
            state = partner.get('state_id')
            state_name = state[1] if state else ''
            
            country = partner.get('country_id')
            country_name = country[1] if country else ''
            
            full_address = ' '.join(filter(None, [
                partner.get('street', ''),
                partner.get('street2', ''),
                partner.get('city', ''),
                state_name,
                partner.get('zip', '')
            ]))
            
            writer.writerow([
                partner['id'],
                partner.get('name', ''),
                partner.get('vat', ''),
                partner.get('ref', ''),
                partner.get('street', ''),
                partner.get('street2', ''),
                partner.get('city', ''),
                state_name,
                partner.get('zip', ''),
                country_name,
                partner.get('etax_effective_tax_id', ''),
                partner.get('etax_building_name', ''),
                partner.get('etax_floor_number', ''),
                partner.get('etax_room_number', ''),
                partner.get('etax_moo', ''),
                partner.get('etax_soi', ''),
                partner.get('etax_sub_district', ''),
                partner.get('etax_district', ''),
                partner.get('etax_province', ''),
                full_address
            ])
    
    print(f"✅ Exported {len(partners)} partners to {filename}\n")
    
    # Statistics
    thai_fields_populated = sum(1 for p in partners if any([
        p.get('etax_moo'),
        p.get('etax_soi'),
        p.get('etax_sub_district'),
        p.get('etax_district'),
        p.get('etax_province')
    ]))
    
    print(f"📊 Statistics:")
    print(f"   Total partners: {len(partners)}")
    print(f"   With Thai fields: {thai_fields_populated} ({thai_fields_populated/len(partners)*100:.1f}%)")
    print(f"   Need parsing: {len(partners) - thai_fields_populated} ({(len(partners)-thai_fields_populated)/len(partners)*100:.1f}%)")
    
    return filename


def main():
    print("=" * 60)
    print("Partner Export Tool")
    print("=" * 60)
    
    # Export from all projects
    exported_files = []
    
    for project_key in PROJECTS.keys():
        try:
            filename = export_partners(project_key)
            exported_files.append((project_key, filename))
        except Exception as e:
            print(f"❌ Error exporting {project_key}: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("Export Complete")
    print("=" * 60)
    print("\nExported files:")
    for project, filename in exported_files:
        print(f"   {project}: {filename}")
    
    print("\n📝 Next steps:")
    print("   1. Review the CSV files")
    print("   2. I'll analyze each address and create the parsed file")
    print("   3. Review my work in the parsed CSV")
    print("   4. Run: python 02_import_thai_addresses.py <parsed_file>")


if __name__ == '__main__':
    main()
