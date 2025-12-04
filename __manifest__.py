{
    'name': 'BML Custom Reports',
    'version': '19.0.1.0.0',
    'summary': 'BML & Panyaraksa - Custom PDF reports',
    'author': 'Jaylinnyc',
    'depends': ['account', 'purchase', 'web'],
    'data': [
        'views/report_purchase_order.xml',   # keep your footer override
        'views/account_move_views.xml',      # bill date sync feature
    ],
    'installable': True,
    'license': 'OPL-1',
}