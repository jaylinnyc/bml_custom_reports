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
        // Get the journal ID from multiple possible sources
        let journalId = false;
        
        // Try 1: Get from context (if set explicitly)
        if (this.props.context.default_journal_id) {
            journalId = this.props.context.default_journal_id;
        }
        
        // Try 2: Get from the current domain filter (when viewing from dashboard)
        // The domain looks like: [('journal_id', '=', 41)]
        if (!journalId && this.props.domain) {
            for (const condition of this.props.domain) {
                if (Array.isArray(condition) && condition[0] === 'journal_id' && condition[1] === '=' && condition[2]) {
                    journalId = condition[2];
                    break;
                }
            }
        }
        
        // Try 3: If there are selected records, get journal from first selected statement
        if (!journalId && this.model.root.selection && this.model.root.selection.length > 0) {
            const firstSelected = this.model.root.selection[0];
            if (firstSelected.data && firstSelected.data.journal_id) {
                journalId = firstSelected.data.journal_id[0];
            }
        }
        
        // Try 4: If viewing records, get journal from first visible record
        if (!journalId && this.model.root.records && this.model.root.records.length > 0) {
            const firstRecord = this.model.root.records[0];
            if (firstRecord.data && firstRecord.data.journal_id) {
                journalId = firstRecord.data.journal_id[0];
            }
        }
        
        // Open the Thai bank statement upload wizard
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
