# -*- coding: utf-8 -*-
"""
Thailand Withholding Tax Payment Register Extension

This module extends the payment registration wizard to display WHT breakdown
for bills being paid. 

NOTE: 
- WHT journal entries are handled by Odoo's native cash basis mechanism
  (tax_exigibility = 'on_payment'). No custom journal entry creation needed.
- Payment adjustments (bank charges) use Odoo's built-in payment_difference
  and writeoff_account_id fields. No custom adjustment lines needed.
"""

from odoo import models, fields, api, Command
from collections import defaultdict
import logging

_logger = logging.getLogger(__name__)


class AccountPaymentRegister(models.TransientModel):
    """
    Extend the payment register wizard to display Thai withholding tax information.
    This is purely informational - WHT entries are created by Odoo's cash basis.
    
    Also adds simplified adjustment feature for scenarios like:
    - Bank charges deduction
    - Partial/split payments with writeoff
    """
    _inherit = 'account.payment.register'

    # -------------------------------------------------------------------------
    # Simplified Payment Adjustment
    # -------------------------------------------------------------------------
    
    apply_adjustment = fields.Boolean(
        string="Deduct Charges",
        default=False,
        help="Enable to deduct bank charges or other fees from this payment"
    )
    
    adjustment_amount = fields.Monetary(
        string="Charge Amount",
        currency_field='currency_id',
        default=0.0,
        help="Amount to deduct (e.g., bank transfer fee). Will be posted to the selected account."
    )
    
    adjustment_account_id = fields.Many2one(
        comodel_name='account.account',
        string="Charge Account",
        domain="[('account_type', 'in', ['expense', 'expense_direct_cost'])]",
        help="Account to post the charge (e.g., Bank Charges expense account)"
    )
    
    adjustment_label = fields.Char(
        string="Charge Description",
        default="Bank Charges",
        help="Description for the journal entry line"
    )
    
    show_writeoff_section = fields.Boolean(
        string="Show Writeoff Section",
        compute='_compute_show_writeoff_section',
        help="Technical field to control visibility of writeoff section"
    )

    @api.depends('apply_adjustment', 'payment_difference', 'early_payment_discount_mode', 
                 'can_edit_wizard', 'can_group_payments', 'group_payment', 'payment_method_line_id')
    def _compute_show_writeoff_section(self):
        """Show writeoff section when manually enabled OR when there's a payment difference."""
        for wizard in self:
            # Show if manually forced
            if wizard.apply_adjustment:
                wizard.show_writeoff_section = True
            # Or show based on standard Odoo logic (payment_difference exists)
            else:
                wizard.show_writeoff_section = (
                    wizard.payment_difference != 0.0
                    and not wizard.early_payment_discount_mode
                    and wizard.can_edit_wizard
                    and (not wizard.can_group_payments or wizard.group_payment)
                    and wizard.payment_method_line_id.payment_account_id
                )

    @api.onchange('apply_adjustment', 'adjustment_amount')
    def _onchange_adjustment(self):
        """When adjustment is enabled/changed, set Odoo's writeoff fields accordingly."""
        if self.apply_adjustment and self.adjustment_amount > 0:
            # Set Odoo's native fields to handle the writeoff
            self.payment_difference_handling = 'reconcile'
            self.writeoff_account_id = self.adjustment_account_id
            self.writeoff_label = self.adjustment_label or 'Bank Charges'
            # Reduce payment amount by the charge
            if self.can_edit_wizard:
                total_values = self._get_total_amounts_to_pay(self.batches)
                self.amount = total_values.get('amount_by_default', self.amount) - self.adjustment_amount
        elif not self.apply_adjustment:
            # Reset to default
            self.payment_difference_handling = 'open'

    @api.onchange('adjustment_account_id')
    def _onchange_adjustment_account(self):
        """Sync adjustment account to Odoo's writeoff account."""
        if self.apply_adjustment and self.adjustment_account_id:
            self.writeoff_account_id = self.adjustment_account_id

    @api.onchange('adjustment_label')
    def _onchange_adjustment_label(self):
        """Sync adjustment label to Odoo's writeoff label."""
        if self.apply_adjustment and self.adjustment_label:
            self.writeoff_label = self.adjustment_label

    # -------------------------------------------------------------------------
    # WHT Display Fields (informational only)
    # -------------------------------------------------------------------------
    
    wht_line_ids = fields.One2many(
        comodel_name='account.payment.register.wht.line',
        inverse_name='payment_register_id',
        string="Withholding Taxes",
        compute='_compute_wht_lines',
        store=True,
        readonly=True,
    )
    
    has_wht = fields.Boolean(
        string="Has Withholding Tax",
        compute='_compute_wht_lines',
        store=True,
    )
    
    total_wht_amount = fields.Monetary(
        string="Total WHT Amount",
        currency_field='currency_id',
        compute='_compute_wht_lines',
        store=True,
    )
    
    gross_amount = fields.Monetary(
        string="Gross Amount",
        currency_field='currency_id',
        compute='_compute_wht_lines',
        store=True,
    )

    @api.depends('line_ids', 'line_ids.move_id')
    def _compute_wht_lines(self):
        """Compute WHT information from bills for display purposes."""
        for wizard in self:
            wht_data = defaultdict(lambda: {
                'tax_name': '',
                'rate': 0.0,
                'base_amount': 0.0,
                'wht_amount': 0.0,
            })
            
            gross_amount = 0.0
            total_wht = 0.0
            moves = wizard.line_ids.mapped('move_id')
            
            for move in moves:
                if move.move_type == 'in_invoice':
                    wht_taxes = move._get_wht_taxes()
                    for tax, amounts in wht_taxes.items():
                        wht_data[tax.id]['tax_name'] = tax.name
                        wht_data[tax.id]['rate'] = amounts['rate']
                        wht_data[tax.id]['base_amount'] += amounts['base_amount']
                        wht_data[tax.id]['wht_amount'] += amounts['tax_amount']
                        total_wht += amounts['tax_amount']
                    gross_amount += move.amount_total + move.wht_amount
            
            wht_lines = [Command.clear()]
            for tax_id, data in wht_data.items():
                wht_lines.append(Command.create({
                    'tax_id': tax_id,
                    'tax_name': data['tax_name'],
                    'rate': data['rate'],
                    'base_amount': data['base_amount'],
                    'wht_amount': data['wht_amount'],
                }))
            
            wizard.wht_line_ids = wht_lines
            wizard.has_wht = bool(wht_data)
            wizard.total_wht_amount = total_wht
            wizard.gross_amount = gross_amount


class AccountPaymentRegisterWhtLine(models.TransientModel):
    """Transient model to display WHT breakdown in payment wizard."""
    _name = 'account.payment.register.wht.line'
    _description = 'Payment Register WHT Line'

    payment_register_id = fields.Many2one(
        'account.payment.register', required=True, ondelete='cascade')
    tax_id = fields.Many2one('account.tax', string="Tax")
    tax_name = fields.Char(string="Withholding Tax")
    rate = fields.Float(string="Rate (%)")
    currency_id = fields.Many2one(
        'res.currency', related='payment_register_id.currency_id')
    base_amount = fields.Monetary(string="Base Amount", currency_field='currency_id')
    wht_amount = fields.Monetary(string="WHT Amount", currency_field='currency_id')
