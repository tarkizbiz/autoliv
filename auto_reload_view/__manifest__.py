{
    'name': 'Auto Reload List & Kanban View',
    'summary': 'Auto reload view without any setting on the backend. '
               'Individual user can select the timer reload from List & Kanban view.',
    'description': 'Auto Reload View without any setting in backend. '
                   'Individual user can select the timer reload from List & Kanban view. '
                   'Keep search condition when reload view.',
    'author': "Sonny Huynh",
    'category': 'Extra Tools',
    'version': '0.1',
    'depends': ["base"],
    'data': [],

    'assets': {
        'web.assets_backend': [
            'auto_reload_view/static/src/js/worker_timeout.js',
            'auto_reload_view/static/src/js/auto_reload_kanban_controller.js',
            'auto_reload_view/static/src/js/auto_reload_list_controller.js',

            'auto_reload_view/static/src/xml/auto_reload.xml',
        ],
    },

    'support': 'huynh.giang.son.gs@gmail.com',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'price': 75.00,
    'currency': 'EUR',
}