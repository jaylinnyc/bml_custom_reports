#!/usr/bin/env python3
"""
Thai Address Parser for e-Tax Components
Analyzes Thai addresses and extracts structured components for e-Tax filing.
"""

import csv
import re
from typing import Dict, Optional


class ThaiAddressParser:
    """Parser for extracting Thai e-Tax address components."""
    
    def __init__(self):
        # Building name patterns
        self.building_patterns = [
            r'(?:อาคาร|Building|อาคาร์)\s*([^\s,]+(?:\s+[^\s,]+)?)',
            r'([^\s,]+)\s+(?:Tower|Plaza)',
        ]
        
        # Floor number patterns
        self.floor_patterns = [
            r'ชั้น(?:ที่)?\s*(\d+)',
            r'Floor\s*(\d+)',
            r'(\d+)(?:st|nd|rd|th)\s*Floor',
            r'ชั้น\s*(\d+)',
        ]
        
        # Room/Unit number patterns
        self.room_patterns = [
            r'ห้อง\s*([\d/-]+)',
            r'Room\s*([\d/-]+)',
            r'Unit\s*([\d/-]+)',
            r'ยูนิต\s*([\d/-]+)',
        ]
        
        # Moo patterns
        self.moo_patterns = [
            r'หมู่(?:ที่)?\s*(\d+)',
            r'ม\.?\s*(\d+)',
            r'Moo\s*(\d+)',
            r'M\.?\s*(\d+)',
            r'Village\s*(?:No\.)?\s*(\d+)',
        ]
        
        # Soi patterns
        self.soi_patterns = [
            r'ซอย\s*([^\s,]+(?:\s+\d+)?)',
            r'ซ\.\s*([^\s,]+)',
            r'Soi\s*([^\s,]+(?:\s+\d+)?)',
        ]
        
        # Sub-district patterns (Tambon/Khwaeng)
        self.subdistrict_patterns = [
            r'(?:ตำบล|ต\.)\s*([^\s,]+)',
            r'(?:แขวง)\s*([^\s,]+)',
            r'T\.\s*([^\s,]+)',
            r'([^\s,]+)\s+Subdistrict',
        ]
        
        # District patterns (Amphoe/Khet)
        self.district_patterns = [
            r'(?:อำเภอ|อ\.)\s*([^\s,]+)',
            r'(?:เขต)\s*([^\s,]+)',
            r'A\.\s*([^\s,]+)',
            r'([^\s,]+)\s+District',
        ]
        
        # Province patterns
        self.province_patterns = [
            r'(?:จังหวัด|จ\.)\s*([^\s,]+)',
            r'([^\s,]+)\s+Province',
        ]
    
    def extract_building_name(self, address: str) -> Optional[str]:
        """Extract building name from address."""
        for pattern in self.building_patterns:
            match = re.search(pattern, address, re.IGNORECASE)
            if match:
                building = match.group(1).strip()
                # Clean up common suffixes - handle "อาคารXXXชั้น" cases
                building = re.sub(r'(?:ชั้น|Floor|ห้อง|Room).*$', '', building)
                if building and len(building) > 1:
                    return building.strip()
        return None
    
    def extract_floor_number(self, address: str) -> Optional[str]:
        """Extract floor number from address."""
        for pattern in self.floor_patterns:
            match = re.search(pattern, address, re.IGNORECASE)
            if match:
                floor = match.group(1).strip()
                return floor
        return None
    
    def extract_room_number(self, address: str) -> Optional[str]:
        """Extract room/unit number from address."""
        for pattern in self.room_patterns:
            match = re.search(pattern, address, re.IGNORECASE)
            if match:
                room = match.group(1).strip()
                return room
        return None
    
    def extract_moo(self, address: str) -> Optional[str]:
        """Extract and format Moo number (zero-padded to 2 digits)."""
        for pattern in self.moo_patterns:
            match = re.search(pattern, address, re.IGNORECASE)
            if match:
                moo = match.group(1).strip()
                try:
                    # Zero-pad to 2 digits
                    moo_num = int(moo)
                    return f"{moo_num:02d}"
                except ValueError:
                    continue
        return None
    
    def extract_soi(self, address: str) -> Optional[str]:
        """Extract Soi/Lane from address."""
        for pattern in self.soi_patterns:
            match = re.search(pattern, address, re.IGNORECASE)
            if match:
                soi = match.group(1).strip()
                # Clean up trailing commas or periods
                soi = re.sub(r'[,.]$', '', soi)
                if soi and len(soi) > 1:
                    return soi
        return None
    
    def extract_sub_district(self, address: str) -> Optional[str]:
        """Extract sub-district (Tambon/Khwaeng) from address."""
        for pattern in self.subdistrict_patterns:
            match = re.search(pattern, address, re.IGNORECASE)
            if match:
                subdistrict = match.group(1).strip()
                # Clean up trailing punctuation
                subdistrict = re.sub(r'[,.]$', '', subdistrict)
                if subdistrict and len(subdistrict) > 1:
                    return subdistrict
        return None
    
    def extract_district(self, address: str) -> Optional[str]:
        """Extract district (Amphoe/Khet) from address."""
        for pattern in self.district_patterns:
            match = re.search(pattern, address, re.IGNORECASE)
            if match:
                district = match.group(1).strip()
                # Clean up trailing punctuation
                district = re.sub(r'[,.]$', '', district)
                # Remove common prefixes that might be captured
                district = re.sub(r'^(?:อ|อ\.|A\.)\s*', '', district)
                if district and len(district) > 1:
                    return district
        return None
    
    def extract_province(self, address: str) -> Optional[str]:
        """Extract province from address and remove suffixes like มหานคร."""
        # Special handling for Bangkok variations
        if re.search(r'กรุงเทพ(?:มหานคร)?', address, re.IGNORECASE):
            return 'กรุงเทพ'
        if re.search(r'กทม\.?', address, re.IGNORECASE):
            return 'กรุงเทพ'
        if re.search(r'Bangkok', address, re.IGNORECASE):
            return 'Bangkok'
        
        for pattern in self.province_patterns:
            match = re.search(pattern, address, re.IGNORECASE)
            if match:
                province = match.group(1).strip()
                # Clean up trailing punctuation
                province = re.sub(r'[,.]$', '', province)
                # Remove มหานคร suffix (e.g., กรุงเทพมหานคร -> กรุงเทพ)
                province = re.sub(r'มหานคร$', '', province)
                # Remove common prefixes that might be captured
                province = re.sub(r'^(?:จ|จ\.)\s*', '', province)
                if province and len(province) > 1:
                    return province
        return None
    
    def parse_address(self, full_address: str, street: str = "", street2: str = "", city: str = "") -> Dict[str, str]:
        """
        Parse a Thai address and extract all e-Tax components.
        
        Args:
            full_address: The complete address string
            street: Additional street information
            street2: Additional street2 information
            city: Additional city information
            
        Returns:
            Dictionary with extracted e-Tax fields
        """
        # Combine all address parts
        combined = f"{full_address} {street} {street2} {city}".strip()
        
        # Extract all components
        result = {
            'etax_building_name': self.extract_building_name(combined) or '',
            'etax_floor_number': self.extract_floor_number(combined) or '',
            'etax_room_number': self.extract_room_number(combined) or '',
            'etax_moo': self.extract_moo(combined) or '',
            'etax_soi': self.extract_soi(combined) or '',
            'etax_sub_district': self.extract_sub_district(combined) or '',
            'etax_district': self.extract_district(combined) or '',
            'etax_province': self.extract_province(combined) or '',
        }
        
        return result


def process_csv(input_file: str, output_file: str):
    """
    Process the partner export CSV and extract Thai e-Tax components.
    
    Args:
        input_file: Path to input CSV file
        output_file: Path to output CSV file
    """
    parser = ThaiAddressParser()
    
    with open(input_file, 'r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        
        # Prepare output rows
        output_rows = []
        processed_count = 0
        
        for row in reader:
            # Extract address components
            full_address = row.get('full_address', '')
            street = row.get('street', '')
            street2 = row.get('street2', '')
            city = row.get('city', '')
            
            # Parse address
            etax_components = parser.parse_address(full_address, street, street2, city)
            
            # Update row with extracted components
            row.update(etax_components)
            output_rows.append(row)
            
            processed_count += 1
            if processed_count % 10 == 0:
                print(f"Processed {processed_count} records...")
        
        print(f"\nTotal records processed: {processed_count}")
        
    # Write output CSV
    with open(output_file, 'w', encoding='utf-8', newline='') as outfile:
        if output_rows:
            fieldnames = output_rows[0].keys()
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(output_rows)
    
    print(f"Output written to: {output_file}")
    
    # Print sample results
    print("\n=== Sample Results (first 5 records) ===")
    for i, row in enumerate(output_rows[:5], 1):
        print(f"\n{i}. {row['name']}")
        print(f"   Building: {row['etax_building_name']}")
        print(f"   Floor: {row['etax_floor_number']}")
        print(f"   Room: {row['etax_room_number']}")
        print(f"   Moo: {row['etax_moo']}")
        print(f"   Soi: {row['etax_soi']}")
        print(f"   Sub-district: {row['etax_sub_district']}")
        print(f"   District: {row['etax_district']}")
        print(f"   Province: {row['etax_province']}")


if __name__ == "__main__":
    import sys
    from datetime import datetime
    
    # Input file
    input_csv = "/Users/Jay/development/git/nexus/panya19prod/jaylinnyc/bml_custom_reports/scripts/partners_export_panya19prod_20260105_142401.csv"
    
    # Output file with AI_PARSED suffix
    output_csv = "/Users/Jay/development/git/nexus/panya19prod/jaylinnyc/bml_custom_reports/scripts/partners_export_panya19prod_20260105_142401_AI_PARSED.csv"
    
    print("=" * 80)
    print("Thai Address Parser for e-Tax Components")
    print("=" * 80)
    print(f"\nInput file: {input_csv}")
    print(f"Output file: {output_csv}")
    print(f"Processing started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        process_csv(input_csv, output_csv)
        print(f"\n✓ Processing completed successfully!")
        print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
