# -*- coding: utf-8 -*-

from odoo import models, api, _


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def action_open_thai_bank_statement_upload(self):
        """Open wizard for uploading Thai bank statement"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Upload Thai Bank Statement'),
            'res_model': 'bml.thai.bank.statement.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_journal_id': self.id,
            }
        }
