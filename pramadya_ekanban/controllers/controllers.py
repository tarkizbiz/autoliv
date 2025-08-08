# -*- coding: utf-8 -*-
# from odoo import http


# class PramadyaEkanban(http.Controller):
#     @http.route('/pramadya_ekanban/pramadya_ekanban', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/pramadya_ekanban/pramadya_ekanban/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('pramadya_ekanban.listing', {
#             'root': '/pramadya_ekanban/pramadya_ekanban',
#             'objects': http.request.env['pramadya_ekanban.pramadya_ekanban'].search([]),
#         })

#     @http.route('/pramadya_ekanban/pramadya_ekanban/objects/<model("pramadya_ekanban.pramadya_ekanban"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('pramadya_ekanban.object', {
#             'object': obj
#         })
