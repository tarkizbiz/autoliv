# -*- coding: utf-8 -*-

from odoo import _, models, fields, api
from odoo.exceptions import UserError
import requests

class L2lConfig(models.Model):
    _name = 'pramadya.l2l.config'
    _description = 'L2l API Config'
    _rec_name ="server"

    server = fields.Selection([
        ('sanbox', 'Sanbox'),
        ('production', 'Production')], default='sanbox')
    url = fields.Char()
    api_key = fields.Char(string="API Key")
    site = fields.Char()
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('inactive', 'inctive')
    ], string='Status', copy=False, index=True, readonly=True, store=True, default='draft')

    def set_active(self):
        for config in self:
            config.state = "active"

    def set_inactive(self):
        for config in self:
            config.state = "inactive"

    def test_config(self):
        for config in self:
            finished = False
            lines=[]
            url = config.url + '/api/1.0/lines/'
            apikey = config.api_key
            limit = 1
            while not finished:
                resp = requests.get(url, {'auth': apikey, 'site': config.site, 'limit': limit, 'offset': len(lines)}, timeout=60)
                if resp.ok:
                    resp_js = resp.json()
                    if not resp_js['success']:
                        raise UserError(_("api call failed with error: %s") % resp_js['error'])
                    lines.extend(resp_js['data'])

                    if len(resp_js['data']) < limit:
                        finished = True
                    message = _("Test Connection successfully ! %s") % resp_js
                    return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': message,
                        'type': 'success',
                        'sticky': False,
                    }
                }
                else:
                    raise UserError(_("Failed request, error: %d") % resp.status_code)



class LineCapacity(models.Model):
    _name = 'pramadya.line'
    _description = 'AID Line Capacity'

    name = fields.Char(string="Line Code")
    product_cycle = fields.Float()
    line_type = fields.Selection([('fg',"Finished Goods"),('sub',"Sub-Assembly")])
    capacity = fields.Float(string="1 Shiftcap")

class CustomerCycle(models.Model):
    _name = 'pramadya.cycle'
    _description = 'AID Customer Cycle'

    partner_id = fields.Many2one('res.partner', ondelete='cascade')
    name = fields.Char()
    cycle = fields.Integer()
    time = fields.Float()
    start_time = fields.Float()
    end_time = fields.Float()
    days_pull = fields.Selection([('-1',"-1"),('0',"0")])


class ResPartner(models.Model):
    _inherit = 'res.partner'

    customer_cycle = fields.One2many('pramadya.cycle', 'partner_id')
    