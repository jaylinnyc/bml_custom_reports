# -*- coding: utf-8 -*-

from odoo import models, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def web_search_read(self, domain=None, specification=None, offset=0, limit=None, order=None, count_limit=None):
        """
        Override web_search_read to filter journal items in bank reconciliation widget.
        
        When called from bank reconciliation widget (detected by presence of 
        'preferred_aml_value' in context), modify the domain to:
        1. Filter by same journal (extracted from active_id which is the statement line)
        2. Exclude ALL bank statement lines (statement_line_id = False)
        """
        # Check if we're in bank reconciliation context
        if self.env.context.get('preferred_aml_value') is not None and self.env.context.get('active_id'):
            # Get the statement line from active_id
            st_line = self.env['account.bank.statement.line'].browse(self.env.context['active_id'])
            
            if st_line.exists() and st_line.journal_id:
                # Add journal filter - only show items from same journal as the statement
                domain = domain + [('journal_id', '=', st_line.journal_id.id)]
                
                # Exclude ALL statement lines to prevent self-reconciliation
                domain = domain + [('statement_line_id', '=', False)]
        
        return super().web_search_read(domain=domain, specification=specification, offset=offset, limit=limit, order=order, count_limit=count_limit)
