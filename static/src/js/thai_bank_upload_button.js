/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";

/**
 * Extend the list controller to add Upload Thai Statement functionality
 * for bank statements list view
 */
export class BankStatementListController extends ListController {
    setup() {
        super.setup();
        this.action = useService("action");
    }

    async uploadThaiStatement() {
        // Get journal ID from context - mimics how Odoo's dashboard passes journal context
        // When clicking "Statements" from dashboard, open_action_with_context sets default_journal_id
        const journalId = this.props.context.default_journal_id || false;
        
        // Open the Thai bank statement upload wizard with the journal context
        // This is the same pattern used by Odoo's standard import functionality
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'bml.thai.bank.statement.wizard',
            views: [[false, 'form']],
            target: 'new',
            context: {
                default_journal_id: journalId,
            }
        });
    }
}

// Create the view configuration extending the base list view
export const bankStatementListView = {
    ...listView,
    Controller: BankStatementListController,
    buttonTemplate: "bml_custom_reports.ThaiBankUploadButton",
};

// Register the custom view for bank statements list
registry.category("views").add("bank_statement_list_upload", bankStatementListView);
