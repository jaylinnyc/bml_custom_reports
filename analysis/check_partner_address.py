#!/usr/bin/env python3
"""
Check Thai address fields for a specific partner
"""
from odoo_client import OdooClient
import sys


def main():
    if len(sys.argv) < 2:
        print("Usage: python check_partner_address.py <tax_id>")
        print("Example: python check_partner_address.py 0105509000014")
        sys.exit(1)
    
    tax_id = sys.argv[1]
    
    print("=" * 60)
    print(f"Checking Partner with Tax ID: {tax_id}")
    print("=" * 60)
    
    client = OdooClient()
    
    # Search for partner by tax ID
    print(f"\n🔍 Searching for partner with VAT: {tax_id}...")
    partners = client.search_read(
        'res.partner',
        [('vat', 'ilike', tax_id)],
        ['name', 'vat', 'street', 'street2', 'city', 'state_id', 'zip', 'country_id',
         'etax_effective_tax_id', 'etax_building_name', 'etax_floor_number', 
         'etax_room_number', 'etax_moo', 'etax_soi', 'etax_sub_district',
         'etax_district', 'etax_province']
    )
    
    if not partners:
        print(f"❌ No partner found with tax ID: {tax_id}")
        return
    
    for partner in partners:
        print(f"\n{'=' * 60}")
        print(f"Partner: {partner['name']}")
        print("=" * 60)
        
        print("\n📋 Standard Address Fields:")
        print(f"   VAT: {partner.get('vat', 'Not set')}")
        print(f"   Street: {partner.get('street', 'Not set')}")
        print(f"   Street2: {partner.get('street2', 'Not set')}")
        print(f"   City: {partner.get('city', 'Not set')}")
        state = partner.get('state_id')
        print(f"   State: {state[1] if state else 'Not set'}")
        print(f"   ZIP: {partner.get('zip', 'Not set')}")
        country = partner.get('country_id')
        print(f"   Country: {country[1] if country else 'Not set'}")
        
        print("\n🇹🇭 Thai e-Tax Address Fields:")
        print(f"   Effective Tax ID: {partner.get('etax_effective_tax_id', 'Not set')}")
        print(f"   Building Name: {partner.get('etax_building_name', 'Not set')}")
        print(f"   Floor Number: {partner.get('etax_floor_number', 'Not set')}")
        print(f"   Room Number: {partner.get('etax_room_number', 'Not set')}")
        print(f"   Moo (หมู่): {partner.get('etax_moo', 'Not set')}")
        print(f"   Soi (ซอย): {partner.get('etax_soi', 'Not set')}")
        print(f"   Sub-district (ตำบล/แขวง): {partner.get('etax_sub_district', 'Not set')}")
        print(f"   District (อำเภอ/เขต): {partner.get('etax_district', 'Not set')}")
        print(f"   Province (จังหวัด): {partner.get('etax_province', 'Not set')}")
        
        # Check if Thai fields are populated
        thai_fields = ['etax_building_name', 'etax_floor_number', 'etax_room_number',
                       'etax_moo', 'etax_soi', 'etax_sub_district', 'etax_district', 
                       'etax_province']
        populated = [f for f in thai_fields if partner.get(f)]
        
        print("\n📊 Analysis:")
        print(f"   Thai-specific fields populated: {len(populated)}/{len(thai_fields)}")
        if populated:
            print(f"   Populated fields: {', '.join(populated)}")
        
        # Try to parse standard address for Thai components
        print("\n🔍 Checking if standard address contains Thai components:")
        street = partner.get('street', '')
        street2 = partner.get('street2', '')
        city = partner.get('city', '')
        
        combined_address = f"{street} {street2} {city}".lower()
        
        thai_keywords = {
            'ตำบล': 'Sub-district (ตำบล)',
            'แขวง': 'Sub-district (แขวง)',
            'อำเภอ': 'District (อำเภอ)',
            'เขต': 'District (เขต)',
            'จังหวัด': 'Province',
            'หมู่': 'Moo (หมู่)',
            'ซอย': 'Soi (ซอย)',
            'ถนน': 'Road (ถนน)',
        }
        
        found_keywords = []
        for keyword, label in thai_keywords.items():
            if keyword in combined_address:
                found_keywords.append(label)
        
        if found_keywords:
            print(f"   ✅ Found Thai keywords in standard address: {', '.join(found_keywords)}")
            print(f"   → Consider extracting these to Thai-specific fields")
        else:
            print(f"   ℹ️  No Thai keywords found in standard address")
        
        print(f"\n   Full Address:")
        if street:
            print(f"      {street}")
        if street2:
            print(f"      {street2}")
        if city:
            print(f"      {city}")


if __name__ == '__main__':
    main()
