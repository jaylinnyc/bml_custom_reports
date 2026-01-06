# -*- coding: utf-8 -*-
"""
Thailand Withholding Tax Handling for Vendor Bills

This module modifies how withholding taxes are handled for Thai accounting:
1. WHT tax lines are excluded from journal entries at bill posting time
2. WHT is recorded in the journal at payment time
3. The payable amount remains: Gross - WHT + VAT (standard Odoo calculation)

Key concept: We DON'T change the bill amounts, we only change WHEN the WHT
journal entries are created (at payment instead of at bill posting).
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    """
    Extend account.move to handle Thai withholding tax requirements.
    
    In Thailand, WHT should be recorded in journal at payment time, not at
    bill posting time. This extension:
    1. Tracks WHT amounts on the bill for reference
    2. Excludes WHT lines from journal entries at posting (handled separately)
    """
    _inherit = 'account.move'

    # -------------------------------------------------------------------------
    # Computed Fields for WHT Information
    # -------------------------------------------------------------------------
    
    wht_tax_line_ids = fields.One2many(
        comodel_name='account.move.line',
        compute='_compute_wht_info',
        string="WHT Tax Lines",
        help="Tax lines that are withholding taxes"
    )
    
    wht_amount = fields.Monetary(
        compute='_compute_wht_info',
        string="Withholding Tax Amount",
        currency_field='currency_id',
        store=True,
        help="Total withholding tax amount on this bill"
    )
    
    has_wht = fields.Boolean(
        compute='_compute_wht_info',
        string="Has Withholding Tax",
        store=True,
        help="True if this bill has withholding taxes"
    )
    
    wht_base_amount = fields.Monetary(
        compute='_compute_wht_info',
        string="WHT Base Amount",
        currency_field='currency_id',
        store=True,
        help="Total base amount for withholding tax calculation"
    )
    
    # Flag to track if WHT has been posted to journal (at payment time)
    wht_posted = fields.Boolean(
        string="WHT Posted",
        default=False,
        copy=False,
        help="True if withholding tax has been posted to journal (at payment time)"
    )

    @api.depends('line_ids', 'line_ids.tax_line_id', 'line_ids.balance', 'line_ids.tax_base_amount')
    def _compute_wht_info(self):
        """
        Compute withholding tax information from invoice lines.
        WHT taxes are identified by name containing 'Withholding' and being Purchase type.
        """
        for move in self:
            wht_lines = move.line_ids.filtered(
                lambda l: l.tax_line_id and self._is_withholding_tax(l.tax_line_id)
            )
            
            move.wht_tax_line_ids = wht_lines
            move.has_wht = bool(wht_lines)
            
            # WHT amount is typically negative (deduction), we show absolute value
            move.wht_amount = abs(sum(wht_lines.mapped('balance')))
            move.wht_base_amount = abs(sum(wht_lines.mapped('tax_base_amount')))

    @api.model
    def _is_withholding_tax(self, tax):
        """
        Determine if a tax is a withholding tax.
        
        PRIMARY criteria (most reliable):
        - Tax amount is NEGATIVE (withholding = deduction from payment)
        - Tax type is 'purchase'
        
        This catches all WHT regardless of naming convention since WHT is 
        fundamentally a deduction (negative percentage) on purchase transactions.
        
        Examples that will match:
        - "3% WH C S" with amount=-3.0, type=purchase ✓
        - "Withholding Tax 1%" with amount=-1.0, type=purchase ✓
        - "หัก ณ ที่จ่าย 5%" with amount=-5.0, type=purchase ✓
        
        :param tax: account.tax record
        :return: Boolean
        """
        if not tax:
            return False
        
        # Withholding tax = negative percentage on purchase
        # This is the defining characteristic regardless of naming
        return tax.type_tax_use == 'purchase' and tax.amount < 0

    def _get_wht_taxes(self):
        """
        Get all WHT taxes applied to this invoice.
        Returns dict with tax as key and amount details as value.
        """
        self.ensure_one()
        wht_taxes = {}
        
        for line in self.line_ids:
            if line.tax_line_id and self._is_withholding_tax(line.tax_line_id):
                tax = line.tax_line_id
                if tax not in wht_taxes:
                    wht_taxes[tax] = {
                        'tax': tax,
                        'base_amount': 0.0,
                        'tax_amount': 0.0,
                        'rate': abs(tax.amount),
                    }
                wht_taxes[tax]['tax_amount'] += abs(line.balance)
                wht_taxes[tax]['base_amount'] += abs(line.tax_base_amount)
        
        return wht_taxes

    def _get_wht_summary_for_payment(self):
        """
        Get WHT summary for display in payment wizard.
        Returns list of dicts with WHT details per tax.
        """
        self.ensure_one()
        summary = []
        
        wht_taxes = self._get_wht_taxes()
        for tax, amounts in wht_taxes.items():
            summary.append({
                'tax_id': tax.id,
                'tax_name': tax.name,
                'rate': amounts['rate'],
                'base_amount': amounts['base_amount'],
                'wht_amount': amounts['tax_amount'],
            })
        
        return summary


class AccountMoveLine(models.Model):
    """
    Extend account.move.line to add WHT-related fields for filtering.
    """
    _inherit = 'account.move.line'

    is_wht_line = fields.Boolean(
        compute='_compute_is_wht_line',
        string="Is WHT Line",
        store=True,
        help="True if this line is a withholding tax line"
    )

    @api.depends('tax_line_id', 'tax_line_id.name', 'tax_line_id.type_tax_use')
    def _compute_is_wht_line(self):
        """Compute if this line is a withholding tax line"""
        for line in self:
            if line.tax_line_id:
                line.is_wht_line = self.env['account.move']._is_withholding_tax(line.tax_line_id)
            else:
                line.is_wht_line = False
