#!/usr/bin/env python3
"""Compare expected vs actual transactions"""
import sys
import os
import types

sys.path.insert(0, '.')

# Mock Odoo
odoo_mock = types.ModuleType('odoo')
odoo_exceptions_mock = types.ModuleType('odoo.exceptions')
odoo_exceptions_mock.UserError = Exception
odoo_mock.exceptions = odoo_exceptions_mock
sys.modules['odoo'] = odoo_mock
sys.modules['odoo.exceptions'] = odoo_exceptions_mock

from utils.thai_bank_converter import ThaiBankStatementConverter
import pandas as pd

# Expected transactions from user's data (rows 2-37, 36 total)
expected_descriptions = [
    "จ่าย กยศ./กรอ. ประจำเดือน 12/2025 (3คน) บิล 157918960141002",
    "รับเงิน BML (ผลต่าง Salary 12/2025 )",
    "จ่าย กรมสรรพากร (ค่าอากรแสตมป์ ดวงละ 5 บาท 40ดวง)",
    "จ่าย บจ.ไปรษณีย์ไทย ( ค่าส่งเอกสาร GS,จิรเจริญ, P&S  อื่นๆ  ) Ref.No.46533",
    "ธนกาญจน์แก๊ส CPOKAN6901001",  # appears twice
    "ธนกาญจน์แก๊ส CPOKAN6901001",
    "ฟลูเฮ้าส์ CPOKAN6901001",  # appears twice
    "ฟลูเฮ้าส์ CPOKAN6901001",
    "ลาดหญ้าค้าส่ง CPOKAN6901001",
    "รับเงินสด",
    "จ่าย บจ.พงศ์สันติการบัญชี(คุณเพียงพรรณ  พิฤทธิ์บูรณะ Internal Audit Fee & Auditor Accountant 12/2025)",
    "จ่าย นิติบุคคลสมาร์ท คอนโด(ค่าน้ำประปา 36 บ.+ค่าที่จอดรถ 100 บ. ประจำเดือน 12/25) ใบแจ้งหนี้ 68/12/049",
    "ฉินอี่กี่  CPOKAN6901002",
    "สยาม บิลด์อิท CPOKAN6901002",  # appears twice
    "สยาม บิลด์อิท CPOKAN6901002",
    "ธนกาญจน์แก๊ส CPOKAN6901001",
    "ซีพีแอ๊กซ์ตร้า CPOKAN6901002",
    "ยูนิตี้ ไอที  CPOKAN6901002",
    "จ่าย ของขวัญวันเด็ก ปี 2569 รร.ทุ่งนานางหรอก/ รร.บ้านวังด้ง/รร.วัดลาดหญ้ากาญจนบุรี/รร.วัดกาญจนบุรีเก่า @3,000.-และ ศูนย์เด็กเล็ก @2,000.-",
    "จ่าย บจ.ไปรษณีย์ไทย ( ค่าส่งเอกสาร GS  ) Ref.No.49961",
    "จ่ายการไฟฟ้านครหลวง(ค่าไฟฟ้า สมาร์ทคอนโด  12/25 ใช้ไป 43 หน่วย เลขจดหลัง 9720) ใบแจ้งหนี้ 00806006259",
    "จ่าย บจ.โตชิบาเทค(ค่าหมึกเครื่องถ่ายเอกสาร งวด 10/11-09/12/25) ใบแจ้งหนี้ IS2512T1047",
    "จ่าย บจ.ร่วมพัฒนากิจ (ค่าเช่า 12/2025 หักงด.พม่า 5 คนๆละ500 บาท)",
    "จ่าย บมจ.ทริปเปิลที บรอดแบนด์ (ค่าโทรศัพท์ รอบ 11/12/68 - 10/01/69 ประจำเดือน 12/2568) Ref.No.DRCPV03BKKCB/2601/0214",
    "จ่าย บมจ.โทรคมนาคมแห่งชาติ (ค่าโทรศัพท์ รอบ 11/12/68 - 10/01/69 ประจำเดือน 12/2568) Ref.No.B00150052594",
    "จ่าย  เงินสดย่อยโรงงาน CPOKAN6901003(84+350+860+1070+1455.2+642+470.8+214+1027.2+1356+856)",
    "ศรีฟ้าโฟรเซนฟู้ด  CPOKAN6901003",
    "เอกวนิชฟาร์ม่า  CPOKAN6901003",
    "สยาม บิลด์อิท CPOKAN6901003",  # appears 5 times
    "สยาม บิลด์อิท CPOKAN6901003",
    "สยาม บิลด์อิท CPOKAN6901003",
    "สยาม บิลด์อิท CPOKAN6901003",
    "สยาม บิลด์อิท CPOKAN6901003",
    "สยาม บิลด์อิท  CPOKAN6901003",
    "ธนกาญจน์แก๊ส  CPOKAN6901003",
    "ฉินอี่กี่",
]

print(f'Expected transactions: {len(expected_descriptions)}')
print()

# Get actual from converter
converter = ThaiBankStatementConverter()
with open('demo_data/Petty Cash 01-080126.xlsx', 'rb') as f:
    file_data = f.read()

result = converter.convert_file(file_data, 'Petty Cash 01-080126.xlsx')

print(f'Actual transactions found: {len(result)}')
print()

# Extract descriptions from results
actual_descriptions = [trans['payment_ref'].split(' / ')[0] for trans in result]

print('Checking for missing transaction...')
print()

# Check which expected description is missing
for i, expected in enumerate(expected_descriptions, 1):
    # Normalize for comparison
    found = any(expected[:30] in actual for actual in actual_descriptions)
    if not found:
        print(f'❌ MISSING Transaction #{i}: {expected[:80]}')

print()
print('Done.')
