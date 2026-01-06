# -*- coding: utf-8 -*-
"""
Thailand Withholding Tax Tracking for Vendor Bills

Tracks WHT amounts on vendor bills for display and export purposes.
WHT journal entries are handled by Odoo's native cash basis mechanism
(tax_exigibility = 'on_payment').
"""

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    """Extend account.move to track Thai withholding tax information."""
    _inherit = 'account.move'

    # Non-stored computed field
    wht_tax_line_ids = fields.One2many(
        comodel_name='account.move.line',
        compute='_compute_wht_tax_line_ids',
        string="WHT Tax Lines",
    )
    
    # Stored computed fields
    wht_amount = fields.Monetary(
        compute='_compute_wht_amounts',
        string="WHT Amount",
        currency_field='currency_id',
        store=True,
    )
    
    has_wht = fields.Boolean(
        compute='_compute_wht_amounts',
        string="Has WHT",
        store=True,
    )
    
    wht_base_amount = fields.Monetary(
        compute='_compute_wht_amounts',
        string="WHT Base",
        currency_field='currency_id',
        store=True,
    )

    @api.depends('line_ids', 'line_ids.tax_line_id')
    def _compute_wht_tax_line_ids(self):
        for move in self:
            move.wht_tax_line_ids = move.line_ids.filtered(
                lambda l: l.tax_line_id and self._is_withholding_tax(l.tax_line_id)
            )

    @api.depends('line_ids', 'line_ids.tax_line_id', 'line_ids.balance', 'line_ids.tax_base_amount')
    def _compute_wht_amounts(self):
        for move in self:
            wht_lines = move.line_ids.filtered(
                lambda l: l.tax_line_id and self._is_withholding_tax(l.tax_line_id)
            )
            move.has_wht = bool(wht_lines)
            move.wht_amount = abs(sum(wht_lines.mapped('balance')))
            move.wht_base_amount = abs(sum(wht_lines.mapped('tax_base_amount')))

    @api.model
    def _is_withholding_tax(self, tax):
        """WHT = negative purchase tax"""
        return tax and tax.type_tax_use == 'purchase' and tax.amount < 0

    def _get_wht_taxes(self):
        """Get WHT taxes for this invoice. Used by payment wizard and export."""
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


class AccountMoveLine(models.Model):
    """Extend account.move.line to identify WHT lines."""
    _inherit = 'account.move.line'

    is_wht_line = fields.Boolean(
        compute='_compute_is_wht_line',
        string="Is WHT",
        store=True,
    )

    @api.depends('tax_line_id', 'tax_line_id.type_tax_use', 'tax_line_id.amount')
    def _compute_is_wht_line(self):
        for line in self:
            line.is_wht_line = bool(
                line.tax_line_id and 
                self.env['account.move']._is_withholding_tax(line.tax_line_id)
            )
