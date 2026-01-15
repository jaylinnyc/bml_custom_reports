# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import logging

_logger = logging.getLogger(__name__)


class ThaiBankStatementUploadWizard(models.TransientModel):
    _name = 'bml.thai.bank.statement.wizard'
    _description = 'Thai Bank Statement Upload Wizard'

    journal_id = fields.Many2one(
        'account.journal',
        string='Bank Journal',
        required=True,
        domain="[('type', '=', 'bank')]",
        help='Select the bank journal for this statement'
    )
    
    statement_file = fields.Binary(
        string='Bank Statement File',
        required=True,
        help='Upload Thai bank statement file (Excel or CSV format)'
    )
    
    filename = fields.Char(string='Filename')
    
    statement_name = fields.Char(
        string='Statement Reference',
        help='Optional reference name for this statement'
    )
    
    balance_start = fields.Monetary(
        string='Starting Balance',
        currency_field='currency_id',
        help='Optional starting balance'
    )
    
    balance_end = fields.Monetary(
        string='Ending Balance',
        currency_field='currency_id',
        help='Optional ending balance'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        related='journal_id.currency_id',
        string='Currency',
        readonly=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        related='journal_id.company_id',
        string='Company',
        readonly=True
    )

    @api.model
    def default_get(self, fields_list):
        """Set default journal from context"""
        res = super().default_get(fields_list)
        
        # Get journal from context
        journal_id = self.env.context.get('default_journal_id')
        if journal_id:
            res['journal_id'] = journal_id
        
        return res

    def action_upload_statement(self):
        """Process uploaded file and create bank statement"""
        self.ensure_one()
        
    def action_upload_statement(self):
        """Process uploaded file and create bank statement"""
        self.ensure_one()
        if not self.filename:
            raise UserError(_('Filename is missing.'))
        
        # Check journal configuration before processing
        if not self.journal_id.default_account_id:
            raise UserError(_(
                'The journal "%s" does not have a Default Account configured.\n\n'
                'Please configure it first:\n'
                '1. Go to: Accounting → Configuration → Journals\n'
                '2. Open the journal "%s"\n'
                '3. Go to "Accounting Information" tab\n'
                '4. Set the "Default Account" field\n'
                '5. Save and try uploading again.'
            ) % (self.journal_id.name, self.journal_id.name))
        
        # Decode file data
        try:
            file_data = base64.b64decode(self.statement_file)
        except Exception as e:
            raise UserError(_('Error decoding file: %s') % str(e))
        
        # Import converter
        from ..utils.thai_bank_converter import ThaiBankStatementConverter
        
        # Convert file
        converter = ThaiBankStatementConverter()
        try:
            transactions = converter.convert_file(file_data, self.filename)
        except UserError as e:
            raise e
        except Exception as e:
            _logger.error(f"Error converting Thai bank statement: {str(e)}", exc_info=True)
            raise UserError(_(
                'Error processing file: %s\n\n'
                'Please ensure the file is a valid Thai bank statement in Excel or CSV format.'
            ) % str(e))
        
        if not transactions:
            raise UserError(_('No valid transactions found in the file.'))
        
        # Generate unique import IDs to prevent duplicates
        for idx, trans in enumerate(transactions):
            date_str = trans['date'].strftime('%Y%m%d')
            amount_str = str(abs(trans['amount'])).replace('.', '')
            trans['unique_import_id'] = f"{self.journal_id.id}-{date_str}-{amount_str}-{idx}"
            # Explicitly set journal_id on each transaction line
            trans['journal_id'] = self.journal_id.id
        
        # Prepare statement values (must be a list for _create_bank_statements)
        statement_vals = {
            'reference': self.statement_name or self.filename,
            'journal_id': self.journal_id.id,
            'balance_start': self.balance_start if self.balance_start else 0.0,
            'balance_end_real': self.balance_end if self.balance_end else 0.0,
            'transactions': transactions,
        }
        
        # Use Odoo's standard statement creation method (expects a list of statement dicts)
        try:
            statement_ids, ignored_qty = self.journal_id._create_bank_statements([statement_vals])
        except Exception as e:
            _logger.error(f"Error creating bank statement: {str(e)}", exc_info=True)
            raise UserError(_('Error creating bank statement: %s') % str(e))
        
        if not statement_ids:
            raise UserError(_('No statement was created. All transactions may have been previously imported.'))
        
        # Get created statement lines
        statement_lines = self.env['account.bank.statement.line'].search([
            ('statement_id', 'in', statement_ids)
        ])
        
        # Run auto-reconciliation
        if statement_lines:
            try:
                if len(statement_lines) <= 80:
                    statement_lines._try_auto_reconcile_statement_lines()
                else:
                    statement_lines._cron_try_auto_reconcile_statement_lines(batch_size=100)
            except Exception as e:
                _logger.warning(f"Auto-reconciliation failed: {str(e)}")
                # Don't fail the whole import if auto-reconciliation fails
        
        # Show success message
        message = _('%d transactions imported successfully.') % len(transactions)
        if ignored_qty:
            message += _('\n%d transactions were already imported and were ignored.') % ignored_qty
        
        # Log statement creation for debugging
        statements = self.env['account.bank.statement'].browse(statement_ids)
        _logger.info(f"Created {len(statement_ids)} statement(s) for journal '{self.journal_id.name}' (ID: {self.journal_id.id}): "
                    f"Statement IDs: {statement_ids}, Names: {statements.mapped('name')}, "
                    f"Journal IDs on statements: {statements.mapped('journal_id.id')}")
        
        # Return action to open bank reconciliation widget (standard Odoo behavior)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': message,
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window',
                    'name': _('Bank Reconciliation'),
                    'res_model': 'account.bank.statement.line',
                    'view_mode': 'kanban,list',
                    'views': [(False, 'kanban'), (False, 'list')],
                    'domain': [('statement_id', 'in', statement_ids)],
                    'context': {
                        'search_default_not_matched': True,
                        'default_journal_id': self.journal_id.id,
                    }
                }
            }
        }
