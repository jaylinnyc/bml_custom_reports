# -*- coding: utf-8 -*-

import logging
from odoo import models, api

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def web_search_read(self, domain=None, specification=None, offset=0, limit=None, order=None, count_limit=None):
        """
        Override web_search_read to filter journal items in bank reconciliation widget.
        
        When called from bank reconciliation widget (detected by presence of 
        'preferred_aml_value' in context), modify the domain to:
        1. Filter by same journal (extracted from statement line in domain)
        2. Exclude ALL bank statement lines (statement_line_id = False)
        """
        _logger.info("=" * 80)
        _logger.info("BML CUSTOM: web_search_read called on account.move.line")
        _logger.info(f"Context keys: {list(self.env.context.keys())}")
        _logger.info(f"Context values: {dict(self.env.context)}")
        _logger.info(f"Domain: {domain}")
        _logger.info(f"preferred_aml_value: {self.env.context.get('preferred_aml_value')}")
        _logger.info(f"active_id: {self.env.context.get('active_id')}")
        
        # Check if we're in bank reconciliation context
        if self.env.context.get('preferred_aml_value') is not None:
            _logger.info(">>> BANK REC WIDGET DETECTED (preferred_aml_value exists)")
            
            # Try to find statement_line_id from domain
            statement_line_id = None
            for clause in domain:
                if isinstance(clause, (list, tuple)) and len(clause) == 3:
                    if clause[0] == 'statement_line_id' and clause[1] == '!=':
                        statement_line_id = clause[2]
                        _logger.info(f">>> Found statement_line_id in domain: {statement_line_id}")
                        break
            
            # Also try active_id from context
            if not statement_line_id and self.env.context.get('active_id'):
                statement_line_id = self.env.context['active_id']
                _logger.info(f">>> Using active_id from context: {statement_line_id}")
            
            if statement_line_id:
                st_line = self.env['account.bank.statement.line'].browse(statement_line_id)
                
                if st_line.exists() and st_line.journal_id:
                    journal_id = st_line.journal_id.id
                    journal_name = st_line.journal_id.name
                    _logger.info(f">>> Statement line found! Journal: {journal_name} (ID: {journal_id})")
                    
                    original_len = len(domain)
                    # Add journal filter - only show items from same journal as the statement
                    domain = domain + [('journal_id', '=', journal_id)]
                    # Exclude ALL statement lines to prevent self-reconciliation
                    domain = domain + [('statement_line_id', '=', False)]
                    
                    _logger.info(f">>> Added {len(domain) - original_len} filter clauses")
                    _logger.info(f">>> Modified domain: {domain}")
                else:
                    _logger.warning(f">>> Statement line {statement_line_id} not found or has no journal!")
            else:
                _logger.warning(">>> Could not find statement_line_id (not in domain or active_id)")
        else:
            _logger.info(">>> Not bank rec widget (no preferred_aml_value)")
        
        _logger.info("=" * 80)
        return super().web_search_read(domain=domain, specification=specification, offset=offset, limit=limit, order=order, count_limit=count_limit)
