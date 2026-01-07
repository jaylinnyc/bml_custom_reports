{
    'name': 'Custom Reports',
    'version': '19.0.1.8.0',
    'summary': 'Custom PDF reports with configurable headers and footers, Thai WHT handling, Payment enhancements',
    'author': 'Jaylinnyc',
    'depends': ['account', 'account_accountant', 'purchase', 'stock', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_company_views.xml',       # company settings for custom header
        'views/report_header.xml',           # custom header override
        'views/report_footer_config_views.xml',
        'views/report_purchase_order.xml',   # keep your footer override
        'views/report_invoice.xml',          # tax invoice with product description
        'views/report_inventory_operations.xml',  # inventory repair & consumption reports
        'views/account_move_views.xml',      # hide accounting date, show delivery date
        'views/account_payment_views.xml',   # invoice selector for direct payments
        'data/report_footer_data.xml',       # default footer configurations
        # WHT Handling & Payment Enhancements
        'wizard/account_payment_register_wht_views.xml',
        'wizard/wht_text_export_wizard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'bml_custom_reports/static/src/js/bank_rec_auto_reconcile.js',
            'bml_custom_reports/static/src/xml/bank_rec_auto_reconcile.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'OPL-1',
}