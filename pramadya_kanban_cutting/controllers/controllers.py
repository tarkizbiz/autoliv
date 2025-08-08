# -*- coding: utf-8 -*-
from odoo import http

# class AsaMergeProduct(http.Controller):
#     @http.route('/asa_merge_product/asa_merge_product/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/asa_merge_product/asa_merge_product/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('asa_merge_product.listing', {
#             'root': '/asa_merge_product/asa_merge_product',
#             'objects': http.request.env['asa_merge_product.asa_merge_product'].search([]),
#         })

#     @http.route('/asa_merge_product/asa_merge_product/objects/<model("asa_merge_product.asa_merge_product"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('asa_merge_product.object', {
#             'object': obj
#         })