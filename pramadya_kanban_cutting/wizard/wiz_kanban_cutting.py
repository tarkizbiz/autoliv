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

class WizKanbanCutting(models.TransientModel):
    _name = 'wiz.kanban.cutting'
    _description = 'Print Kanban Cutting'

    pdf_file = fields.Binary("PDF File")
    pdf_name = fields.Char("PDF Name")
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')

    def kanban_potong(self):
        # # file_name = self.pdf_name
        # # with open(file_name, "wb") as in_f:
        # filename = self.attachment_ids[0].name
        # directory = "splitted/" + filename
        # self.split(directory)
        # atth = self.attachment_ids[0]
        # file_attch = self.env['ir.attachment']
        # full_path = file_attch._full_path(atth.store_fname)
        # pdfFileObj = open(full_path, 'rb')
        # input1 = PdfFileReader(pdfFileObj)
        # raise UserError("input1"%input1)
        # output = PdfFileWriter()
        # numPages = input1.getNumPages()
        # x, y, w, h = (23, 16, 573, 189)
        # page_x, page_y = input1.getPage(0).cropBox.getUpperLeft()
        # upperLeft = [page_x.as_numeric(), page_y.as_numeric()] # convert PyPDF2.FloatObjects into floats
        # new_upperLeft  = (upperLeft[0] + x, upperLeft[1] - y)
        # new_lowerRight = (new_upperLeft[0] + w, new_upperLeft[1] - h)
        # for i in range(numPages):
        #     page = input1.getPage(i)
        #     page.cropBox.upperLeft  = new_upperLeft
        #     page.cropBox.lowerRight = new_lowerRight
        #     output.addPage(page)
        # with open("out.pdf", "wb") as out_f:
        #     output.write(out_f)
        if not self.pdf_file:
            print("No PDF content available in the binary field.")
            return
        
        pdf_data = base64.b64decode(self.pdf_file)
        input_pdf = PdfFileReader(io.BytesIO(pdf_data))
        input2 = PdfFileReader(io.BytesIO(pdf_data))
        input3 = PdfFileReader(io.BytesIO(pdf_data))
        output_pdf = PdfFileWriter()
        num_pages = len(input_pdf.pages)
        x, y, w, h = (11.4, 5.4, 575.8, 260)            #baris 1
        x1, y1, w1, h1 = (11.4, 265.4, 575.8, 260)      #baris 2
        x2, y2, w2, h2 = (11.4, 525.4, 575.8, 260)      #baris 3
        #baris 1
        page_x, page_y = input_pdf.getPage(0).cropBox.getUpperLeft()
        upper_left = [page_x.as_numeric(), page_y.as_numeric()]
        new_upper_left = (upper_left[0] + x, upper_left[1] - y)
        new_lower_right = (new_upper_left[0] + w, new_upper_left[1] - h)
        #baris 2
        page_x1, page_y1 = input2.getPage(0).cropBox.getUpperLeft()
        upper_left = [page_x1.as_numeric(), page_y1.as_numeric()]
        new_upper_left_1 = (upper_left[0] + x1, upper_left[1] - y1)
        new_lower_right_1 = (new_upper_left_1[0] + w1, new_upper_left_1[1] - h1)
        #baris 3
        page_x2, page_y2 = input2.getPage(0).cropBox.getUpperLeft()
        upper_left = [page_x2.as_numeric(), page_y2.as_numeric()]
        new_upper_left_2 = (upper_left[0] + x2, upper_left[1] - y2)
        new_lower_right_2 = (new_upper_left_2[0] + w2, new_upper_left_2[1] - h2)

        for i in range(num_pages):
            #baris 1
            page = input_pdf.getPage(i)
            page.cropBox.upperLeft = new_upper_left
            page.cropBox.lowerRight = new_lower_right
            output_pdf.addPage(page)
            #baris 2
            page = input2.getPage(i)
            page.cropBox.upperLeft = new_upper_left_1
            page.cropBox.lowerRight = new_lower_right_1
            output_pdf.addPage(page)
            #baris 3
            page = input3.getPage(i)
            page.cropBox.upperLeft = new_upper_left_2
            page.cropBox.lowerRight = new_lower_right_2
            output_pdf.addPage(page)

        output_stream = io.BytesIO()
        output_pdf.write(output_stream)
        output_stream.seek(0)
        output_pdf_base64 = base64.b64encode(output_stream.read()).decode('utf-8')

        # raise UserError("Processed PDF saved as an attachment successfully.")
        attachment = self.env['ir.attachment'].create({
            'name': 'out.pdf',
            'type': 'binary',
            'datas': output_pdf_base64,
            'res_model': 'wiz.kanban.cutting',
            'res_id': self.id,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/{}?download=true'.format(attachment.id),
            'target': 'self',
        }

    
