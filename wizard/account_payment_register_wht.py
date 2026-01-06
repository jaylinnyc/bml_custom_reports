# -*- coding: utf-8 -*-
"""
Thailand Withholding Tax Payment Register Extension

This module extends the payment registration wizard to:
1. Display WHT breakdown for bills being paid
2. Create WHT journal entries at payment time
3. Support payment adjustments (bank charges, etc.)
"""

from odoo import models, fields, api, Command, _
from odoo.exceptions import UserError
from collections import defaultdict
import logging

_logger = logging.getLogger(__name__)


class AccountPaymentRegister(models.TransientModel):
    """
    Extend the payment register wizard to handle Thai withholding tax.
    """
    _inherit = 'account.payment.register'

    # -------------------------------------------------------------------------
    # WHT Display Fields
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
        help="Total withholding tax amount to be recorded at payment"
    )
    
    # Original bill amount before WHT deduction
    gross_amount = fields.Monetary(
        string="Gross Amount",
        currency_field='currency_id',
        compute='_compute_wht_lines',
        store=True,
        help="Original bill amount before WHT deduction"
    )
    
    # -------------------------------------------------------------------------
    # Payment Adjustment Fields
    # -------------------------------------------------------------------------
    
    adjustment_line_ids = fields.One2many(
        comodel_name='account.payment.register.adjustment',
        inverse_name='payment_register_id',
        string="Payment Adjustments",
    )
    
    total_adjustment_amount = fields.Monetary(
        string="Total Adjustments",
        currency_field='currency_id',
        compute='_compute_adjustment_totals',
    )
    
    # Final payment amount after adjustments
    net_payment_amount = fields.Monetary(
        string="Net Payment",
        currency_field='currency_id',
        compute='_compute_adjustment_totals',
        help="Actual amount to be paid after adjustments"
    )

    # -------------------------------------------------------------------------
    # Compute Methods
    # -------------------------------------------------------------------------

    @api.depends('line_ids', 'line_ids.move_id')
    def _compute_wht_lines(self):
        """
        Compute WHT information from the bills being paid.
        Aggregates WHT by tax across all selected bills.
        """
        for wizard in self:
            wht_data = defaultdict(lambda: {
                'tax_name': '',
                'rate': 0.0,
                'base_amount': 0.0,
                'wht_amount': 0.0,
            })
            
            gross_amount = 0.0
            total_wht = 0.0
            
            # Get unique moves from lines
            moves = wizard.line_ids.mapped('move_id')
            
            for move in moves:
                if move.move_type == 'in_invoice':  # Vendor bills only
                    # Get WHT summary from bill
                    wht_taxes = move._get_wht_taxes()
                    
                    for tax, amounts in wht_taxes.items():
                        wht_data[tax.id]['tax_name'] = tax.name
                        wht_data[tax.id]['rate'] = amounts['rate']
                        wht_data[tax.id]['base_amount'] += amounts['base_amount']
                        wht_data[tax.id]['wht_amount'] += amounts['tax_amount']
                        total_wht += amounts['tax_amount']
                    
                    # Calculate gross (amount before WHT deduction)
                    # Gross = Amount Total (what we pay) + WHT Amount (what was deducted)
                    gross_amount += move.amount_total + move.wht_amount
            
            # Create WHT line records
            wht_lines = []
            for tax_id, data in wht_data.items():
                wht_lines.append(Command.create({
                    'tax_id': tax_id,
                    'tax_name': data['tax_name'],
                    'rate': data['rate'],
                    'base_amount': data['base_amount'],
                    'wht_amount': data['wht_amount'],
                }))
            
            wizard.wht_line_ids = [Command.clear()] + wht_lines
            wizard.has_wht = bool(wht_data)
            wizard.total_wht_amount = total_wht
            wizard.gross_amount = gross_amount

    @api.depends('amount', 'adjustment_line_ids', 'adjustment_line_ids.amount')
    def _compute_adjustment_totals(self):
        """Compute total adjustments and net payment amount"""
        for wizard in self:
            total_adj = sum(wizard.adjustment_line_ids.mapped('amount'))
            wizard.total_adjustment_amount = total_adj
            # Net payment = bill amount - adjustments (positive adj = reduce payment)
            wizard.net_payment_amount = wizard.amount - total_adj

    # -------------------------------------------------------------------------
    # Business Methods Override
    # -------------------------------------------------------------------------

    def _create_payment_vals_from_wizard(self, batch_result):
        """
        Override to add adjustment lines to the payment write-off lines.
        """
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        
        # Add adjustment lines as write-off lines
        for adj in self.adjustment_line_ids:
            if adj.amount and adj.account_id:
                if self.payment_type == 'outbound':
                    # Paying vendor - positive adjustment = expense = reduces payment
                    amount_currency = adj.amount
                else:
                    # Receiving from customer
                    amount_currency = -adj.amount
                
                payment_vals['write_off_line_vals'].append({
                    'name': adj.name or _('Payment Adjustment'),
                    'account_id': adj.account_id.id,
                    'partner_id': self.partner_id.id,
                    'currency_id': self.currency_id.id,
                    'amount_currency': amount_currency,
                    'balance': self.currency_id._convert(
                        amount_currency, 
                        self.company_id.currency_id, 
                        self.company_id, 
                        self.payment_date
                    ),
                })
        
        return payment_vals

    def _post_payments(self, to_process, edit_mode=False):
        """
        Override to create WHT journal entries after payment is posted.
        """
        result = super()._post_payments(to_process, edit_mode=edit_mode)
        
        # Create WHT journal entries for payments with WHT
        if self.has_wht:
            for vals in to_process:
                payment = vals['payment']
                self._create_wht_journal_entry(payment, vals['batch'])
        
        return result

    def _create_wht_journal_entry(self, payment, batch):
        """
        Create WHT journal entry at payment time.
        
        This creates a journal entry to record the WHT that was deducted.
        The entry debits the WHT payable account (liability) and credits
        the vendor payable account.
        """
        moves = batch['lines'].mapped('move_id')
        
        for move in moves:
            if not move.has_wht or move.wht_posted:
                continue
            
            wht_taxes = move._get_wht_taxes()
            if not wht_taxes:
                continue
            
            # Create journal entry for WHT
            journal = self.env.company.tax_cash_basis_journal_id or self.journal_id
            
            line_vals = []
            total_wht = 0.0
            
            for tax, amounts in wht_taxes.items():
                wht_amount = amounts['tax_amount']
                total_wht += wht_amount
                
                # Get the WHT account from tax repartition lines
                rep_lines = tax.invoice_repartition_line_ids.filtered(
                    lambda l: l.repartition_type == 'tax'
                )
                wht_account = rep_lines[0].account_id if rep_lines else None
                
                if not wht_account:
                    _logger.warning(
                        f"No account found for WHT tax {tax.name}. "
                        "Please configure tax repartition lines."
                    )
                    continue
                
                # Debit WHT account (we're recording the WHT that was withheld)
                line_vals.append(Command.create({
                    'name': f"WHT - {tax.name} ({move.name})",
                    'account_id': wht_account.id,
                    'partner_id': move.partner_id.id,
                    'debit': wht_amount,
                    'credit': 0.0,
                }))
            
            if line_vals and total_wht > 0:
                # Credit vendor payable (offset the WHT debit)
                payable_account = move.partner_id.property_account_payable_id
                line_vals.append(Command.create({
                    'name': f"WHT Offset - {move.name}",
                    'account_id': payable_account.id,
                    'partner_id': move.partner_id.id,
                    'debit': 0.0,
                    'credit': total_wht,
                }))
                
                # Create the journal entry
                wht_move = self.env['account.move'].create({
                    'move_type': 'entry',
                    'date': payment.date,
                    'journal_id': journal.id,
                    'ref': f"WHT for {move.name} - Payment {payment.name}",
                    'partner_id': move.partner_id.id,
                    'line_ids': line_vals,
                })
                
                # Post the WHT entry
                wht_move.action_post()
                
                # Mark the original bill as WHT posted
                move.wht_posted = True
                
                _logger.info(
                    f"Created WHT journal entry {wht_move.name} "
                    f"for payment {payment.name}"
                )


class AccountPaymentRegisterWhtLine(models.TransientModel):
    """
    Transient model to display WHT breakdown in payment wizard.
    """
    _name = 'account.payment.register.wht.line'
    _description = 'Payment Register WHT Line'

    payment_register_id = fields.Many2one(
        comodel_name='account.payment.register',
        string="Payment Register",
        required=True,
        ondelete='cascade',
    )
    
    tax_id = fields.Many2one(
        comodel_name='account.tax',
        string="Tax",
    )
    
    tax_name = fields.Char(
        string="Withholding Tax",
    )
    
    rate = fields.Float(
        string="Rate (%)",
    )
    
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='payment_register_id.currency_id',
    )
    
    base_amount = fields.Monetary(
        string="Base Amount",
        currency_field='currency_id',
    )
    
    wht_amount = fields.Monetary(
        string="WHT Amount",
        currency_field='currency_id',
    )


class AccountPaymentRegisterAdjustment(models.TransientModel):
    """
    Transient model for payment adjustments (bank charges, fees, etc.)
    """
    _name = 'account.payment.register.adjustment'
    _description = 'Payment Register Adjustment'

    payment_register_id = fields.Many2one(
        comodel_name='account.payment.register',
        string="Payment Register",
        required=True,
        ondelete='cascade',
    )
    
    name = fields.Char(
        string="Description",
        required=True,
        default="Bank Charge",
    )
    
    account_id = fields.Many2one(
        comodel_name='account.account',
        string="Account",
        required=True,
        domain="[('account_type', 'not in', ('asset_receivable', 'liability_payable'))]",
    )
    
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='payment_register_id.currency_id',
    )
    
    amount = fields.Monetary(
        string="Amount",
        currency_field='currency_id',
        required=True,
        help="Positive amount = deduction from payment (e.g., bank charge). "
             "Negative amount = addition to payment.",
    )
