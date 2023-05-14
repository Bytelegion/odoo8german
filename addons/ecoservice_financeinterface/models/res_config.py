# -*- coding: utf-8 -*-
# Part of Odoo. Developed by ecoservice (Uwe Böttcher und Falk Neubert GbR).
# See COPYRIGHT and LICENSE at the top level of this module for full copyright and licensing details.

from openerp import fields, models


class EcoserviceFinanceInterfaceConfigSettings(models.TransientModel):
    _name = 'ecoservice.finance.interface.config.settings'
    _inherit = 'res.config.settings'

    company_id = fields.Many2one(comodel_name='res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)

    company_finance_interface = fields.Selection(related='company_id.finance_interface')
    company_journal_ids = fields.Many2many(related='company_id.journal_ids')
