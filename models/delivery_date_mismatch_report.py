from odoo import models, fields, api


class DeliveryDateMismatchReport(models.Model):
    _name = 'delivery.date.mismatch.report'
    _description = 'Delivery Date vs Bill Date Mismatch Report'
    _auto = False
    _order = 'invoice_date desc, name'

    name = fields.Char(string='Number', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    move_type = fields.Selection([
        ('out_invoice', 'Customer Invoice'),
        ('in_invoice', 'Vendor Bill'),
        ('out_refund', 'Customer Credit Note'),
        ('in_refund', 'Vendor Credit Note'),
    ], string='Type', readonly=True)
    invoice_date = fields.Date(string='Invoice/Bill Date', readonly=True)
    delivery_date = fields.Date(string='Delivery Date', readonly=True)
    date_difference = fields.Integer(string='Days Difference', readonly=True)
    amount_total = fields.Monetary(string='Total', readonly=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)

    def init(self):
        """Create the SQL view for the report"""
        self._cr.execute("""
            CREATE OR REPLACE VIEW delivery_date_mismatch_report AS (
                SELECT
                    am.id,
                    am.name,
                    am.partner_id,
                    am.move_type,
                    am.invoice_date,
                    COALESCE(am.delivery_date, am.invoice_date) as delivery_date,
                    ABS(COALESCE(am.delivery_date, am.invoice_date) - am.invoice_date) as date_difference,
                    am.amount_total,
                    am.currency_id,
                    am.state,
                    am.company_id
                FROM
                    account_move am
                WHERE
                    am.move_type IN ('out_invoice', 'in_invoice', 'out_refund', 'in_refund')
                    AND am.state = 'posted'
                    AND COALESCE(am.delivery_date, am.invoice_date) != am.invoice_date
            )
        """)
