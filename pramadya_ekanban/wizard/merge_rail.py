from odoo import _, api, exceptions, fields, models
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta, time, date

class MergeRail(models.TransientModel):
    _name = 'merge.rail'
    _description = "merge e-rail"

    product_id = fields.Many2one('product.product',string='Product')
    qty = fields.Float(string="Quantity",digits='Product Unit of Measure')
    line_id = fields.Many2one('mrp.workcenter')
    schedule_date = fields.Datetime()
    due_date = fields.Datetime()
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

    item_ids = fields.One2many('merge.rail.line','wiz_id', string='Items')

    def default_get(self, fields):
        res = super(MergeRail, self).default_get(fields)
        
        obj_rail = self.env['pramadya.rail']
        rail_ids = self.env.context.get('active_ids', False)
        active_model = self.env.context.get('active_model', False)
        if not rail_ids:
            return res
        assert active_model == 'pramadya.rail', \
            'Bad context propagation'

        items = []
        rail_items = obj_rail.browse(rail_ids)
        rail_schedule_date = obj_rail.search([('id', 'in', rail_ids)], order="schedule_date asc")
        if any(r.product_id.id != rail_items[0].product_id.id for r in rail_items):
            raise UserError(_("Merge beberapa Rail harus dengan Product yang sama"))
        if any(r.line_id.id != rail_items[0].line_id.id for r in rail_items):
            raise UserError(_("Merge beberapa Rail harus dengan line yang sama"))

        
        total_qty = sum(rail_items.mapped('qty'))
        total_cycle = rail_items[0].cycle * total_qty
        due_date = rail_schedule_date[0].schedule_date + timedelta(seconds=total_cycle)

        res['product_id'] = rail_items[0].product_id.id
        res['line_id'] = rail_items[0].line_id.id
        res['state'] = 'scheduled'
        res['schedule_date'] = rail_schedule_date[0].schedule_date
        res['due_date'] = due_date
        res['qty'] = total_qty
        
        for rail in rail_items:
            vals = {
                'product_id': rail.product_id.id,
                'qty': rail.qty,
                'line_id': rail.line_id.id,
                'schedule_date': rail.schedule_date,
                'due_date': rail.due_date,
                'state': rail.state,
                'rail_id': rail.id,
            }
            items.append((0, 0, vals))

        res['item_ids'] = items
        return res

    def merge_rails(self):
        for merge in self:
            obj_rail = self.env['pramadya.rail']
            new_rail = obj_rail.create({
                'product_id': merge.product_id.id,
                'qty': merge.qty,
                'line_id': merge.line_id.id,
                'state': merge.state,
                'schedule_date': merge.schedule_date,
                'due_date': merge.due_date,
            })

            for items in merge.item_ids:
                items.rail_id.state = 'canceled'

class ItemsMergeRail(models.TransientModel):
    _name = "merge.rail.line"
    _description = "ItemsMergeRail"

    wiz_id = fields.Many2one('merge.rail', string='Wizard', required=True, ondelete='cascade',readonly=True)
    product_id = fields.Many2one('product.product',string='Product')
    default_code = fields.Char(related='product_id.default_code')
    aid_partnumber = fields.Char(related='product_id.aid_partnumber')
    schedule_date = fields.Datetime(default=fields.Datetime.now)
    due_date = fields.Datetime()
    qty = fields.Float(string="Quantity",digits='Product Unit of Measure')
    line_id = fields.Many2one('mrp.workcenter')
    rail_id = fields.Many2one('pramadya.rail')
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