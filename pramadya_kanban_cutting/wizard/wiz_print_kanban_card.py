from odoo import models, fields, api, _
from odoo.exceptions import UserError
import csv
from datetime import date, datetime, timedelta
from re import sub
from decimal import Decimal
import os, errno
import base64
import qrcode
import io
from PyPDF2 import PdfFileWriter, PdfFileReader
import logging
_logger = logging.getLogger(__name__)

class WizPrintKanbanCard(models.TransientModel):
    _name = 'wiz.print.kanban.card'
    _description = 'Print Kanban Card'

    line_id = fields.One2many('line.wiz.print.kanban.card', 'wiz_id', string="Line ID")
    pdf_file = fields.Binary("PDF File")
    pdf_name = fields.Char("PDF Name")
    attachment_ids          = fields.Many2many('ir.attachment', string='Attachments')

    def default_get(self, fields):
        res = super(WizPrintKanbanCard, self).default_get(fields)
        content_card_obj = self.env['content.card.tmmin']
        content_card_ids = self.env.context.get('active_ids', False)
        active_model = self.env.context.get('active_model', False)
        if not content_card_ids:
            return res
        assert active_model == 'content.card.tmmin', 'Bad context propagation'

        items = []
        cc_lines = content_card_obj.browse(content_card_ids)
        for line in cc_lines:
            if line.departure_time:
                d_split_1 = line.departure_time[:6]
                d_split_2 = line.departure_time[7:17]
            else:
                d_split_1 = ""
                d_split_2 = ""
            if line.arrival_time:
                a_split_1 = line.arrival_time[:6]
                a_split_2 = line.arrival_time[7:17]
            else:
                a_split_1 = ""
                a_split_2 = ""
            if line.out_time:
                o_split_1 = line.out_time[:6]
                o_split_2 = line.out_time[7:17]
            else:
                o_split_1 = ""
                o_split_2 = ""
            if line.order_no:
                ord_split_1 = line.order_no[:4]
                ord_split_2 = line.order_no[4:8]
                ord_split_3 = line.order_no[8:10]
            else:
                ord_split_1 = ""
                ord_split_2 = ""
                ord_split_3 = ""
            pn = str(line.part_code).replace("-","")
            item_seq = line.part_sequence[:1]
            space=f"{ ' ' * 6}"
            barcode = line.part_code.replace('-','')
            # real_qr = "KBN%s%s%s000%s000%s"%(line.manifest_no,space,pn,line.unique_no_seq,item_seq)
            # _logger.info('==================QR==================', real_qr)
            vals = {
                        'supplier_name'     : line.supplier_name,
                        'supplier_code'     : line.supplier_code,
                        'supplier_info'     : line.supplier_info,
                        'departure_time'    : line.departure_time,
                        'arrival_time'      : line.arrival_time,
                        'route'             : line.route,
                        'cycle'             : line.cycle,
                        'dock_code'         : line.dock_code,
                        'part_code'         : line.part_code,
                        'part_name'         : line.part_name,
                        'part_sequence'     : line.part_sequence,
                        'unique_no'         : line.unique_no,
                        'unique_no_seq'     : line.unique_no_seq,
                        'barcode'           : barcode,
                        'qr_code'           : line.qr_code,
                        'real_qr_code'      : line.real_qr_code,
                        'progres_lane_no'   : line.progres_lane_no,
                        'out_time'          : line.out_time,
                        'manifest_no'       : line.manifest_no,
                        'conveyance_no'     : line.conveyance_no,
                        'part_address'      : line.part_address,
                        'printed'           : line.printed,
                        'order_no'          : line.order_no,
                        'pcs_kanban'        : line.pcs_kanban,
                        'departure_split_1': d_split_1,
                        'departure_split_2': d_split_2,
                        'arrival_split_1': a_split_1,
                        'arrival_split_2': a_split_2,
                        'out_time_split_1': o_split_1,
                        'out_time_split_2': o_split_2,
                        'order_split_1': ord_split_1,
                        'order_split_2': ord_split_2,
                        'order_split_3': ord_split_3,
                    }
            items.append((0, 0, vals))
        res['line_id'] = items
        return res
    
    def generate_qr_code(self, data):
        for x in self.line_id:
            qr = qrcode.make(data)
            buffered = io.BytesIO()
            qr.save(buffered, format='PNG')
            qr_code_base64 = base64.b64encode(buffered.getvalue()).decode()
            return f"data:image/png;base64,{qr_code_base64}"

    def print_pdf_tmmin(self):
        for x in self.line_id:
            return self.env.ref('pramadya_kanban_cutting.action_print_kanban_card_1').report_action(self)

class LineWizPrintKanbanCard(models.TransientModel):
    _name = 'line.wiz.print.kanban.card'
    _description = 'List Kanban Card'

    wiz_id              = fields.Many2one('wiz.print.kanban.card', string="Wiz ID")
    supplier_name       = fields.Char(string='Supplier Name')
    supplier_code       = fields.Char(string='Supplier Code')
    supplier_info       = fields.Char(string='Supplier Info')
    departure_time      = fields.Char(string='Departure Time')
    departure_split_1   = fields.Char(string='Departure Split 1')
    departure_split_2   = fields.Char(string='Departure Split 2')
    arrival_time        = fields.Char(string='Arrival Time')
    arrival_split_1     = fields.Char(string='Arrival Split 1')
    arrival_split_2     = fields.Char(string='Arrival Split 2')
    route               = fields.Char(string='Route')
    cycle               = fields.Char(string='Cycle')
    dock_code           = fields.Char(string='Dock Code')
    part_code           = fields.Char(string='Part Number Code')
    part_name           = fields.Char(string='Part Number Name')
    part_sequence       = fields.Char(string='Part Number Sequence')
    unique_no           = fields.Char(string='Unique No')
    unique_no_seq       = fields.Char(string='Unique No SEQ')
    pcs_kanban          = fields.Char(string='Pcs/Kanban')
    order_no            = fields.Char(string='Order No')
    order_split_1       = fields.Char(string='Order No Split 1')
    order_split_2       = fields.Char(string='Order No Split 2')
    order_split_3       = fields.Char(string='Order No Split 3')
    barcode             = fields.Char(string='Barcode')
    qr_code             = fields.Char(string='QR Code')
    real_qr_code        = fields.Char(string='Real QR Code')
    progres_lane_no     = fields.Char(string='Progress Lane No')
    out_time            = fields.Char(string='Out Time')
    out_time_split_1    = fields.Char(string='Out Time Split 1')
    out_time_split_2    = fields.Char(string='Out Time Split 2')
    manifest_no         = fields.Char(string='Manifest No')
    conveyance_no       = fields.Char(string='Conveyance No')
    part_address        = fields.Char(string='Part Address')
    printed             = fields.Char(string='Printed')
    
