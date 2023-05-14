# -*- coding: utf-8 -*-
# Part of Odoo. Developed by ecoservice (Uwe Böttcher und Falk Neubert GbR).
# See COPYRIGHT and LICENSE at the top level of this module for full copyright and licensing details.

{
    'name': 'ecoservice: Financial Interface Datev',
    'summary': 'Export of account moves to Datev',
    'version': '8.0.1.5.3',
    'author': 'ecoservice',
    'website': 'https://www.ecoservice.de',
    'license': 'Other proprietary',
    'category': 'Accounting',
    'depends': [
        'mail',
        'ecoservice_financeinterface',
    ],
    'data': [
        'views/account_cron.xml',
        'views/account_invoice_view.xml',
        'views/account_view.xml',
        'views/ecofi_sequence.xml',
        'views/ecofi_view.xml',
        'views/res_company_view.xml',
        'views/res_config_view.xml',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
    'price': 625,
    'currency': 'EUR',
}
