# -*- coding: utf-8 -*-
# Part of Odoo. Developed by ecoservice (Uwe Böttcher und Falk Neubert GbR).
# See COPYRIGHT and LICENSE at the top level of this module for full copyright and licensing details.

from openerp import api, fields, models


class ResCompany(models.Model):
    """ Inherits the res.company class and adds methods and attributes
    """
    _inherit = 'res.company'

    finance_interface = fields.Selection(selection_add=[('datev', 'Datev')], string='Financial Interface')
    exportmethod = fields.Selection(selection=[('netto', 'netto'), ('brutto', 'brutto')], string='Export method', default='brutto')
    enable_datev_checks = fields.Boolean(string='Perform Datev Checks', default=True)
    datev_ignore_currency = fields.Boolean(string='Ignore Currency', help="If set the export currency will always be the company's default currency")
    datev_client_no = fields.Char(string='Client No.', size=5)
    datev_consultant_no = fields.Char(string='Consultant No.', size=7)
    skr_no = fields.Selection([('03', '03'), ('04', '04')], required=True)
