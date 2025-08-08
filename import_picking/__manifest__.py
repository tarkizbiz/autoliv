# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Import Picking(Shipment/Delivery) from Excel or CSV File',
    'version': '17.0.0.0',
    'category': 'Warehouse',
    'summary': 'Apps for import picking import delivery import stock import product stock import receipt import picking with serial number import DO import picking from excel import internal transfer import serial number with picking import lot number',
    'description': """
	BrowseInfo developed a new Odoo/OpenERP module apps.
	This apps helps to 
    odoo import incoming shipment and delivery order from Excel or CSV file.
    odoo import receipt odoo import delivery order odoo import internal transfer odoo import stock 
    odoo import inventory operation odoo import operation import on odoo
	This module use for 
    odoo import bulk picking from Excel file Import Delivery order from CSV or Excel file.
	Import Shipment Import incoming shipment Import Delivery Orders Import Internal Transfer.
    odoo Add Excel from Picking Add CSV file Import picking data Import excel file

    odoo import incoming shipment and delivery order from Excel or CSV file.
    This module use for 
    odoo import bulk picking from Excel file Import Delivery order from CSV or Excel file.
    odoo Import Shipment Import incoming shipment Import Delivery Orders Import Internal Transfer.
    odoo Add Excel from Picking odoo Add CSV file.Import picking data odoo Import excel file
    This module is useful for 
    odoo import inventory with serial number from Excel and CSV file .
    odoo Import Stock from CSV and Excel Import Stock inventory from CSV and Excel file.
    odoo Import inventory adjustment import stock balance Import oΩpening stock balance from CSV and Excel file.
    Inventory import from CSV stock import from CSV Inventory adjustment import Opening stock import Import warehouse stock import
    odoo Import product stock Manage Inventory import inventory with lot number import inventory with serial number import inventory adjustment with serial number
    odoo serila number import inventory adjustment with lot number import inventory data import stock data import 
    odoo import opening stock with lot number import lot number import serial number. 
    Odoo import transfer import stock transfer import receipt import odoo import stock transfers import tranfers
    This apps helps to import incoming shipment and delivery order with lot number from Excel or CSV file.
    odoo import shipment with lot number import shipment with serial number import delivery with lot number
    odoo import delivery with serial number Import stock with Serial number import Import stock with lot number import
    odoo import lot number with stock import import serial number with stock import
    odoo import lines import import order lines import import orders lines import import so lines import
    odoo imporr po lines import import invoice lines import import invoice line import import incoming shipment with lot number
    odoo import incoming shipment with serial number import delivery order with lot number import delivery order with serial numner
    odoo import internal Transfer with lot number import internal Transfer with serial number import internal picking with lot number
    odoo import internal picking with serial numner

    This module use for 
    odoo import bulk picking with serial number from Excel file Import Delivery order with lot/serial number from CSV or Excel file.
    odoo Import Shipment with lot number Import incoming shipment Import Delivery Orders Import Internal Transfer with serial number.
    odoo Add Excel from Picking Add CSV file Import picking data Import excel file odoo
    This module is useful for import inventory with serial number from Excel and CSV file .
    Import Stock from CSV and Excel file. odoo import picking with lot number odoo import picking with serial number
	-
    import pickings
    import delivery order
    import do
    import csv
    """,
    'author': 'BrowseInfo',
    'website': 'https://www.browseinfo.com',
    "price": 12,
    "currency": 'EUR',
    'depends': ['base', 'stock','documents'],
    'data': [
        'security/ir.model.access.csv',
        'data/attachment_sample.xml',
        'views/picking_view.xml',
    ],
    "license": 'OPL-1',
    'installable': True,
    'auto_install': False,
    'live_test_url': 'https://youtu.be/VUOifT3sx2c',
    "images": ["static/description/Banner.gif"],
}
