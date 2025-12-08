from odoo import models, fields, api


class ReportFooterConfig(models.Model):
    _name = 'bml.report.footer.config'
    _description = 'Report Footer Configuration'
    _order = 'report_type, company_id'

    name = fields.Char(
        string='Configuration Name',
        compute='_compute_name',
        store=True
    )
    
    report_type = fields.Selection([
        ('sales_tax_invoice', 'Sales - Tax Invoice'),
        ('inventory_consumption', 'Inventory - Consumption (ใบเบิก FM-ST-01-04)'),
        ('inventory_repair', 'Inventory - Repair (ใบแจ้งซ่อม/ปรับปรุง เครื่องจักร FM-MN-01-03)'),
        ('purchase_order_rfq', 'Purchase Order - RFQ'),
        ('purchase_order_bill', 'Purchase Order - Bill (ใบสั่งซื้อ FM-PO-01-06)'),
    ], string='Report Type', required=True)
    
    footer_left = fields.Text(
        string='Footer Left',
        help='Text to display on the left side of the footer (e.g., storage/retention notes)'
    )
    
    footer_right = fields.Text(
        string='Footer Right',
        help='Text to display on the right side of the footer (e.g., ISO code, revision, effective date)'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Uncheck to disable this footer configuration'
    )

    @api.depends('report_type', 'company_id')
    def _compute_name(self):
        """Generate a readable name for the configuration"""
        for record in self:
            report_type_label = dict(self._fields['report_type'].selection).get(record.report_type, '')
            company_name = record.company_id.name if record.company_id else ''
            record.name = f"{report_type_label} - {company_name}"

    _sql_constraints = [
        ('unique_report_company', 
         'UNIQUE(report_type, company_id)', 
         'Only one active configuration per report type and company is allowed!')
    ]
