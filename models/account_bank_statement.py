# -*- coding: utf-8 -*-

import re
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
        Enhanced auto-reconciliation with smarter matching logic.
        
        Matching Strategy (in priority order):
        1. EXACT MATCH: Same journal + same date + exact amount + reference match
        2. DATE MATCH: Same journal + same date + exact amount (any reference)
        3. COMBINED MATCH: Same journal + same date + same partner + items sum to amount
        
        Key improvements:
        - Match by journal_id (same bank account) instead of partner
        - Exclude ALL statement lines from matching (prevent self-reconciliation)
        - Use date from account_move table (st_line inherits from account.move)
        - **STRICT**: Only match on exact same date (no tolerance)
        - **COMBINED**: Must be same vendor AND same date
        - Try to combine multiple journal items if single match not found
        - **NEW**: Reference/memo matching to disambiguate same-amount entries
        - **NEW**: Extract invoice numbers from payment_ref for better matching
        - **NEW**: Score-based selection when multiple candidates exist
        """
        if not self:
            return
            
        st_move_ids = self.mapped('move_id').ids
        self.lock_for_update()

        # Get reconcile models
        domain = []
        if company_id is not None:
            from odoo.fields import Domain
            domain = Domain(self.env['account.reconcile.model']._check_company_domain(company_id))
        reco_models = self.env['account.reconcile.model'].search(domain)

        # Partner mapping from reconcile models (keep standard logic)
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

        # Flush all required data
        self.env['account.account'].flush_model(['account_type', 'active'])
        self.env['account.move'].flush_model(['date', 'amount_total'])
        self.env['account.move.line'].flush_model([
            'ref', 'move_id', 'move_name', 'account_id', 'partner_id', 'company_id',
            'reconciled', 'company_currency_id', 'amount_residual',
            'currency_id', 'amount_residual_currency',
            'discount_date', 'discount_balance', 'discount_amount_currency',
            'statement_line_id', 'balance', 'date',
        ])
        self.flush_recordset([
            'move_id', 'partner_id', 'company_id', 'currency_id',
            'amount', 'foreign_currency_id', 'amount_currency', 'payment_ref', 'journal_id'
        ])
        self.env['account.payment'].flush_model(['move_id', 'journal_id', 'memo'])

        # Get reconciliable accounts (exclude cash/bank suspense accounts)
        account_ids = self.env['account.account'].search([
            ('reconcile', '=', True),
            ('account_type', 'not in', ('asset_cash', 'liability_credit_card'))
        ])
        account_ids -= self.env['account.journal'].search([
            ('type', 'in', ['bank', 'cash', 'credit'])
        ]).suspense_account_id
        account_ids = account_ids.ids
        
        if not account_ids:
            return

        processed_st_line_ids = set()
        remaining_st_line_ids = set(self.ids)

        # =====================================================================
        # STRATEGY 1: EXACT MATCH WITH REFERENCE (same journal + same date + amount + ref)
        # Most reliable: exact date, amount, AND matching reference/invoice number
        # =====================================================================
        query_exact_ref = SQL("""
                SELECT st_line.id AS st_line_id,
                       ARRAY_AGG(aml.id ORDER BY aml.date ASC, aml.id ASC) AS all_aml_ids,
                       SUM(aml.amount_residual) AS total_residual
                  FROM account_bank_statement_line st_line
                  JOIN account_move st_move ON st_line.move_id = st_move.id
                  JOIN account_move_line aml ON (
                       st_line.journal_id = aml.journal_id 
                       AND aml.company_id = st_line.company_id
                       AND st_move.date = aml.date
                       AND ABS(st_line.amount) = ABS(aml.balance)
                  )
                 WHERE aml.move_id NOT IN %s
                   AND aml.reconciled = false
                   AND aml.account_id IN %s
                   AND aml.statement_line_id IS NULL
                   AND ((st_line.amount > 0 AND aml.balance > 0) OR (st_line.amount < 0 AND aml.balance < 0))
                   AND aml.parent_state IN ('draft', 'posted')
                   AND st_line.id IN %s
                   AND (
                       -- Reference matching: payment_ref contains move name or ref
                       st_line.payment_ref ILIKE '%%' || aml.move_name || '%%'
                       OR st_line.payment_ref ILIKE '%%' || COALESCE(aml.ref, '') || '%%'
                       OR COALESCE(aml.ref, '') ILIKE '%%' || st_line.payment_ref || '%%'
                   )
              GROUP BY st_line.id
        """, tuple(st_move_ids), tuple(account_ids), tuple(remaining_st_line_ids))
        
        self.env.cr.execute(query_exact_ref)
        processed_st_line_ids.update(
            self._process_auto_reconcile_matches(self.env.cr.fetchall())
        )
        remaining_st_line_ids -= processed_st_line_ids

        # =====================================================================
        # STRATEGY 2: EXACT DATE MATCH (same journal + same date + exact amount)
        # Very reliable: exact date and amount, but no reference match
        # =====================================================================
        if remaining_st_line_ids:
            query_exact_date = SQL("""
                    SELECT st_line.id AS st_line_id,
                           ARRAY_AGG(aml.id ORDER BY aml.date ASC, aml.id ASC) AS all_aml_ids,
                           SUM(aml.amount_residual) AS total_residual
                      FROM account_bank_statement_line st_line
                      JOIN account_move st_move ON st_line.move_id = st_move.id
                      JOIN account_move_line aml ON (
                           st_line.journal_id = aml.journal_id 
                           AND aml.company_id = st_line.company_id
                           AND st_move.date = aml.date
                           AND ABS(st_line.amount) = ABS(aml.balance)
                      )
                     WHERE aml.move_id NOT IN %s
                       AND aml.reconciled = false
                       AND aml.account_id IN %s
                       AND aml.statement_line_id IS NULL
                       AND ((st_line.amount > 0 AND aml.balance > 0) OR (st_line.amount < 0 AND aml.balance < 0))
                       AND aml.parent_state IN ('draft', 'posted')
                       AND st_line.id IN %s
                  GROUP BY st_line.id
            """, tuple(st_move_ids), tuple(account_ids), tuple(remaining_st_line_ids))
            
            self.env.cr.execute(query_exact_date)
            processed_st_line_ids.update(
                self._process_auto_reconcile_matches(self.env.cr.fetchall())
            )
            remaining_st_line_ids -= processed_st_line_ids

        # =====================================================================
        # STRATEGY 3: COMBINED MATCH (combine items to match total)
        # Same journal + SAME DATE + SAME PARTNER + items sum to statement amount
        # More strict: all combined items must be for same vendor and same date
        # =====================================================================
        if remaining_st_line_ids:
            # For each remaining statement line, try to find combinations
            for st_line_id in list(remaining_st_line_ids):
                st_line = self.browse(st_line_id)
                if st_line.is_reconciled:
                    continue
                    
                st_move = st_line.move_id
                target_amount = st_line.amount
                
                # Find candidate journal items - SAME DATE only
                # Group by partner_id to ensure all combined items are same vendor
                query_candidates = SQL("""
                    SELECT aml.id, aml.balance, aml.amount_residual, aml.date,
                           aml.move_name, aml.ref, aml.partner_id
                      FROM account_move_line aml
                     WHERE aml.journal_id = %s
                       AND aml.company_id = %s
                       AND aml.date = %s
                       AND aml.move_id NOT IN %s
                       AND aml.reconciled = false
                       AND aml.account_id IN %s
                       AND aml.statement_line_id IS NULL
                       AND (((%s > 0 AND aml.balance > 0) OR (%s < 0 AND aml.balance < 0)))
                       AND aml.parent_state IN ('draft', 'posted')
                  ORDER BY aml.partner_id, ABS(ABS(aml.balance) - ABS(%s)) ASC
                     LIMIT 20
                """, st_line.journal_id.id, st_line.company_id.id, st_move.date,
                     tuple(st_move_ids), tuple(account_ids),
                     target_amount, target_amount, target_amount)
                
                self.env.cr.execute(query_candidates)
                candidates = self.env.cr.fetchall()
                
                if not candidates:
                    continue
                
                # Try to find a subset that sums to target_amount
                # Pass payment_ref for reference-based scoring
                # Enforce same partner constraint
                payment_ref = st_line.payment_ref or ''
                matching_ids = self._find_matching_combination_same_partner(
                    candidates, target_amount, st_line.currency_id, payment_ref
                )
                
                if matching_ids:
                    from odoo import SUPERUSER_ID
                    st_line.with_user(SUPERUSER_ID).set_line_bank_statement_line(matching_ids)
                    if st_line.currency_id.is_zero(st_line.amount_residual):
                        processed_st_line_ids.add(st_line_id)
                        remaining_st_line_ids.discard(st_line_id)

        # Apply reconcile models to any remaining lines
        if remaining_st_line_ids:
            remaining_st_lines = self.browse(list(remaining_st_line_ids)).with_prefetch(self._prefetch_ids)
            reco_models._apply_reconcile_models(remaining_st_lines)

    def _process_auto_reconcile_matches(self, matches):
        """
        Process matches from SQL query and reconcile statement lines.
        Returns set of processed statement line IDs.
        """
        from odoo import SUPERUSER_ID
        processed = set()
        
        for st_line_id, all_aml_ids, total_residual in matches:
            st_line = self.browse(st_line_id).with_prefetch(self._prefetch_ids)
            
            if st_line.is_reconciled:
                continue
                
            if total_residual == st_line.amount:
                # Total open amount equals the statement amount - perfect match
                st_line.with_user(SUPERUSER_ID).set_line_bank_statement_line(all_aml_ids)
            elif all_aml_ids:
                # Try partial matching
                amls = self.env['account.move.line'].browse(all_aml_ids)
                candidate_amls = self._invoice_matching_post_process(st_line, amls)
                if candidate_amls:
                    st_line.with_user(SUPERUSER_ID).set_line_bank_statement_line(candidate_amls.ids)

            if st_line.currency_id.is_zero(st_line.amount_residual):
                processed.add(st_line_id)
                
        return processed

    def _find_matching_combination(self, candidates, target_amount, currency, payment_ref=''):
        """
        Find a combination of candidate journal items that sum to target_amount.
        Uses a greedy algorithm with backtracking for efficiency.
        
        Args:
            candidates: List of tuples (id, balance, amount_residual, date, move_name, ref)
            target_amount: The target amount to match
            currency: Currency record for rounding comparison
            payment_ref: Statement line payment reference for matching
            
        Returns:
            List of aml IDs that sum to target_amount, or empty list if no match found
        """
        if not candidates:
            return []
        
        # Calculate reference match score for each candidate
        def calc_ref_score(move_name, ref):
            """Higher score = better reference match"""
            if not payment_ref:
                return 0
            score = 0
            payment_ref_lower = payment_ref.lower()
            if move_name and move_name.lower() in payment_ref_lower:
                score += 10
            if ref and ref.lower() in payment_ref_lower:
                score += 10
            # Check for common invoice number patterns in payment_ref
            invoice_patterns = re.findall(r'\b(INV[/-]?\d+|SI[/-]?\d+|\d{4,})\b', payment_ref, re.IGNORECASE)
            for pattern in invoice_patterns:
                if move_name and pattern.lower() in move_name.lower():
                    score += 5
                if ref and pattern.lower() in ref.lower():
                    score += 5
            return score
            
        # Convert to list of (id, residual, ref_score) for processing
        # candidates format: (id, balance, amount_residual, date, move_name, ref)
        items = []
        for c in candidates:
            item_id = c[0]
            residual = c[2]
            move_name = c[4] if len(c) > 4 else ''
            ref = c[5] if len(c) > 5 else ''
            ref_score = calc_ref_score(move_name, ref)
            items.append((item_id, residual, ref_score))
        
        # Sort by reference score (highest first), then by amount proximity
        items_sorted = sorted(items, key=lambda x: (-x[2], abs(abs(x[1]) - abs(target_amount))))
        
        # First check if any single item matches (prefer ones with ref match)
        single_matches = [(item_id, residual, score) for item_id, residual, score in items_sorted 
                          if currency.is_zero(residual - target_amount)]
        if single_matches:
            # Return the one with highest ref score
            return [single_matches[0][0]]
        
        # Try combinations of 2 (prefer combinations with ref matches)
        combos_2 = []
        for i, (id1, res1, score1) in enumerate(items):
            for id2, res2, score2 in items[i+1:]:
                if currency.is_zero(res1 + res2 - target_amount):
                    combos_2.append(([id1, id2], score1 + score2))
        if combos_2:
            # Return combo with highest total score
            combos_2.sort(key=lambda x: -x[1])
            return combos_2[0][0]
        
        # Try combinations of 3
        if len(items) >= 3:
            combos_3 = []
            for i, (id1, res1, score1) in enumerate(items):
                for j, (id2, res2, score2) in enumerate(items[i+1:], i+1):
                    for id3, res3, score3 in items[j+1:]:
                        if currency.is_zero(res1 + res2 + res3 - target_amount):
                            combos_3.append(([id1, id2, id3], score1 + score2 + score3))
            if combos_3:
                combos_3.sort(key=lambda x: -x[1])
                return combos_3[0][0]
        
        # For larger combinations, use greedy approach prioritizing ref matches
        if len(items) >= 4:
            # Sort by ref_score desc, then by largest amount
            sorted_items = sorted(items, key=lambda x: (-x[2], -abs(x[1])))
            selected = []
            remaining = target_amount
            
            for item_id, residual, _ in sorted_items:
                if currency.is_zero(remaining):
                    break
                if (remaining > 0 and residual > 0 and residual <= remaining + currency.rounding) or \
                   (remaining < 0 and residual < 0 and residual >= remaining - currency.rounding):
                    selected.append(item_id)
                    remaining -= residual
                    
            if currency.is_zero(remaining):
                return selected
        
        return []

    def _find_matching_combination_same_partner(self, candidates, target_amount, currency, payment_ref=''):
        """
        Find a combination of candidate journal items that sum to target_amount.
        All items in the combination MUST have the same partner_id.
        
        Args:
            candidates: List of tuples (id, balance, amount_residual, date, move_name, ref, partner_id)
            target_amount: The target amount to match
            currency: Currency record for rounding comparison
            payment_ref: Statement line payment reference for matching
            
        Returns:
            List of aml IDs that sum to target_amount (all same partner), or empty list if no match
        """
        if not candidates:
            return []
        
        # Group candidates by partner_id
        from collections import defaultdict
        by_partner = defaultdict(list)
        for c in candidates:
            partner_id = c[6] if len(c) > 6 else None
            by_partner[partner_id].append(c)
        
        # Calculate reference match score
        def calc_ref_score(move_name, ref):
            if not payment_ref:
                return 0
            score = 0
            payment_ref_lower = payment_ref.lower()
            if move_name and move_name.lower() in payment_ref_lower:
                score += 10
            if ref and ref.lower() in payment_ref_lower:
                score += 10
            invoice_patterns = re.findall(r'\b(INV[/-]?\d+|SI[/-]?\d+|\d{4,})\b', payment_ref, re.IGNORECASE)
            for pattern in invoice_patterns:
                if move_name and pattern.lower() in move_name.lower():
                    score += 5
                if ref and pattern.lower() in ref.lower():
                    score += 5
            return score
        
        best_match = None
        best_score = -1
        
        # Try each partner group separately
        for partner_id, partner_candidates in by_partner.items():
            # Convert to items list: (id, residual, ref_score)
            items = []
            for c in partner_candidates:
                item_id = c[0]
                residual = c[2]
                move_name = c[4] if len(c) > 4 else ''
                ref = c[5] if len(c) > 5 else ''
                ref_score = calc_ref_score(move_name, ref)
                items.append((item_id, residual, ref_score))
            
            # Check single item match
            for item_id, residual, score in items:
                if currency.is_zero(residual - target_amount):
                    if score > best_score:
                        best_match = [item_id]
                        best_score = score
            
            # Try combinations of 2
            for i, (id1, res1, score1) in enumerate(items):
                for id2, res2, score2 in items[i+1:]:
                    if currency.is_zero(res1 + res2 - target_amount):
                        total_score = score1 + score2
                        if total_score > best_score:
                            best_match = [id1, id2]
                            best_score = total_score
            
            # Try combinations of 3
            if len(items) >= 3:
                for i, (id1, res1, score1) in enumerate(items):
                    for j, (id2, res2, score2) in enumerate(items[i+1:], i+1):
                        for id3, res3, score3 in items[j+1:]:
                            if currency.is_zero(res1 + res2 + res3 - target_amount):
                                total_score = score1 + score2 + score3
                                if total_score > best_score:
                                    best_match = [id1, id2, id3]
                                    best_score = total_score
            
            # Try combinations of 4
            if len(items) >= 4:
                for i, (id1, res1, score1) in enumerate(items):
                    for j, (id2, res2, score2) in enumerate(items[i+1:], i+1):
                        for k, (id3, res3, score3) in enumerate(items[j+1:], j+1):
                            for id4, res4, score4 in items[k+1:]:
                                if currency.is_zero(res1 + res2 + res3 + res4 - target_amount):
                                    total_score = score1 + score2 + score3 + score4
                                    if total_score > best_score:
                                        best_match = [id1, id2, id3, id4]
                                        best_score = total_score
        
        return best_match or []
