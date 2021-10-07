# -*- coding: utf-8 -*-
{
    'name': 'Connectividad',
    'version': '13',
    'summary': '',
    'category': 'Inventory',
    'author': 'JackDevelopers',
    'maintainer': 'JackDevelopers',
    'company': 'JackDevelopers',
    'website': 'https://www.jackdevelopers.com',
    'depends': ['stock', 'product','account', 'sale'],
    'data': [
        'data/sequence.xml',
        'views/account_payment.xml',
        'views/res_bank.xml',
        'views/sale_order_view.xml',
    ],
    'license': 'AGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
