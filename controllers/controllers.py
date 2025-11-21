# from odoo import http


# class BmlCustomReports(http.Controller):
#     @http.route('/bml_custom_reports/bml_custom_reports', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/bml_custom_reports/bml_custom_reports/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('bml_custom_reports.listing', {
#             'root': '/bml_custom_reports/bml_custom_reports',
#             'objects': http.request.env['bml_custom_reports.bml_custom_reports'].search([]),
#         })

#     @http.route('/bml_custom_reports/bml_custom_reports/objects/<model("bml_custom_reports.bml_custom_reports"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('bml_custom_reports.object', {
#             'object': obj
#         })

