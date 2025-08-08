# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, timedelta, time

class LotSystem(models.Model):
    _name = 'pramadya.lot'
    _description = 'Lot System'
    _rec_name = 'product_id'

    partner_id = fields.Many2one('res.partner')
    product_id = fields.Many2one('product.product')
    default_code = fields.Char(related='product_id.default_code')
    aid_partnumber = fields.Char(related='product_id.aid_partnumber')
    qty = fields.Float(string="Qty", compute='_compute_qty',digits='Product Unit of Measure', store=True)
    capacity = fields.Float(string="Capacity",digits='Product Unit of Measure')
    line_id = fields.Many2one('mrp.workcenter')
    schedule_date = fields.Datetime()
    due_date = fields.Datetime()
    lot_details = fields.One2many('pramadya.lot.details', 'lot_id')
    state = fields.Selection([
        ('draft', 'In Progress'),
        ('ready', 'Ready'),
        ('done', 'Done')
    ], string='Status', copy=False, index=True, readonly=False, store=True, default='draft')

    is_qty_less_than_capacity = fields.Boolean(string='Is Qty Less Than Capacity', compute='_compute_is_qty_less_than_capacity',store=True)

    @api.depends('qty', 'capacity')
    def _compute_is_qty_less_than_capacity(self):
        for record in self:
            record.is_qty_less_than_capacity = record.qty < record.capacity

    @api.depends('lot_details')
    def _compute_qty(self):
        for lot in self:
            total = 0.0
            for details in lot.lot_details:
                total += details.qty
            lot.qty = total

    def send_kanban(self):
        for lot in self:
            if lot.qty == lot.capacity:
                # Number of seconds to add
                schedule_date = fields.Datetime.now()
                total_cycle = lot.product_id.cycle_time * lot.qty

                # Create a timedelta object with the specified number of seconds
                time_total_cycle = timedelta(seconds=total_cycle)

                # time range from schedule_date to due_date
                wib_schedule_date = schedule_date + timedelta(hours=7)
                wib_due_date = schedule_date + timedelta(hours=7) + time_total_cycle
                schedule_time = wib_schedule_date.time()
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

                

                print("schedule_time",schedule_time)
                print("wib_due_date",wib_due_date)

                if schedule_time <= time(10, 0, 0) and due_date > time(10, 0, 0):
                    istirahat_pagi = timedelta(seconds=600)
                    print("istirahat_pagi",istirahat_pagi)

                pagi_due_date = wib_due_date + istirahat_pagi
                print("pagi_due_date",pagi_due_date)
                
                # Gelombang I: SB1-5, Steering Wheel, PAB 1+2, SAB, ICAB​
                if lot.product_id.primary_line_id.code in ['410B001','410B002','410B003','410B004','410B005','410S002','410P001','410PAB02','410SAB1','410CAB01']:
                    if schedule_time <= time(12, 0, 0) and pagi_due_date.time() > time(12, 0, 0):
                        istirahat_siang = timedelta(seconds=2100)
                        print("istirahat_siang",istirahat_siang)

                    siang_due_date = pagi_due_date + istirahat_siang
                    print("siang_due_date",siang_due_date)

                    if schedule_time <= time(15, 30, 0) and siang_due_date.time() > time(15, 30, 0):
                        istirahat_sore = timedelta(seconds=900)
                        print("istirahat_sore",istirahat_sore)

                # Gelombang II: R1-5, F1-2, LB1-2
                if lot.product_id.primary_line_id.code in ['410R001','410R002','410R003','410R004','410R005','410F001','410F002','410L001','410L002']:
                    if schedule_time <= time(12, 25, 0) and pagi_due_date.time() >= time(12, 25, 0):
                        istirahat_siang = timedelta(seconds=2100)
                        print("istirahat_siang",istirahat_siang)

                    siang_due_date = pagi_due_date + istirahat_siang
                    print("siang_due_date",siang_due_date)

                    if schedule_time <= time(15, 45, 0) and siang_due_date.time() >= time(15, 45, 0):
                        istirahat_sore = timedelta(seconds=900)
                        print("istirahat_sore",istirahat_sore)

                
                
                # Shift II​
                # Senin – Jumat : 21.00 – 06.00​

                # Istirahat tengah malam: 00:00 – 00:40​ (40 min/2400 sec)
                # Istirahat subuh: 04:30 – 04:50 (20 min/1200 sec)
                istirahat_malam = timedelta(seconds=0)
                istirahat_subuh = timedelta(seconds=0)

                if due_date < time(4, 30, 0):
                    istirahat_malam = timedelta(seconds=2400)
                    print("istirahat_malam1",istirahat_malam)
                    

                malam_due_date = wib_due_date + istirahat_malam
                print("malam_due_date",malam_due_date)

                if schedule_time <= time(4, 30, 0) and malam_due_date.time() > time(4, 30, 0):
                    istirahat_subuh = timedelta(seconds=1200)
                    print("istirahat_subuh",istirahat_subuh)


                

                # Add the timedelta to the original datetime
                new_datetime = fields.Datetime.from_string(schedule_date) + time_total_cycle + istirahat_pagi + istirahat_siang + istirahat_sore + istirahat_malam + istirahat_subuh

                new_kanban = self.env['pramadya.rail'].create({
                            'product_id': lot.product_id.id,
                            'line_id': lot.product_id.primary_line_id.id,
                            'qty': lot.qty,
                            'schedule_date': schedule_date,
                            'due_date': new_datetime,
                            'cycle': lot.product_id.cycle_time,
                            'state': 'scheduled'
                        })
                lot.write({'state': 'done'})

    def split(self):
        for lot in self:
            if lot.qty <= lot.capacity:
                seconds_to_add = lot.product_id.cycle_time * lot.qty

                # Create a timedelta object with the specified number of seconds
                time_delta = timedelta(seconds=seconds_to_add)

                # Add the timedelta to the original datetime
                due_datetime = fields.Datetime.from_string(fields.Datetime.now()) + time_delta

                new_kanban = self.env['pramadya.rail'].create({
                            'product_id': lot.product_id.id,
                            'line_id': lot.product_id.primary_line_id.id,
                            'qty': lot.qty,
                            'schedule_date': fields.Datetime.now(),
                            'due_date': due_datetime,
                            'cycle': lot.product_id.cycle_time,
                            'state': 'scheduled'
                        })

                lot.write({'state': 'done'})
            else:
                # split
                split = lot.qty - lot.capacity
                seconds_to_add = lot.product_id.cycle_time * lot.capacity

                # Create a timedelta object with the specified number of seconds
                time_delta = timedelta(seconds=seconds_to_add)

                # Add the timedelta to the original datetime
                due_datetime = fields.Datetime.from_string(fields.Datetime.now()) + time_delta

                new_kanban = self.env['pramadya.rail'].create({
                            'product_id': lot.product_id.id,
                            'line_id': lot.product_id.primary_line_id.id,
                            'qty': lot.capacity,
                            'schedule_date': fields.Datetime.now(),
                            'due_date': due_datetime,
                            'cycle': lot.product_id.cycle_time,
                            'state': 'scheduled'
                        })

                lot.write({'state': 'done'})

                new_lot = self.env['pramadya.lot'].create({
                            'product_id': lot.product_id.id,
                            'line_id': lot.line_id.id,
                            'qty': split,
                            'capacity': lot.capacity,
                            'schedule_date': fields.Datetime.now(),
                            'due_date': due_datetime,
                        })

                lot_details = self.env['pramadya.lot.details'].create({
                                            'lot_id': new_lot.id,
                                            'delivery_note': 'Split from Product ' + lot.product_id.default_code,
                                            'qty': split,
                                            'qty_kanban': 1,
                                            'order_date': fields.Datetime.now()
                                        })

    def send_to_kanban(self):
        data_lot = self.env['pramadya.lot'].search([('state','=','ready')])
        for lot in data_lot:
            if lot.qty == lot.capacity:
                # Number of seconds to add
                schedule_date = fields.Datetime.now()
                total_cycle = lot.product_id.cycle_time * lot.qty

                # Create a timedelta object with the specified number of seconds
                time_total_cycle = timedelta(seconds=total_cycle)

                # time range from schedule_date to due_date
                wib_schedule_date = schedule_date + timedelta(hours=7)
                wib_due_date = schedule_date + timedelta(hours=7) + time_total_cycle
                schedule_time = wib_schedule_date.time()
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

                

                print("schedule_time",schedule_time)
                print("wib_due_date",wib_due_date)

                if schedule_time <= time(10, 0, 0) and due_date > time(10, 0, 0):
                    istirahat_pagi = timedelta(seconds=600)
                    print("istirahat_pagi",istirahat_pagi)

                pagi_due_date = wib_due_date + istirahat_pagi
                print("pagi_due_date",pagi_due_date)
                
                # Gelombang I: SB1-5, Steering Wheel, PAB 1+2, SAB, ICAB​
                if lot.product_id.primary_line_id.code in ['410B001','410B002','410B003','410B004','410B005','410S002','410P001','410PAB02','410SAB1','410CAB01']:
                    if schedule_time <= time(12, 0, 0) and pagi_due_date.time() > time(12, 0, 0):
                        istirahat_siang = timedelta(seconds=2100)
                        print("istirahat_siang",istirahat_siang)

                    siang_due_date = pagi_due_date + istirahat_siang
                    print("siang_due_date",siang_due_date)

                    if schedule_time <= time(15, 30, 0) and siang_due_date.time() > time(15, 30, 0):
                        istirahat_sore = timedelta(seconds=900)
                        print("istirahat_sore",istirahat_sore)

                # Gelombang II: R1-5, F1-2, LB1-2
                if lot.product_id.primary_line_id.code in ['410R001','410R002','410R003','410R004','410R005','410F001','410F002','410L001','410L002']:
                    if schedule_time <= time(12, 25, 0) and pagi_due_date.time() >= time(12, 25, 0):
                        istirahat_siang = timedelta(seconds=2100)
                        print("istirahat_siang",istirahat_siang)

                    siang_due_date = pagi_due_date + istirahat_siang
                    print("siang_due_date",siang_due_date)

                    if schedule_time <= time(15, 45, 0) and siang_due_date.time() >= time(15, 45, 0):
                        istirahat_sore = timedelta(seconds=900)
                        print("istirahat_sore",istirahat_sore)

                
                
                # Shift II​
                # Senin – Jumat : 21.00 – 06.00​

                # Istirahat tengah malam: 00:00 – 00:40​ (40 min/2400 sec)
                # Istirahat subuh: 04:30 – 04:50 (20 min/1200 sec)
                istirahat_malam = timedelta(seconds=0)
                istirahat_subuh = timedelta(seconds=0)

                if due_date < time(4, 30, 0):
                    istirahat_malam = timedelta(seconds=2400)
                    print("istirahat_malam1",istirahat_malam)
                    

                malam_due_date = wib_due_date + istirahat_malam
                print("malam_due_date",malam_due_date)

                if schedule_time <= time(4, 30, 0) and malam_due_date.time() > time(4, 30, 0):
                    istirahat_subuh = timedelta(seconds=1200)
                    print("istirahat_subuh",istirahat_subuh)


                

                # Add the timedelta to the original datetime
                new_datetime = fields.Datetime.from_string(schedule_date) + time_total_cycle + istirahat_pagi + istirahat_siang + istirahat_sore + istirahat_malam + istirahat_subuh

                new_kanban = self.env['pramadya.rail'].create({
                            'product_id': lot.product_id.id,
                            'line_id': lot.product_id.primary_line_id.id,
                            'qty': lot.qty,
                            'schedule_date': schedule_date,
                            'due_date': new_datetime,
                            'cycle': lot.product_id.cycle_time,
                            'state': 'scheduled'
                        })
                lot.write({'state': 'done'})

class LotDetails(models.Model):
    _name = 'pramadya.lot.details'
    _description = 'Lot System details'
    
    lot_id = fields.Many2one('pramadya.lot', ondelete='cascade')
    delivery_note = fields.Char(size=64)
    pack = fields.Char(size=64)
    qty = fields.Float(string="Qty")
    qty_kanban = fields.Float(string="Qty Kanban")
    order_date = fields.Date()
    create_date = fields.Date()
    production_date = fields.Date()