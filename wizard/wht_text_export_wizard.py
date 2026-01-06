# -*- coding: utf-8 -*-
"""
Thailand Withholding Tax Text Export Wizard

Exports WHT data in the Thai Revenue Department pipe-delimited text format
for PND (ภ.ง.ด.) submission.

Format Reference (from sample):
00|00001|0000000000000|0000000000000|0135523000051|00000|1|0|1|0|1|2568|12|
3710100893846|0000000000|00000|นาย|อุดม|รี่แท้|||||72 หมู่ที่||||สองคอน|
แก่งคอย|สระบุรี|18110|082-45-41-429|31122568|ค่าจ้างเหมา|.00|63291.67|4339.79|1|
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import io
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


# Buddhist year offset
BUDDHIST_YEAR_OFFSET = 543


def to_buddhist_year(date_obj):
    """Convert a date to Buddhist year"""
    return date_obj.year + BUDDHIST_YEAR_OFFSET


def format_date_buddhist(date_obj, format_type='DDMMYYYY'):
    """Format date in Buddhist calendar format"""
    if not date_obj:
        return ''
    
    buddhist_year = to_buddhist_year(date_obj)
    
    if format_type == 'DDMMYYYY':
        return f"{date_obj.day:02d}{date_obj.month:02d}{buddhist_year}"
    elif format_type == 'YEAR':
        return str(buddhist_year)
    elif format_type == 'MONTH':
        return str(date_obj.month)
    
    return ''


class WhtTextExportWizard(models.TransientModel):
    """
    Wizard to export WHT data in Thai Revenue Department text format.
    """
    _name = 'wht.text.export.wizard'
    _description = 'WHT Text Export Wizard'

    # Filter fields
    date_from = fields.Date(
        string="From Date",
        required=True,
        default=lambda self: fields.Date.today().replace(day=1),
    )
    
    date_to = fields.Date(
        string="To Date",
        required=True,
        default=fields.Date.today,
    )
    
    pnd_form_type = fields.Selection(
        selection=[
            ('pnd3', 'ภ.ง.ด.3 (PND 3) - Individual'),
            ('pnd53', 'ภ.ง.ด.53 (PND 53) - Company'),
        ],
        string="PND Form Type",
        required=True,
        default='pnd53',
        help="Select the PND form type for export"
    )
    
    income_type = fields.Selection(
        selection=[
            ('1', '1 - เงินเดือน ค่าจ้าง (Salary/Wages)'),
            ('2', '2 - ค่านายหน้า (Brokerage)'),
            ('3', '3 - ค่าลิขสิทธิ์ (Royalties)'),
            ('4a', '4(a) - ดอกเบี้ย (Interest)'),
            ('4b', '4(b) - เงินปันผล (Dividends)'),
            ('5', '5 - ค่าเช่าทรัพย์สิน (Rental)'),
            ('6', '6 - ค่าวิชาชีพอิสระ (Liberal profession)'),
            ('7', '7 - รับเหมาก่อสร้าง (Construction)'),
            ('8', '8 - ค่าจ้างทำของ/บริการ (Service fees)'),
            ('9', '9 - ค่าโฆษณา (Advertising)'),
            ('10', '10 - ค่าขนส่ง (Transportation)'),
        ],
        string="Income Type",
        default='8',
        help="Default income type for export (can be overridden per line)"
    )
    
    company_id = fields.Many2one(
        comodel_name='res.company',
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    
    # Output fields
    file_data = fields.Binary(
        string="File",
        readonly=True,
    )
    
    file_name = fields.Char(
        string="Filename",
        readonly=True,
    )
    
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('done', 'Done'),
        ],
        default='draft',
    )
    
    # Statistics
    record_count = fields.Integer(
        string="Records Exported",
        readonly=True,
    )
    
    total_base_amount = fields.Float(
        string="Total Base Amount",
        readonly=True,
    )
    
    total_wht_amount = fields.Float(
        string="Total WHT Amount",
        readonly=True,
    )

    def action_export(self):
        """
        Export WHT data to text file in Thai Revenue Department format.
        """
        self.ensure_one()
        
        # Get payments with WHT in the date range
        payments = self._get_wht_payments()
        
        if not payments:
            raise UserError(_("No payments with withholding tax found in the selected date range."))
        
        # Generate the text content
        lines = []
        sequence = 0
        total_base = 0.0
        total_wht = 0.0
        
        for payment in payments:
            # Get WHT details from the related bills
            wht_records = self._get_payment_wht_records(payment)
            
            for record in wht_records:
                sequence += 1
                line = self._format_wht_line(sequence, record)
                lines.append(line)
                total_base += record.get('base_amount', 0)
                total_wht += record.get('wht_amount', 0)
        
        if not lines:
            raise UserError(_("No WHT records found for export."))
        
        # Combine all lines
        content = '\n'.join(lines)
        
        # Create file
        file_content = content.encode('utf-8')
        
        # Generate filename
        date_str = fields.Date.today().strftime('%Y%m%d')
        filename = f"WHT_{self.pnd_form_type}_{date_str}.txt"
        
        # Update wizard with results
        self.write({
            'file_data': base64.b64encode(file_content),
            'file_name': filename,
            'state': 'done',
            'record_count': len(lines),
            'total_base_amount': total_base,
            'total_wht_amount': total_wht,
        })
        
        # Return action to download file
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def _get_wht_payments(self):
        """
        Get payments that have WHT within the date range.
        """
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('state', '=', 'paid'),
            ('payment_type', '=', 'outbound'),  # Vendor payments
            ('company_id', '=', self.company_id.id),
        ]
        
        payments = self.env['account.payment'].search(domain)
        
        # Filter to only those with WHT bills
        wht_payments = payments.filtered(
            lambda p: any(
                inv.has_wht for inv in p.reconciled_bill_ids
            )
        )
        
        return wht_payments

    def _get_payment_wht_records(self, payment):
        """
        Get WHT records for a payment.
        Returns list of dicts with WHT details.
        """
        records = []
        
        for bill in payment.reconciled_bill_ids:
            if not bill.has_wht:
                continue
            
            partner = bill.partner_id
            wht_taxes = bill._get_wht_taxes()
            
            for tax, amounts in wht_taxes.items():
                records.append({
                    'payment': payment,
                    'bill': bill,
                    'partner': partner,
                    'tax': tax,
                    'payment_date': payment.date,
                    'base_amount': amounts['base_amount'],
                    'wht_amount': amounts['tax_amount'],
                    'rate': amounts['rate'],
                })
        
        return records

    def _format_wht_line(self, sequence, record):
        """
        Format a single WHT record as a pipe-delimited line.
        
        Field positions based on sample:
        1. Record type (00)
        2. Sequence number (5 digits)
        3. Tax ID payer (13 digits, padded)
        4. Branch code (13 digits, padded)
        5. Company Tax ID (13 digits)
        6. Unknown (5 digits)
        7. Form type indicator
        8-10. Unknown flags
        11. Month type
        12. Buddhist Year
        13. Month
        14. Payee ID (13 digits)
        15. Unknown (10 digits)
        16. Unknown (5 digits)
        17. Title
        18. First name
        19. Last name
        20-24. Company name fields (for companies)
        25. Address line 1
        26-28. Address fields
        29. Sub-district (Tambon)
        30. District (Amphoe)
        31. Province
        32. Postal code
        33. Phone
        34. Payment date (DDMMYYYY Buddhist)
        35. Income description
        36. Tax rate (or .00)
        37. Base amount
        38. WHT amount
        39. Income type code
        40. End marker (empty)
        """
        partner = record['partner']
        payment_date = record['payment_date']
        bill = record['bill']
        
        # Parse partner name (handle both individual and company)
        title, first_name, last_name = self._parse_partner_name(partner)
        company_name = '' if partner.is_company else ''
        
        # Get address components
        address = self._parse_address(partner)
        
        # Get tax ID
        partner_vat = (partner.vat or '').replace('-', '').strip()
        partner_vat = partner_vat.zfill(13) if partner_vat else '0' * 13
        
        # Company tax ID
        company_vat = (self.company_id.vat or '').replace('-', '').strip()
        company_vat = company_vat.zfill(13) if company_vat else '0' * 13
        
        # Form type indicator (1 for PND53, adjust for others)
        form_indicator = '1' if self.pnd_form_type == 'pnd53' else '1'
        
        # Build the line
        fields_list = [
            '00',                                    # 1. Record type
            f'{sequence:05d}',                       # 2. Sequence
            '0' * 13,                                # 3. Tax ID payer (padded)
            '0' * 13,                                # 4. Branch code (padded)
            company_vat,                             # 5. Company Tax ID
            '00000',                                 # 6. Unknown
            form_indicator,                          # 7. Form type
            '0',                                     # 8. Unknown
            '1',                                     # 9. Unknown
            '0',                                     # 10. Unknown
            '1',                                     # 11. Month type
            format_date_buddhist(payment_date, 'YEAR'),  # 12. Buddhist Year
            format_date_buddhist(payment_date, 'MONTH'), # 13. Month
            partner_vat,                             # 14. Payee ID
            '0' * 10,                                # 15. Unknown
            '00000',                                 # 16. Unknown
            title,                                   # 17. Title
            first_name,                              # 18. First name
            last_name,                               # 19. Last name
            '',                                      # 20. Company field 1
            '',                                      # 21. Company field 2
            '',                                      # 22. Company field 3
            '',                                      # 23. Company field 4
            '',                                      # 24. Company field 5
            address.get('street', ''),               # 25. Address line 1
            '',                                      # 26. Address field
            '',                                      # 27. Address field
            '',                                      # 28. Address field
            address.get('tambon', ''),               # 29. Sub-district
            address.get('amphoe', ''),               # 30. District
            address.get('province', ''),             # 31. Province
            address.get('zip', ''),                  # 32. Postal code
            partner.phone or '',                     # 33. Phone
            format_date_buddhist(payment_date, 'DDMMYYYY'),  # 34. Payment date
            self._get_income_description(bill),      # 35. Income description
            '.00',                                   # 36. Tax rate indicator
            f'{record["base_amount"]:.2f}',          # 37. Base amount
            f'{record["wht_amount"]:.2f}',           # 38. WHT amount
            self._get_income_type_code(),            # 39. Income type code
            '',                                      # 40. End marker
        ]
        
        return '|'.join(fields_list)

    def _parse_partner_name(self, partner):
        """
        Parse partner name into title, first name, last name.
        """
        if partner.is_company:
            return '', partner.name or '', ''
        
        name = partner.name or ''
        
        # Common Thai titles
        titles = ['นาย', 'นาง', 'นางสาว', 'Mr.', 'Mrs.', 'Miss', 'Ms.', 'Dr.']
        
        title = ''
        for t in titles:
            if name.startswith(t):
                title = t
                name = name[len(t):].strip()
                break
        
        # Split remaining name
        parts = name.split()
        if len(parts) >= 2:
            first_name = parts[0]
            last_name = ' '.join(parts[1:])
        else:
            first_name = name
            last_name = ''
        
        return title, first_name, last_name

    def _parse_address(self, partner):
        """
        Parse partner address into components.
        Thai addresses: street, sub-district (tambon), district (amphoe), province, zip
        """
        return {
            'street': partner.street or '',
            'street2': partner.street2 or '',
            'tambon': '',  # Would need custom field for Thai sub-district
            'amphoe': partner.city or '',  # City often used for district
            'province': partner.state_id.name if partner.state_id else '',
            'zip': partner.zip or '',
        }

    def _get_income_description(self, bill):
        """
        Get income description for WHT.
        """
        # Try to get from bill reference or use default
        if bill.ref:
            return bill.ref[:50]  # Limit length
        
        # Default descriptions by income type
        descriptions = {
            '1': 'เงินเดือน',
            '2': 'ค่านายหน้า',
            '3': 'ค่าลิขสิทธิ์',
            '4a': 'ดอกเบี้ย',
            '4b': 'เงินปันผล',
            '5': 'ค่าเช่า',
            '6': 'ค่าวิชาชีพ',
            '7': 'ค่าก่อสร้าง',
            '8': 'ค่าจ้างเหมา',
            '9': 'ค่าโฆษณา',
            '10': 'ค่าขนส่ง',
        }
        
        return descriptions.get(self.income_type, 'ค่าจ้างเหมา')

    def _get_income_type_code(self):
        """
        Get income type code for the export.
        """
        # Map selection to numeric code
        type_codes = {
            '1': '1',
            '2': '2',
            '3': '3',
            '4a': '4',
            '4b': '4',
            '5': '5',
            '6': '6',
            '7': '7',
            '8': '1',  # Service fees often coded as 1
            '9': '9',
            '10': '10',
        }
        
        return type_codes.get(self.income_type, '1')

    def action_back(self):
        """Go back to draft state to re-export"""
        self.write({
            'state': 'draft',
            'file_data': False,
            'file_name': False,
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }
