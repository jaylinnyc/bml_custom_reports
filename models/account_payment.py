# -*- coding: utf-8 -*-
"""
Account Payment Extension

Extends the account.payment model with:
1. Invoice selector - select unpaid invoices when creating direct payments
2. Payment adjustment - handle bank charges and fees
3. Link invoices to existing confirmed payments (for advance payments)
"""

from odoo import models, fields, api, _, Command
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    """
    Extend account.payment for invoice selection and payment adjustment.
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
        domain="[('move_type', 'in', ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']), "
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
    
    can_link_invoices = fields.Boolean(
        string="Can Link Invoices",
        compute='_compute_can_link_invoices',
        help="Whether this payment can be linked to invoices (has unreconciled balance)"
    )
    
    unreconciled_amount = fields.Monetary(
        string="Unreconciled Amount",
        compute='_compute_unreconciled_amount',
        currency_field='currency_id',
        help="Amount not yet reconciled with invoices"
    )

    # -------------------------------------------------------------------------
    # Payment Adjustment Fields
    # -------------------------------------------------------------------------
    
    apply_charge_deduction = fields.Boolean(
        string="Apply Adjustment",
        default=False,
        help="Enable to add adjustment for bank charges or fees"
    )
    
    charge_amount = fields.Monetary(
        string="Adjustment Amount",
        currency_field='currency_id',
        default=0.0,
        help="Adjustment amount (e.g., bank transfer fee)"
    )
    
    charge_account_id = fields.Many2one(
        comodel_name='account.account',
        string="Adjustment Account",
        domain="[('account_type', 'in', ['expense', 'expense_direct_cost'])]",
        check_company=True,
        help="Account for the adjustment (e.g., Bank Charges)"
    )
    
    charge_label = fields.Char(
        string="Adjustment Description",
        default="Bank Charges",
        help="Description for the adjustment journal entry line"
    )
    
    bank_amount = fields.Monetary(
        string="Bank Amount",
        compute='_compute_bank_amount',
        currency_field='currency_id',
        help="Actual bank amount: for inbound payments (amount - adjustment), for outbound payments (amount + adjustment)"
    )

    @api.depends('payment_type', 'partner_type', 'state', 'is_reconciled')
    def _compute_show_invoice_selector(self):
        """Show invoice selector for customer inbound payments and vendor outbound payments."""
        for payment in self:
            # Show for draft payments OR confirmed payments that can still be linked
            # Note: Odoo uses 'supplier' for vendors in partner_type field
            payment.show_invoice_selector = (
                ((payment.payment_type == 'inbound' and payment.partner_type == 'customer') or
                 (payment.payment_type == 'outbound' and payment.partner_type == 'supplier'))
                and payment.state in ('draft', 'in_process')
            )

    @api.depends('payment_type', 'partner_type', 'state', 'move_id.line_ids.amount_residual')
    def _compute_can_link_invoices(self):
        """Check if payment has unreconciled balance that can be linked to invoices."""
        for payment in self:
            can_link = False
            # Note: Odoo uses 'supplier' for vendors in partner_type field
            if (((payment.payment_type == 'inbound' and payment.partner_type == 'customer') or
                 (payment.payment_type == 'outbound' and payment.partner_type == 'supplier'))
                and payment.state == 'in_process'
                and payment.move_id):
                # Check if there's unreconciled balance
                account_type = 'asset_receivable' if payment.partner_type == 'customer' else 'liability_payable'
                target_lines = payment.move_id.line_ids.filtered(
                    lambda l: l.account_id.account_type == account_type
                    and not l.reconciled
                )
                can_link = bool(target_lines and any(l.amount_residual != 0 for l in target_lines))
            payment.can_link_invoices = can_link

    @api.depends('move_id.line_ids.amount_residual', 'partner_type')
    def _compute_unreconciled_amount(self):
        """Compute unreconciled amount from payment's receivable/payable lines."""
        for payment in self:
            unreconciled = 0.0
            if payment.move_id:
                account_type = 'asset_receivable' if payment.partner_type == 'customer' else 'liability_payable'
                target_lines = payment.move_id.line_ids.filtered(
                    lambda l: l.account_id.account_type == account_type
                )
                # For inbound/customer: receivable line has negative balance (credit)
                # For outbound/vendor: payable line has positive balance (debit)
                unreconciled = abs(sum(target_lines.mapped('amount_residual')))
            payment.unreconciled_amount = unreconciled

    @api.depends('selected_invoice_ids', 'selected_invoice_ids.amount_residual')
    def _compute_selected_invoices_amount(self):
        """Compute total amount from selected invoices."""
        for payment in self:
            total = sum(payment.selected_invoice_ids.mapped('amount_residual'))
            payment.selected_invoices_amount = total

    @api.depends('amount', 'apply_charge_deduction', 'charge_amount', 'payment_type')
    def _compute_bank_amount(self):
        """Compute bank amount based on payment type.
        
        Inbound (customer payment): bank_amount = amount - adjustment
        - Customer pays 1000, bank charges 100, we receive 900
        
        Outbound (vendor payment): bank_amount = amount (no change)
        - Vendor payments don't use adjustment in journal entry
        - Bank charges for vendor payments are recorded separately
        """
        for payment in self:
            if (payment.apply_charge_deduction and payment.charge_amount > 0 
                and payment.payment_type == 'inbound'):
                # Only adjust bank amount for inbound (customer) payments
                payment.bank_amount = payment.amount - payment.charge_amount
            else:
                payment.bank_amount = payment.amount

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

    def _prepare_move_line_default_vals(self, write_off_line_vals=None, force_balance=None):
        """Override to add adjustment line if applicable.
        
        Adjustment Scenario (inbound payment):
        - Customer pays 1000 for invoice
        - Bank deducts 100 as transfer fee
        - We receive 900 net
        
        Journal Entry should be:
        Debit:  Bank (Outstanding)      900   (net received)
        Debit:  Bank Charges (Expense)  100   (the fee)
        Credit: Accounts Receivable    1000   (customer's payment)
        
        To achieve this, we need:
        - Liquidity (Bank) line: Odoo creates this from self.amount, but we need to reduce it
        - Write-off line: Creates the expense debit
        - Counterpart (Receivable): Should be full amount (1000)
        
        Using Odoo's write-off mechanism with NEGATIVE amount_currency:
        - This reduces the counterpart credit, which is NOT what we want
        
        The solution: Use force_balance to reduce bank to 900, and write-off with
        POSITIVE amount_currency to ADD to counterpart credit (making it 1000).
        """
        # Handle adjustment - ONLY for inbound (customer) payments
        # For vendor payments, bank charges are recorded separately, not as part of the payment
        if (self.apply_charge_deduction and self.charge_amount > 0 
            and self.charge_account_id and self.payment_type == 'inbound'):
            # Convert amounts to company currency
            adjustment_balance = self.currency_id._convert(
                self.charge_amount,
                self.company_id.currency_id,
                self.company_id,
                self.date,
            )
            bank_balance = self.currency_id._convert(
                self.bank_amount,  # 900 = amount - adjustment
                self.company_id.currency_id,
                self.company_id,
                self.date,
            )
            
            # INBOUND (Customer Payment) Adjustment:
            # - Payment Amount = 1000 (what customer paid / applied to invoice)
            # - Adjustment Amount = 100 (bank fee - our expense)
            # - Bank Amount = 900 (net received in bank)
            # 
            # Desired Journal Entry:
            # Debit:  Bank (Outstanding)      900   (net received)
            # Debit:  Bank Charges (Expense)  100   (our expense)
            # Credit: Accounts Receivable    1000   (full customer payment)
            #
            # Odoo's formula: counterpart_balance = -liquidity_balance - sum(write_off_balances)
            # With force_balance = 900:
            # - Liquidity balance = +900 (debit bank)
            # - Write-off balance = +100 (debit expense)  
            # - Counterpart = -900 - 100 = -1000 (credit receivable 1000) ✓
            
            force_balance = bank_balance  # +900 (debit bank)
            
            # Adjustment line: positive balance (debit expense)
            adjustment_line = {
                'name': self.charge_label or 'Bank Charges',
                'account_id': self.charge_account_id.id,
                'partner_id': self.partner_id.id if self.partner_id else False,
                'currency_id': self.currency_id.id,
                'amount_currency': self.charge_amount,
                'balance': adjustment_balance,
            }
            if write_off_line_vals is None:
                write_off_line_vals = []
            write_off_line_vals = list(write_off_line_vals) + [adjustment_line]
        
        return super()._prepare_move_line_default_vals(
            write_off_line_vals=write_off_line_vals, 
            force_balance=force_balance
        )

    @api.model
    def _get_trigger_fields_to_synchronize(self):
        """Add adjustment fields to trigger synchronization with journal entry.
        
        This ensures that when a payment is reset to draft, edited, and re-confirmed,
        the adjustment changes are properly reflected in the journal entry.
        """
        fields = super()._get_trigger_fields_to_synchronize()
        return fields + ('apply_charge_deduction', 'charge_amount', 'charge_account_id', 'charge_label')

    def _synchronize_to_moves(self, changed_fields):
        """Override to handle adjustment fields properly on sync.
        
        When adjustment fields change, we need to:
        1. NOT pass old adjustment write-off values (to avoid duplicates)
        2. Let _prepare_move_line_default_vals create fresh adjustment line
        """
        # Check if any adjustment field changed
        adjustment_fields = {'apply_charge_deduction', 'charge_amount', 'charge_account_id', 'charge_label'}
        adjustment_changed = bool(adjustment_fields & set(changed_fields))
        
        if not adjustment_changed:
            # No adjustment changes - use standard sync
            return super()._synchronize_to_moves(changed_fields)
        
        # Adjustment fields changed - need custom handling
        if not any(field_name in changed_fields for field_name in self._get_trigger_fields_to_synchronize()):
            return
        
        for pay in self:
            if pay.move_id.state == 'posted':
                continue
            
            liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()
            
            # Don't pass old write-off values - let _prepare_move_line_default_vals
            # create fresh adjustment line based on current payment values
            # This prevents duplicate adjustment lines
            write_off_line_vals = []
            
            # Only preserve non-adjustment write-off lines (if any exist)
            if writeoff_lines and pay.charge_account_id:
                non_adjustment_writeoffs = writeoff_lines.filtered(
                    lambda l: l.account_id.id != pay.charge_account_id.id
                )
                for line in non_adjustment_writeoffs:
                    write_off_line_vals.append({
                        'name': line.name,
                        'account_id': line.account_id.id,
                        'partner_id': line.partner_id.id,
                        'currency_id': line.currency_id.id,
                        'amount_currency': line.amount_currency,
                        'balance': line.balance,
                    })
            
            line_vals_list = pay._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals)
            
            line_ids_commands = [
                Command.update(liquidity_lines.id, line_vals_list[0]) if liquidity_lines else Command.create(line_vals_list[0]),
                Command.update(counterpart_lines.id, line_vals_list[1]) if counterpart_lines else Command.create(line_vals_list[1])
            ]
            # Delete all existing writeoff lines
            for line in writeoff_lines:
                line_ids_commands.append((2, line.id))
            # Create new writeoff lines (including adjustment line if applicable)
            for extra_line_vals in line_vals_list[2:]:
                line_ids_commands.append((0, 0, extra_line_vals))
            
            to_write = {
                'date': pay.date,
                'partner_id': pay.partner_id.id,
                'currency_id': pay.currency_id.id,
                'partner_bank_id': pay.partner_bank_id.id,
                'line_ids': line_ids_commands,
            }
            if 'journal_id' in changed_fields:
                to_write.update({
                    'name': '/',
                    'journal_id': pay.journal_id.id
                })
            pay.move_id.with_context(skip_invoice_sync=True).write(to_write)

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
        
        # Get payment's receivable/payable line
        account_type = 'asset_receivable' if self.partner_type == 'customer' else 'liability_payable'
        payment_lines = self.move_id.line_ids.filtered(
            lambda l: l.account_id.account_type == account_type
            and l.partner_id == self.partner_id
        )
        
        if not payment_lines:
            _logger.warning(f"Payment {self.name}: No {account_type} lines found for reconciliation")
            return
        
        # Get invoice receivable/payable lines
        invoice_lines = self.selected_invoice_ids.line_ids.filtered(
            lambda l: l.account_id.account_type == account_type
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

    def action_link_invoices(self):
        """
        Action button to link and reconcile selected invoices with this payment.
        Used for linking invoices to advance payments after confirmation.
        """
        self.ensure_one()
        
        if not self.selected_invoice_ids:
            raise UserError(_("Please select at least one invoice to link."))
        
        if self.state != 'in_process':
            raise UserError(_("Can only link invoices to payments in 'In Process' state."))
        
        if not self.can_link_invoices:
            raise UserError(_("This payment has no unreconciled balance to link with invoices."))
        
        # Link invoices to payment
        existing_invoice_ids = set(self.invoice_ids.ids)
        new_invoice_ids = set(self.selected_invoice_ids.ids)
        all_invoice_ids = existing_invoice_ids | new_invoice_ids
        self.invoice_ids = [(6, 0, list(all_invoice_ids))]
        
        # Perform reconciliation
        self._reconcile_with_selected_invoices()
        
        # Clear selection after linking
        self.selected_invoice_ids = [(5, 0, 0)]
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Invoices Linked"),
                'message': _("Selected invoices have been linked and reconciled with this payment."),
                'type': 'success',
                'sticky': False,
            }
        }
