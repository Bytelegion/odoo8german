# -*- coding: utf-8 -*-
# Part of Odoo. Developed by ecoservice (Uwe Böttcher und Falk Neubert GbR).
# See COPYRIGHT and LICENSE at the top level of this module for full copyright and licensing details.

from openerp import fields, models


class ResCompany(models.Model):
    """ Inherits the res.company class and adds methods and attributes
    """
    _inherit = 'res.company'

    finance_interface = fields.Selection(selection=[])
    journal_ids = fields.Many2many(comodel_name='account.journal',
                                   relation='res_company_account_journal',
                                   column1='res_company_id',
                                   column2='account_journal_id',
                                   string='Default Journals',
                                   domain="[('company_id', '=', company_id)]")
