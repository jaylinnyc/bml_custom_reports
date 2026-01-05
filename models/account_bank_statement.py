# -*- coding: utf-8 -*-

from odoo import models, api
from odoo.tools import SQL


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    def action_manual_auto_reconcile(self):
        """
        Manual trigger for auto-reconciliation.
        Runs the enhanced auto-reconcile logic on selected statement lines.
        """
        # Filter only unreconciled lines
        unreconciled_lines = self.filtered(lambda l: not l.is_reconciled)
        
        if not unreconciled_lines:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No Lines to Reconcile',
                    'message': 'All selected lines are already reconciled.',
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        # Run auto-reconciliation on these lines
        unreconciled_lines._try_auto_reconcile_statement_lines()
        
        # Count results
        reconciled_count = len(self.filtered(lambda l: l.is_reconciled))
        remaining_count = len(self) - reconciled_count
        
        message = f"Auto-reconciled {reconciled_count} of {len(self)} line(s)."
        if remaining_count:
            message += f" {remaining_count} line(s) could not be auto-matched."
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Auto-Reconciliation Complete',
                'message': message,
                'type': 'success' if reconciled_count > 0 else 'warning',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def _try_auto_reconcile_statement_lines(self, company_id=None):
        """
        Override to change matching logic:
        - Match by date + amount + journal_id (absolute match) instead of partner_id
        - Exclude all bank statement lines from matching results
        
        This ensures bank transactions auto-reconcile with journal items that have:
        1. Same journal account (statement's journal)
        2. Same date (transaction date)
        3. Same amount (absolute value match)
        
        This prevents self-reconciliation with statement lines and provides
        more reliable matching than partner-based logic.
        """
        # Call parent to handle most of the logic
        # We only need to override the final SQL query that matches by partner
        
        st_move_ids = self.mapped('move_id').ids
        self.lock_for_update()

        # Get reconcile models (from parent)
        domain = []
        if company_id is not None:
            from odoo.fields import Domain
            domain = Domain(self.env['account.reconcile.model']._check_company_domain(company_id))
        reco_models = self.env['account.reconcile.model'].search(domain)

        # Partner mapping (from parent - unchanged)
        self.env['account.reconcile.model'].flush_model()
        self.flush_recordset(['journal_id', 'transaction_details', 'payment_ref', 'company_id'])
        self.env.cr.execute(SQL("""
            WITH matching_journal_ids AS (
                    SELECT account_reconcile_model_id,
                           ARRAY_AGG(account_journal_id) AS ids
                      FROM account_journal_account_reconcile_model_rel
                  GROUP BY account_reconcile_model_id
                 )

          SELECT st_line.id AS st_line_id, reco_model.mapped_partner_id
            FROM account_bank_statement_line st_line
       LEFT JOIN LATERAL (
                   SELECT reco_model.id,
                          reco_model.mapped_partner_id
                     FROM account_reconcile_model reco_model
                LEFT JOIN matching_journal_ids ON reco_model.id = matching_journal_ids.account_reconcile_model_id
                    WHERE (matching_journal_ids.ids IS NULL OR st_line.journal_id = ANY(matching_journal_ids.ids))
                      AND reco_model.mapped_partner_id IS NOT NULL
                      AND (
                              (
                                  reco_model.match_label = 'contains'
                                  AND (
                                      st_line.payment_ref IS NOT NULL AND st_line.payment_ref ILIKE '%%' || reco_model.match_label_param || '%%'
                                      OR st_line.transaction_details IS NOT NULL AND st_line.transaction_details::TEXT ILIKE '%%' || reco_model.match_label_param || '%%'
                                   )
                              ) OR (
                                  reco_model.match_label = 'not_contains'
                                  AND NOT (
                                      st_line.payment_ref IS NOT NULL AND st_line.payment_ref ILIKE '%%' || reco_model.match_label_param || '%%'
                                      OR st_line.transaction_details IS NOT NULL AND st_line.transaction_details::TEXT ILIKE '%%' || reco_model.match_label_param || '%%'
                                  )
                              ) OR (
                                  reco_model.match_label = 'match_regex'
                                  AND (
                                      st_line.payment_ref IS NOT NULL AND st_line.payment_ref ~* reco_model.match_label_param
                                      OR st_line.transaction_details IS NOT NULL AND st_line.transaction_details::TEXT ~* reco_model.match_label_param
                                  )
                              )
                          )
                      AND reco_model.id = ANY(%s)
                      AND reco_model.company_id = st_line.company_id
                 ORDER BY reco_model.sequence ASC, reco_model.id ASC
                    LIMIT 1
                 ) AS reco_model ON TRUE
           WHERE st_line.id IN %s
             AND st_line.partner_id IS NULL
             AND reco_model.mapped_partner_id IS NOT NULL
            """, reco_models.ids, tuple(self.ids)))

        for st_line_id, mapped_partner_id in self.env.cr.fetchall():
            st_line = self.browse(st_line_id).with_prefetch(self._prefetch_ids)
            st_line.partner_id = mapped_partner_id

        # Global flushing (from parent - unchanged)
        self.env['account.account'].flush_model(['account_type', 'active'])
        self.env['account.move'].flush_model(['date', 'amount_total'])
        self.env['account.move.line'].flush_model([
            'ref', 'move_id', 'move_name', 'account_id', 'partner_id', 'company_id',
            'reconciled', 'company_currency_id', 'amount_residual',
            'currency_id', 'amount_residual_currency',
            'discount_date', 'discount_balance', 'discount_amount_currency',
            'statement_line_id',  # Added for exclusion check
        ])
        self.flush_recordset([
            'move_id', 'partner_id', 'company_id', 'currency_id',
            'amount', 'foreign_currency_id', 'amount_currency', 'payment_ref', 'journal_id'
        ])
        self.env['account.payment'].flush_model(['move_id', 'journal_id', 'memo'])

        # Get reconciliable accounts (from parent - unchanged)
        account_ids = self.env['account.account'].search([
            ('reconcile', '=', True),
            ('account_type', 'not in', ('asset_cash', 'liability_credit_card'))
        ])
        account_ids -= self.env['account.journal'].search([
            ('type', 'in', ['bank', 'cash', 'credit'])
        ]).suspense_account_id
        account_ids = account_ids.ids

        # Let parent handle: end_to_end_uuid matching, outstanding payments, payment_ref matching
        # We skip to the final query that needs modification
        
        processed_st_line_ids = set()
        remaining_st_line_ids = set(self.ids)

        # MODIFIED QUERY: Match by journal_id + date + amount (absolute match)
        # Instead of partner-based matching, use exact date + amount + journal
        # AND exclude all statement lines to prevent self-reconciliation
        query = SQL("""
                SELECT st_line.id AS st_line_id,
                       ARRAY_AGG(aml.id ORDER BY aml.id ASC) AS all_aml_ids,
                       SUM(aml.amount_residual) AS total_residual
                  FROM account_bank_statement_line st_line
                  JOIN account_move_line aml ON (
                       st_line.journal_id = aml.journal_id 
                       AND aml.company_id = st_line.company_id
                       AND st_line.date = aml.date
                       AND ABS(st_line.amount) = ABS(aml.balance)
                  )
                  JOIN account_move move ON aml.move_id = move.id
                 WHERE aml.move_id NOT IN %s
                   AND aml.reconciled = false
                   AND aml.account_id IN %s
                   AND aml.statement_line_id IS NULL
                   AND ((st_line.amount > 0 AND aml.balance > 0) OR (st_line.amount < 0 AND aml.balance < 0))
                   AND (aml.parent_state IN ('draft', 'posted'))
                   AND st_line.id IN %s
              GROUP BY st_line.id
        """, tuple(st_move_ids), tuple(account_ids), tuple(remaining_st_line_ids))
        
        self.env.cr.execute(query)

        # Process matches (from parent logic)
        from odoo import SUPERUSER_ID
        for st_line_id, all_aml_ids, total_residual in self.env.cr.fetchall():
            st_line = self.browse(st_line_id).with_prefetch(self._prefetch_ids)
            if total_residual == st_line.amount:
                # Total open amount equals the paid amount
                st_line.with_user(SUPERUSER_ID).set_line_bank_statement_line(all_aml_ids)
            elif all_aml_ids:
                amls = self.env['account.move.line'].browse(all_aml_ids)
                candidate_amls = self._invoice_matching_post_process(st_line, amls)
                if candidate_amls:
                    st_line.with_user(SUPERUSER_ID).set_line_bank_statement_line(candidate_amls.ids)

            if st_line.currency_id.is_zero(st_line.amount_residual):
                processed_st_line_ids.add(st_line.id)

        remaining_st_line_ids -= processed_st_line_ids

        # Apply reconcile models to remaining lines
        if remaining_st_line_ids:
            remaining_st_lines = self.browse(list(remaining_st_line_ids)).with_prefetch(self._prefetch_ids)
            reco_models._apply_reconcile_models(remaining_st_lines)

        # Update cron check timestamp
        from odoo import fields
        self.write({'cron_last_check': fields.Datetime.now()})
