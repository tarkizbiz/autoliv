# -*- coding: utf-8 -*-
{
    'name': "Autoliv e-kanban",

    'summary': """
        Odoo AID E-Kanban PT Autoliv Indonesia""",

    'description': """
        Interfacing E-Kanban in Odoo System and Integration to L2L Aplication
    """,

    'author': "Pramadya Teknologi Indonesia",
    'website': "https://www.pramadya.co.id",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Inventory',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','stock','documents','web','web_gantt','mrp'],

    # always loaded
    'data': [
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'data/workflow_data.xml',
        'data/ir_cron_data.xml',
        'views/ocr.xml',
        'views/master.xml',
        'views/lot.xml',
        'views/rail.xml',
        'views/collect.xml',
        'views/adjustment.xml',
        'views/wip.xml',
        'wizard/merge_rail_view.xml',
    ],

    "assets": {
        "web._assets_primary_variables": [
            "pramadya_ekanban/static/src/css/style.scss",
        ],
        "web.assets_backend": [
            'pramadya_ekanban/static/src/js/warning_dialog.js',
            'pramadya_ekanban/static/src/js/dialog.js',
            'pramadya_ekanban/static/src/js/kanban_model.js',
        ],
    },
    
    'application': True,
    'external_dependencies': {'python': ['tabula-py']},
    
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'license': 'LGPL-3',
}
