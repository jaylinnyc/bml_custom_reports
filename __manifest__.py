{
    'name': 'BML Custom Reports',
    'version': '19.0.1.0.0',
    'summary': 'BML & Panyaraksa - Custom PDF reports',
    'author': 'Jaylinnyc',
    'depends': ['account', 'purchase', 'stock', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/report_footer_config_views.xml',
        'views/report_purchase_order.xml',   # keep your footer override
        'views/report_inventory_operations.xml',  # inventory repair & consumption reports
        'views/account_move_views.xml',      # bill date sync feature
        'data/report_footer_data.xml',       # default footer configurations
    ],
    'installable': True,
    'license': 'OPL-1',
}