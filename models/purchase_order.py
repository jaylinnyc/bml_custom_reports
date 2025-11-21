from odoo import fields, models

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    x_studio_approval_signature = fields.Binary(
        string="Approval Signature",
        attachment=True,
        help="Digital signature of the approver"
    )