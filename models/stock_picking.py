from odoo import models, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_print_picking(self):
        """
        Override the default print action to conditionally print
        repair or consumption reports based on operation type.
        """
        self.ensure_one()
        
        # Check operation type name
        operation_type_name = self.picking_type_id.name.lower() if self.picking_type_id else ''
        
        # Print Repair Report if operation type contains 'repair'
        if 'repair' in operation_type_name:
            return self.env.ref('bml_custom_reports.action_report_picking_repair').report_action(self)
        
        # Print Consumption Report if operation type contains 'consumption'
        elif 'consumption' in operation_type_name:
            return self.env.ref('bml_custom_reports.action_report_picking_consumption').report_action(self)
        
        # Default: use standard stock picking report
        else:
            return super().action_print_picking()
