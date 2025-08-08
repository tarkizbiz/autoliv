from odoo import models, fields, api
from datetime import datetime, timedelta

class Document(models.Model):
    _inherit = 'documents.document'

    def delete_docs_cron(self):
        already_30_days = datetime.now() - timedelta(days=30)
        print("--30 days back--",already_30_days)
        search_docs = self.env['documents.document'].search([('create_date','<=',already_30_days)])
        for docs in search_docs:
            if docs.folder_id.name in ['Scanned Delivery','Delivery']:
                print("-----------",docs.name, docs.create_date + timedelta(hours=+7))
                docs.sudo().unlink()