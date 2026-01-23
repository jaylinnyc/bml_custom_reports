from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    delivery_date = fields.Date(
        string='Delivery Date',
        compute='_compute_delivery_date',
        store=True,
        readonly=False,
        copy=True,
        help='Date when goods/services were delivered. Defaults to bill/invoice date if not specified.'
    )

    vat_deduction_used = fields.Boolean(
        string='VAT Deduction Used',
        default=False,
        copy=False,
        help='Indicates whether this invoice has been used for VAT deduction in monthly closing'
    )

    vat_deduction_date = fields.Date(
        string='VAT Deduction Date',
        copy=False,
        help='Date when this invoice was used for VAT deduction in monthly closing'
    )

    @api.depends('invoice_date')
    def _compute_delivery_date(self):
        """Set delivery_date to invoice_date by default for new records"""
        for move in self:
            if not move.delivery_date and move.invoice_date:
                move.delivery_date = move.invoice_date

    def _get_delivery_date_display(self):
        """Return delivery_date or invoice_date if delivery_date is not set"""
        self.ensure_one()
        return self.delivery_date or self.invoice_date

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-sync accounting date with invoice date on creation"""
        for vals in vals_list:
            if vals.get('move_type') == 'in_invoice' and vals.get('invoice_date'):
                vals['date'] = vals['invoice_date']
            # Set delivery_date to invoice_date if not provided
            if vals.get('invoice_date') and not vals.get('delivery_date'):
                vals['delivery_date'] = vals['invoice_date']
        return super().create(vals_list)

    def write(self, vals):
        """Auto-sync accounting date when invoice date changes"""
        # If invoice_date is being updated on vendor bills, sync the accounting date
        if 'invoice_date' in vals:
            for move in self:
                if move.move_type == 'in_invoice':
                    vals['date'] = vals['invoice_date']
        return super().write(vals)
