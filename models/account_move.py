from odoo import models, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-sync accounting date with invoice date on creation"""
        for vals in vals_list:
            if vals.get('move_type') == 'in_invoice' and vals.get('invoice_date'):
                vals['date'] = vals['invoice_date']
        return super().create(vals_list)

    def write(self, vals):
        """Auto-sync accounting date when invoice date changes"""
        # If invoice_date is being updated on vendor bills, sync the accounting date
        if 'invoice_date' in vals:
            for move in self:
                if move.move_type == 'in_invoice':
                    vals['date'] = vals['invoice_date']
        return super().write(vals)
