# -*- coding: utf-8 -*-
# Part of Odoo. Developed by ecoservice (Uwe Böttcher und Falk Neubert GbR).
# See COPYRIGHT and LICENSE at the root directory of this module for full copyright and licensing details.

{
    'name': 'ecoservice: Financial Interface Migration',
    'summary': 'Convert existing accounting entries to Datev',
    'version': '8.0.1.0.0',
    'author': 'ecoservice',
    'website': 'https://www.ecoservice.de',
    'license': 'AGPL-3',
    'category': 'Accounting',
    'depends': [
        'base',
        'account',
        'account_cancel',
        'ecoservice_financeinterface',
    ],
    'data': [
        'views/res_company_view.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
}
