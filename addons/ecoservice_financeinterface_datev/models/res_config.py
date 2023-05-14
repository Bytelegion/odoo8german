# -*- coding: utf-8 -*-
# Part of Odoo. Developed by ecoservice (Uwe Böttcher und Falk Neubert GbR).
# See COPYRIGHT and LICENSE at the top level of this module for full copyright and licensing details.

from openerp import fields, models


class EcoserviceFinanceInterfaceConfigSettings(models.TransientModel):
    _inherit = 'ecoservice.finance.interface.config.settings'

    company_exportmethod = fields.Selection(related='company_id.exportmethod')
    company_enable_datev_checks = fields.Boolean(related='company_id.enable_datev_checks')
    company_datev_ignore_currency = fields.Boolean(related='company_id.datev_ignore_currency')
    company_skr_no = fields.Selection(related='company_id.skr_no')
    datev_client_no = fields.Char(related='company_id.datev_client_no')
    datev_consultant_no = fields.Char(related='company_id.datev_consultant_no')
