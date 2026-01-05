{
    'name': 'Custom Reports',
    'version': '19.0.1.2.0',
    'summary': 'Custom PDF reports with configurable headers and footers',
    'author': 'Jaylinnyc',
    'depends': ['account', 'purchase', 'stock', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_company_views.xml',       # company settings for custom header
        'views/report_header.xml',           # custom header override
        'views/report_footer_config_views.xml',
        'views/report_purchase_order.xml',   # keep your footer override
        'views/report_invoice.xml',          # tax invoice with product description
        'views/report_inventory_operations.xml',  # inventory repair & consumption reports
        'views/account_move_views.xml',      # hide accounting date & taxinvoice date, show delivery date
        'views/delivery_date_mismatch_report_views.xml',  # delivery date mismatch report
        'data/report_footer_data.xml',       # default footer configurations
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'OPL-1',
}