from odoo import fields, models, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    # --- Approver Fields (Manager) ---
    x_studio_approval_signature = fields.Binary(
        string="Approval Signature",
        attachment=True,
        help="Digital signature of the approver (Manager)"
    )
    # Note: We use the standard 'date_approve' field for the approval date.

    # --- Requester Fields (Employee) ---
    x_studio_requester_signature = fields.Binary(
        string="Requester Signature",
        attachment=True,
        help="Digital signature of the person requesting the purchase"
    )

    x_studio_request_date = fields.Date(
        string="Request Date",
        default=fields.Date.context_today,
        help="Date when the requester signed or verified this document"
    )
    
    @api.onchange('x_studio_requester_signature')
    def _onchange_requester_signature(self):
        """
        Automatically set the request date to today when the requester signs
        in the UI form view.
        """
        if self.x_studio_requester_signature:
            self.x_studio_request_date = fields.Date.context_today(self)

    def write(self, vals):
        """
        Ensure the date is updated when saving, specifically useful if signed
        via digital signature widgets or external calls.
        """
        # If the signature field is present in the write values (vals) AND it has data
        if 'x_studio_requester_signature' in vals and vals['x_studio_requester_signature']:
            # If the date isn't already being manually set in this transaction
            if 'x_studio_request_date' not in vals:
                vals['x_studio_request_date'] = fields.Date.context_today(self)
        
        return super(PurchaseOrder, self).write(vals)