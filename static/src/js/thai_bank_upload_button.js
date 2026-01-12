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
        // Open the Thai bank statement upload wizard
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'bml.thai.bank.statement.wizard',
            views: [[false, 'form']],
            target: 'new',
            context: {
                default_journal_id: this.props.context.default_journal_id || false,
            }
        });
    }
}

// Create the view configuration extending the base list view
export const bankStatementListView = {
    ...listView,
    Controller: BankStatementListController,
};

// Register the custom view for bank statements list
registry.category("views").add("bank_statement_list_upload", bankStatementListView);
