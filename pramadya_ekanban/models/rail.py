# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, SUPERUSER_ID
from datetime import datetime, timedelta, time, date
from odoo.exceptions import warnings, UserError, ValidationError
import requests
import logging
from dateutil import parser
import pytz
_logger = logging.getLogger(__name__)

class KanbanRail(models.Model):
    _name = 'pramadya.rail'
    _description = 'E-Kanban Rail'
    _rec_name = 'product_id'
    _order = 'status_rtb,status_stock_condition,schedule_date'

    product_id = fields.Many2one('product.product',string="Part Number", required=True)
    default_code = fields.Char(related='product_id.default_code')
    aid_partnumber = fields.Char(related='product_id.aid_partnumber')
    schedule_date = fields.Datetime(default=fields.Datetime.now)
    due_date = fields.Datetime()
    actual_date = fields.Datetime()
    qty = fields.Float(string="Quantity",digits='Product Unit of Measure')
    cop_qty = fields.Float(string="COP",digits='Product Unit of Measure')
    lat = fields.Float(string="LAT",digits='Product Unit of Measure')
    sum_cop = fields.Float(string="COP + Quantity",digits='Product Unit of Measure',compute='_compute_cop')
    qty_build = fields.Float(string="Quantity Build",digits='Product Unit of Measure')
    qty_build_actual = fields.Float(string="Quantity Build Actual",digits='Product Unit of Measure', compute='_compute_build')
    cycle = fields.Float(string="Product Cycle Time")
    line_id = fields.Many2one('mrp.workcenter')
    state = fields.Selection([
        ('rtb', 'On Going'),
        ('new', 'Scheduling'),
        ('planning', 'Planning'),
        ('scheduled', 'Automatic E-Lot'),
        ('changeover', 'Changeover/Setup'),
        ('wip', 'Work in Progess'),
        ('onhold', 'On Hold'),
        ('completed', 'Completed'),
        ('canceled', 'Canceled'),
        ('cleanup', 'Cleanup'),
        ('paused', 'Paused')
    ], string='Status', copy=False, index=True, readonly=False, store=True, default='new')

    qty_available = fields.Float(string="On Hand", related='product_id.qty_available')
    status_stock = fields.Selection(string="Status Stock", related='product_id.status_stock')
    status_cop = fields.Selection([('cop',"COP"),('nocop',"No COP")], string="Status COP", compute='_compute_cop') 
    sequence = fields.Integer('Sequence', default=20) 
    stock_condition = fields.Float(store=True,compute='_compute_stock_condition')
    status_stock_condition = fields.Selection([('01',"Urgent"),('02',"Minimum")])
    snp = fields.Float(related='product_id.snp',digits='Product Unit of Measure')
    kanban_qty = fields.Float(string="Quantity(Kanban)",digits='Product Unit of Measure',compute='_compute_kanban')
    today_demand = fields.Float(digits='Product Unit of Measure',compute='_compute_today_demand', store=True)
    status_rtb = fields.Selection([('01',"RTB"),('02',"No RTB")],compute='_compute_rtb', store=True)
    pitch_ids = fields.One2many('pitch', 'rail_id')

    @api.depends('pitch_ids','pitch_ids.actual','pitch_ids.actual_product')
    def _compute_build(self):
        for rail in self:
            rail.qty_build_actual = sum(rail.pitch_ids.mapped('actual'))
    
    @api.depends('state')
    def _compute_rtb(self):
        for rail in self:
            if rail.state in ['rtb','onhold']:
                rail.status_rtb = '01'
            else:
                rail.status_rtb = '02'

    @api.depends('product_id.demand_monthly','product_id.daily_demand')
    def _compute_today_demand(self):
        for rail in self:
            today = date.today()
            move = self.env['stock.move'].search([('product_id', '=', rail.product_id.id),('picking_id.picking_type_id.code', '=', 'outgoing'),('pickup_date', '>', datetime.combine(today, datetime.min.time())),('pickup_date', '<=', datetime.combine(today, datetime.max.time()))])
            if move:
                rail.today_demand = sum(move.mapped('product_uom_qty'))
                print(move)
            else:
                rail.today_demand = rail.product_id.daily_demand

    def _compute_kanban(self):
        for rail in self:
            rail.kanban_qty = rail.qty / rail.snp

    # @api.depends('product_id.qty_available','product_id.outgoing_qty','qty')
    # def _compute_status_condition(self):
    #     for rail in self:
    #         _logger.info("qty_urgent")
    #         qty_urgent = sum(self.env['pramadya.rail'].search([('product_id', '=', rail.product_id.id),('status_stock_condition','=', '01'),('state','!=','completed')]).mapped('qty'))
    #         _logger.info(qty_urgent)
    #         balance = rail.product_id.qty_available - rail.product_id.outgoing_qty + qty_urgent
    #         _logger.info("balance")
    #         _logger.info(balance)
    #         if balance < 0:
    #             rail.status_stock_condition = '01'
    #         else:
    #             rail.status_stock_condition = False

    @api.depends('product_id.qty_available','product_id.demand_monthly','today_demand')
    def _compute_stock_condition(self):
        for rail in self:
            if rail.today_demand == 0:
                rail.stock_condition = 0
            else:
                rail.stock_condition = rail.product_id.qty_available / rail.today_demand

    def _compute_cop(self):
        for rail in self:
            sum_cop = rail.qty + rail.cop_qty
            if rail.cop_qty == 0:
                rail.sudo().write({'status_cop': 'nocop'})
            else:
                rail.sudo().write({'status_cop': 'cop'})
            rail.sudo().write({'sum_cop': sum_cop})

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.write({'line_id': self.product_id.primary_line_id.id, 'cycle': self.product_id.cycle_time})

    @api.onchange('schedule_date','qty')
    def _onchange_schedule_date(self):
        for rail in self:
            if rail.product_id:
                # Number of seconds to add
                total_cycle = rail.cycle * rail.qty
                print("total_cycle",total_cycle)
                # Create a timedelta object with the specified number of seconds
                time_total_cycle = timedelta(seconds=total_cycle)

                # time range from schedule_date to due_date
                wib_schedule_date = rail.schedule_date + timedelta(hours=7)
                wib_due_date = rail.schedule_date + timedelta(hours=7) + time_total_cycle
                schedule_date = wib_schedule_date.time()
                due_date = wib_due_date.time()


                #Working Hours​
                # Shift I​
                # Senin – Kamis : 08.00 – 17.00​
                # Jumat : 08.00 – 17.30​

                # Istirahat pagi: 10:00 – 10.10​ (10 min/600 sec)
                # Istirahat siang I: 12:00 – 12:35​ (35 min/2100 sec)
                # Istirahat siang II: 12:25 – 13:00​ (35 min/2100 sec)
                # Istirahat sore I: 15:30 – 15:45​ (15 min/900 sec)
                # Istirahat sore II: 15:45 – 16:00 (15 min/900 sec)
                istirahat_pagi = timedelta(seconds=0)
                istirahat_siang = timedelta(seconds=0)
                istirahat_sore = timedelta(seconds=0)

                

                print("schedule_date",schedule_date)
                print("wib_due_date",wib_due_date)

                if schedule_date <= time(10, 0, 0) and due_date > time(10, 0, 0):
                    istirahat_pagi = timedelta(seconds=600)
                    print("istirahat_pagi",istirahat_pagi)

                pagi_due_date = wib_due_date + istirahat_pagi
                print("pagi_due_date",pagi_due_date)
                
                # Gelombang I: SB1-5, Steering Wheel, PAB 1+2, SAB, ICAB​
                if rail.product_id.primary_line_id.code in ['410B001','410B002','410B003','410B004','410B005','410S002','410P001','410PAB02','410SAB1','410CAB01']:
                    if schedule_date <= time(12, 0, 0) and pagi_due_date.time() > time(12, 0, 0):
                        istirahat_siang = timedelta(seconds=2100)
                        print("istirahat_siang",istirahat_siang)

                    siang_due_date = pagi_due_date + istirahat_siang
                    print("siang_due_date",siang_due_date)

                    if schedule_date <= time(15, 30, 0) and siang_due_date.time() > time(15, 30, 0):
                        istirahat_sore = timedelta(seconds=900)
                        print("istirahat_sore",istirahat_sore)

                # Gelombang II: R1-5, F1-2, LB1-2
                if rail.product_id.primary_line_id.code in ['410R001','410R002','410R003','410R004','410R005','410F001','410F002','410L001','410L002']:
                    if schedule_date <= time(12, 25, 0) and pagi_due_date.time() >= time(12, 25, 0):
                        istirahat_siang = timedelta(seconds=2100)
                        print("istirahat_siang",istirahat_siang)

                    siang_due_date = pagi_due_date + istirahat_siang
                    print("siang_due_date",siang_due_date)

                    if schedule_date <= time(15, 45, 0) and siang_due_date.time() >= time(15, 45, 0):
                        istirahat_sore = timedelta(seconds=900)
                        print("istirahat_sore",istirahat_sore)

                
                
                # Shift II​
                # Senin – Jumat : 21.00 – 06.00​

                # Istirahat tengah malam: 00:00 – 00:40​ (40 min/2400 sec)
                # Istirahat subuh: 04:30 – 04:50 (20 min/1200 sec)
                istirahat_malam = timedelta(seconds=0)
                istirahat_subuh = timedelta(seconds=0)

                # if schedule_date >= time(21, 0, 0) and due_date > time(23, 59, 59):
                #     istirahat_malam = timedelta(seconds=2400)
                #     print("istirahat_malam",istirahat_malam)
                if due_date < time(4, 30, 0):
                    istirahat_malam = timedelta(seconds=2400)
                    print("istirahat_malam1",istirahat_malam)
                    

                malam_due_date = wib_due_date + istirahat_malam
                print("malam_due_date",malam_due_date)

                if schedule_date <= time(4, 30, 0) and malam_due_date.time() > time(4, 30, 0):
                    istirahat_subuh = timedelta(seconds=1200)
                    print("istirahat_subuh",istirahat_subuh)

                # if schedule_date >= time(21, 0, 0) and malam_due_date.time() > time(4, 30, 0):
                #     istirahat_subuh = timedelta(seconds=1200)
                #     print("istirahat_subuh",istirahat_subuh)


                

                # Add the timedelta to the original datetime
                new_datetime = fields.Datetime.from_string(self.schedule_date) + time_total_cycle + istirahat_pagi + istirahat_siang + istirahat_sore + istirahat_malam + istirahat_subuh

                rail.write({'due_date': new_datetime})


    def ready(self):
        for rail in self:
            rail_ready = self.env['pramadya.rail'].search([('product_id', '=', rail.product_id.id),('state','=', 'rtb')],limit=1)
            if rail_ready:
                raise UserError(_("Part Number ini sudah Ready to Build di E-rail !!."))
            else:   
                rail.state = 'rtb'

    def on_hold(self):
        for rail in self:
            rail_onhold = self.env['pramadya.rail'].search([('product_id', '=', rail.product_id.id),('state','=', 'onhold')],limit=1)
            if rail_onhold:
                raise UserError(_("Part Number ini sudah On Hold di E-rail !!."))
            else:   
                rail.state = 'onhold'

    def cancel_ready(self):
        for rail in self:
            if rail.line_id.code not in ['7096','7518']:
                rail.state = 'scheduled'
            else:
                rail.state = 'new'

    def sync_l2l(self):
        today = date.today()
        for rail in self:
            if rail.state == 'rtb' and rail.line_id.code not in ['7096','7518']:
                pitch_odoo = self.env['pitch'].search([('actual_product','=',rail.product_id.l2l_product_id),('line','=',int(rail.line_id.code)),('rail_id','=',False),
                ('shift_start_date', '>', datetime.combine(today, datetime.min.time())),('shift_start_date', '<=', datetime.combine(today, datetime.max.time()))])
                if pitch_odoo:
                    for pitch in pitch_odoo:
                        pitch.write({'rail_id': rail.id})
            else:
                raise UserError(_("E-rail Belum On Going !!."))

    def cron_sync_l2l(self):
        rail_ready = self.env['pramadya.rail'].search([('state','in', ['rtb','onhold']),('line_id.code','not in', ['7096','7518'])])
        _logger.info("rail_ready")
        _logger.info(rail_ready)
        today = datetime.now()
        for rail in rail_ready:
            pitch_odoo = self.env['pitch'].search([('actual_product','=',rail.product_id.l2l_product_id),('line','=',int(rail.line_id.code)),('rail_id','=',False),
            ('shift_start_date', '>', datetime.combine(today, datetime.min.time())),('shift_start_date', '<=', datetime.combine(today, datetime.max.time()))])
            if pitch_odoo:
                for pitch in pitch_odoo:
                    pitch.write({'rail_id': rail.id})
        """
        Get list rail status='on-going'
        kemudian dilooping jika ID product dan line ID match dengan data pitch_odoo maka add rail_id ke pitch dan 
        akan akumulasi qty di rail tsb
        kelemahan = tidak bisa set ongoing rail
        kelebihan = looping tidak akan banyak
        -------------------------------------

        ADDING QTY
        Get list pitch odoo kemudian filtering date today dan memiliki ID Product dan rail_id=False
        kemudian dilooping jika ID Product dan line ID match dengan rail maka add rail_id ke pitch record dan 
        akan akumulasi qty di record rail tsb (compute pitch line)
        SET ON GOING
        SET PARTIAL
        SET FINISH

        """

    def _cron_rail(self):
        rail_ready = self.env['pramadya.rail'].search([('state','in', ['rtb']),('line_id.code','not in', ['7096','7518'])])
        _logger.info("rail_ready_move")
        _logger.info(rail_ready)
        today = datetime.now()
        default_warehouse = self.env['stock.warehouse'].search(self.env['stock.warehouse']._check_company_domain(self.env.company), limit=1)
        for rail in rail_ready:
            for pitch in rail.pitch_ids:
                _logger.info(today)
                _logger.info("pitch_end")
                pitch_end = fields.Datetime.from_string(pitch.pitch_end)
                _logger.info(pitch.pitch_end)
                if pitch.pitch_end < today and not pitch.move_id and pitch.actual != 0:
                    _logger.info("rail_ready_move_false")
                    quants = self.env['stock.quant']._update_available_quantity(rail.product_id, default_warehouse.lot_stock_id, pitch.actual)
                    stock_move = self.env['stock.move'].create({
                        'name': 'Auto Stock Receipt From L2L',
                        'product_id': rail.product_id.id,
                        'product_uom_qty': abs(pitch.actual),
                        'quantity':abs(pitch.actual),
                        'location_id': default_warehouse.sam_loc_id.id,
                        'location_dest_id': default_warehouse.lot_stock_id.id,  # Set the destination location based on your requirements
                        'state': 'done',  # Set the state to 'done' to complete the move immediately
                    })
                    pitch.write({'move_id': stock_move.id})
            last_pitch = rail.pitch_ids.search([('rail_id','=',rail.id)],order='pitch_end desc',limit=1).pitch_end
            lat_cop = rail.cop_qty + rail.lat
            actual_after_cop = rail.qty_build_actual - lat_cop
            if rail.qty == actual_after_cop and last_pitch < today:
                if lat_cop > 0:
                        quants = self.env['stock.quant']._update_available_quantity(rail.product_id, default_warehouse.lot_stock_id, -lat_cop)
                        stock_move = self.env['stock.move'].create({
                            'name': 'Auto Adjustment LAT and CPO From L2L',
                            'product_id': rail.product_id.id,
                            'product_uom_qty': abs(lat_cop),
                            'quantity':abs(lat_cop),
                            'location_id': default_warehouse.lot_stock_id.id,
                            'location_dest_id': default_warehouse.sam_loc_id.id,  # Set the destination location based on your requirements
                            'state': 'done',  # Set the state to 'done' to complete the move immediately
                        })
                rail.write({'state': 'completed'})
                rail.write({'actual_date': fields.Datetime.now()})

    def _cron_rail_changeover(self):
        rail_ready = self.env['pramadya.rail'].search([('state','in', ['changeover']),('line_id.code','not in', ['7096','7518'])])
        _logger.info("rail_ready_move")
        _logger.info(rail_ready)
        today = datetime.now()
        default_warehouse = self.env['stock.warehouse'].search(self.env['stock.warehouse']._check_company_domain(self.env.company), limit=1)
        for rail in rail_ready:
            for pitch in rail.pitch_ids:
                _logger.info(today)
                _logger.info("pitch_end")
                pitch_end = fields.Datetime.from_string(pitch.pitch_end)
                _logger.info(pitch.pitch_end)
                if pitch.pitch_end < today and not pitch.move_id and pitch.actual != 0:
                    _logger.info("rail_ready_move_false")
                    quants = self.env['stock.quant']._update_available_quantity(rail.product_id, default_warehouse.lot_stock_id, pitch.actual)
                    stock_move = self.env['stock.move'].create({
                        'name': 'Auto Stock Receipt From L2L',
                        'product_id': rail.product_id.id,
                        'product_uom_qty': abs(pitch.actual),
                        'quantity':abs(pitch.actual),
                        'location_id': default_warehouse.sam_loc_id.id,
                        'location_dest_id': default_warehouse.lot_stock_id.id,  # Set the destination location based on your requirements
                        'state': 'done',  # Set the state to 'done' to complete the move immediately
                    })
                    pitch.write({'move_id': stock_move.id})
            last_pitch = rail.pitch_ids.search([('rail_id','=',rail.id)],order='pitch_end desc',limit=1).pitch_end
            lat_cop = rail.cop_qty + rail.lat
            actual_after_cop = rail.qty_build_actual - lat_cop
            if rail.qty == actual_after_cop and last_pitch < today:
                if lat_cop > 0:
                        quants = self.env['stock.quant']._update_available_quantity(rail.product_id, default_warehouse.lot_stock_id, -lat_cop)
                        stock_move = self.env['stock.move'].create({
                            'name': 'Auto Adjustment LAT and CPO From L2L',
                            'product_id': rail.product_id.id,
                            'product_uom_qty': abs(lat_cop),
                            'quantity':abs(lat_cop),
                            'location_id': default_warehouse.lot_stock_id.id,
                            'location_dest_id': default_warehouse.sam_loc_id.id,  # Set the destination location based on your requirements
                            'state': 'done',  # Set the state to 'done' to complete the move immediately
                        })
                rail.write({'state': 'completed'})
                rail.write({'actual_date': fields.Datetime.now()})

    def partial(self):
        for rail in self:
            if rail.line_id.code not in ['7096','7518']:
                if rail.qty_build_actual and rail.qty > rail.qty_build_actual:
                    today = datetime.now()
                    default_warehouse = self.env['stock.warehouse'].search(self.env['stock.warehouse']._check_company_domain(self.env.company), limit=1)
                    for pitch in rail.pitch_ids:
                        _logger.info(today)
                        _logger.info("pitch_end")
                        pitch_end = fields.Datetime.from_string(pitch.pitch_end)
                        _logger.info(pitch.pitch_end)
                        if pitch.pitch_end < today and not pitch.move_id and pitch.actual != 0:
                            _logger.info("rail_ready_move_false")
                            quants = self.env['stock.quant']._update_available_quantity(rail.product_id, default_warehouse.lot_stock_id, pitch.actual)
                            stock_move = self.env['stock.move'].create({
                                'name': 'Auto Stock Receipt From L2L',
                                'product_id': rail.product_id.id,
                                'product_uom_qty': abs(pitch.actual),
                                'quantity':abs(pitch.actual),
                                'location_id': default_warehouse.lot_stock_id.id,
                                'location_dest_id': default_warehouse.lot_stock_id.id,  # Set the destination location based on your requirements
                                'state': 'done',  # Set the state to 'done' to complete the move immediately
                            })
                            pitch.write({'move_id': stock_move.id})
                        # else:
                        #     raise UserError(_("Time Pitch end belum selesai !!"))
                    remain = rail.qty - rail.qty_build_actual
                    if remain > 0 :
                        if rail.product_id.lot == 'schedule':
                            new_kanban = self.env['pramadya.rail'].sudo().create({
                                        'product_id': rail.product_id.id,
                                        'line_id': rail.product_id.primary_line_id.id,
                                        'qty': remain,
                                        'schedule_date': fields.Datetime.now(),
                                        'cycle': rail.cycle,
                                        'state': 'new'
                                    })
                        elif rail.product_id.lot == False:
                            new_kanban = self.env['pramadya.rail'].sudo().create({
                                        'product_id': rail.product_id.id,
                                        'line_id': rail.product_id.primary_line_id.id,
                                        'qty': remain,
                                        'schedule_date': fields.Datetime.now(),
                                        'cycle': rail.cycle,
                                        'state': 'new'
                                    })
                        else:
                            #jika type product Elot
                            get_lot = self.env['pramadya.lot'].sudo().search([('product_id','=',rail.product_id.id),('state','=','draft'),('is_qty_less_than_capacity', '=', True)],limit=1)
                            if get_lot:
                                #kalau ada antrian elot maka mengisi yg sudah ada sampai terpenuhi capacity
                                total = remain + get_lot.qty
                                if total > get_lot.capacity:
                                    # antrian diselesaikan dan dibuat elot baru dengan qty remain
                                    new_qty = total - get_lot.capacity
                                    new_lot = self.env['pramadya.lot'].sudo().create({
                                            'product_id': rail.product_id.id,
                                            'line_id': rail.product_id.primary_line_id.id,
                                            'capacity': rail.product_id.lot_size,
                                        'schedule_date': fields.Datetime.now(),
                                        })
                                    lot_details = self.env['pramadya.lot.details'].sudo().create({
                                                'lot_id': new_lot.id,
                                                'delivery_note': rail.product_id.name + " 2 Partial Items Erail",
                                                'qty': new_qty,
                                                'order_date': fields.Datetime.now(),
                                            })
                                    lot_exsis = self.env['pramadya.lot.details'].sudo().create({
                                                'lot_id': get_lot.id,
                                                'delivery_note': rail.product_id.name + " 2 Partial Items Erail",
                                                'qty': remain - new_qty,
                                                'order_date': fields.Datetime.now(),
                                            })
                                    get_lot.send_kanban()
                                    
                                else:
                                    # antrian tetap ada
                                    lot_details = self.env['pramadya.lot.details'].sudo().create({
                                                'lot_id': get_lot.id,
                                                'delivery_note': rail.product_id.name + "1 Partial Items Erail",
                                                'qty': remain,
                                                'order_date': fields.Datetime.now(),
                                            })
                            else:
                                #kalau tidak ada antrian elot maka elot dibuat baru
                                new_lot = self.env['pramadya.lot'].sudo().create({
                                        'product_id': rail.product_id.id,
                                        'line_id': rail.product_id.primary_line_id.id,
                                        'capacity': rail.product_id.lot_size,
                                        'schedule_date': fields.Datetime.now(),
                                    })
                                lot_details = self.env['pramadya.lot.details'].sudo().create({
                                                'lot_id': new_lot.id,
                                                'delivery_note': rail.product_id.name + "New Partial Items Erail",
                                                'qty': remain,
                                                'order_date': fields.Datetime.now(),
                                            })
                        rail.write({'state': 'changeover'})
                        rail.write({'actual_date': fields.Datetime.now()})
                        lat_cop = rail.cop_qty + rail.lat
                        if lat_cop > 0:
                            quants = self.env['stock.quant']._update_available_quantity(rail.product_id, default_warehouse.lot_stock_id, -lat_cop)
                            stock_move = self.env['stock.move'].create({
                                'name': 'Auto Adjustment LAT and CPO From L2L',
                                'product_id': rail.product_id.id,
                                'product_uom_qty': abs(lat_cop),
                                'quantity':abs(lat_cop),
                                'location_id': default_warehouse.lot_stock_id.id,
                                'location_dest_id': default_warehouse.sam_loc_id.id,  # Set the destination location based on your requirements
                                'state': 'done',  # Set the state to 'done' to complete the move immediately
                            })
                    else:
                        raise UserError(_("Quantity Build melebihi Quantity Scheduled."))
            else:
                if rail.qty_build and rail.qty > rail.qty_build:
                    # if rail.qty > rail.product_id.lot_size and rail.product_id.lot == 'lot':
                    #     raise UserError(_("Quantity melebihi dari Quantity LOT Size!!."))
                    default_warehouse = self.env['stock.warehouse'].search(self.env['stock.warehouse']._check_company_domain(self.env.company), limit=1)
                    if not default_warehouse:
                        default_warehouse = self.env['stock.warehouse'].search([], limit=1)
                    stock_quant = self.env['stock.quant'].search([('product_id', '=', rail.product_id.id)],limit=1)
                    if stock_quant:
                        # Update existing stock quant record
                        new_quantity = stock_quant.quantity + rail.qty_build
                        # stock_quant.write({'quantity': new_quantity})
                        quants = self.env['stock.quant']._update_available_quantity(rail.product_id, default_warehouse.lot_stock_id, rail.qty_build)
                        # Create a stock move to track the adjustment
                        stock_move = self.env['stock.move'].create({
                            'name': 'Stock Receipt From L2L',
                            'product_id': rail.product_id.id,
                            'product_uom_qty': abs(rail.qty_build),
                            'quantity':abs(rail.qty_build),
                            'location_id': default_warehouse.lot_stock_id.id,
                            'location_dest_id': default_warehouse.lot_stock_id.id,  # Set the destination location based on your requirements
                            'state': 'done',  # Set the state to 'done' to complete the move immediately
                        })
                    else:
                        # Create a new stock quant record if not exists
                        # new_quant = self.env['stock.quant'].create({
                        #     'product_id': rail.product_id.id,
                        #     'quantity': rail.qty_build,
                        #     'location_id': default_warehouse.lot_stock_id.id,
                        # })
                        quants = self.env['stock.quant']._update_available_quantity(rail.product_id, default_warehouse.lot_stock_id, rail.qty_build)
                        stock_move = self.env['stock.move'].create({
                            'name': 'Stock Receipt From L2L',
                            'product_id': rail.product_id.id,
                            'product_uom_qty': abs(rail.qty_build),
                            'quantity':abs(rail.qty_build),
                            'location_id': default_warehouse.lot_stock_id.id,
                            'location_dest_id': default_warehouse.lot_stock_id.id,  # Set the destination location based on your requirements
                            'state': 'done',  # Set the state to 'done' to complete the move immediately
                        })
                    remain = rail.qty - rail.qty_build
                    if remain > 0 :
                        if rail.product_id.lot == 'schedule':
                            new_kanban = self.env['pramadya.rail'].sudo().create({
                                        'product_id': rail.product_id.id,
                                        'line_id': rail.product_id.primary_line_id.id,
                                        'qty': remain,
                                        'schedule_date': fields.Datetime.now(),
                                        'cycle': rail.cycle,
                                        'state': 'new'
                                    })
                        elif rail.product_id.lot == False:
                            new_kanban = self.env['pramadya.rail'].sudo().create({
                                        'product_id': rail.product_id.id,
                                        'line_id': rail.product_id.primary_line_id.id,
                                        'qty': remain,
                                        'schedule_date': fields.Datetime.now(),
                                        'cycle': rail.cycle,
                                        'state': 'new'
                                    })
                        else:
                            #jika type product Elot
                            get_lot = self.env['pramadya.lot'].sudo().search([('product_id','=',rail.product_id.id),('state','=','draft'),('is_qty_less_than_capacity', '=', True)],limit=1)
                            if get_lot:
                                #kalau ada antrian elot maka mengisi yg sudah ada sampai terpenuhi capacity
                                total = remain + get_lot.qty
                                if total > get_lot.capacity:
                                    # antrian diselesaikan dan dibuat elot baru dengan qty remain
                                    new_qty = total - get_lot.capacity
                                    new_lot = self.env['pramadya.lot'].sudo().create({
                                            'product_id': rail.product_id.id,
                                            'line_id': rail.product_id.primary_line_id.id,
                                            'capacity': rail.product_id.lot_size,
                                        'schedule_date': fields.Datetime.now(),
                                        })
                                    lot_details = self.env['pramadya.lot.details'].sudo().create({
                                                'lot_id': new_lot.id,
                                                'delivery_note': rail.product_id.name + " 2 Partial Items Erail",
                                                'qty': new_qty,
                                                'order_date': fields.Datetime.now(),
                                            })
                                    lot_exsis = self.env['pramadya.lot.details'].sudo().create({
                                                'lot_id': get_lot.id,
                                                'delivery_note': rail.product_id.name + " 2 Partial Items Erail",
                                                'qty': remain - new_qty,
                                                'order_date': fields.Datetime.now(),
                                            })
                                    get_lot.send_kanban()
                                    
                                else:
                                    # antrian tetap ada
                                    lot_details = self.env['pramadya.lot.details'].sudo().create({
                                                'lot_id': get_lot.id,
                                                'delivery_note': rail.product_id.name + "1 Partial Items Erail",
                                                'qty': remain,
                                                'order_date': fields.Datetime.now(),
                                            })
                            else:
                                #kalau tidak ada antrian elot maka elot dibuat baru
                                new_lot = self.env['pramadya.lot'].sudo().create({
                                        'product_id': rail.product_id.id,
                                        'line_id': rail.product_id.primary_line_id.id,
                                        'capacity': rail.product_id.lot_size,
                                        'schedule_date': fields.Datetime.now(),
                                    })
                                lot_details = self.env['pramadya.lot.details'].sudo().create({
                                                'lot_id': new_lot.id,
                                                'delivery_note': rail.product_id.name + "New Partial Items Erail",
                                                'qty': remain,
                                                'order_date': fields.Datetime.now(),
                                            })
                        rail.write({'state': 'completed'})
                        rail.write({'actual_date': fields.Datetime.now()})

                    else:
                        raise UserError(_("Quantity Build melebihi Quantity Scheduled."))


    def finish(self):
        for record in self:
            # Perform the stock adjustment logic here
            # You might want to create stock moves, adjust quantities, etc.
            
            # Example: Increase stock on hand for each selected product
            today = datetime.now()
            if record.line_id.code not in ['7096','7518']:
                default_warehouse = self.env['stock.warehouse'].search(self.env['stock.warehouse']._check_company_domain(self.env.company), limit=1)
                last_pitch = record.pitch_ids.search([('rail_id','=',record.id)],order='pitch_end desc',limit=1).pitch_end
                _logger.info("last_pitch")
                _logger.info(last_pitch)
                for pitch in record.pitch_ids:
                    _logger.info(today)
                    _logger.info("pitch_end")
                    _logger.info(pitch.pitch_end)
                    if pitch.pitch_end < today and not pitch.move_id and pitch.actual != 0:
                        quants = self.env['stock.quant']._update_available_quantity(record.product_id, default_warehouse.lot_stock_id, pitch.actual)
                        stock_move = self.env['stock.move'].create({
                            'name': 'Auto Stock Receipt From L2L',
                            'product_id': record.product_id.id,
                            'product_uom_qty': abs(pitch.actual),
                            'quantity':abs(pitch.actual),
                            'location_id': default_warehouse.sam_loc_id.id,
                            'location_dest_id': default_warehouse.lot_stock_id.id,  # Set the destination location based on your requirements
                            'state': 'done',  # Set the state to 'done' to complete the move immediately
                        })
                        pitch.write({'move_id': stock_move.id})
                
                lat_cop = record.cop_qty + record.lat
                actual_after_cop = record.qty_build_actual - lat_cop
                if record.qty == actual_after_cop and last_pitch < today:
                    if lat_cop > 0:
                        quants = self.env['stock.quant']._update_available_quantity(record.product_id, default_warehouse.lot_stock_id, -lat_cop)
                        stock_move = self.env['stock.move'].create({
                            'name': 'Auto Adjustment LAT and CPO From L2L',
                            'product_id': record.product_id.id,
                            'product_uom_qty': abs(lat_cop),
                            'quantity':abs(lat_cop),
                            'location_id': default_warehouse.lot_stock_id.id,
                            'location_dest_id': default_warehouse.sam_loc_id.id,  # Set the destination location based on your requirements
                            'state': 'done',  # Set the state to 'done' to complete the move immediately
                        })
                    record.write({'state': 'completed'})
                    record.write({'actual_date': fields.Datetime.now()})
                else:
                    raise UserError(_("Quantity and Quantity Build Actual must be equal."))

            else:
                stock_quant = self.env['stock.quant'].search([('product_id', '=', record.product_id.id)],limit=1)
                
                default_warehouse = self.env['stock.warehouse'].search(self.env['stock.warehouse']._check_company_domain(self.env.company), limit=1)
                # If the user doesn't have a default warehouse, you may want to set a default value or handle it accordingly
                if not default_warehouse:
                    default_warehouse = self.env['stock.warehouse'].search([], limit=1)

                if record.qty != record.qty_build:
                    
                    raise UserError(_("Quantity and Quantity Build must be equal."))
                else:
                    if stock_quant:
                        # Update existing stock quant record
                        new_quantity = stock_quant.quantity + record.qty_build
                        # stock_quant.write({'quantity': new_quantity})
                        quants = self.env['stock.quant']._update_available_quantity(record.product_id, default_warehouse.lot_stock_id, record.qty_build)
                        # Create a stock move to track the adjustment
                        stock_move = self.env['stock.move'].create({
                            'name': 'Stock Receipt From L2L',
                            'product_id': record.product_id.id,
                            'product_uom_qty': abs(record.qty_build),
                            'quantity':abs(record.qty_build),
                            'location_id': default_warehouse.lot_stock_id.id,
                            'location_dest_id': default_warehouse.lot_stock_id.id,  # Set the destination location based on your requirements
                            'state': 'done',  # Set the state to 'done' to complete the move immediately
                        })
                    else:
                        quants = self.env['stock.quant']._update_available_quantity(record.product_id, default_warehouse.lot_stock_id, record.qty_build)
                        stock_move = self.env['stock.move'].create({
                            'name': 'Stock Receipt From L2L',
                            'product_id': record.product_id.id,
                            'product_uom_qty': abs(record.qty_build),
                            'quantity':abs(record.qty_build),
                            'location_id': default_warehouse.lot_stock_id.id,
                            'location_dest_id': default_warehouse.lot_stock_id.id,  # Set the destination location based on your requirements
                            'state': 'done',  # Set the state to 'done' to complete the move immediately
                        })

                

                record.write({'state': 'completed'})
                record.write({'actual_date': fields.Datetime.now()})

        return {'type': 'ir.actions.act_window_close'}

class Pitch(models.Model):
    _name = "pitch"
    _description = "Pitch L2L"

    active = fields.Boolean()
    actual = fields.Float()
    actual_product = fields.Integer()
    area = fields.Integer()
    build_sequence  = fields.Integer()
    changeover_earned_hours = fields.Float()
    comment = fields.Char()
    created = fields.Datetime()
    createdby= fields.Char()
    cycle_time = fields.Float()
    demand = fields.Float()
    downtime_minutes = fields.Float()
    earned_hours = fields.Float()
    has_actual_details = fields.Boolean()
    has_operator_count_details = fields.Boolean()
    has_scrap_details = fields.Boolean()
    id_pitch= fields.Integer()
    ideal_cycle_time = fields.Float()
    lastupdated= fields.Datetime()
    lastupdatedby= fields.Datetime()
    line= fields.Integer()
    name= fields.Char()
    nonproduction_minutes = fields.Float()
    operational_availability = fields.Float()
    operator_count = fields.Float()
    overall_equipment_effectiveness = fields.Float()
    pitch_end= fields.Datetime()
    pitch_start= fields.Datetime()
    planned_operator_count = fields.Float()
    planned_product= fields.Integer()
    planned_product_order_group= fields.Integer()
    planned_production_minutes = fields.Float()
    product_order_group= fields.Integer()
    scrap = fields.Float()
    shift= fields.Integer()
    shift_start_date= fields.Datetime()
    site= fields.Integer()
    rail_id = fields.Many2one('pramadya.rail', ondelete='cascade')
    move_id = fields.Many2one('stock.move', ondelete='cascade')
    qty_move = fields.Float(related='move_id.product_uom_qty')

    def get_pitch(self):
        _logger.info("L2l Pitch")
        url = 'https://autoliv-asia.leading2lean.com/api/1.0/pitches/'
        apikey = "DWYT57xhyzimOjy5n5WdDtna5rS8dvjp"
        limit = 2000
        local_tz = pytz.timezone('Asia/Jakarta')
        now = datetime.now()
        date_start = datetime.combine(now.date(), time(7, 0, 0)) - timedelta(days=1)
        date_end = datetime.combine(now.date(), time(8, 0, 0)) + timedelta(days=1)
        pitch_start = date_start.strftime('%Y-%m-%d %H:%M')
        pitch_end = date_end.strftime('%Y-%m-%d %H:%M')
        _logger.info("pitch_start")
        _logger.info(pitch_start)
        line_active = [5209,5202,5195,7096,8423,5201,7518,5193,5194,7699,7698,5198,8424,5203,5192,5199,5196,8223,5197,5200,9955]
        _logger.info("pitch_end")
        _logger.info(pitch_end)
        resp = requests.get(url, {'auth': apikey, 'site': "900490", 'limit': limit,'pitch_start__gt':pitch_start,'pitch_end__lt':pitch_end}, timeout=60)
        if resp.ok:
            _logger.info("L2l Pitch oke")
            
            resp_js = resp.json()
            # _logger.info(resp_js)
            if not resp_js['success']:
                raise UserError(_("api call failed with error: %s") % resp_js['error'])
            
            obj_pitch= self.env['pitch']
            # pitch= self.env['pitch'].search([])
            # pitch.unlink()
            data = resp_js['data']
            for pitch in data:
                if pitch['line'] in line_active:
                    pitch_odoo = self.env['pitch'].search([('id_pitch','=', pitch['id'])],limit=1)
                    if not pitch_odoo:
                        data_pitch = {
                                    'active': pitch['active'],
                                    'actual': pitch['actual'],
                                    'actual_product': pitch['actual_product'],
                                    'area': pitch['area'],
                                    'line': pitch['line'],
                                    'name': pitch['name'],
                                    'demand': pitch['demand'],
                                    'site': pitch['site'],
                                    'shift_start_date': parser.parse(pitch['shift_start_date'])+ timedelta(hours=-7),
                                    'pitch_start': parser.parse(pitch['pitch_start'])+ timedelta(hours=-7),
                                    'pitch_end': parser.parse(pitch['pitch_end'])+ timedelta(hours=-7),
                                    'id_pitch': pitch['id'],
                        }
                        obj_pitch.create(data_pitch)
                    else:
                        data_pitch = {
                                    'active': pitch['active'],
                                    'actual': pitch['actual'],
                                    'actual_product': pitch['actual_product'],
                                    'area': pitch['area'],
                                    'line': pitch['line'],
                                    'name': pitch['name'],
                                    'demand': pitch['demand'],
                                    'site': pitch['site'],
                                    'shift_start_date': parser.parse(pitch['shift_start_date'])+ timedelta(hours=-7),
                                    'pitch_start': parser.parse(pitch['pitch_start'])+ timedelta(hours=-7),
                                    'pitch_end': parser.parse(pitch['pitch_end'])+ timedelta(hours=-7),
                                    'id_pitch': pitch['id'],
                        }
                        pitch_odoo.write(data_pitch)