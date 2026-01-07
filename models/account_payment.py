# -*- coding: utf-8 -*-
"""
Account Payment Extension for Invoice Selection

Extends the account.payment model to allow selecting unpaid invoices
when creating a direct customer payment. This enables:
- Linking payments to multiple unpaid invoices
- Partial payments across invoices
- Better tracking of which invoices a payment covers
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    """
    Extend account.payment to allow selecting invoices when creating payment directly.
    """
    _inherit = 'account.payment'

    # -------------------------------------------------------------------------
    # Invoice Selection Fields
    # -------------------------------------------------------------------------
    
    selected_invoice_ids = fields.Many2many(
        comodel_name='account.move',
        relation='account_payment_selected_invoice_rel',
        column1='payment_id',
        column2='move_id',
        string="Invoices to Pay",
        domain="[('move_type', 'in', ['out_invoice', 'out_refund']), "
               "('state', '=', 'posted'), "
               "('payment_state', 'in', ['not_paid', 'partial']), "
               "('partner_id', '=', partner_id)]",
        help="Select unpaid invoices to link to this payment. "
             "The payment will be reconciled with these invoices.",
        copy=False,
    )
    
    selected_invoices_amount = fields.Monetary(
        string="Selected Invoices Total",
        compute='_compute_selected_invoices_amount',
        currency_field='currency_id',
        help="Total amount due from selected invoices"
    )
    
    show_invoice_selector = fields.Boolean(
        string="Show Invoice Selector",
        compute='_compute_show_invoice_selector',
        help="Technical field to control visibility"
    )

    @api.depends('payment_type', 'partner_type', 'state')
    def _compute_show_invoice_selector(self):
        """Show invoice selector for customer inbound payments in draft state."""
        for payment in self:
            payment.show_invoice_selector = (
                payment.payment_type == 'inbound'
                and payment.partner_type == 'customer'
                and payment.state == 'draft'
            )

    @api.depends('selected_invoice_ids', 'selected_invoice_ids.amount_residual')
    def _compute_selected_invoices_amount(self):
        """Compute total amount from selected invoices."""
        for payment in self:
            total = sum(payment.selected_invoice_ids.mapped('amount_residual'))
            payment.selected_invoices_amount = total

    @api.onchange('selected_invoice_ids')
    def _onchange_selected_invoice_ids(self):
        """Update payment amount when invoices are selected."""
        if self.selected_invoice_ids:
            # Set amount to total of selected invoices (can be adjusted by user)
            self.amount = self.selected_invoices_amount
            # Set memo to invoice references
            refs = self.selected_invoice_ids.mapped(lambda m: m.name or m.ref or '')
            self.memo = ', '.join(filter(None, refs))

    @api.onchange('partner_id')
    def _onchange_partner_clear_invoices(self):
        """Clear selected invoices when partner changes."""
        if self.selected_invoice_ids:
            # Check if any selected invoices don't match new partner
            if self.partner_id and any(inv.partner_id != self.partner_id for inv in self.selected_invoice_ids):
                self.selected_invoice_ids = [(5, 0, 0)]  # Clear all

    def action_post(self):
        """Override to link selected invoices and trigger reconciliation."""
        res = super().action_post()
        
        for payment in self:
            if payment.selected_invoice_ids:
                # Link invoices to payment via invoice_ids field
                payment.invoice_ids = [(6, 0, payment.selected_invoice_ids.ids)]
                
                # Attempt auto-reconciliation if amounts allow
                payment._reconcile_with_selected_invoices()
        
        return res

    def _reconcile_with_selected_invoices(self):
        """Reconcile payment with selected invoices."""
        self.ensure_one()
        if not self.selected_invoice_ids:
            return
        
        # Get payment's receivable line
        payment_lines = self.move_id.line_ids.filtered(
            lambda l: l.account_id.account_type == 'asset_receivable'
            and l.partner_id == self.partner_id
        )
        
        if not payment_lines:
            _logger.warning(f"Payment {self.name}: No receivable lines found for reconciliation")
            return
        
        # Get invoice receivable lines
        invoice_lines = self.selected_invoice_ids.line_ids.filtered(
            lambda l: l.account_id.account_type == 'asset_receivable'
            and l.partner_id == self.partner_id
            and not l.reconciled
            and l.amount_residual != 0
        )
        
        if not invoice_lines:
            _logger.warning(f"Payment {self.name}: No unreconciled invoice lines found")
            return
        
        # Combine lines for reconciliation
        lines_to_reconcile = payment_lines | invoice_lines
        
        try:
            lines_to_reconcile.reconcile()
            _logger.info(f"Payment {self.name}: Reconciled with {len(self.selected_invoice_ids)} invoice(s)")
        except Exception as e:
            _logger.warning(f"Payment {self.name}: Auto-reconciliation failed - {str(e)}")
            # Don't raise error - user can manually reconcile
