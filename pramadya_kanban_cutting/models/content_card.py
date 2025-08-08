from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date, datetime, timedelta
import base64
import io
import logging
import PyPDF2
import pdfplumber
import cv2
import numpy as np
from pyzbar.pyzbar import decode

_logger = logging.getLogger(__name__)


class ContentCardTMMIN(models.Model):
    _name = 'content.card.tmmin'
    _description = 'Content Card'

    supplier_name       = fields.Char(string='Supplier Name')
    supplier_code       = fields.Char(string='Supplier Code')
    supplier_info       = fields.Char(string='Supplier Info')
    departure_time      = fields.Char(string='Departure Time')
    arrival_time        = fields.Char(string='Arrival Time')
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
    qr_code             = fields.Char(string='QR Code')
    real_qr_code        = fields.Char(string='Real QR Code')
    progres_lane_no     = fields.Char(string='Progress Lane No')
    out_time            = fields.Char(string='Out Time')
    manifest_no         = fields.Char(string='Manifest No')
    conveyance_no       = fields.Char(string='Conveyance No')
    part_address        = fields.Char(string='Part Address')
    printed             = fields.Char(string='Printed')
    scan_id             = fields.Char(string='Scan ID')

    def print_pdf_content(self):
        view_id = self.env.ref('pramadya_kanban_cutting.view_print_kanban_card').id
        return {
            'name':'Print Card',
            'view_mode':'form',
            'res_model':'wiz.print.kanban.card',
            'view_id':view_id,
            'type':'ir.actions.act_window',
            'target':'new',
        }


class WorkflowActionRuleAccount(models.Model):
    _inherit = ['documents.workflow.rule']

    create_model = fields.Selection(selection_add=[('content.card', "Kanban Potong")])

    def decode_qr_code(self, image):
        decoded_objects = decode(image)
        return [obj.data.decode('utf-8') for obj in decoded_objects]

    def create_record(self, documents=None):
        rv = super(WorkflowActionRuleAccount, self).create_record(documents=documents)
        if self.create_model.startswith('content.card'):
            for document in documents:
                partner = self.partner_id or document.partner_id
                with io.BytesIO(base64.b64decode(document.attachment_id.datas)) as pdf_file:
                    if partner :
                        if partner.ref in ["99100004"] :
                            results = {}
                            with pdfplumber.open(pdf_file) as pdf:
                                seq_scan = self.env["ir.sequence"].next_by_code("seq.pdf")
                                _logger.info('==========================seq====================================', seq_scan)
                                
                                num = 0
                                for page_number in range(len(pdf.pages)):
                                    page = pdf.pages[page_number]
                                    #kotak 1
                                    Supplier_Name       = [15.6,31.9,222.2,47.4]
                                    data_supplier_name  = page.within_bbox(Supplier_Name).extract_text()
                                    Supplier_Code       = [15.6,47,222.2,71]
                                    data_supplier_code  = page.within_bbox(Supplier_Code).extract_text()
                                    Departure_Time      = [15.6,88.2,115.3,115.8]
                                    data_departure_time = page.within_bbox(Departure_Time).extract_text()
                                    Arrival_Time        = [117.1,88.2,222.2,115.8]
                                    data_arrival_time   = page.within_bbox(Arrival_Time).extract_text()
                                    Route               = [28.8,118.9,140.5,165.7]
                                    data_route          = page.within_bbox(Route).extract_text()
                                    Cycle               = [156.1,118.9,222.2,165.7]
                                    data_cycle          = page.within_bbox(Cycle).extract_text()
                                    Supplier_Data_F2    = [15.6,216.8,222.2,250.4]
                                    data_supplier_f2    = page.within_bbox(Supplier_Data_F2).extract_text()
                                    Printed_at_Supplier = [15.6,250.4,222.2,264.9]
                                    data_print_supplier = page.within_bbox(Printed_at_Supplier).extract_text()
                                    Part_Number_Code    = [229.8,93.5,457.1,116.1]
                                    data_number_code    = page.within_bbox(Part_Number_Code).extract_text()
                                    Part_Number_Seq     = [457.1,93.5,489.6,116.1]
                                    data_number_seq     = page.within_bbox(Part_Number_Seq).extract_text()
                                    Part_Number_Name    = [229.8,116.1,489.6,147.6]
                                    data_number_name    = page.within_bbox(Part_Number_Name).extract_text()
                                    Unique_No           = [243.8,151.1,403.1,204.6]
                                    data_unique_no      = page.within_bbox(Unique_No).extract_text()
                                    Barcode             = [408.2,151.1,489.6,204.6]
                                    data_barcode        = page.within_bbox(Barcode).extract_text()
                                    Pcs_Kanban          = [229.8,222.1,294.8,250.4]
                                    data_pcs_kanban     = page.within_bbox(Pcs_Kanban).extract_text()
                                    Order_No            = [307.4,207.6,434.1,250.4]
                                    data_order_no       = page.within_bbox(Order_No).extract_text()
                                    Dock_Code           = [414.6,20.1,489.1,90.1]
                                    data_dock_code      = page.within_bbox(Dock_Code).extract_text()
                                    Progress_Lane_No    = [507.7,20.1,584.8,90.1]
                                    data_lane_no        = page.within_bbox(Progress_Lane_No).extract_text()
                                    Out                 = [507.7,90.1,584.8,155.5]
                                    data_out            = page.within_bbox(Out).extract_text()
                                    Manifest_No         = [497.1,131.1,584.8,152.1]
                                    data_manifest_no    = page.within_bbox(Manifest_No).extract_text()
                                    Conveyance_No       = [507.7,157.1,584.8,204.6]
                                    data_conveyance_no  = page.within_bbox(Conveyance_No).extract_text()
                                    Part_Address        = [453.1,207.6,584.8,250.4]
                                    data_part_address   = page.within_bbox(Part_Address).extract_text()
                                    x1_min, y1_min, x1_max, y1_max = 408.2, 151.1, 489.6, 204.6
                                    img1 = page.to_image()
                                    img_cv1 = np.array(img1.original)
                                    img_cv1 = cv2.cvtColor(img_cv1, cv2.COLOR_BGR2RGB)
                                    cropped_img1 = img_cv1[int(y1_min):int(y1_max), int(x1_min):int(x1_max)]
                                    qr_codes_1=[]
                                    if cropped_img1.size > 0:
                                        qr_codes_1.extend(self.decode_qr_code(cropped_img1))

                                    exist_record = self.env['content.card.tmmin'].search([('scan_id','=', seq_scan),('unique_no','=', data_unique_no)])
                                    if not exist_record :
                                        num = num+1
                                    else :
                                        num = num

                                    self.env['content.card.tmmin'].create({  
                                                                            'supplier_name'     : data_supplier_name,
                                                                            'supplier_code'     : data_supplier_code,
                                                                            'departure_time'    : data_departure_time,
                                                                            'arrival_time'      : data_arrival_time,
                                                                            'route'             : data_route,
                                                                            'cycle'             : data_cycle,
                                                                            'supplier_info'     : data_supplier_f2,
                                                                            'dock_code'         : data_dock_code,
                                                                            'part_code'         : data_number_code,
                                                                            'part_name'         : data_number_name,
                                                                            'part_sequence'     : data_number_seq,
                                                                            'unique_no'         : data_unique_no,
                                                                            'pcs_kanban'        : data_pcs_kanban,
                                                                            'order_no'          : data_order_no,
                                                                            'qr_code'           : data_barcode[::-1],
                                                                            'progres_lane_no'   : data_lane_no,
                                                                            'out_time'          : data_out,
                                                                            'manifest_no'       : data_manifest_no,
                                                                            'conveyance_no'     : data_conveyance_no,
                                                                            'part_address'      : data_part_address,
                                                                            'printed'           : data_print_supplier,
                                                                            'scan_id'           : seq_scan,
                                                                            'unique_no_seq'     : num,
                                                                            'real_qr_code'      : qr_codes_1[0],
                                                                                        
                                                                                    })


                                    #kotak 2
                                    Supplier_Name           = [15.6,291.9,222.2,307.4]
                                    data_supplier_name  = page.within_bbox(Supplier_Name).extract_text()
                                    if data_supplier_name :
                                        Supplier_Name       = [15.6,291.9,222.2,307.4]
                                        data_supplier_name  = page.within_bbox(Supplier_Name).extract_text()
                                        Supplier_Code       = [15.6,307,222.2,331]
                                        data_supplier_code  = page.within_bbox(Supplier_Code).extract_text()
                                        Departure_Time      = [15.6,348.2,115.3,375.8]
                                        data_departure_time = page.within_bbox(Departure_Time).extract_text()
                                        Arrival_Time        = [117.1,348.2,222.2,375.8]
                                        data_arrival_time   = page.within_bbox(Arrival_Time).extract_text()
                                        Route               = [28.8,378.9,140.5,425.7]
                                        data_route          = page.within_bbox(Route).extract_text()
                                        Cycle               = [156.1,378.9,222.2,425.7]
                                        data_cycle          = page.within_bbox(Cycle).extract_text()
                                        Supplier_Data_F2    = [15.6,476.8,222.2,510.4]
                                        data_supplier_f2    = page.within_bbox(Supplier_Data_F2).extract_text()
                                        Printed_at_Supplier = [15.6,510.4,222.2,524.9]
                                        data_print_supplier = page.within_bbox(Printed_at_Supplier).extract_text()
                                        Part_Number_Code    = [229.8,353.5,457.1,376.1]
                                        data_number_code    = page.within_bbox(Part_Number_Code).extract_text()
                                        Part_Number_Seq     = [457.1,353.5,489.6,376.1]
                                        data_number_seq     = page.within_bbox(Part_Number_Seq).extract_text()
                                        Part_Number_Name    = [229.8,376.1,489.6,407.6]
                                        data_number_name    = page.within_bbox(Part_Number_Name).extract_text()
                                        Unique_No           = [243.8,411.1,403.1,464.6]
                                        data_unique_no      = page.within_bbox(Unique_No).extract_text()
                                        Barcode             = [408.2,411.1,489.6,464.6]
                                        data_barcode        = page.within_bbox(Barcode).extract_text()
                                        Pcs_Kanban          = [229.8,482.1,294.8,510.4]
                                        data_pcs_kanban     = page.within_bbox(Pcs_Kanban).extract_text()
                                        Order_No            = [307.4,467.6,434.1,510.4]
                                        data_order_no       = page.within_bbox(Order_No).extract_text()
                                        Dock_Code           = [414.6,280.1,489.1,350.1]
                                        data_dock_code      = page.within_bbox(Dock_Code).extract_text()
                                        Progress_Lane_No    = [507.7,280.1,584.8,350.1]
                                        data_lane_no        = page.within_bbox(Progress_Lane_No).extract_text()
                                        Out                 = [507.7,350.1,584.8,415.5]
                                        data_out            = page.within_bbox(Out).extract_text()
                                        Manifest_No         = [497.1,391.1,584.8,412.1]
                                        data_manifest_no    = page.within_bbox(Manifest_No).extract_text()
                                        Conveyance_No       = [507.7,417.1,584.8,464.6]
                                        data_conveyance_no  = page.within_bbox(Conveyance_No).extract_text()
                                        Part_Address        = [453.1,467.6,584.8,510.4]
                                        data_part_address   = page.within_bbox(Part_Address).extract_text()
                                        x2_min, y2_min, x2_max, y2_max = 408.2, 411.1, 489.6, 464.6
                                        img2 = page.to_image()
                                        img_cv2 = np.array(img2.original)
                                        img_cv2 = cv2.cvtColor(img_cv2, cv2.COLOR_BGR2RGB)
                                        cropped_img2 = img_cv2[int(y2_min):int(y2_max), int(x2_min):int(x2_max)]
                                        qr_codes_2=[]
                                        if cropped_img2.size > 0:
                                            qr_codes_2.extend(self.decode_qr_code(cropped_img2))
                                        exist_record = self.env['content.card.tmmin'].search([('scan_id','=', seq_scan),('unique_no','=', data_unique_no)])
                                        if not exist_record :
                                            num = num+1
                                        else :
                                            num = num

                                        self.env['content.card.tmmin'].create({  
                                                                                'supplier_name'     : data_supplier_name,
                                                                                'supplier_code'     : data_supplier_code,
                                                                                'departure_time'    : data_departure_time,
                                                                                'arrival_time'      : data_arrival_time,
                                                                                'route'             : data_route,
                                                                                'cycle'             : data_cycle,
                                                                                'supplier_info'     : data_supplier_f2,
                                                                                'dock_code'         : data_dock_code,
                                                                                'part_code'         : data_number_code,
                                                                                'part_name'         : data_number_name,
                                                                                'part_sequence'     : data_number_seq,
                                                                                'unique_no'         : data_unique_no,
                                                                                'pcs_kanban'        : data_pcs_kanban,
                                                                                'order_no'          : data_order_no,
                                                                                'qr_code'           : data_barcode[::-1],
                                                                                'progres_lane_no'   : data_lane_no,
                                                                                'out_time'          : data_out,
                                                                                'manifest_no'       : data_manifest_no,
                                                                                'conveyance_no'     : data_conveyance_no,
                                                                                'part_address'      : data_part_address,
                                                                                'printed'           : data_print_supplier,
                                                                                'scan_id'           : seq_scan,
                                                                                'unique_no_seq'     : num,
                                                                                'real_qr_code'      : qr_codes_2[0],
                                                                                            
                                                                                        })

                                    else :
                                        _logger.info('==========================Data Tidak Ada=====================================')


                                    #kotak 3
                                    Supplier_Name           = [15.6,551.9,222.2,567.4]
                                    data_supplier_name  = page.within_bbox(Supplier_Name).extract_text()
                                    if data_supplier_name :
                                        Supplier_Name       = [15.6,551.9,222.2,567.4]
                                        data_supplier_name  = page.within_bbox(Supplier_Name).extract_text()
                                        Supplier_Code       = [15.6,567,222.2,591]
                                        data_supplier_code  = page.within_bbox(Supplier_Code).extract_text()
                                        Departure_Time      = [15.6,608.2,115.3,635.8]
                                        data_departure_time = page.within_bbox(Departure_Time).extract_text()
                                        Arrival_Time        = [117.1,608.2,222.2,635.8]
                                        data_arrival_time   = page.within_bbox(Arrival_Time).extract_text()
                                        Route               = [28.8,638.9,140.5,685.7]
                                        data_route          = page.within_bbox(Route).extract_text()
                                        Cycle               = [156.1,638.9,222.2,685.7]
                                        data_cycle          = page.within_bbox(Cycle).extract_text()
                                        Supplier_Data_F2    = [15.6,736.8,222.2,770.4]
                                        data_supplier_f2    = page.within_bbox(Supplier_Data_F2).extract_text()
                                        Printed_at_Supplier = [15.6,770.4,222.2,784.9]
                                        data_print_supplier = page.within_bbox(Printed_at_Supplier).extract_text()
                                        Part_Number_Code    = [229.8,613.5,457.1,636.1]
                                        data_number_code    = page.within_bbox(Part_Number_Code).extract_text()
                                        Part_Number_Seq     = [457.1,613.5,489.6,636.1]
                                        data_number_seq     = page.within_bbox(Part_Number_Seq).extract_text()
                                        Part_Number_Name    = [229.8,636.1,489.6,667.6]
                                        data_number_name    = page.within_bbox(Part_Number_Name).extract_text()
                                        Unique_No           = [243.8,671.1,403.1,724.6]
                                        data_unique_no      = page.within_bbox(Unique_No).extract_text()
                                        Barcode             = [408.2,671.1,489.6,724.6]
                                        data_barcode        = page.within_bbox(Barcode).extract_text()
                                        Pcs_Kanban          = [229.8,742.1,294.8,770.4]
                                        data_pcs_kanban     = page.within_bbox(Pcs_Kanban).extract_text()
                                        Order_No            = [307.4,727.6,434.1,770.4]
                                        data_order_no       = page.within_bbox(Order_No).extract_text()
                                        Dock_Code           = [414.6,540.1,489.1,610.1]
                                        data_dock_code      = page.within_bbox(Dock_Code).extract_text()
                                        Progress_Lane_No    = [507.7,540.1,584.8,610.1]
                                        data_lane_no        = page.within_bbox(Progress_Lane_No).extract_text()
                                        Out                 = [507.7,610.1,584.8,675.5]
                                        data_out            = page.within_bbox(Out).extract_text()
                                        Manifest_No         = [497.1,651.1,584.8,672.1]
                                        data_manifest_no    = page.within_bbox(Manifest_No).extract_text()
                                        Conveyance_No       = [507.7,677.1,584.8,724.6]
                                        data_conveyance_no  = page.within_bbox(Conveyance_No).extract_text()
                                        Part_Address        = [453.1,727.6,584.8,770.4]
                                        data_part_address   = page.within_bbox(Part_Address).extract_text()
                                        x3_min, y3_min, x3_max, y3_max = 408.2, 671.1, 489.6, 724.6
                                        img3 = page.to_image()
                                        img_cv3 = np.array(img3.original)
                                        img_cv3 = cv2.cvtColor(img_cv3, cv2.COLOR_BGR2RGB)
                                        cropped_img3 = img_cv3[int(y3_min):int(y3_max), int(x3_min):int(x3_max)]
                                        qr_codes_3=[]
                                        if cropped_img3.size > 0:
                                            qr_codes_3.extend(self.decode_qr_code(cropped_img3))

                                        exist_record = self.env['content.card.tmmin'].search([('scan_id','=', seq_scan),('unique_no','=', data_unique_no)])
                                        if not exist_record :
                                            num = num+1
                                        else :
                                            num = num

                                        self.env['content.card.tmmin'].create({  
                                                                                'supplier_name'     : data_supplier_name,
                                                                                'supplier_code'     : data_supplier_code,
                                                                                'departure_time'    : data_departure_time,
                                                                                'arrival_time'      : data_arrival_time,
                                                                                'route'             : data_route,
                                                                                'cycle'             : data_cycle,
                                                                                'supplier_info'     : data_supplier_f2,
                                                                                'dock_code'         : data_dock_code,
                                                                                'part_code'         : data_number_code,
                                                                                'part_name'         : data_number_name,
                                                                                'part_sequence'     : data_number_seq,
                                                                                'unique_no'         : data_unique_no,
                                                                                'pcs_kanban'        : data_pcs_kanban,
                                                                                'order_no'          : data_order_no,
                                                                                'qr_code'           : data_barcode[::-1],
                                                                                'progres_lane_no'   : data_lane_no,
                                                                                'out_time'          : data_out,
                                                                                'manifest_no'       : data_manifest_no,
                                                                                'conveyance_no'     : data_conveyance_no,
                                                                                'part_address'      : data_part_address,
                                                                                'printed'           : data_print_supplier,
                                                                                'scan_id'           : seq_scan,
                                                                                'unique_no_seq'     : num,
                                                                                'real_qr_code'      : qr_codes_3[0],
                                                                                            
                                                                                        })

                                    else :
                                        _logger.info('==========================Data Tidak Ada=====================================')

                                message = _("Scan Data Success !!")
                                return {
                                                    'type': 'ir.actions.client',
                                                    'tag': 'display_notification',
                                                    'params': {
                                                        'message': message,
                                                        'type': 'success',
                                                        'sticky': False,
                                                    }
                                                }


                        else :
                            message = _("Contact Customer Tidak Ditemukan !!")
                            return {
                                                'type': 'ir.actions.client',
                                                'tag': 'display_notification',
                                                'params': {
                                                    'message': message,
                                                    'type': 'info',
                                                    'sticky': False,
                                                }
                                            }

                    else :
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




        return rv

