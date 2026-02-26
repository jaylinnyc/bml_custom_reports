# -*- coding: utf-8 -*-

import logging
from datetime import timedelta
from odoo import models, api, fields

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def _get_bank_rec_day_margin(self):
        default_margin = 15
        param_value = self.env['ir.config_parameter'].sudo().get_param(
            'bml_custom_reports.bank_rec_day_margin',
            default=str(default_margin),
        )
        try:
            return max(0, int(param_value))
        except (TypeError, ValueError):
            _logger.warning(
                "Invalid ir.config_parameter bml_custom_reports.bank_rec_day_margin=%r; using default %s days",
                param_value,
                default_margin,
            )
            return default_margin

    @api.model
    def web_search_read(self, domain=None, specification=None, offset=0, limit=None, order=None, count_limit=None):
        """
        Override web_search_read to filter journal items in bank reconciliation widget.
        
        When called from bank reconciliation widget (detected by presence of 
        'preferred_aml_value' in context), modify the domain to:
        1. Filter by same journal (extracted from statement line in domain)
        2. Exclude ALL bank statement lines (statement_line_id = False)
        3. Filter by date range: bank statement date range ± 7 days based on JOURNAL ENTRY date
           (e.g., if statement covers Dec 1-31, show entries from Nov 24 to Jan 7)
        """
        day_margin = self._get_bank_rec_day_margin()

        # Check if we're in bank reconciliation context
        if self.env.context.get('preferred_aml_value') is not None:
            # Try to find statement_line_id from domain
            statement_line_id = None
            for clause in domain:
                if isinstance(clause, (list, tuple)) and len(clause) == 3:
                    if clause[0] == 'statement_line_id' and clause[1] == '!=':
                        statement_line_id = clause[2]
                        break
            
            # Also try active_id from context
            if not statement_line_id and self.env.context.get('active_id'):
                statement_line_id = self.env.context['active_id']
            
            if statement_line_id:
                st_line = self.env['account.bank.statement.line'].browse(statement_line_id)
                
                if st_line.exists() and st_line.journal_id:
                    journal_id = st_line.journal_id.id
                    
                    # Add journal filter - only show items from same journal as the statement
                    domain = domain + [('journal_id', '=', journal_id)]
                    # Exclude ALL statement lines to prevent self-reconciliation
                    domain = domain + [('statement_line_id', '=', False)]
                    
                    # Add date range filter based on BANK STATEMENT date range ± configured days
                    # Filter by JOURNAL ENTRY date (move_id.date) not journal item date
                    statement = st_line.statement_id
                    if statement:
                        # Get min and max dates from all statement lines
                        statement_lines = statement.line_ids
                        if statement_lines:
                            dates = statement_lines.mapped('date')
                            min_date = min(dates)
                            max_date = max(dates)
                            
                            # Expand by configured days on each side
                            date_from = min_date - timedelta(days=day_margin)
                            date_to = max_date + timedelta(days=day_margin)
                            
                            domain = domain + [
                                ('move_id.date', '>=', fields.Date.to_string(date_from)),
                                ('move_id.date', '<=', fields.Date.to_string(date_to)),
                            ]
                    elif st_line.date:
                        # Fallback: if no statement, use statement line date ± configured days
                        date_from = st_line.date - timedelta(days=day_margin)
                        date_to = st_line.date + timedelta(days=day_margin)
                        domain = domain + [
                            ('move_id.date', '>=', fields.Date.to_string(date_from)),
                            ('move_id.date', '<=', fields.Date.to_string(date_to)),
                        ]
        
        return super().web_search_read(domain=domain, specification=specification, offset=offset, limit=limit, order=order, count_limit=count_limit)
