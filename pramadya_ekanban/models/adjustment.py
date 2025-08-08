# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, timedelta, time

class AdjustmentSystem(models.Model):
    _name = 'adjustment'
    _description = 'adjustment System'
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product')
    default_code = fields.Char(related='product_id.default_code')
    aid_partnumber = fields.Char(related='product_id.aid_partnumber')
    line_id = fields.Many2one('mrp.workcenter')
    qty = fields.Float(string="Qty", digits='Product Unit of Measure')
    qty_kanban = fields.Float(digits='Product Unit of Measure')
    adjustment_date = fields.Datetime(default=fields.Datetime.now)
    schedule_date = fields.Datetime(default=fields.Datetime.now)
    state = fields.Selection([
        ('draft', 'In Progress'),
        ('done', 'Done')
    ], string='Status', copy=False, index=True, readonly=False, store=True, default='draft')