# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import io
import base64
import re
import tabula
from datetime import datetime, timedelta, time
import os
import subprocess
import logging
import re
import math

_logger = logging.getLogger(__name__)

class Product(models.Model):
    _inherit = ['product.product']

    customer_partnumber = fields.Char()
    aid_partnumber = fields.Char()
    l2l_product_id = fields.Integer()
    lot_size = fields.Float(digits='Product Unit of Measure')
    cycle_time = fields.Float()
    lot = fields.Selection([('lot',"LOT System"),('schedule',"Schedule")], string="Production Type")
    customer_id = fields.Many2one('res.partner')
    primary_line_id = fields.Many2one('mrp.workcenter')
    secondary_line_id = fields.Many2one('mrp.workcenter')
    total_kanban = fields.Float(compute='_compute_kanban',digits='Product Unit of Measure', store=True)
    kanban_rotation = fields.Float(compute='_compute_kanban',digits='Product Unit of Measure', store=True)
    fg_rotation = fields.Float(compute='_compute_kanban',digits='Product Unit of Measure', store=True)
    std_rotation = fields.Float(digits='Product Unit of Measure', compute="_compute_kc", store=True)
    e_lot = fields.Float(compute='_e_lot',digits='Product Unit of Measure', store=True)
    kanban_e_lot = fields.Float(compute='_e_lot',digits='Product Unit of Measure', store=True)
    kanban_e_rail = fields.Float(compute='_e_rail',digits='Product Unit of Measure', store=True)
    e_rail = fields.Float(compute='_e_rail',digits='Product Unit of Measure', store=True)
    e_collecting = fields.Float(compute='_e_collecting',digits='Product Unit of Measure', store=True)
    e_heijunka = fields.Float(compute='_e_heijunka',digits='Product Unit of Measure', store=True)
    kanban_e_collecting = fields.Float(compute='_e_collecting',digits='Product Unit of Measure', store=True)
    kanban_e_heijunka = fields.Float(compute='_e_heijunka',digits='Product Unit of Measure', store=True)
    # safety_stock = fields.Float(digits='Product Unit of Measure',compute='_compute_status_stock')
    status_stock = fields.Selection([('maksimum',"Maksimum"),('normal',"Normal"),('minimum',"Minimum"),('urgent',"Urgent")],compute='_compute_status_stock', string="Status Stock")
    demand_monthly = fields.Float(digits='Product Unit of Measure')
    snp = fields.Float(compute='_compute_kanban',digits='Product Unit of Measure', store=True)
    selisih = fields.Float(compute='_compute_kanban',digits='Product Unit of Measure', store=True)
    adjustment = fields.Float(compute='_compute_adj',digits='Product Unit of Measure', store=True)
    adjustment_ids = fields.One2many('adjustment','product_id')
    collecting_ids = fields.One2many('collecting','product_id')
    heijunka_ids = fields.One2many('heijunka','product_id')
    lot_ids = fields.One2many('pramadya.lot','product_id')
    rail_ids = fields.One2many('pramadya.rail','product_id')
    #input kanban calculation
    store = fields.Float(default=0.5)
    stagnasi = fields.Float(default=0.5)
    fluktuasi = fields.Float(digits='Product Unit of Measure', default=20)
    safety = fields.Float(default=1)
    shikumi = fields.Float(default=1)
    collecting = fields.Float(default=1)
    working_days = fields.Float(digits='Product Unit of Measure', default=20)
    working_hour = fields.Float(digits='Product Unit of Measure', related='primary_line_id.resource_calendar_id.hours_per_day')
    working_mins = fields.Float(digits='Product Unit of Measure')
    daily_demand = fields.Float(digits='Product Unit of Measure', compute="_compute_kc", store=True)
    #output kanban calculation
    qty_store = fields.Float(digits='Product Unit of Measure', compute="_compute_kc", store=True)
    qty_elot = fields.Float(digits='Product Unit of Measure', compute="_compute_kc", store=True)
    qty_erail = fields.Float(digits='Product Unit of Measure', compute="_compute_kc", store=True)
    qty_stagnasi = fields.Float(digits='Product Unit of Measure', compute="_compute_kc", store=True)
    qty_base = fields.Float(digits='Product Unit of Measure', compute="_compute_kc", store=True)
    qty_fluktuasi = fields.Float(digits='Product Unit of Measure', compute="_compute_kc", store=True)
    qty_safety = fields.Float(digits='Product Unit of Measure', compute="_compute_kc", store=True)
    qty_shikumi = fields.Float(digits='Product Unit of Measure', compute="_compute_kc", store=True)
    qty_collecting = fields.Float(digits='Product Unit of Measure', compute="_compute_kc", store=True)

    #Heijunka cycles
    heijunka_cycle = fields.Selection([('8',"60 Menit"),('16',"30 Menit")], string="Heijunka cycle")

    def compute_urgent(self):
        list_product = self.env['product.product'].sudo().search([])
        for product in list_product:
            # product.with_context({'from_date': '2024-08-29 00:00','to_date': '2024-08-29 23:59'}).outgoing_qty
            # jika forcast qty minus maka erail akan urgent sesuai dengan kekurangan
            _logger.info("compute_urgent")
            minimum = product.qty_safety + product.qty_store
            list_rail = self.env['pramadya.rail'].search([('product_id', '=', product.id),('state','not in',('changeover','canceled','completed'))],order='status_rtb,status_stock_condition,schedule_date')
            if product.virtual_available < 0 and list_rail:
                kekurangan = abs(product.virtual_available)
                _logger.info("kekurangan")
                _logger.info(kekurangan)
                urgent = 0
                for rail in list_rail:
                    if urgent < kekurangan:
                        rail.status_stock_condition = '01'
                        urgent += rail.qty
                    else:
                        rail.status_stock_condition = False
            elif product.total_kanban <= minimum and product.virtual_available > 0 and list_rail:
                kekurangan = abs(product.qty_available)
                _logger.info("minimum")
                _logger.info(kekurangan)
                qty_minimum = 0
                for rail in list_rail:
                    if qty_minimum == 0:
                        rail.status_stock_condition = '02'
                        qty_minimum += rail.qty
                    else:
                        rail.status_stock_condition = False

            else:
                for rail in list_rail:
                    rail.status_stock_condition = False

    @api.depends('lot_size','demand_monthly','working_days','store','stagnasi','fluktuasi','safety','shikumi','collecting')
    def _compute_kc(self):
        for product in self:
            snp = 1
            if product.lot == 'lot' and product.snp > 0:
                snp = product.snp
            product.daily_demand = product.demand_monthly / product.working_days
            product.qty_store = math.ceil((product.daily_demand * product.store) / snp)
            product.qty_stagnasi = (product.daily_demand * product.stagnasi) / snp
            product.qty_elot = product.lot_size / snp
            product.qty_erail = 0
            product.qty_base = product.qty_store + product.qty_stagnasi + product.qty_elot + product.qty_erail
            product.qty_fluktuasi = (product.daily_demand * (product.fluktuasi/100)) /snp
            product.qty_safety = math.ceil((product.daily_demand * product.safety) / snp)
            product.qty_shikumi = math.ceil((product.daily_demand * product.shikumi) / snp)
            product.qty_collecting = (product.daily_demand * product.collecting) / snp
            product.std_rotation = product.qty_base + product.qty_fluktuasi + product.qty_safety + product.qty_shikumi + product.qty_collecting
            

    def _compute_status_stock(self):
        for product in self:
            # Minimum <= (KBN safety + store)
            # Maximum >= (KBN safety + store + shikumi + fluktuasi + stagnasi)
            # Normal Qty KBN antara maksimum dan minimum
            minimum = product.qty_safety + product.qty_store
            maksimum = product.qty_safety + product.qty_store + product.qty_shikumi + product.qty_fluktuasi + product.qty_stagnasi
            if product.virtual_available < 0:
                product.status_stock = 'urgent'
            elif product.total_kanban <= minimum and product.virtual_available > 0:
                product.status_stock = 'minimum'
            elif product.total_kanban >= maksimum:
                product.status_stock = 'maksimum'
            else:
                product.status_stock = 'normal'

            # >= 2 * lot size >> Over Stock
            #< 2 * lot size dan >= 1,5 * lot size >> Normal
            # < 1,5 * lot size dan >= 1 lot size >> Intermediate​
            # < 1 lot size dan >= 0,5 lot size >> Urgent​
            # < 0,5 lot size >> Out of Stock
            # lot_2x = product.lot_size * 2
            # lot_15x = product.lot_size * 1.5
            # lot_1x = product.lot_size
            # lot_05x = product.lot_size * 0.5
            # if product.qty_available >= lot_2x and product.lot == 'lot':
            #     product.status_stock = 'over'
            # elif  product.qty_available < lot_2x and product.qty_available >= lot_15x and product.lot == 'lot':
            #     product.status_stock = 'normal'
            # elif product.qty_available < lot_15x and product.qty_available >= lot_1x and product.lot == 'lot':
            #     product.status_stock = 'inter'
            # elif product.qty_available < lot_1x and product.qty_available >= lot_05x and product.lot == 'lot':
            #     product.status_stock = 'urgent'
            # elif product.qty_available < lot_05x and product.lot == 'lot':
            #     product.status_stock = 'out'
            # else:
            #     product.status_stock = 'normal'

    @api.depends('packaging_ids','lot_ids.qty','lot_ids.state')
    def _e_lot(self):
        for product in self:
            qty_package = 1
            if product.packaging_ids:
                qty_package = product.packaging_ids[0].qty
            product.e_lot = sum(product.lot_ids.filtered(lambda e_lot: e_lot.state != 'done').mapped('qty'))
            product.kanban_e_lot = product.e_lot / qty_package

    @api.depends('packaging_ids','rail_ids.qty','rail_ids.state')
    def _e_rail(self):
        for product in self:
            qty_package = 1
            if product.packaging_ids:
                qty_package = product.packaging_ids[0].qty
            product.e_rail = sum(product.rail_ids.filtered(lambda e_lot: e_lot.state not in ['completed','canceled','changeover']).mapped('qty'))
            product.kanban_e_rail = product.e_rail / qty_package

    @api.depends('packaging_ids','collecting_ids.qty','collecting_ids.state')
    def _e_collecting(self):
        for product in self:
            qty_package = 1
            if product.packaging_ids:
                qty_package = product.packaging_ids[0].qty
            product.e_collecting = sum(product.collecting_ids.filtered(lambda e_collecting: e_collecting.state != 'done').mapped('qty'))
            product.kanban_e_collecting = product.e_collecting / qty_package


    @api.depends('packaging_ids','heijunka_ids.qty','heijunka_ids.state')
    def _e_heijunka(self):
        for product in self:
            qty_package = 1
            if product.packaging_ids:
                qty_package = product.packaging_ids[0].qty
            product.e_heijunka = sum(product.heijunka_ids.filtered(lambda e_heijunka: e_heijunka.state != 'done').mapped('qty'))
            product.kanban_e_heijunka = product.e_heijunka / qty_package
            
    @api.depends('adjustment_ids.qty_kanban','adjustment_ids.state')
    def _compute_adj(self):
        for product in self:
            adjustment = self.env['adjustment'].sudo().search([('product_id','=',product.id),('state','!=','done')])
            product.adjustment = sum(product.adjustment_ids.filtered(lambda adjustment: adjustment.state != 'done').mapped('qty_kanban'))

    @api.depends('packaging_ids','qty_available','std_rotation','e_lot','kanban_e_lot','e_rail','kanban_e_rail','kanban_e_collecting','kanban_e_heijunka','adjustment')
    def _compute_kanban(self):
        for product in self:
            total_kanban = 0.0
            kanban_rotation = 0.0
            qty_package = 1
            if product.packaging_ids:
                qty_package = product.packaging_ids[0].qty
            product.total_kanban = product.qty_available / qty_package
            product.kanban_rotation = product.total_kanban + product.kanban_e_lot + product.kanban_e_rail + product.kanban_e_collecting + product.kanban_e_heijunka
            product.fg_rotation = product.qty_available + product.e_lot + product.e_rail
            product.snp = qty_package
            product.selisih = product.std_rotation - (product.kanban_rotation + product.adjustment)   

    @api.onchange('lot')
    def _change_lot_size(self):
        if self.lot == 'schedule':
            self.lot_size = 0

    def cron_adjustment(self):
        obj_adjustment = self.env['adjustment'].sudo().search([('schedule_date','<', fields.Datetime.now()),('state','=','draft')])
        for adjustment in obj_adjustment:
            lot = self.env['pramadya.lot'].search([('product_id','=', adjustment.product_id.id),('state','=','draft')],limit=1)
            if lot:
                total_lot = lot.qty + adjustment.qty
                if total_lot < lot.capacity:
                    data = {'lot_id': lot.id,
                        'order_date': adjustment.schedule_date,
                        'create_date': fields.Datetime.now(),
                        'delivery_note': "Adjustment",
                        'qty_kanban': adjustment.qty_kanban,
                        'qty': adjustment.qty}
                    lot_details = self.env['pramadya.lot.details'].sudo().create(data)
                    adjustment.write({'state': 'done'})
                    lot.send_kanban()
                else:
                    sisa = total_lot - lot.capacity
                    qty_split = adjustment.qty - sisa
                    if qty_split > 0:
                        data = {'lot_id': lot.id,
                                'order_date': adjustment.schedule_date,
                                'create_date': fields.Datetime.now(),
                                'delivery_note': "Adjustment",
                                # 'qty_kanban': adjustment.qty_kanban,
                                'qty': qty_split}
                        lot_details = self.env['pramadya.lot.details'].sudo().create(data)
                        lot.send_kanban()
                        new_lot = self.env['pramadya.lot'].sudo().create({'product_id'  : adjustment.product_id.id,
                                                                        'state'     : 'draft',
                                                                        'line_id'   : adjustment.product_id.primary_line_id.id,
                                                                        'capacity'  : adjustment.product_id.lot_size})
                        data = {'lot_id': new_lot.id,
                                'order_date': adjustment.schedule_date,
                                'create_date': fields.Datetime.now(),
                                'delivery_note': "Adjustment",
                                # 'qty_kanban': adjustment.qty_kanban,
                                'qty': sisa}
                        lot_details = self.env['pramadya.lot.details'].sudo().create(data)
                        adjustment.write({'state': 'done'})
            else:
                new_lot = self.env['pramadya.lot'].sudo().create({'product_id'  : adjustment.product_id.id,
                                                                'state'     : 'draft',
                                                                'line_id'   : adjustment.product_id.primary_line_id.id,
                                                                'capacity'  : adjustment.product_id.lot_size})
                data = {'lot_id': new_lot.id,
                        'order_date': adjustment.schedule_date,
                        'create_date': fields.Datetime.now(),
                        'delivery_note': "Adjustment",
                        'qty_kanban': adjustment.qty_kanban,
                        'qty': adjustment.qty}
                lot_details = self.env['pramadya.lot.details'].sudo().create(data)
                adjustment.write({'state': 'done'})

    def cron_selisih(self):
        list_product = self.env['product.product'].sudo().search([('lot','=','lot')])
        for product in list_product:
            if product.selisih != 0:
                total = product.selisih
                parts = 5
                selisih = total // parts
                remainder = total % parts
                today = fields.Datetime.now()
                result = [selisih] * (parts - 1) + [selisih + remainder]
                for i, value in enumerate(result):
                    data = {'product_id': product.id,
                        'adjustment_date': today,
                        'schedule_date': today + timedelta(days=i),
                        'qty_kanban': value,
                        'qty': value * product.snp}
                    adjustment = self.env['adjustment'].sudo().create(data)

class StockPicking(models.Model):
    _inherit = ['stock.picking']

    order_date = fields.Date()
    pickup_date = fields.Datetime()
    order_ready = fields.Datetime(string="Order Readiness")
    start_pull = fields.Datetime(string="Start Pulling")
    end_pull = fields.Datetime(string="End Pulling")
    cycle = fields.Integer()
    qty_kanban = fields.Float(string="Total Kanban", compute="_compute_total_kanban",digits='Product Unit of Measure')
    result = fields.Selection([('schedule',"On Schedule"),('advance',"Advance"),('delay',"Delay")], default='schedule')
    status_pickup = fields.Selection([('picking',"Picking Order"),('palleting',"Palleting & Scanning"),('ready',"Ready To Pick Up"),('delay',"Delay")], default='picking')

    barcode = fields.Char(string='Barcode', help="Barcode for Scanning Product")
    scanned_line = fields.One2many('pramadya.scan','picking_id')
    scanned_kanban_customer_header = fields.Boolean(default=False)


    @api.onchange('barcode')
    def _onchange_barcode(self):
        """Function to add Quantity when entering a Barcode."""
        warm_sound_code = "BARCODE_SCANNER_"
        match = False
        # Define the regex pattern
        pattern = r'Z([^Z]+)$'

        # Use re.search to find the match AID Barcode
        re_match = re.search(pattern, str(self.barcode))

        # Check if there is a match and get the data

        aid_kanban = False
        product_id = False
        if re_match:
            aid_kanban = re_match.group(1)
            product_id = self.env['product.product'].search(
                [('aid_partnumber', '=', str(aid_kanban))])
            if not product_id:
                input_string = self.barcode
                start_index = input_string.find("P") + len("P")
                end_index = input_string.find("Q")
                aid_kanban = input_string[start_index:end_index]
                product_id = self.env['product.product'].search(
                [('aid_partnumber', '=', aid_kanban),('customer_id','=', self.partner_id.id)],limit=1)
        
        if not re_match and self.barcode:
            # Barcode AID Besar
            input_string = self.barcode
            start_index = input_string.find("P") + len("P")
            end_index = input_string.find("Q")
            aid_kanban = input_string[start_index:end_index]
            product_id = self.env['product.product'].search(
            [('aid_partnumber', '=', aid_kanban),('customer_id','=', self.partner_id.id)],limit=1)
        
        if not product_id:
            #Customer Barcode
            if self.partner_id.ref in ["99100003","99100004","99100005"]:
                #Barcode TMMIN
                between_digits = self.barcode[14:26]
                customer_barcode = between_digits
                product_tmmin = self.env['product.product'].search(
                [('customer_partnumber', '=', customer_barcode),('customer_id','=', self.partner_id.id)],limit=1)
                if product_tmmin and self.move_ids_without_package:
                    for line in self.move_ids_without_package:
                        if line.customer_partnumber == product_tmmin.customer_partnumber:
                            if line.qty_kanban != line.scanned_kanban:
                                #pokayoke
                                if self.scanned_kanban_customer_header:
                                    warning_mess = {
                                        'title': _('Warning !'),
                                        'message': 
                                        _(warm_sound_code + f'Anda harus memindai barcode ATRAQ product {line.product_id.aid_partnumber} terlebih dahulu !!')
                                    }
                                    return {'warning': warning_mess, 'value': {'barcode': False}}
                                else:
                                    line.scanned_kanban_customer = True
                                    self.scanned_kanban_customer_header = True

                                line.scanned_kanban += 1
                                vals = {}
                                vals['scanned_line'] = [(0,0,{'picking_id': self.id,'move_id': line.id,'product_id': line.product_id.id, 'barcode': self.barcode, 'date_scan': fields.Datetime.now()})]
                                vals['barcode'] = False    
                                line.scanned_kanban_customer = True    
                                return {'value': vals}
                            else:
                                warning_mess = {
                                    'title': _('Warning !'),
                                    'message': _(warm_sound_code + f'Qty Kanban dan Scanned Kanban Product {line.product_id.customer_partnumber} Sudah Sesuai.')
                                }
                                return {'warning': warning_mess, 'value': {'barcode': False}}
                else:
                    warning_mess = {
                        'title': _('Warning !'),
                        'message': _(warm_sound_code + f'Customer Barcode ({customer_barcode}) Tidak Ditemukan!!')
                    }
                    return {'warning': warning_mess, 'value': {'barcode': False}}
            
            elif self.partner_id.ref in ["99100040"]:
                #Barcode ADM
                between_digits = self.barcode[16:23]
                customer_barcode = between_digits
                product_adm = self.env['product.product'].search(
                [('default_code', '=', customer_barcode),('customer_id','=', self.partner_id.id)],limit=1)
                if product_adm and self.move_ids_without_package:
                    for line in self.move_ids_without_package:
                        if line.product_id.default_code == product_adm.default_code:
                            if line.qty_kanban != line.scanned_kanban:
                                #pokayoke
                                if self.scanned_kanban_customer_header:
                                    warning_mess = {
                                        'title': _('Warning !'),
                                        'message': 
                                        _(warm_sound_code + f'Anda harus memindai barcode ATRAQ product {line.product_id.aid_partnumber} terlebih dahulu !!')
                                    }
                                    return {'warning': warning_mess, 'value': {'barcode': False}}
                                else:
                                    line.scanned_kanban_customer = True
                                    self.scanned_kanban_customer_header = True

                                line.scanned_kanban += 1
                                vals = {}
                                vals['scanned_line'] = [(0,0,{'picking_id': self.id,'move_id': line.id,'product_id': line.product_id.id, 'barcode': self.barcode, 'date_scan': fields.Datetime.now()})]
                                vals['barcode'] = False    
                                line.scanned_kanban_customer = True   
                                return {'value': vals}
                            else:
                                warning_mess = {
                                    'title': _('Warning !'),
                                    'message': _(warm_sound_code + f'Qty Kanban dan Scanned Kanban Product {line.product_id.default_code} Sudah Sesuai.')
                                }
                                return {'warning': warning_mess, 'value': {'barcode': False}}
                else:
                    warning_mess = {
                        'title': _('Warning !'),
                        'message': _(warm_sound_code + f'Customer Barcode ({self.barcode}) Tidak Ditemukan!!')
                    }
                    return {'warning': warning_mess, 'value': {'barcode': False}}

            elif self.partner_id.ref in ["99100102"]:
                # Barcode TB INA KARAWANG
                customer_barcode = self.barcode
                product_tbina = self.env['product.product'].search(
                [('customer_partnumber', '=', customer_barcode),('customer_id','=', self.partner_id.id)],limit=1)
                if product_tbina and self.move_ids_without_package:
                    for line in self.move_ids_without_package:
                        if line.customer_partnumber == product_tbina.customer_partnumber:
                            if line.qty_kanban != line.scanned_kanban:
                                #pokayoke
                                if self.scanned_kanban_customer_header:
                                    warning_mess = {
                                        'title': _('Warning !'),
                                        'message': 
                                        _(warm_sound_code + f'Anda harus memindai barcode ATRAQ product {line.product_id.aid_partnumber} terlebih dahulu !!')
                                    }
                                    return {'warning': warning_mess, 'value': {'barcode': False}}
                                else:
                                    line.scanned_kanban_customer = True
                                    self.scanned_kanban_customer_header = True

                                line.scanned_kanban += 1
                                vals = {}
                                vals['scanned_line'] = [(0,0,{'picking_id': self.id,'move_id': line.id,'product_id': line.product_id.id, 'barcode': self.barcode, 'date_scan': fields.Datetime.now()})]
                                vals['barcode'] = False    
                                line.scanned_kanban_customer = True
                                return {'value': vals}
                            else:
                                warning_mess = {
                                    'title': _('Warning !'),
                                    'message': _(warm_sound_code + f'Qty Kanban dan Scanned Kanban Product {line.product_id.customer_partnumber} Sudah Sesuai.')
                                }
                                return {'warning': warning_mess, 'value': {'barcode': False}}
                else:
                    warning_mess = {
                        'title': _('Warning !'),
                        'message': _(warm_sound_code + f'Customer Barcode ({customer_barcode}) Tidak Ditemukan!!')
                    }
                    return {'warning': warning_mess, 'value': {'barcode': False}}

            elif self.partner_id.ref in ["99100011"]:
                # Barcode TB INA MM
                input_string = self.barcode
                pattern = r'@([^@]+)@'
                match = re.search(pattern, input_string)
                customer_barcode = False
                if match:
                    customer_barcode = match.group(1)
                product_tbina = self.env['product.product'].search(
                [('customer_partnumber', '=', self.barcode),('customer_id','=', self.partner_id.id)],limit=1)
                if product_tbina and self.move_ids_without_package:
                    for line in self.move_ids_without_package:
                        if line.customer_partnumber == product_tbina.customer_partnumber:
                            if line.qty_kanban != line.scanned_kanban:
                                #pokayoke
                                if self.scanned_kanban_customer_header:
                                    warning_mess = {
                                        'title': _('Warning !'),
                                        'message': 
                                        _(warm_sound_code + f'Anda harus memindai barcode ATRAQ product {line.product_id.aid_partnumber} terlebih dahulu !!')
                                    }
                                    return {'warning': warning_mess, 'value': {'barcode': False}}
                                else:
                                    line.scanned_kanban_customer = True
                                    self.scanned_kanban_customer_header = True

                                line.scanned_kanban += 1
                                vals = {}
                                vals['scanned_line'] = [(0,0,{'picking_id': self.id,'move_id': line.id,'product_id': line.product_id.id, 'barcode': self.barcode, 'date_scan': fields.Datetime.now()})]
                                vals['barcode'] = False    
                                line.scanned_kanban_customer = True
                                return {'value': vals}
                            else:
                                warning_mess = {
                                    'title': _('Warning !'),
                                    'message': _(warm_sound_code + f'Qty Kanban dan Scanned Kanban Product {line.product_id.customer_partnumber} Sudah Sesuai.')
                                }
                                return {'warning': warning_mess, 'value': {'barcode': False}}
                else:
                    warning_mess = {
                        'title': _('Warning !'),
                        'message': _(warm_sound_code + f'Customer Barcode ({customer_barcode}) Tidak Ditemukan!!')
                    }
                    return {'warning': warning_mess, 'value': {'barcode': False}}

            elif self.partner_id.ref in ["99100023"]:
                # Barcode MMKI
                customer_barcode = self.barcode
                product_mmki = self.env['product.product'].search(
                [('customer_partnumber', '=', customer_barcode),('customer_id','=', self.partner_id.id)],limit=1)
                if product_mmki and self.move_ids_without_package:
                    for line in self.move_ids_without_package:
                        if line.customer_partnumber == product_mmki.customer_partnumber:
                            if line.qty_kanban != line.scanned_kanban:
                                #pokayoke
                                if self.scanned_kanban_customer_header:
                                    warning_mess = {
                                        'title': _('Warning !'),
                                        'message': 
                                        _(warm_sound_code + f'Anda harus memindai barcode ATRAQ product {line.product_id.aid_partnumber} terlebih dahulu !!')
                                    }
                                    return {'warning': warning_mess, 'value': {'barcode': False}}
                                else:
                                    line.scanned_kanban_customer = True
                                    self.scanned_kanban_customer_header = True

                                line.scanned_kanban += 1
                                vals = {}
                                vals['scanned_line'] = [(0,0,{'picking_id': self.id,'move_id': line.id,'product_id': line.product_id.id, 'barcode': self.barcode, 'date_scan': fields.Datetime.now()})]
                                vals['barcode'] = False
                                line.scanned_kanban_customer = True    
                                return {'value': vals}
                            else:
                                warning_mess = {
                                    'title': _('Warning !'),
                                    'message': _(warm_sound_code + f'Qty Kanban dan Scanned Kanban Product {line.product_id.customer_partnumber} Sudah Sesuai.')
                                }
                                return {'warning': warning_mess, 'value': {'barcode': False}}
                        
                else:
                    warning_mess = {
                        'title': _('Warning !'),
                        'message': _(warm_sound_code + f'Customer Barcode ({customer_barcode}) Tidak Ditemukan!!')
                    }
                    return {'warning': warning_mess, 'value': {'barcode': False}}

            elif self.partner_id.ref in ["99100058"]:
                # Barcode Hyundai
                input_string = self.barcode
                start_index = input_string.find("HB0G") + len("HB0G")
                end_index = 17
                customer_barcode = input_string[start_index:end_index]
                product_hyundai = self.env['product.product'].search(
                [('customer_partnumber', '=', customer_barcode),('customer_id','=', self.partner_id.id)],limit=1)
                if product_hyundai and self.move_ids_without_package:
                    for line in self.move_ids_without_package:
                        if line.customer_partnumber == product_hyundai.customer_partnumber:
                            if line.qty_kanban != line.scanned_kanban:
                                #pokayoke
                                if self.scanned_kanban_customer_header:
                                    warning_mess = {
                                        'title': _('Warning !'),
                                        'message': 
                                        _(warm_sound_code + f'Anda harus memindai barcode ATRAQ product {line.product_id.aid_partnumber} terlebih dahulu !!')
                                    }
                                    return {'warning': warning_mess, 'value': {'barcode': False}}
                                else:
                                    line.scanned_kanban_customer = True
                                    self.scanned_kanban_customer_header = True

                                line.scanned_kanban += 1
                                vals = {}
                                vals['scanned_line'] = [(0,0,{'picking_id': self.id,'move_id': line.id,'product_id': line.product_id.id, 'barcode': self.barcode, 'date_scan': fields.Datetime.now()})]
                                vals['barcode'] = False    
                                line.scanned_kanban_customer = True
                                return {'value': vals}
                            else:
                                warning_mess = {
                                    'title': _('Warning !'),
                                    'message': _(warm_sound_code + f'Qty Kanban dan Scanned Kanban Product {line.product_id.customer_partnumber} Sudah Sesuai.')
                                }
                                return {'warning': warning_mess, 'value': {'barcode': False}}

            elif self.partner_id.ref in ["99100015"]:
                # Barcode SUZUKI
                input_string = self.barcode
                start_index = input_string.find("GA11") + len("GA11")
                end_index = input_string.find("0NG")
                customer_barcode = input_string[start_index:end_index]
                product_translate = {
                    '340': '340',
                    '341': '341',
                    '342': '342',
                    '343': '343',
                    '012': 'YHA-7',
                    '013': 'YHA-8'
                }
                if not isinstance(customer_barcode, float):
                    for false_code, true_code in product_translate.items():
                        customer_barcode = customer_barcode.replace(false_code,true_code)
                product_SUZUKI = self.env['product.product'].search(
                [('default_code', '=', customer_barcode),('customer_id','=', self.partner_id.id)],limit=1)
                if not product_SUZUKI:
                    start_index = input_string.find("GG14") + len("GG14")
                    end_index = input_string.find("0NG")
                    customer_barcode = input_string[start_index:end_index]
                    product_translate = {
                        '340': '340',
                        '341': '341',
                        '342': '342',
                        '343': '343',
                        '012': 'YHA-7',
                        '013': 'YHA-8'
                    }
                    if not isinstance(customer_barcode, float):
                        for false_code, true_code in product_translate.items():
                            customer_barcode = customer_barcode.replace(false_code,true_code)
                    product_SUZUKI = self.env['product.product'].search(
                    [('default_code', '=', customer_barcode),('customer_id','=', self.partner_id.id)],limit=1)
                if product_SUZUKI and self.move_ids_without_package:
                    for line in self.move_ids_without_package:
                        if line.customer_partnumber == product_SUZUKI.customer_partnumber:
                            if line.qty_kanban != line.scanned_kanban:
                                #pokayoke
                                if self.scanned_kanban_customer_header:
                                    warning_mess = {
                                        'title': _('Warning !'),
                                        'message': 
                                        _(warm_sound_code + f'Anda harus memindai barcode ATRAQ product {line.product_id.aid_partnumber} terlebih dahulu !!')
                                    }
                                    return {'warning': warning_mess, 'value': {'barcode': False}}
                                else:
                                    line.scanned_kanban_customer = True
                                    self.scanned_kanban_customer_header = True

                                line.scanned_kanban += 1
                                vals = {}
                                vals['scanned_line'] = [(0,0,{'picking_id': self.id,'move_id': line.id,'product_id': line.product_id.id, 'barcode': self.barcode, 'date_scan': fields.Datetime.now()})]
                                vals['barcode'] = False    
                                line.scanned_kanban_customer = True
                                return {'value': vals}
                            else:
                                warning_mess = {
                                    'title': _('Warning !'),
                                    'message': _(warm_sound_code + f'Qty Kanban dan Scanned Kanban Product {line.product_id.customer_partnumber} Sudah Sesuai.')
                                }
                                return {'warning': warning_mess, 'value': {'barcode': False}}
                        
                else:
                    warning_mess = {
                        'title': _('Warning !'),
                        'message': _(warm_sound_code + f'Customer Barcode ({customer_barcode}) Tidak Ditemukan!!')
                    }
                    return {'warning': warning_mess, 'value': {'barcode': False}}

            elif self.partner_id.ref in ["99100027"]:
                # Barcode HONDA
                customer_barcode = self.barcode.replace("-", "")
                product_honda = self.env['product.product'].search(
                [('customer_partnumber', '=', customer_barcode),('customer_id','=', self.partner_id.id)],limit=1)

                if product_honda and self.move_ids_without_package:
                    for line in self.move_ids_without_package:
                        if line.customer_partnumber == product_honda.customer_partnumber:
                            if line.qty_kanban != line.scanned_kanban:
                                #pokayoke
                                if self.scanned_kanban_customer_header:
                                    warning_mess = {
                                        'title': _('Warning !'),
                                        'message': 
                                        _(warm_sound_code + f'Anda harus memindai barcode ATRAQ product {line.product_id.aid_partnumber} terlebih dahulu !!')
                                    }
                                    return {'warning': warning_mess, 'value': {'barcode': False}}
                                else:
                                    line.scanned_kanban_customer = True
                                    self.scanned_kanban_customer_header = True

                                line.scanned_kanban += 1
                                vals = {}
                                vals['scanned_line'] = [(0,0,{'picking_id': self.id,'move_id': line.id,'product_id': line.product_id.id, 'barcode': self.barcode, 'date_scan': fields.Datetime.now()})]
                                vals['barcode'] = False    
                                line.scanned_kanban_customer = True
                                return {'value': vals}
                            else:
                                warning_mess = {
                                    'title': _('Warning !'),
                                    'message': _(warm_sound_code + f'Qty Kanban dan Scanned Kanban Product {line.product_id.customer_partnumber} Sudah Sesuai.')
                                }
                                return {'warning': warning_mess, 'value': {'barcode': False}}
            
            elif self.partner_id.ref in ["99100008","99100007"]:
                # Barcode Hino
                customer_barcode = self.barcode
                product_translate = {
                    '73210F102000': '73210-F1020-00',
                    '73150F102000': '73150-F1020-00',
                    '73178F101000': '73178-F1010-00',
                    '73240F102000': '73240-F1020-00',
                    '73160E004000': '73160-E0040-00',
                    '73178EW01000': '73178-EW010-00',
                    '73240E027000': '73240-E0270-00',
                    '73240EW01000': '73240-EW010-00',
                    '73210EW010A0': '73210-EW010-A0',
                    '73210EW010B0': '73210-EW010-B0'
                }
                if not isinstance(customer_barcode, float):
                    for false_code, true_code in product_translate.items():
                        customer_barcode = customer_barcode.replace(false_code,true_code)
                product_hino = self.env['product.product'].search(
                [('customer_partnumber', '=', customer_barcode),('customer_id','=', self.partner_id.id)],limit=1)
                if product_hino and self.move_ids_without_package:
                    for line in self.move_ids_without_package:
                        if line.customer_partnumber == product_hino.customer_partnumber:
                            if line.qty_kanban != line.scanned_kanban:
                                #pokayoke
                                if self.scanned_kanban_customer_header:
                                    warning_mess = {
                                        'title': _('Warning !'),
                                        'message': 
                                        _(warm_sound_code + f'Anda harus memindai barcode ATRAQ product {line.product_id.aid_partnumber} terlebih dahulu !!')
                                    }
                                    return {'warning': warning_mess, 'value': {'barcode': False}}
                                else:
                                    line.scanned_kanban_customer = True
                                    self.scanned_kanban_customer_header = True
                                line.scanned_kanban += 1
                                vals = {}
                                vals['scanned_line'] = [(0,0,{'picking_id': self.id,'move_id': line.id,'product_id': line.product_id.id, 'barcode': self.barcode, 'date_scan': fields.Datetime.now()})]
                                vals['barcode'] = False    
                                line.scanned_kanban_customer = True
                                return {'value': vals}
                            else:
                                warning_mess = {
                                    'title': _('Warning !'),
                                    'message': _(warm_sound_code + f'Qty Kanban dan Scanned Kanban Product {line.product_id.customer_partnumber} Sudah Sesuai.')
                                }
                                return {'warning': warning_mess, 'value': {'barcode': False}}

            elif self.partner_id.ref in ["99100042"]:
                # Barcode Fujiseat
                customer_barcode = self.barcode
                product_translate = {
                    '73230-BZE30': '73230-BZE30-C0',
                    '73230-BZE40': '73230-BZE40-C0',
                    '73230-BZE50': '73230-BZE50-C0'
                }
                if not isinstance(customer_barcode, float):
                    for false_code, true_code in product_translate.items():
                        customer_barcode = customer_barcode.replace(false_code,true_code)
                product_fuji = self.env['product.product'].search(
                [('customer_partnumber', '=', customer_barcode),('customer_id','=', self.partner_id.id)],limit=1)
                if product_fuji and self.move_ids_without_package:
                    for line in self.move_ids_without_package:
                        if line.customer_partnumber == product_fuji.customer_partnumber:
                            if line.qty_kanban != line.scanned_kanban:
                                #pokayoke
                                if self.scanned_kanban_customer_header:
                                    warning_mess = {
                                        'title': _('Warning !'),
                                        'message': 
                                        _(warm_sound_code + f'Anda harus memindai barcode ATRAQ product {line.product_id.aid_partnumber} terlebih dahulu !!')
                                    }
                                    return {'warning': warning_mess, 'value': {'barcode': False}}
                                else:
                                    line.scanned_kanban_customer = True
                                    self.scanned_kanban_customer_header = True

                                line.scanned_kanban += 1
                                vals = {}
                                vals['scanned_line'] = [(0,0,{'picking_id': self.id,'move_id': line.id,'product_id': line.product_id.id, 'barcode': self.barcode, 'date_scan': fields.Datetime.now()})]
                                vals['barcode'] = False    
                                line.scanned_kanban_customer = True
                                return {'value': vals}
                            else:
                                warning_mess = {
                                    'title': _('Warning !'),
                                    'message': _(warm_sound_code + f'Qty Kanban dan Scanned Kanban Product {line.product_id.customer_partnumber} Sudah Sesuai.')
                                }
                                return {'warning': warning_mess, 'value': {'barcode': False}}

            elif self.partner_id.ref in ["99100012"]:
                # Barcode Toyota TSUSHO
                barcode = self.barcode
                part = barcode.split('|')
                _logger.info("part")
                _logger.info(part)
                
                customer_barcode = part[3]
                _logger.info(customer_barcode)

                product_translate = {
                    '73330-0K010': '733300K010B',
                    '73350-0K280': '733500K280B',
                    '73380-0K250': '733800K250B',
                    '73530-0K020': '735300K020B',
                    '73540-0K090': '735400K090B',
                    '73580-0K090': '735800K090B',
                    '73580-0K240-C0': '735800K240C0',
                }
                if not isinstance(customer_barcode, float):
                    for false_code, true_code in product_translate.items():
                        customer_barcode = customer_barcode.replace(false_code,true_code)
                product_tb = self.env['product.product'].search(
                [('customer_partnumber', '=', customer_barcode),('customer_id','=', self.partner_id.id)],limit=1)
                if product_tb and self.move_ids_without_package:
                    for line in self.move_ids_without_package:
                        if line.customer_partnumber == product_tb.customer_partnumber:
                            if line.qty_kanban != line.scanned_kanban:
                                #pokayoke
                                if self.scanned_kanban_customer_header:
                                    warning_mess = {
                                        'title': _('Warning !'),
                                        'message': 
                                        _(warm_sound_code + f'Anda harus memindai barcode ATRAQ product {line.product_id.aid_partnumber} terlebih dahulu !!')
                                    }
                                    return {'warning': warning_mess, 'value': {'barcode': False}}
                                else:
                                    line.scanned_kanban_customer = True
                                    self.scanned_kanban_customer_header = True

                                line.scanned_kanban += 1
                                vals = {}
                                vals['scanned_line'] = [(0,0,{'picking_id': self.id,'move_id': line.id,'product_id': line.product_id.id, 'barcode': self.barcode, 'date_scan': fields.Datetime.now()})]
                                vals['barcode'] = False    
                                line.scanned_kanban_customer = True
                                return {'value': vals}
                            else:
                                warning_mess = {
                                    'title': _('Warning !'),
                                    'message': _(warm_sound_code + f'Qty Kanban dan Scanned Kanban Product {line.product_id.customer_partnumber} Sudah Sesuai.')
                                }
                                return {'warning': warning_mess, 'value': {'barcode': False}}

            elif self.partner_id.ref in ["99100025"]:
                # Barcode TS Tech
                aid_barcode = self.barcode
                product_ts = self.env['product.product'].search(
                [('aid_partnumber', '=', aid_barcode),('customer_id','=', self.partner_id.id)],limit=1)
                if product_ts and self.move_ids_without_package:
                    for line in self.move_ids_without_package:
                        if line.aid_partnumber == product_ts.aid_partnumber:
                            if line.qty_kanban != line.scanned_kanban:
                                #pokayoke
                                if self.scanned_kanban_customer_header:
                                    warning_mess = {
                                        'title': _('Warning !'),
                                        'message': 
                                        _(warm_sound_code + f'Anda harus memindai barcode ATRAQ product {line.product_id.aid_partnumber} terlebih dahulu !!')
                                    }
                                    return {'warning': warning_mess, 'value': {'barcode': False}}
                                else:
                                    line.scanned_kanban_customer = True
                                    self.scanned_kanban_customer_header = True

                                line.scanned_kanban += 1
                                vals = {}
                                vals['scanned_line'] = [(0,0,{'picking_id': self.id,'move_id': line.id,'product_id': line.product_id.id, 'barcode': self.barcode, 'date_scan': fields.Datetime.now()})]
                                vals['barcode'] = False    
                                line.scanned_kanban_customer = True
                                return {'value': vals}
                            else:
                                warning_mess = {
                                    'title': _('Warning !'),
                                    'message': _(warm_sound_code + f'Qty Kanban dan Scanned Kanban Product {line.product_id.aid_partnumber} Sudah Sesuai.')
                                }
                                return {'warning': warning_mess, 'value': {'barcode': False}}
                else:
                    warning_mess = {
                        'title': _('Warning !'),
                        'message': _(warm_sound_code + f'Customer Barcode ({aid_barcode}) Tidak Ditemukan!!')
                    }
                    return {'warning': warning_mess, 'value': {'barcode': False}}

            else:
                if self.barcode:
                    warning_mess = {
                        'title': _('Warning !'),
                        'message': _(warm_sound_code + f'Customer Barcode ({self.barcode}) Tidak Ditemukan!!'),
                    }
                    return {'warning': warning_mess, 'value': {'barcode': False}}

        
        
        
        if aid_kanban and not product_id:
            warning_mess = {
                'title': _('Warning !'),
                'message': _(warm_sound_code + 'Barcode AID Kanban Tidak Ditemukan dalam Master Product !!')
            }
            return {'warning': warning_mess, 'value': {'barcode': False}}

        if aid_kanban and self.move_ids_without_package:
            for line in self.move_ids_without_package:
                if line.product_id.aid_partnumber == aid_kanban:
                    if line.scanned:
                        if line.quantity >= line.product_uom_qty:
                            
                            warning_mess = {
                                'title': _('Warning !'),
                                'message': 
                                _(warm_sound_code + f'Demand and Scanned Quantity for product {line.product_id.aid_partnumber} are equal.')
                            }
                            return {'warning': warning_mess, 'value': {'barcode': False}}
                        else:
                            seven_days_ago = fields.Datetime.now() - timedelta(days=7)
                            _logger.info("seven_days_ago")
                            _logger.info(seven_days_ago)
                            scanneds = self.env['pramadya.scan'].search([('barcode', '=', self.barcode),('date_scan', '>=', seven_days_ago)],limit=1)
                            _logger.info(scanneds)
                            if self.barcode in self.scanned_line.mapped('barcode'):
                                warning_mess = {
                                    'title': _('Warning !'),
                                    'message': _(warm_sound_code + 'Barcode Sudah Discan, Silahkan Scan dengan Bercode yang berbeda')
                                }
                                return {'warning': warning_mess, 'value': {'barcode': False}}
                            elif scanneds:
                                warning_mess = {
                                    'title': _('Warning !'),
                                    'message': _(warm_sound_code + 'Barcode Sudah Discan, Silahkan Scan dengan Bercode yang berbeda')
                                }
                                return {'warning': warning_mess, 'value': {'barcode': False}}
                            else:
                                #pokayoke
                                if not line.scanned_kanban_customer:
                                    warning_mess = {
                                        'title': _('Warning !'),
                                        'message': 
                                        _(warm_sound_code + f'Anda harus memindai barcode Customer product {line.product_id.aid_partnumber} terlebih dahulu !!')
                                    }
                                    return {'warning': warning_mess, 'value': {'barcode': False}}
                                else:
                                    line.scanned_kanban_customer = False
                                    self.scanned_kanban_customer_header = False

                                #Penambahan Quantity ketika scan Barcode AID
                                line.quantity += line.product_uom_qty/line.qty_kanban
                                match = True
                                # Send To LOT System
                                if line.product_id.lot == 'lot' and line.product_id.collecting == 0:
                                    lot = self.env['pramadya.lot'].sudo().search([('product_id','=',line.product_id.id),('state', '=', 'draft'),('is_qty_less_than_capacity', '=', True)], limit=1)
                                    if lot:
                                        qty_add = line.product_uom_qty/line.qty_kanban
                                        total_lot = lot.qty + qty_add
                                        
                                        if total_lot < lot.capacity:
                                            lot_details = self.env['pramadya.lot.details'].sudo().create({
                                                'lot_id': lot.id,
                                                'delivery_note': self.name,
                                                'qty': qty_add,
                                                'qty_kanban': 1,
                                                'order_date': self.order_date
                                            })
                                            lot.send_kanban()
                                        else:
                                            sisa = total_lot - lot.capacity
                                            qty_split = qty_add - sisa
                                            if qty_split > 0:
                                                lot_details = self.env['pramadya.lot.details'].sudo().create({
                                                    'lot_id': lot.id,
                                                    'delivery_note': self.name,
                                                    'qty': qty_split,
                                                    'qty_kanban': qty_split/qty_add,
                                                    'order_date': self.order_date
                                                })
                                            lot.send_kanban()
                                            new_lot_id = self.env['pramadya.lot'].sudo().create({
                                                'product_id': line.product_id.id,
                                                'line_id': line.product_id.primary_line_id.id,
                                                'capacity': line.product_id.lot_size,
                                                'schedule_date': self.order_date
                                            })
                                            lot_details = self.env['pramadya.lot.details'].sudo().create({
                                                'lot_id': new_lot_id.id,
                                                'delivery_note': self.name,
                                                'qty': sisa,
                                                'qty_kanban': sisa/qty_add,
                                                'order_date': self.order_date
                                            })
                                    else:
                                        new_lot_id = self.env['pramadya.lot'].sudo().create({
                                            'product_id': line.product_id.id,
                                            'line_id': line.product_id.primary_line_id.id,
                                            'capacity': line.product_id.lot_size,
                                            'schedule_date': self.order_date
                                        })
                                        lot_details = self.env['pramadya.lot.details'].sudo().create({
                                            'lot_id': new_lot_id.id,
                                            'delivery_note': self.name,
                                            'qty': qty_add,
                                            'qty_kanban': 1,
                                            'order_date': self.order_date
                                        })

                                if line.product_id.lot == 'lot' and line.product_id.collecting != 0:
                                    qty_add = line.product_uom_qty/line.qty_kanban
                                    collecting = self.env['collecting'].sudo().search([('product_id','=',line.product_id.id),('state', '=', 'draft')], limit=1)
                                    if collecting:
                                        collecting_details = self.env['collecting.line'].sudo().create({
                                            'collecting_id': collecting.id,
                                            'delivery_note': self.name,
                                            'qty': qty_add,
                                            'qty_kanban': 1,
                                            'picking_date': self.order_date
                                        })
                                    else:
                                        now = datetime.now()
                                        start_time = datetime.combine(now.date(), time(8, 0, 0))
                                        end_time = datetime.combine(now.date(), time(7, 59, 59)) + timedelta(days=1)
                                        _logger.info("start_time")
                                        _logger.info(now)
                                        _logger.info(start_time)
                                        _logger.info(end_time)
                                        new_collecting_id = self.env['collecting'].sudo().create({
                                            'product_id': line.product_id.id,
                                            'line_id': line.product_id.primary_line_id.id,
                                            'start_date': start_time - timedelta(hours=7),
                                            'end_date': end_time - timedelta(hours=7),
                                        }) 
                                        collecting_details = self.env['collecting.line'].sudo().create({
                                            'collecting_id': new_collecting_id.id,
                                            'delivery_note': self.name ,
                                            'qty': qty_add,
                                            'qty_kanban': 1,
                                            'picking_date': self.order_date
                                        })

                                # Add Record Barcode
                                vals = {}
                                vals['scanned_line'] = [(0,0,{'picking_id': self.id,'move_id': line.id,'product_id': line.product_id.id, 'barcode': self.barcode, 'date_scan': fields.Datetime.now()})]
                                vals['barcode'] = False    
                                return {'value': vals}

                    else:
                        seven_days_ago = fields.Datetime.now() - timedelta(days=7)
                        _logger.info("seven_days_ago")
                        _logger.info(seven_days_ago)
                        scanneds = self.env['pramadya.scan'].search([('barcode', '=', self.barcode),('date_scan', '>=', seven_days_ago)],limit=1)
                        _logger.info(scanneds)
                        if self.barcode in self.scanned_line.mapped('barcode'):
                                warning_mess = {
                                    'title': _('Warning !'),
                                    'message': _(warm_sound_code + 'Barcode Sudah Discan, Silahkan Scan dengan Bercode yang berbeda')
                                }
                                return {'warning': warning_mess, 'value': {'barcode': False}}
                        elif scanneds:
                            warning_mess = {
                                'title': _('Warning !'),
                                'message': _(warm_sound_code + 'Barcode Sudah Discan, Silahkan Scan dengan Bercode yang berbeda')
                            }
                            return {'warning': warning_mess, 'value': {'barcode': False}}
                        else:
                            #pokayoke
                            if not line.scanned_kanban_customer:
                                warning_mess = {
                                    'title': _('Warning !'),
                                    'message': 
                                    _(warm_sound_code + f'Anda harus memindai barcode Customer product {line.product_id.aid_partnumber} terlebih dahulu !!')
                                }
                                return {'warning': warning_mess, 'value': {'barcode': False}}
                            else:
                                line.scanned_kanban_customer = False
                                self.scanned_kanban_customer_header = False

                            # Penambahan Quantity ketika scan Barcode AID dari 0
                            if line.qty_kanban == 0:
                                warning_mess = {
                                    'title': _('Warning !'),
                                    'message': _(warm_sound_code + f'Total Kanban {line.product_id.customer_partnumber} Tidak Boleh kosong !!')
                                }
                                return {'warning': warning_mess, 'value': {'barcode': False}}
                            qty_add = line.product_uom_qty/line.qty_kanban 
                            line.quantity = qty_add
                            line.scanned = True
                            match = True

                            # Send To LOT System
                            if line.product_id.lot == 'lot' and line.product_id.collecting == 0:
                                lot = self.env['pramadya.lot'].sudo().search([('product_id','=',line.product_id.id),('state', '=', 'draft'),('is_qty_less_than_capacity', '=', True)], limit=1)
                                if lot:
                                    total_lot = lot.qty + qty_add
                                    
                                    if total_lot < lot.capacity:
                                        lot_details = self.env['pramadya.lot.details'].sudo().create({
                                            'lot_id': lot.id,
                                            'delivery_note': self.name,
                                            'qty': qty_add,
                                            'qty_kanban': 1,
                                            'order_date': self.order_date
                                        })
                                        lot.send_kanban()
                                    else:
                                        sisa = total_lot - lot.capacity
                                        qty_split = qty_add - sisa
                                        if qty_split > 0:
                                            lot_details = self.env['pramadya.lot.details'].sudo().create({
                                                'lot_id': lot.id,
                                                'delivery_note': self.name,
                                                'qty': qty_split,
                                                'order_date': self.order_date
                                            })
                                        lot.send_kanban()
                                        new_lot_id = self.env['pramadya.lot'].sudo().create({
                                            'product_id': line.product_id.id,
                                            'line_id': line.product_id.primary_line_id.id,
                                            'capacity': line.product_id.lot_size,
                                            'schedule_date': self.order_date
                                        })
                                        lot_details = self.env['pramadya.lot.details'].sudo().create({
                                            'lot_id': new_lot_id.id,
                                            'delivery_note': self.name,
                                            'qty': sisa,
                                            'order_date': self.order_date
                                        })
                                else:
                                    new_lot_id = self.env['pramadya.lot'].sudo().create({
                                        'product_id': line.product_id.id,
                                        'line_id': line.product_id.primary_line_id.id,
                                        'capacity': line.product_id.lot_size,
                                        'schedule_date': self.order_date
                                    })
                                    lot_details = self.env['pramadya.lot.details'].sudo().create({
                                        'lot_id': new_lot_id.id,
                                        'delivery_note': self.name,
                                        'qty': qty_add,
                                        'qty_kanban': 1,
                                        'order_date': self.order_date
                                    })
                                    new_lot_id.send_kanban()
                            
                            if line.product_id.lot == 'lot' and line.product_id.collecting != 0:
                                collecting = self.env['collecting'].sudo().search([('product_id','=',line.product_id.id),('state', '=', 'draft')], limit=1)
                                if collecting:
                                    collecting_details = self.env['collecting.line'].sudo().create({
                                        'collecting_id': collecting.id,
                                        'delivery_note': self.name,
                                        'qty': qty_add,
                                        'qty_kanban': 1,
                                        'picking_date': self.order_date
                                    })
                                else:
                                    now = datetime.now()
                                    start_time = datetime.combine(now.date(), time(8, 0, 0))
                                    end_time = datetime.combine(now.date(), time(7, 59, 59)) + timedelta(days=1)
                                    new_collecting_id = self.env['collecting'].sudo().create({
                                        'product_id': line.product_id.id,
                                        'line_id': line.product_id.primary_line_id.id,
                                        'start_date': start_time - timedelta(hours=7),
                                        'end_date': end_time - timedelta(hours=7),
                                    }) 
                                    collecting_details = self.env['collecting.line'].sudo().create({
                                        'collecting_id': new_collecting_id.id,
                                        'delivery_note': self.name ,
                                        'qty': qty_add,
                                        'qty_kanban': 1,
                                        'picking_date': self.order_date
                                    })
                            # Add Record Barcode    
                            vals = {}
                            vals['scanned_line'] = [(0,0,{'picking_id': self.id,'move_id': line.id,'product_id': line.product_id.id, 'barcode': self.barcode, 'date_scan': fields.Datetime.now()})]
                            vals['barcode'] = False  
                            return {'value': vals}


        if aid_kanban and not match:
            if product_id:
                warning_mess = {
                    'title': _('Warning !'),
                    'message': _(warm_sound_code + f'Hasil Scan [{self.barcode} ] product tidak ditemukan dalam Manifest/DN.')
                }
                return {'warning': warning_mess, 'value': {'barcode': False}}
                
        self.barcode = False 

    def _compute_total_kanban(self):
        for picking in self:
            total = 0.0
            for move in picking.move_ids_without_package:
                total += move.qty_kanban
            picking.qty_kanban = total

    def action_confirm(self):
        res = super(StockPicking, self).action_confirm()
        self.status_pickup = 'palleting'
        return res

    def action_ready(self):
        for picking in self:
            for items in picking.move_ids_without_package:
                if items.product_uom_qty != items.quantity:
                    if items.missing_kanban > 0:
                        qty_package = 1
                        for p in items.product_id:
                            if p.packaging_ids:
                                qty_package = p.packaging_ids[0].qty
                        qty_missing = items.missing_kanban * qty_package
                        items.quantity += qty_missing

                        if items.product_id.lot == 'lot' and items.product_id.collecting == 0:
                            lot = self.env['pramadya.lot'].sudo().search([('product_id','=',items.product_id.id),('state', '=', 'draft'),('is_qty_less_than_capacity', '=', True)], limit=1)
                            if lot:
                                total = qty_missing + lot.qty
                                if total > lot.capacity:
                                    new_qty = total - lot.capacity
                                    new_lot = self.env['pramadya.lot'].sudo().create({
                                            'product_id'    : items.product_id.id,
                                            'line_id'       : items.product_id.primary_line_id.id,
                                            'capacity'      : items.product_id.lot_size,
                                            'schedule_date' : fields.Datetime.now(),
                                            })
                                    lot_details = self.env['pramadya.lot.details'].sudo().create({
                                            'lot_id'        : new_lot.id,
                                            'delivery_note' : picking.name + " Missing Items",
                                            'qty'           : new_qty,
                                            'order_date'    : fields.Datetime.now(),
                                            })
                                    lot_exsis = self.env['pramadya.lot.details'].sudo().create({
                                            'lot_id'        : lot.id,
                                            'delivery_note' : picking.name + " Missing Items",
                                            'qty'           : qty_missing - new_qty,
                                            'order_date'    : fields.Datetime.now(),
                                            })
                                    lot.send_kanban()
                                    new_lot.send_kanban()
                                else:
                                    lot_details = self.env['pramadya.lot.details'].sudo().create({
                                            'lot_id': lot.id,
                                            'delivery_note': picking.name + " Missing Items",
                                            'qty': qty_missing,
                                            'qty_kanban': items.missing_kanban,
                                            'order_date': picking.order_date
                                        })
                                    lot.send_kanban()
                            else:
                                new_lot_id = self.env['pramadya.lot'].sudo().create({
                                    'product_id': items.product_id.id,
                                    'line_id': items.product_id.primary_line_id.id,
                                    'capacity': items.product_id.lot_size,
                                    'schedule_date': picking.order_date
                                })
                                lot_details = self.env['pramadya.lot.details'].sudo().create({
                                    'lot_id': new_lot_id.id,
                                    'delivery_note': picking.name + " Missing Items",
                                    'qty': qty_missing,
                                    'qty_kanban': items.missing_kanban,
                                    'order_date': picking.order_date
                                })
                                new_lot_id.send_kanban()

                        if items.product_id.lot == 'lot' and items.product_id.collecting != 0:
                            collecting = self.env['collecting'].sudo().search([('product_id','=',items.product_id.id),('state', '=', 'draft')], limit=1)
                            if collecting:
                                collecting_details = self.env['collecting.line'].sudo().create({
                                    'collecting_id': collecting.id,
                                    'delivery_note': picking.name + " Missing Items",
                                    'qty': qty_missing,
                                    'qty_kanban': items.missing_kanban,
                                    'picking_date': picking.order_date
                                })
                            else:
                                now = datetime.now()
                                start_time = datetime.combine(now.date(), time(8, 0, 0))
                                end_time = start_time + timedelta(hours=8)
                                new_collecting_id = self.env['collecting'].sudo().create({
                                    'product_id': items.product_id.id,
                                    'line_id': items.product_id.primary_line_id.id,
                                    'start_date': start_time - timedelta(hours=7),
                                    'end_date': end_time - timedelta(hours=7),
                                }) 
                                collecting_details = self.env['collecting.line'].sudo().create({
                                    'collecting_id': new_collecting_id.id,
                                    'delivery_note': picking.name + " Missing Items",
                                    'qty': qty_missing,
                                    'qty_kanban': items.missing_kanban,
                                    'picking_date': picking.order_date
                                })
                    else:
                        print("kalau missing kanban ada isi")
                        message = _("Hasil Scan Kanban Belum Lengkap !!")
                        return {
                                'type': 'ir.actions.client',
                                'tag': 'display_notification',
                                'params': {
                                    'message': message,
                                    'type': 'danger',
                                    'sticky': False,
                                }
                            }
        self.status_pickup = 'ready'
        current_date = fields.Datetime.now()
        self.order_ready = current_date
        time_difference = current_date - self.pickup_date
        if time_difference > timedelta(days=2):
            self.result = 'delay'
        self.button_validate()

    def action_assign(self):
        """Prevent auto-reservation of stock by overriding this method."""
        return True  # Simply do nothing when 'Check Availability' is clicked
        
    @api.onchange('partner_id')
    def _get_total_kanban(self):
        for x in self:
            if x.partner_id:
                partner_name = ['DCC_WH','SUZUKI INDOMOBIL MOTOR PT_SIM','PT. MMKI','PT. MMKI_']
                if x.partner_id.name in partner_name:
                    for sm in x.move_ids_without_package:
                        sm._get_total_kanban()

class StockMove(models.Model):
    _inherit = ['stock.move']

    missing_kanban = fields.Float(string="Missing Kanban",digits='Product Unit of Measure')
    scanned_kanban = fields.Float(string="Scan Kanban",digits='Product Unit of Measure')
    qty_kanban = fields.Float(string="Total Kanban",digits='Product Unit of Measure')
    customer_partnumber = fields.Char(related='product_id.customer_partnumber')
    aid_partnumber = fields.Char(related='product_id.aid_partnumber')
    scanned = fields.Boolean()
    pickup_date = fields.Datetime(related='picking_id.pickup_date')
    scanned_kanban_customer = fields.Boolean(default=False)

    # @api.onchange('missing_kanban')
    # def _compute_missing(self):
    #     for move in self:
    #         if move.missing_kanban > 0:
    #             move.scanned_kanban = move.scanned_kanban + move.missing_kanban

    @api.onchange('product_uom_qty')
    def _get_total_kanban(self):
        for x in self:
            qty_package = 1
            if x.product_id:
                for p in x.product_id:
                    if p.packaging_ids:
                        qty_package = p.packaging_ids[0].qty
                total_kanban = x.product_uom_qty / qty_package
                x.qty_kanban = total_kanban
    
    def _merge_moves_fields(self):
        """ This method will return a dict of stock move’s values that represent the values of all moves in `self` merged. """
        merge_extra = self.env.context.get('merge_extra')
        state = self._get_relevant_state_among_moves()
        origin = '/'.join(set(self.filtered(lambda m: m.origin).mapped('origin')))
        return {
            'product_uom_qty': sum(self.mapped('product_uom_qty')) if not merge_extra else self[0].product_uom_qty,
            'qty_kanban': sum(self.mapped('qty_kanban')) if not merge_extra else self[0].qty_kanban,
            'date': min(self.mapped('date')) if all(p.move_type == 'direct' for p in self.picking_id) else max(self.mapped('date')),
            'move_dest_ids': [(4, m.id) for m in self.mapped('move_dest_ids')],
            'move_orig_ids': [(4, m.id) for m in self.mapped('move_orig_ids')],
            'state': state,
            'origin': origin,
        }

class StockScanned(models.Model):
    _name = 'pramadya.scan'
    _description = 'Detail Hasil Scan'

    picking_id = fields.Many2one('stock.picking', ondelete='cascade')
    move_id = fields.Many2one('stock.move')
    product_id = fields.Many2one('product.product')
    qty = fields.Float()
    pack = fields.Char(compute='_cari_pack')
    batch = fields.Char(compute='_cari_batch')
    aid_partnumber = fields.Char(related='product_id.aid_partnumber', string='AID Part Number')
    barcode = fields.Char()
    date_scan = fields.Datetime()

    def _cari_batch(self):
        for data in self:
            data_batch = False
            if data.barcode:
                pattern_pack = r'S(\d+)P' # pattern S
                pattern_batch = r'H(\d+)5D' # pattern H 
                re_batch = re.search(pattern_batch, str(data.barcode))
                if re_batch:
                    data_batch = re_batch.group(1)
            
            data.batch = data_batch

    def _cari_pack(self):
        for data in self:
            data_pack = False
            if data.barcode:
                pattern_pack = r'S(\d+)P' # pattern S
                re_pack = re.search(pattern_pack, str(data.barcode))
                if re_pack:
                    data_pack = re_pack.group(1)
            
            data.pack = data_pack

                

class WorkflowActionRuleAccount(models.Model):
    _inherit = ['documents.workflow.rule']

    create_model = fields.Selection(selection_add=[('stock.picking', "Delivery Orders")])

    def set_java_environment(self, java_home):
        # Set JAVA_HOME environment variable
        os.environ['JAVA_HOME'] = java_home

        # Update PATH to include the bin directory of Java
        os.environ['PATH'] = os.path.join(java_home, 'bin') + os.pathsep + os.environ['PATH']

    def create_record(self, documents=None):
        rv = super(WorkflowActionRuleAccount, self).create_record(documents=documents)
        if self.create_model.startswith('stock.picking'):
            move = None
            delivery_ids = []
            for document in documents:
                partner = self.partner_id or document.partner_id
                if document.res_model == 'pramadya.shipping' and document.res_id:
                    move = self.env['pramadya.shipping'].browse(document.res_id)
                else:
                    if document.res_model == 'stock.picking' and document.res_id:
                        move = self.env['stock.picking'].browse(document.res_id)
                    else:
                        user = self.env.user
                        default_warehouse = self.env['stock.warehouse'].search(self.env['stock.warehouse']._check_company_domain(self.env.company), limit=1)
                        default_customer_location = user.partner_id.property_stock_customer
                        # If the user doesn't have a default warehouse, you may want to set a default value or handle it accordingly
                        if not default_warehouse:
                            default_warehouse = self.env['stock.warehouse'].search([], limit=1)


                        # If the user doesn't have a default customer location, you may want to set a default value or handle it accordingly
                        if not default_customer_location:
                            default_customer_location = self.env['res.partner'].search([], limit=1).property_stock_customer
                        delivery_picking_type = self.env['stock.picking.type'].search([
                            ('warehouse_id', '=', default_warehouse.id),
                            ('code', '=', 'outgoing'),
                        ], limit=1)
                        attachment = document.attachment_id.id

                        #OCR
                        # set_java_environment
                        java_portable_path = '/home/odoo/data/jdk8u392-b08-jre/'
                        self.set_java_environment(java_portable_path)
                        _logger.info(os.system('java -version'))
                        
                        with io.BytesIO(base64.b64decode(document.attachment_id.datas)) as pdf_file:
                            nomor_dn = False
                            cycle = 0
                            date_order_object = False
                            combined_datetime = False
                            if partner:
                                if partner.ref in ["99100003","99100004","99100005"]:

                                    #Get No DN TMMIN
                                    data = tabula.read_pdf(pdf_file, pages='all',output_format="json", area=[100.20,46.80,113.28,152.40])
                                    nomor_dn = data[0]['data'][0][0]['text']

                                    #Get Cycle TMMIN
                                    data_cycle = tabula.read_pdf(pdf_file, pages='all',output_format="json", area=[205.80,82.20,230.40,100])
                                    cycle = data_cycle[0]['data'][0][0]['text']

                                    #date Order TMMIN
                                    data_date_order = tabula.read_pdf(pdf_file, pages='all',output_format="json", area=[675.00,36.00,686.40,82.20])
                                    date_order = data_date_order[0]['data'][0][0]['text']
                                    if date_order:
                                        date_order_object = datetime.strptime(date_order, "%d.%m.%Y")

                                    #date Pickup TMMIN
                                    data_date_pickup = tabula.read_pdf(pdf_file, pages='all',output_format="json", area=[203.40,102.60,222.00,162.60])
                                    date_pickup = data_date_pickup[0]['data'][0][0]['text']
                                    if date_pickup:
                                        date_pickup_object = datetime.strptime(date_pickup, "%d/%m/%Y")

                                    #time pickup TMMIN
                                    data_timepickup = tabula.read_pdf(pdf_file, pages='all',output_format="json", area=[219.00,102.60,240.00,162.60])
                                    time_pickup = data_timepickup[0]['data'][0][0]['text']
                                    if time_pickup:
                                        time_object = datetime.strptime(time_pickup, "%H:%M").time()

                                        # Combine date and time TMMIN
                                        combined_datetime = datetime.combine(date_pickup_object, time_object)

                                    #Picking
                                    move = self.env['stock.picking'].create({
                                        'name': nomor_dn or "/",
                                        'cycle': int(cycle),
                                        'order_date': date_order_object or "",
                                        'pickup_date': combined_datetime - timedelta(hours=7) or fields.Datetime.now(),
                                        'start_pull': combined_datetime - timedelta(hours=16) or fields.Datetime.now(),
                                        'end_pull': combined_datetime - timedelta(hours=15) or fields.Datetime.now(),
                                        'location_id': default_warehouse.lot_stock_id.id,
                                        'location_dest_id': default_customer_location.id,
                                        'picking_type_id': delivery_picking_type.id,
                                    })

                                    #Get Order TMMIN
                                    orders = tabula.read_pdf(pdf_file, pages='all', stream=True, multiple_tables=True, area=[244.20,36.60,652.00,608.40])
                                    for idx, df in enumerate(orders):
                                        table_data = df.values.tolist()
                                        # _logger.info("table_data")
                                        # _logger.info(table_data)
                                        for inner_list in table_data:
                                            # _logger.info("details order")
                                            # _logger.info(inner_list[3])
                                            # _logger.info(inner_list[6])
                                            # _logger.info(inner_list[7])
                                            # Stock Move
                                            product_id = self.env['product.product'].search([('default_code','=', inner_list[3])])
                                            if product_id:
                                                stock_move = self.env['stock.move'].create({
                                                    'name': product_id.name,
                                                    'product_id': product_id.id,
                                                    'product_uom': product_id.uom_id.id,
                                                    'product_uom_qty': float(inner_list[7]),
                                                    'qty_kanban': float(inner_list[6]),
                                                    'procure_method': 'make_to_stock',
                                                    'picking_id': move.id,
                                                    'date': combined_datetime - timedelta(hours=7) or fields.Datetime.now(),
                                                    'location_id': default_warehouse.lot_stock_id.id,
                                                    'location_dest_id': default_customer_location.id,
                                                    'company_id': self.env.company.id
                                                })                                        

                                elif partner.ref in ["99100015"]:

                                    #Get No DN Suzuki
                                    data = tabula.read_pdf(pdf_file, pages='all', output_format="json", area=[187.95,33.39,209.4,170.35])
                                    nomor_dn = data[0]['data'][0][0]['text']

                                    #Get Cycle Suzuki
                                    # data_cycle = tabula.read_pdf(pdf_file, pages='all', output_format="json", area=[200,80,260,110])
                                    # cycle = data_cycle[0]['data'][0][0]['text']
                                    cycle = '1'

                                    #date Order
                                    data_date_order = tabula.read_pdf(pdf_file, pages='all', output_format="json", area=[49.04,369.22,60.67,414.25])
                                    date_order = data_date_order[0]['data'][0][0]['text']
                                    if date_order:
                                        date_order_object = datetime.strptime(date_order, "%d/%m/%Y")

                                    #date Pickup Suzuki
                                    data_date_pickup = tabula.read_pdf(pdf_file, pages='all', output_format="json", area=[104.59,98.56,116.52,142.58])
                                    date_pickup = data_date_pickup[0]['data'][0][0]['text']
                                    if date_pickup:
                                        date_pickup_object = datetime.strptime(date_pickup, "%d/%m/%Y")

                                    #time pickup Suzuki
                                    data_timepickup = tabula.read_pdf(pdf_file, pages='all', output_format="json", area=[116.60,100.56,128.24,124.07])
                                    time_pickup = data_timepickup[0]['data'][0][0]['text']
                                    if time_pickup:
                                        time_object = datetime.strptime(time_pickup, "%H:%M").time()

                                        # Combine date and time Suzuki
                                        combined_datetime = datetime.combine(date_pickup_object, time_object)

                                    #Picking
                                    move = self.env['stock.picking'].create({
                                        'name': nomor_dn.replace(" ", "") or "/",
                                        'cycle': int(cycle),
                                        'order_date': date_order_object or "",
                                        'pickup_date': combined_datetime - timedelta(hours=7) or fields.Datetime.now(),
                                        'start_pull': combined_datetime - timedelta(hours=16) or fields.Datetime.now(),
                                        'end_pull': combined_datetime - timedelta(hours=15) or fields.Datetime.now(),
                                        'location_id': default_warehouse.lot_stock_id.id,
                                        'location_dest_id': default_customer_location.id,
                                        'picking_type_id': delivery_picking_type.id,
                                    })

                                    #Get Order Suzuki
                                    orders = tabula.read_pdf(pdf_file, pages='all', stream=True, multiple_tables=True, area=[216.18,16.01,486.76,425.75])
                                    for idx, df in enumerate(orders):
                                        table_data = df.values.tolist()
                                        for inner_list in table_data:
                                            # Stock Move
                                            _logger.info("SUZUKI Produk")
                                            _logger.info(inner_list[1])
                                            _logger.info(inner_list[1][:15])
                                            _logger.info(inner_list[4])
                                            _logger.info(inner_list[5])
                                            product_id = self.env['product.product'].search([('customer_partnumber','=', inner_list[1][:15])],limit=1)
                                            if product_id:
                                                qty_package = 1
                                                for p in product_id:
                                                    if p.packaging_ids:
                                                        qty_package = p.packaging_ids[0].qty
                                                if math.isnan(inner_list[4]):
                                                    if math.isnan(inner_list[5]):
                                                        qty = 0.0
                                                    else:
                                                        qty = inner_list[5]
                                                else:
                                                    qty = inner_list[4]
                                                total_kanban = float(qty) / float(qty_package)
                                                stock_move = self.env['stock.move'].create({
                                                    'name': product_id.name,
                                                    'product_id': product_id.id,
                                                    'product_uom': product_id.uom_id.id,
                                                    'product_uom_qty': float(qty),
                                                    'qty_kanban': total_kanban,
                                                    'procure_method': 'make_to_stock',
                                                    'picking_id': move.id,
                                                    'date': combined_datetime - timedelta(hours=7) or fields.Datetime.now(),
                                                    'location_id': default_warehouse.lot_stock_id.id,
                                                    'location_dest_id': default_customer_location.id,
                                                    'company_id': self.env.company.id
                                                })
                                            
                                elif partner.ref in ["99100040"]:

                                    #Get No DN ADM
                                    data = tabula.read_pdf(pdf_file, pages='all', output_format="json", area=[128.57,666.14,140,760])
                                    nomor_dn = data[0]['data'][0][0]['text']


                                    #Get Cycle ADM
                                    data_cycle = tabula.read_pdf(pdf_file, pages='all', output_format="json", area=[130,411,150,421])
                                    cycle = data_cycle[0]['data'][0][0]['text']

                                    #date Order ADM
                                    data_date_order = tabula.read_pdf(pdf_file, pages='all', output_format="json", area=[113,118,133,190])
                                    date_order = data_date_order[0]['data'][0][0]['text']
                                    if date_order:
                                        date_order_object = datetime.strptime(date_order, "%d-%b-%Y")

                                    #date pickup ADM
                                    data_pickup = tabula.read_pdf(pdf_file, pages='all', output_format="json", area=[126,366,144,422])
                                    date_pickup = data_pickup[0]['data'][0][0]['text']
                                    if date_pickup:
                                        date_pickup_object = datetime.strptime(date_pickup, "%d-%b-%Y")

                                    #time pickup ADM
                                    data_timepickup = tabula.read_pdf(pdf_file, pages='all', output_format="json", area=[130,366,155,410])
                                    time_pickup = data_timepickup[0]['data'][0][0]['text']
                                    if time_pickup:
                                        time_object = datetime.strptime(time_pickup, "%H:%M:%S").time()

                                        # Combine date and time
                                        combined_datetime = datetime.combine(date_pickup_object, time_object)

                                    #Picking
                                    move = self.env['stock.picking'].create({
                                        'name': nomor_dn or "/",
                                        'cycle': int(cycle),
                                        'order_date': date_order_object or "",
                                        'pickup_date': combined_datetime - timedelta(hours=7) or fields.Datetime.now(),
                                        'start_pull': combined_datetime - timedelta(hours=16) or fields.Datetime.now(),
                                        'end_pull': combined_datetime - timedelta(hours=15) or fields.Datetime.now(),
                                        'location_id': default_warehouse.lot_stock_id.id,
                                        'location_dest_id': default_customer_location.id,
                                        'picking_type_id': delivery_picking_type.id,
                                    })

                                    #Get Orders ADM
                                    orders = tabula.read_pdf(pdf_file, pages='all', multiple_tables=True, area=[180,26,350,540])
                                    for idx, df in enumerate(orders):
                                        table_data = df.values.tolist()
                                        for inner_list in table_data:
                                            # Stock Move ADM
                                            product_id = self.env['product.product'].search([('default_code','=', inner_list[2])])
                                            stock_move = self.env['stock.move'].create({
                                                'name': product_id.name,
                                                'product_id': product_id.id,
                                                'product_uom': product_id.uom_id.id,
                                                'product_uom_qty': float(inner_list[6]),
                                                'qty_kanban': float(inner_list[5]),
                                                'procure_method': 'make_to_stock',
                                                'picking_id': move.id,
                                                'date': combined_datetime - timedelta(hours=7) or fields.Datetime.now(),
                                                'location_id': default_warehouse.lot_stock_id.id,
                                                'location_dest_id': default_customer_location.id,
                                                'company_id': self.env.company.id
                                        })
                                
                                elif partner.ref in ["99100058"]:

                                    #Get No DN HYUNDAI
                                    data = tabula.read_pdf(pdf_file, pages='all', output_format="json", area=[515.00,315.40,530.00,479.60])
                                    nomor_dn = data[0]['data'][0][0]['text']


                                    #Get Cycle HYUNDAI
                                    data_cycle = tabula.read_pdf(pdf_file, pages='all', output_format="json", area=[72.06,684.18,85.50,697.57])
                                    cycle = data_cycle[0]['data'][0][0]['text']

                                    #date Order HYUNDAI
                                    data_date_order = tabula.read_pdf(pdf_file, pages='all', output_format="json", area=[117.96,711.47,131.25,758.44])
                                    date_order = data_date_order[0]['data'][0][0]['text']
                                    if date_order:
                                        date_order_object = datetime.strptime(date_order, "%d.%m.%Y")

                                    #date pickup HYUNDAI
                                    data_pickup = tabula.read_pdf(pdf_file, pages='all', output_format="json", area=[117.96,398.70,132.75,445.67])
                                    date_pickup = data_pickup[0]['data'][0][0]['text']
                                    if date_pickup:
                                        date_pickup_object = datetime.strptime(date_pickup, "%d.%m.%Y")

                                    #time pickup HYUNDAI
                                    data_timepickup = tabula.read_pdf(pdf_file, pages='all', output_format="json", area=[117.96,445.14,132.75,471.82])
                                    time_pickup = data_timepickup[0]['data'][0][0]['text']
                                    if time_pickup:
                                        time_object = datetime.strptime(time_pickup, "%H:%M").time()

                                        # Combine date and time
                                        combined_datetime = datetime.combine(date_pickup_object, time_object)

                                    #Picking
                                    move = self.env['stock.picking'].create({
                                        'name': nomor_dn or "/",
                                        'cycle': int(cycle),
                                        'order_date': date_order_object or "",
                                        'pickup_date': combined_datetime - timedelta(hours=7) or fields.Datetime.now(),
                                        'start_pull': combined_datetime - timedelta(hours=16) or fields.Datetime.now(),
                                        'end_pull': combined_datetime - timedelta(hours=15) or fields.Datetime.now(),
                                        'location_id': default_warehouse.lot_stock_id.id,
                                        'location_dest_id': default_customer_location.id,
                                        'picking_type_id': delivery_picking_type.id,
                                    })

                                    #Get Orders HYUNDAI
                                    orders = tabula.read_pdf(pdf_file, pages='all', multiple_tables=True, area=[138.38,37.90,435.00,755.73])
                                    for idx, df in enumerate(orders):
                                        table_data = df.values.tolist()
                                        for inner_list in table_data:
                                            # Stock Move HYUNDAI
                                            product_id = self.env['product.product'].search([('customer_partnumber','=', inner_list[1])],limit=1)
                                            if product_id:
                                                stock_move = self.env['stock.move'].create({
                                                        'name': product_id.name,
                                                        'product_id': product_id.id,
                                                        'product_uom': product_id.uom_id.id,
                                                        'product_uom_qty': float(inner_list[5]),
                                                        'qty_kanban': float(inner_list[4]),
                                                        'procure_method': 'make_to_stock',
                                                        'picking_id': move.id,
                                                        'date': combined_datetime - timedelta(hours=7) or fields.Datetime.now(),
                                                        'location_id': default_warehouse.lot_stock_id.id,
                                                        'location_dest_id': default_customer_location.id,
                                                        'company_id': self.env.company.id
                                                })
                                
                                elif partner.ref in ["99100999"]:

                                    #Get No DN HYUNDAI CKD
                                    data = tabula.read_pdf(pdf_file, pages='all', output_format="json", area=[514.2,308.7,534.6,484.1])
                                    nomor_dn = data[0]['data'][0][0]['text']


                                    #Get Cycle HYUNDAI
                                    # data_cycle = tabula.read_pdf(pdf_file, pages='all', output_format="json", area=[72.06,684.18,85.50,697.57])
                                    # cycle = data_cycle[0]['data'][0][0]['text']

                                    #date Order HYUNDAI CKD
                                    data_date_order = tabula.read_pdf(pdf_file, pages='all', output_format="json", area=[98.4,652.85,121.2,717.1])
                                    date_order = data_date_order[0]['data'][0][0]['text']
                                    if date_order:
                                        date_order_object = datetime.strptime(date_order, "%d.%m.%Y")

                                    #date pickup HYUNDAI CKD
                                    data_pickup = tabula.read_pdf(pdf_file, pages='all', output_format="json", area=[98.4,551.95,121.2,617.4])
                                    date_pickup = data_pickup[0]['data'][0][0]['text']
                                    if date_pickup:
                                        date_pickup_object = datetime.strptime(date_pickup, "%d.%m.%Y")

                                    #time pickup HYUNDAI CKD
                                    data_timepickup = tabula.read_pdf(pdf_file, pages='all', output_format="json", area=[98.4,614.4,121.2,652.25])
                                    time_pickup = data_timepickup[0]['data'][0][0]['text']
                                    if time_pickup:
                                        time_object = datetime.strptime(time_pickup, "%H:%M").time()

                                        # Combine date and time
                                        combined_datetime = datetime.combine(date_pickup_object, time_object)

                                    #Picking
                                    move = self.env['stock.picking'].create({
                                        'name': nomor_dn or "/",
                                        # 'cycle': int(cycle),
                                        'order_date': date_order_object or "",
                                        'pickup_date': combined_datetime - timedelta(hours=7) or fields.Datetime.now(),
                                        'start_pull': combined_datetime - timedelta(hours=16) or fields.Datetime.now(),
                                        'end_pull': combined_datetime - timedelta(hours=15) or fields.Datetime.now(),
                                        'location_id': default_warehouse.lot_stock_id.id,
                                        'location_dest_id': default_customer_location.id,
                                        'picking_type_id': delivery_picking_type.id,
                                    })

                                    #Get Orders HYUNDAI CKD
                                    orders = tabula.read_pdf(pdf_file, pages='all', multiple_tables=True, area=[135.6,36,472.8,759.4])
                                    for idx, df in enumerate(orders):
                                        table_data = df.values.tolist()
                                        for inner_list in table_data:
                                            # Stock Move HYUNDAI CKD
                                            product_id = self.env['product.product'].search([('customer_partnumber','=', inner_list[1])],limit=1)
                                            if product_id:
                                                stock_move = self.env['stock.move'].create({
                                                        'name': product_id.name,
                                                        'product_id': product_id.id,
                                                        'product_uom': product_id.uom_id.id,
                                                        'product_uom_qty': float(inner_list[5]),
                                                        'qty_kanban': float(inner_list[4]),
                                                        'procure_method': 'make_to_stock',
                                                        'picking_id': move.id,
                                                        'date': combined_datetime - timedelta(hours=7) or fields.Datetime.now(),
                                                        'location_id': default_warehouse.lot_stock_id.id,
                                                        'location_dest_id': default_customer_location.id,
                                                        'company_id': self.env.company.id
                                                })
                                
                                elif partner.ref in ["99100042"]:

                                    #Get No DN PT FUJI SEAT INDONESIA
                                    # (top, left, bottom, right)
                                    data = tabula.read_pdf(pdf_file, pages='all', output_format="json", area=[68.67,667.63,80.14,817.16])
                                    nomor_dn = data[0]['data'][0][0]['text']


                                    #Get Cycle PT FUJI SEAT INDONESIA
                                    data_cycle = tabula.read_pdf(pdf_file, pages='all', output_format="json", area=[80.14,667.63,94.20,817.16])
                                    original_cycle = data_cycle[0]['data'][0][0]['text']
                                    cycle = ''.join(char for char in original_cycle if char.isdigit())

                                    #date Order PT FUJI SEAT INDONESIA
                                    # locale.setlocale(locale.LC_TIME, 'id_ID')
                                    # Mapping of Indonesian month names to English month names
                                    month_translation = {
                                        'Januari': 'January',
                                        'Februari': 'February',
                                        'Maret': 'March',
                                        'April': 'April',
                                        'Mei': 'May',
                                        'Juni': 'June',
                                        'Juli': 'July',
                                        'Agustus': 'August',
                                        'September': 'September',
                                        'Oktober': 'October',
                                        'November': 'November',
                                        'Desember': 'December'
                                    }
                                    
                                    data_date_order = tabula.read_pdf(pdf_file, pages='all', output_format="json", area=[119.25,667.63,130.70,817.16])
                                    date_order = data_date_order[0]['data'][0][0]['text']
                                    if date_order:
                                        # Define the format of the remaining date string
                                        date_format = "%B %d %Y"
                                        # Translate the Indonesian month name to English
                                        parts = date_order.split(", ")
                                        date = parts[1].split()
                                        formatted_date = f"{date[0]} {date[1]} {parts[2]}"
                                        date_order_without_day = formatted_date
                                        # for ind_month, eng_month in month_translation.items():
                                        #     date_order_without_day = date_order_without_day.replace(ind_month, eng_month)
                                        date_order_object = datetime.strptime(date_order_without_day, date_format)

                                    #date pickup PT FUJI SEAT INDONESIA
                                    #bulan pickup
                                    data_bulan_pickup = tabula.read_pdf(pdf_file, pages='all', output_format="json", area=[44.84,675.90,59.19,817.1])
                                    date_bulan_pickup = data_bulan_pickup[0]['data'][0][0]['text']
                                    if date_bulan_pickup:
                                        idn_bulan = date_bulan_pickup.capitalize()
                                        for ind_month, eng_month in month_translation.items():
                                            idn_bulan = idn_bulan.replace(ind_month, eng_month)
                                        bulan_pickup = datetime.strptime(idn_bulan, "%B %Y")
                                    #tgl pickup
                                    data_pickup = tabula.read_pdf(pdf_file, pages='all', output_format="json", area=[130.70,667.63,142.15,817.16])
                                    date_pickup = data_pickup[0]['data'][0][0]['text']
                                    if date_pickup:
                                        date_pickup_days = datetime.strptime(date_pickup, "%d")

                                    #time pickup
                                    data_timepickup = tabula.read_pdf(pdf_file, pages='all', output_format="json", area=[94.20,667.63,104.94,817.16])
                                    time_pickup = data_timepickup[0]['data'][0][0]['text']
                                    if time_pickup:
                                        time_object = datetime.strptime(time_pickup, "%H.%M").time()

                                        # Combine date and time
                                        combined_datetime = datetime(bulan_pickup.year, bulan_pickup.month, date_pickup_days.day, time_object.hour, time_object.minute )

                                    #Picking
                                    move = self.env['stock.picking'].create({
                                        'name': nomor_dn or "/",
                                        'cycle': int(cycle),
                                        'order_date': date_order_object or "",
                                        'pickup_date': combined_datetime - timedelta(hours=7) or fields.Datetime.now(),
                                        'start_pull': combined_datetime - timedelta(hours=16) or fields.Datetime.now(),
                                        'end_pull': combined_datetime - timedelta(hours=15) or fields.Datetime.now(),
                                        'location_id': default_warehouse.lot_stock_id.id,
                                        'location_dest_id': default_customer_location.id,
                                        'picking_type_id': delivery_picking_type.id,
                                    })

                                    #Get Orders PT FUJI SEAT INDONESIA
                                    orders = tabula.read_pdf(pdf_file, pages='all', multiple_tables=True, area=[175.54,22.86,389.25,822.87])
                                    for idx, df in enumerate(orders):
                                        table_data = df.values.tolist()
                                        for inner_list in table_data:
                                            data_product = inner_list[1]
                                            product_translate = {
                                                '73230-BZE30': '73230-BZE30-C0',
                                                '73230-BZE40': '73230-BZE40-C0',
                                                '73230-BZE50': '73230-BZE50-C0'
                                            }
                                            if not isinstance(data_product, float):
                                                for false_code, true_code in product_translate.items():
                                                    data_product = data_product.replace(false_code,true_code)

                                            # Stock Move PT FUJI SEAT INDONESIA
                                            product_id = self.env['product.product'].search([('customer_partnumber','=', data_product)],limit=1)
                                            if product_id:
                                                original_qty = inner_list[8]
                                                original_kanban = inner_list[7]
                                                if isinstance(original_qty, float):
                                                    qty = '0'
                                                else:
                                                    qty =  ''.join(char for char in original_qty if char.isdigit())
                                                if isinstance(original_kanban, float):
                                                    kanban = '0'
                                                else:
                                                    kanban = ''.join(char for char in original_kanban if char.isdigit())
                                                stock_move = self.env['stock.move'].create({
                                                        'name': product_id.name,
                                                        'product_id': product_id.id,
                                                        'product_uom': product_id.uom_id.id,
                                                        'product_uom_qty': float(qty),
                                                        'qty_kanban': float(kanban),
                                                        'procure_method': 'make_to_stock',
                                                        'picking_id': move.id,
                                                        'date': combined_datetime - timedelta(hours=7) or fields.Datetime.now(),
                                                        'location_id': default_warehouse.lot_stock_id.id,
                                                        'location_dest_id': default_customer_location.id,
                                                        'company_id': self.env.company.id
                                                })
                                
                                elif partner.ref in ["99100023","99100038"]:

                                    #Get No DN PT. MMKI
                                    data = tabula.read_pdf(pdf_file, pages='all', output_format="json", area=[119.22,233.96,148,293.79])
                                    nomor_dn = data[0]['data'][0][0]['text']


                                    #Get Cycle PT. MMKI
                                    data_cycle = tabula.read_pdf(pdf_file, pages='all', output_format="json", area=[106.02,105.22,119.23,119.66])
                                    is_data = data_cycle[0]['data']
                                    cycle_partner = False
                                    if is_data:
                                        cycle = data_cycle[0]['data'][0][0]['text']
                                        _logger.info("cycle")
                                        _logger.info(cycle)
                                        if cycle:
                                            cycle_partner = self.env['pramadya.cycle'].search([('partner_id','=', partner.id),('cycle','=', int(cycle))],limit=1)
                                            if not cycle_partner:
                                                cycle_partner = self.env['pramadya.cycle'].search([('partner_id','=', partner.id),('cycle','=', 1)],limit=1)
                                        else:
                                            cycle_partner = self.env['pramadya.cycle'].search([('partner_id','=', partner.id),('cycle','=', 1)],limit=1)
                                    else:
                                        cycle_partner = self.env['pramadya.cycle'].search([('partner_id','=', partner.id),('cycle','=', 1)],limit=1)
                                        


                                    #date Order PT. MMKI
                                    data_date_order = tabula.read_pdf(pdf_file, pages='all', output_format="json", area=[39.60,506.29,51.89,568.59])
                                    date_order = data_date_order[0]['data'][0][0]['text']
                                    if date_order:
                                        date_order_object = datetime.strptime(date_order, "%Y/%m/%d")

                                    #date pickup PT. MMKI
                                    data_pickup = tabula.read_pdf(pdf_file, pages='all', output_format="json", area=[95.30,104.39,108.72,165.46])
                                    date_pickup = data_pickup[0]['data'][0][0]['text']
                                    if date_pickup:
                                        date_pickup_object = datetime.strptime(date_pickup, "%Y/%m/%d")

                                    #time pickup PT. MMKI

                                    # Convert the float value to hours and minutes
                                    pickup_time = timedelta(seconds=cycle_partner.time*3600)

                                    #Picking
                                    move = self.env['stock.picking'].create({
                                        'name': nomor_dn or "/",
                                        'cycle': int(cycle_partner.cycle),
                                        'order_date': date_order_object or "",
                                        'pickup_date': datetime(date_pickup_object.year, date_pickup_object.month, date_pickup_object.day) + pickup_time - timedelta(hours=7) or fields.Datetime.now(),
                                        'start_pull': datetime(date_pickup_object.year, date_pickup_object.month, date_pickup_object.day) + pickup_time - timedelta(hours=16) or fields.Datetime.now(),
                                        'end_pull': datetime(date_pickup_object.year, date_pickup_object.month, date_pickup_object.day) + pickup_time - timedelta(hours=15) or fields.Datetime.now(),
                                        'location_id': default_warehouse.lot_stock_id.id,
                                        'location_dest_id': default_customer_location.id,
                                        'picking_type_id': delivery_picking_type.id,
                                    })

                                    #Get Orders PT. MMKI
                                    orders = tabula.read_pdf(pdf_file, pages='all', multiple_tables=True, area=[142.33,40.22,300.53,570.24])
                                    for idx, df in enumerate(orders):
                                        table_data = df.values.tolist()
                                        for inner_list in table_data:
                                            list_product = inner_list[0]
                                            # Stock Move PT. MMKI
                                            product_id = self.env['product.product'].search([('customer_partnumber','=', list_product)],limit=1)
                                            if product_id:
                                                qty_package = 1
                                                for p in product_id:
                                                    if p.packaging_ids:
                                                        qty_package = p.packaging_ids[0].qty
                                                total_kanban = float(inner_list[2]) / float(qty_package)
                                                stock_move = self.env['stock.move'].create({
                                                        'name': product_id.name,
                                                        'product_id': product_id.id,
                                                        'product_uom': product_id.uom_id.id,
                                                        'product_uom_qty': float(inner_list[2]),
                                                        'qty_kanban': total_kanban,
                                                        'procure_method': 'make_to_stock',
                                                        'picking_id': move.id,
                                                        'date': datetime(date_pickup_object.year, date_pickup_object.month, date_pickup_object.day) + pickup_time - timedelta(hours=7) or fields.Datetime.now(),
                                                        'location_id': default_warehouse.lot_stock_id.id,
                                                        'location_dest_id': default_customer_location.id,
                                                        'company_id': self.env.company.id
                                                })
                                
                                elif partner.ref in ["99100102","99100011"]:

                                    #Get No DN TB INA KRW
                                    data = tabula.read_pdf(pdf_file, pages='all', output_format="json", area=[39.65,232.08,55.36,378.30])
                                    nomor_dn = data[0]['data'][0][0]['text']


                                    #Get Cycle TB INA KRW
                                    data_cycle = tabula.read_pdf(pdf_file, pages='all', output_format="json", area=[112.12,543.00,126.00,560.40])
                                    cycle = data_cycle[0]['data'][0][0]['text']

                                    #date Order TB INA KRW
                                    data_date_order = tabula.read_pdf(pdf_file, pages='all', output_format="json", area=[98.40,87.03,112.80,181.49])
                                    date_order = data_date_order[0]['data'][0][0]['text']
                                    if date_order:
                                        date_order_object = datetime.strptime(date_order, "%B %d, %Y")

                                    #date pickup TB INA KRW
                                    data_pickup = tabula.read_pdf(pdf_file, pages='all', output_format="json", area=[96.60,475.00,112.80,573.60])
                                    date_pickup = data_pickup[0]['data'][0][0]['text']
                                    if date_pickup:
                                        date_pickup_object = datetime.strptime(date_pickup, "%B %d, %Y")

                                    #time pickup TB INA KRW
                                    data_timepickup = tabula.read_pdf(pdf_file, pages='all', output_format="json", area=[112.12,475.00,126.00,508.80])
                                    time_pickup = data_timepickup[0]['data'][0][0]['text']
                                    if time_pickup:
                                        time_object = datetime.strptime(time_pickup, "%H:%M").time()

                                        # Combine date and time
                                        combined_datetime = datetime.combine(date_pickup_object, time_object)

                                    #Picking
                                    move = self.env['stock.picking'].create({
                                        'name': nomor_dn or "/",
                                        'cycle': int(cycle),
                                        'order_date': date_order_object or "",
                                        'pickup_date': combined_datetime - timedelta(hours=7) or fields.Datetime.now(),
                                        'start_pull': combined_datetime - timedelta(hours=16) or fields.Datetime.now(),
                                        'end_pull': combined_datetime - timedelta(hours=15) or fields.Datetime.now(),
                                        'location_id': default_warehouse.lot_stock_id.id,
                                        'location_dest_id': default_customer_location.id,
                                        'picking_type_id': delivery_picking_type.id,
                                    })

                                    #Get Orders TB INA KRW
                                    orders = tabula.read_pdf(pdf_file, pages='all', multiple_tables=True, area=[147.75,54.75,620.25,588.75])
                                    for idx, df in enumerate(orders):
                                        table_data = df.values.tolist()
                                        for inner_list in table_data:
                                            # Stock Move TB INA KRW
                                            lines_table =inner_list[0]
                                            _logger.info(inner_list)
                                            _logger.info(lines_table)
                                            if len(inner_list) > 2:
                                                product_id = self.env['product.product'].search([('default_code','=', inner_list[0])],limit=1)
                                                if product_id:
                                                    stock_move = self.env['stock.move'].create({
                                                            'name': product_id.name,
                                                            'product_id': product_id.id,
                                                            'product_uom': product_id.uom_id.id,
                                                            'product_uom_qty': float(inner_list[-1]),
                                                            'qty_kanban': float(inner_list[-2]),
                                                            'procure_method': 'make_to_stock',
                                                            'picking_id': move.id,
                                                            'date': combined_datetime - timedelta(hours=7) or fields.Datetime.now(),
                                                            'location_id': default_warehouse.lot_stock_id.id,
                                                            'location_dest_id': default_customer_location.id,
                                                            'company_id': self.env.company.id
                                                    })
                                
                                else:
                                    message = _("Contact Customer Tidak Ditemukan !!")
                                    return {
                                            'type': 'ir.actions.client',
                                            'tag': 'display_notification',
                                            'params': {
                                                'message': message,
                                                'type': 'danger',
                                                'sticky': False,
                                            }
                                        }
                            else:
                                message = _("Contact Customer Belum Diisi !!")
                                return {
                                        'type': 'ir.actions.client',
                                        'tag': 'display_notification',
                                        'params': {
                                            'message': message,
                                            'type': 'danger',
                                            'sticky': False,
                                        }
                                    }
                        

                        move.message_post(attachment_ids=[attachment])
                        move.action_confirm()

                        document.attachment_id.write({'res_model': 'stock.picking', 'res_id': move.id})
                
                if partner:
                    move.partner_id = partner
                

                delivery_ids.append(move.id)

            context = dict(self._context)
            action = {
                'type': 'ir.actions.act_window',
                'res_model': 'stock.picking',
                'name': "Delivery",
                'view_id': False,
                'view_mode': 'tree',
                'views': [(False, "list"), (False, "form")],
                'domain': [('id', 'in', delivery_ids)],
                'context': context,
            }
            if len(delivery_ids) == 1:
                record = move or self.env['stock.picking'].browse(delivery_ids[0])
                view_id = record.get_formview_id() if record else False
                action.update({
                    'view_mode': 'form',
                    'views': [(view_id, "form")],
                    'res_id': delivery_ids[0],
                    'view_id': view_id,
                })
            return action
        return rv
