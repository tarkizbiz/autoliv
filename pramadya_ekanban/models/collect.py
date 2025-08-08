# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, timedelta, time
import logging
_logger = logging.getLogger(__name__)

class CollectingSystem(models.Model):
    _name = 'collecting'
    _description = 'Collecting System'
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product')
    default_code = fields.Char(related='product_id.default_code')
    aid_partnumber = fields.Char(related='product_id.aid_partnumber')
    line_id = fields.Many2one('mrp.workcenter')
    qty = fields.Float(string="Qty", compute='_compute_qty',digits='Product Unit of Measure',store=True)
    start_date = fields.Datetime(default=fields.Datetime.now)
    end_date = fields.Datetime(default=fields.Datetime.now)
    collecting_lines = fields.One2many('collecting.line', 'collecting_id')
    state = fields.Selection([
        ('draft', 'In Progress'),
        ('ready', 'Ready'),
        ('done', 'Done')
    ], string='Status', copy=False, index=True, readonly=False, store=True, default='draft')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for c in self:
            c.write({'line_id': c.product_id.primary_line_id.id})
    @api.depends('collecting_lines')
    def _compute_qty(self):
        for lot in self:
            total = 0.0
            for details in lot.collecting_lines:
                total += details.qty
            lot.qty = total

    def cron_heijunka(self):
        list_collect = self.env['collecting'].sudo().search([('state','=','draft')])
        now = datetime.now()
        pitch_start = datetime.combine(now.date(), time(0, 0, 0))
        pitch_end = datetime.combine(now.date(), time(23, 59, 59))
        list_pitch = self.env['pitch'].sudo().search([('shift_start_date','>=',pitch_start),('shift_start_date','<=',pitch_end)])
        _logger.info("collect_pitch_start")
        _logger.info(pitch_start)

        _logger.info("collect_pitch_end")
        _logger.info(pitch_end)
        
        _logger.info("collect_list_pitch")
        lines =list_pitch.mapped('line')
        string_lines = [str(i) for i in lines]
        _logger.info(string_lines)
        for collect in list_collect:
            today = datetime.today().weekday()
            if today not in [5, 6]:
                if collect.qty != 0:
                    if list_pitch and collect.line_id.code in string_lines:
                        _logger.info("collect_list_pitch_true")
                        kanban = collect.qty / collect.product_id.snp
                        total = kanban
                        time_periods = 8
                        if collect.product_id.working_mins == 960:
                            time_periods = 16
                        daily_production = total // time_periods
                        remainder = int(total % time_periods)
                        today = fields.Datetime.now()
                        schedule = [daily_production] * time_periods
                        for i in range(remainder):
                            schedule[i] += 1
                        hours_add = 0
                        collect_start = datetime.combine(today, time(1, 0, 0))
                        for i, value in enumerate(schedule):
                            if i > 7:
                                data = {
                                'collect_id': collect.id,
                                'product_id': collect.product_id.id,
                                'date': today,
                                'schedule_date': collect_start + timedelta(hours=hours_add) + timedelta(hours=13),
                                'qty_kanban': value,
                                'qty': value * collect.product_id.snp}
                                heijunka = self.env['heijunka'].sudo().create(data)
                                hours_add += 1
                            else:
                                data = {
                                    'collect_id': collect.id,
                                    'product_id': collect.product_id.id,
                                    'date': today,
                                    'schedule_date': collect_start + timedelta(hours=i),
                                    'qty_kanban': value,
                                    'qty': value * collect.product_id.snp}
                                heijunka = self.env['heijunka'].sudo().create(data)

                        collect.sudo().write({'state': 'done'})

class Collectinglines(models.Model):
    _name = 'collecting.line'
    _description = 'Collecting System lines'
    
    collecting_id = fields.Many2one('collecting', ondelete='cascade')
    delivery_note = fields.Char(size=64)
    qty = fields.Float(string="Qty")
    qty_kanban = fields.Float(string="Qty Kanban")
    picking_date = fields.Date()

class Heijunka(models.Model):
    _name = 'heijunka'
    _description = 'e-heijunka'

    collect_id = fields.Many2one('collecting', ondelete='cascade')
    product_id = fields.Many2one('product.product')
    default_code = fields.Char(related='product_id.default_code')
    aid_partnumber = fields.Char(related='product_id.aid_partnumber')
    qty = fields.Float(string="Qty", digits='Product Unit of Measure')
    qty_kanban = fields.Float(digits='Product Unit of Measure')
    date = fields.Datetime(default=fields.Datetime.now)
    schedule_date = fields.Datetime(default=fields.Datetime.now)
    state = fields.Selection([
        ('draft', 'In Progress'),
        ('done', 'Done')
    ], string='Status', copy=False, index=True, readonly=False, store=True, default='draft')

    def cron_heijunka_lot(self):
        obj_heijunka = self.env['heijunka'].sudo().search([('schedule_date','<', fields.Datetime.now()),('state','=','draft')])
        for heijunka in obj_heijunka:
            lot = self.env['pramadya.lot'].search([('product_id','=', heijunka.product_id.id),('state','=','draft'),('is_qty_less_than_capacity', '=', True)],limit=1)
            if lot:
                total_lot = lot.qty + heijunka.qty
                if total_lot < lot.capacity:
                    data = {'lot_id': lot.id,
                            'order_date': heijunka.schedule_date,
                            'create_date': fields.Datetime.now(),
                            'delivery_note': "Heijunka",
                            'qty_kanban': heijunka.qty_kanban,
                            'qty': heijunka.qty}
                    lot_details = self.env['pramadya.lot.details'].sudo().create(data)
                    heijunka.write({'state': 'done'})
                    lot.send_kanban()
                else:
                    sisa = total_lot - lot.capacity
                    qty_split = heijunka.qty - sisa
                    if qty_split > 0:
                        lot_details = self.env['pramadya.lot.details'].sudo().create({
                            'lot_id': lot.id,
                            'delivery_note': "Heijunka",
                            'qty': qty_split,
                            'qty_kanban': qty_split/heijunka.qty,
                            'create_date': fields.Datetime.now(),
                            'order_date': heijunka.schedule_date
                        })
                    lot.send_kanban()
                    new_lot_id = self.env['pramadya.lot'].sudo().create({
                        'product_id': heijunka.product_id.id,
                        'line_id': heijunka.product_id.primary_line_id.id,
                        'capacity': heijunka.product_id.lot_size,
                        'schedule_date': heijunka.schedule_date
                    })
                    lot_details = self.env['pramadya.lot.details'].sudo().create({
                        'lot_id': new_lot_id.id,
                        'delivery_note': "Heijunka",
                        'qty': sisa,
                        'qty_kanban': sisa/heijunka.qty,
                        'create_date': fields.Datetime.now(),
                        'order_date': heijunka.schedule_date
                    })
                    heijunka.write({'state': 'done'})
            else:
                new_lot = self.env['pramadya.lot'].sudo().create({'product_id'  : heijunka.product_id.id,
                                                                'state'     : 'draft',
                                                                'line_id'   : heijunka.product_id.primary_line_id.id,
                                                                'capacity'  : heijunka.product_id.lot_size})
                data = {'lot_id': new_lot.id,
                        'order_date': heijunka.schedule_date,
                        'create_date': fields.Datetime.now(),
                        'delivery_note': "Heijunka",
                        'qty_kanban': heijunka.qty_kanban,
                        'qty': heijunka.qty}
                lot_details = self.env['pramadya.lot.details'].sudo().create(data)
                heijunka.write({'state': 'done'})