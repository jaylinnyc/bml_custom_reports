/** @odoo-module **/

import { BankRecKanbanController } from "@account_accountant/components/bank_reconciliation/kanban_controller";
import { BankRecKanbanView } from "@account_accountant/components/bank_reconciliation/kanban_renderer";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

/**
 * Extend the bank reconciliation kanban controller to add Auto Reconcile functionality
 */
export class BmlBankRecKanbanController extends BankRecKanbanController {
    setup() {
        super.setup();
        this.notification = useService("notification");
    }

    async autoReconcileAll() {
        try {
            // Get ALL unreconciled statement line IDs from the database, not just the current page
            // Use the same domain/filters as the current view to respect user's filtering
            const domain = this.model.root.config.domain || [];
            
            // Search for all unreconciled lines matching the current view's domain
            const stLineIds = await this.orm.searchRead(
                'account.bank.statement.line',
                domain,
                ['id'],
                { limit: false }  // No limit - get all records
            );
            
            const allIds = stLineIds.map(r => r.id);
            
            if (!allIds.length) {
                this.notification.add("No transactions to reconcile", { type: "warning" });
                return;
            }
            
            // Show progress notification
            this.notification.add(
                `Starting auto-reconciliation of ${allIds.length} transaction(s)...`,
                { type: "info" }
            );
            
            const result = await this.orm.call(
                'account.bank.statement.line',
                'action_manual_auto_reconcile',
                [allIds]
            );
            
            // Reload the view to show reconciled lines
            await this.model.root.load();
            this.render();
            
            // Show notification from result
            if (result && result.params) {
                this.notification.add(result.params.message, { 
                    type: result.params.type || 'success',
                    title: result.params.title 
                });
            }
        } catch (error) {
            this.notification.add("Error during auto-reconciliation: " + error.message, { 
                type: "danger" 
            });
        }
    }
}

// Create the view configuration extending the base bank rec view
export const bmlBankRecKanbanView = {
    ...BankRecKanbanView,
    Controller: BmlBankRecKanbanController,
    buttonTemplate: "bml_custom_reports.BankRecAutoReconcileButton",
};

// Override the bank_rec_widget_kanban view with our extended version
registry.category("views").add("bank_rec_widget_kanban", bmlBankRecKanbanView, { force: true });
