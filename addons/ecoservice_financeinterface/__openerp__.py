# -*- coding: utf-8 -*-
# Part of Odoo. Developed by ecoservice (Uwe Böttcher und Falk Neubert GbR).
# See COPYRIGHT and LICENSE at the top level of this module for full copyright and licensing details.

# noinspection PyStatementEffect
{
    'name': 'ecoservice: Financial Interface',
    'summary': 'Main Modul for export of accounting moves',
    'version': '8.0.1.2.3',
    'author': 'ecoservice',
    'website': 'www.ecoservice.de',
    'license': 'Other proprietary',
    'category': 'Accounting',
    'depends': [
        'base',
        'account'
    ],
    'data': [
        'security/ecofi_security.xml',
        'security/ir.model.access.csv',
        'views/account_view.xml',
        'views/account_invoice_view.xml',
        'views/ecofi_sequence.xml',
        'views/ecofi_view.xml',
        'views/menu.xml',
        'views/res_company_view.xml',
        'views/res_config_view.xml',
        'wizard/wizard_view.xml'
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
    'price': 62.5,
    'currency': 'EUR',
}
