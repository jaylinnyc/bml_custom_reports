/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { BankRecKanbanController } from "@account_accountant/components/bank_reconciliation/kanban_controller";

patch(BankRecKanbanController.prototype, {
    /**
     * Add Auto Reconcile button action to bank reconciliation widget
     */
    async autoReconcileAll() {
        const stLineIds = this.model.root.records.map(r => r.resId);
        if (!stLineIds.length) {
            this.notification.add("No transactions to reconcile", { type: "warning" });
            return;
        }
        
        const result = await this.orm.call(
            'account.bank.statement.line',
            'action_manual_auto_reconcile',
            [stLineIds]
        );
        
        // Reload the view to show reconciled lines
        await this.model.root.load();
        this.render();
        
        if (result && result.params) {
            this.notification.add(result.params.message, { 
                type: result.params.type,
                title: result.params.title 
            });
        }
    },
});
