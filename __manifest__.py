{
    'name': 'BML Custom Reports',
    'version': '19.0.1.0.0',
    'summary': 'BML & Panyaraksa - Custom PDF reports',
    'author': 'Jaylinnyc',
    'depends': ['purchase', 'web'],
    'data': [
        'views/report_purchase_order.xml',   # keep your footer override
    ],
    'assets': {
        'web.report_assets_common': [        # This bundle loads on ALL PDF reports
            'bml_custom_reports/static/src/css/report_fixes.css',
        ],
    },
    'installable': True,
    'license': 'OPL-1',
}