#!/usr/bin/env python3
"""
Test Thai address parsing accuracy on real data
"""
from odoo_client import OdooClient
import re


def parse_thai_address(street, street2, city):
    """
    Attempt to parse Thai address components from standard fields
    
    Returns dict with parsed components and confidence level
    """
    result = {
        'building_name': None,
        'floor_number': None,
        'room_number': None,
        'moo': None,
        'soi': None,
        'sub_district': None,
        'district': None,
        'province': None,
        'confidence': 'unknown',
        'raw_data': {'street': street, 'street2': street2, 'city': city}
    }
    
    # Combine all address parts
    full_address = f"{street or ''} {street2 or ''} {city or ''}".strip()
    
    if not full_address:
        result['confidence'] = 'no_data'
        return result
    
    parsed_count = 0
    
    # Parse Moo (หมู่)
    moo_patterns = [
        r'(?:Moo|M\.|หมู่)\s*(\d+)',
        r'(?:Village|หมู่บ้าน)\s*(?:No\.|เลขที่)?\s*(\d+)',
    ]
    for pattern in moo_patterns:
        match = re.search(pattern, full_address, re.IGNORECASE)
        if match:
            result['moo'] = match.group(1).zfill(2)  # Pad to 2 digits
            parsed_count += 1
            break
    
    # Parse Soi (ซอย)
    soi_patterns = [
        r'Soi\s+([A-Za-z0-9\s/-]+?)(?:,|\s+(?:Sukhumvit|Rd|Road|T\.|Tambon|A\.|Amphoe|Bangkok))',
        r'ซอย\s*([^\s,]+)',
    ]
    for pattern in soi_patterns:
        match = re.search(pattern, full_address, re.IGNORECASE)
        if match:
            result['soi'] = match.group(1).strip()
            parsed_count += 1
            break
    
    # Parse Sub-district (Tambon/Khwaeng)
    subdistrict_patterns = [
        r'T\.([A-Za-z]+)',  # T.Bangpoomai
        r'Tambon\s+([A-Za-z\s]+?)(?:,|\s+A\.)',
        r'(?:ตำบล|แขวง)\s*([^\s,]+)',
    ]
    for pattern in subdistrict_patterns:
        match = re.search(pattern, full_address, re.IGNORECASE)
        if match:
            result['sub_district'] = match.group(1).strip()
            parsed_count += 1
            break
    
    # Parse District (Amphoe/Khet)
    district_patterns = [
        r'A\.([A-Za-z]+)',  # A.Muang
        r'Amphoe\s+([A-Za-z\s]+?)(?:,|\s+(?:Province|จังหวัด))',
        r'(?:อำเภอ|เขต)\s*([^\s,]+)',
    ]
    for pattern in district_patterns:
        match = re.search(pattern, full_address, re.IGNORECASE)
        if match:
            result['district'] = match.group(1).strip()
            parsed_count += 1
            break
    
    # Parse Province
    province_patterns = [
        r'(?:^|,\s*)([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+\d{5}',  # Province name before ZIP
        r'(?:Province|จังหวัด)\s+([A-Za-z\s]+?)(?:,|\s+\d)',
        r',\s*([A-Za-z]+)\s*$',  # Last word might be province
    ]
    for pattern in province_patterns:
        match = re.search(pattern, full_address, re.IGNORECASE)
        if match:
            province = match.group(1).strip()
            # Filter out common false positives
            if province not in ['Office', 'Rd', 'Road', 'Street', 'Co', 'Ltd']:
                result['province'] = province
                parsed_count += 1
                break
    
    # Parse Building name (before number)
    building_patterns = [
        r'^([A-Za-z][A-Za-z\s&]+(?:Building|Tower|Plaza|Center))',
        r'^(.+?Building)',
    ]
    for pattern in building_patterns:
        match = re.search(pattern, full_address, re.IGNORECASE)
        if match:
            result['building_name'] = match.group(1).strip()
            parsed_count += 1
            break
    
    # Parse Floor number
    floor_patterns = [
        r'(\d+)(?:st|nd|rd|th)?\s*(?:Floor|Fl\.|ชั้น)',
    ]
    for pattern in floor_patterns:
        match = re.search(pattern, full_address, re.IGNORECASE)
        if match:
            result['floor_number'] = match.group(1)
            parsed_count += 1
            break
    
    # Parse Room number
    room_patterns = [
        r'(?:Room|Unit|ห้อง)\s*(?:No\.)?\s*([A-Z0-9-]+)',
    ]
    for pattern in room_patterns:
        match = re.search(pattern, full_address, re.IGNORECASE)
        if match:
            result['room_number'] = match.group(1)
            parsed_count += 1
            break
    
    # Determine confidence
    if parsed_count == 0:
        result['confidence'] = 'none'
    elif parsed_count <= 2:
        result['confidence'] = 'low'
    elif parsed_count <= 4:
        result['confidence'] = 'medium'
    else:
        result['confidence'] = 'high'
    
    result['parsed_fields_count'] = parsed_count
    
    return result


def main():
    print("=" * 60)
    print("Thai Address Parsing Test")
    print("=" * 60)
    
    client = OdooClient()
    
    # Get partners with addresses (limit to sample)
    print("\n🔍 Fetching partner addresses...")
    partners = client.search_read(
        'res.partner',
        [
            '|',
            ('street', '!=', False),
            ('street2', '!=', False)
        ],
        ['name', 'vat', 'street', 'street2', 'city'],
        limit=50,
        order='id desc'
    )
    
    print(f"   Found {len(partners)} partners with addresses\n")
    
    # Test parsing
    results = {
        'high': [],
        'medium': [],
        'low': [],
        'none': [],
        'no_data': []
    }
    
    for partner in partners:
        parsed = parse_thai_address(
            partner.get('street'),
            partner.get('street2'),
            partner.get('city')
        )
        
        results[parsed['confidence']].append({
            'partner': partner,
            'parsed': parsed
        })
    
    # Summary
    print("=" * 60)
    print("Parsing Accuracy Summary")
    print("=" * 60)
    
    total = len(partners)
    print(f"\nTotal partners tested: {total}")
    print(f"\n🎯 Confidence Distribution:")
    print(f"   High (5+ fields):    {len(results['high'])} ({len(results['high'])/total*100:.1f}%)")
    print(f"   Medium (3-4 fields): {len(results['medium'])} ({len(results['medium'])/total*100:.1f}%)")
    print(f"   Low (1-2 fields):    {len(results['low'])} ({len(results['low'])/total*100:.1f}%)")
    print(f"   None (0 fields):     {len(results['none'])} ({len(results['none'])/total*100:.1f}%)")
    
    # Show examples from each category
    print("\n" + "=" * 60)
    print("Sample Results")
    print("=" * 60)
    
    for confidence in ['high', 'medium', 'low', 'none']:
        if results[confidence]:
            print(f"\n🔹 {confidence.upper()} Confidence Examples:")
            for item in results[confidence][:3]:  # Show max 3 examples
                p = item['partner']
                parsed = item['parsed']
                
                print(f"\n   Partner: {p['name']}")
                print(f"   Original: {p.get('street', '')} {p.get('street2', '')}")
                print(f"   Parsed ({parsed['parsed_fields_count']} fields):")
                
                for field in ['moo', 'soi', 'sub_district', 'district', 'province']:
                    if parsed[field]:
                        print(f"      {field}: {parsed[field]}")
    
    # Overall recommendation
    print("\n" + "=" * 60)
    print("Recommendation")
    print("=" * 60)
    
    success_rate = (len(results['high']) + len(results['medium'])) / total * 100
    
    if success_rate >= 70:
        print(f"✅ Good parsing accuracy ({success_rate:.1f}%)")
        print("   → Safe to run automated migration")
    elif success_rate >= 40:
        print(f"⚠️  Moderate parsing accuracy ({success_rate:.1f}%)")
        print("   → Run migration but review results")
        print("   → Manual cleanup may be needed for some records")
    else:
        print(f"❌ Low parsing accuracy ({success_rate:.1f}%)")
        print("   → Not recommended for automated migration")
        print("   → Consider manual data entry or improved parsing logic")


if __name__ == '__main__':
    main()
