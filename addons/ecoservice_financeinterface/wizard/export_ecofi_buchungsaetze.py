# -*- coding: utf-8 -*-
# Part of Odoo. Developed by ecoservice (Uwe Böttcher und Falk Neubert GbR).
# See COPYRIGHT and LICENSE at the top level of this module for full copyright and licensing details.

from openerp import api, fields, models
import time


class ExportEcofi(models.TransientModel):
    _name = 'export.ecofi'
    _description = 'Financeexport'

    def _get_default_journal(self):
        if self.env.user.company_id.finance_interface:
            return self.env.user.company_id.journal_ids

    def _get_default_vorlauf(self):
        vorlauf = False
        if 'active_model' in self.env.context and 'active_id' in self.env.context:
            if self.env.context['active_model'] == 'ecofi':
                vorlauf = self.env.context['active_id']
        return vorlauf

    vorlauf_id = fields.Many2one(comodel_name='ecofi', string='Vorlauf', readonly=True, default=_get_default_vorlauf)
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda r: r.env.user.company_id)
    journal_id = fields.Many2many(comodel_name='account.journal',
                                  relation='export_ecofi_journal_rel',
                                  column1='export_ecofi_id',
                                  column2='journal_id',
                                  string='Journals',
                                  default=_get_default_journal)
    export_type = fields.Selection(selection=[('date', 'Datum')], string='Export Type', required=True, default='date')
    date_from = fields.Date('Date From', default=lambda *a: time.strftime('%Y-%m-01'))
    date_to = fields.Date('Date To', default=lambda *a: time.strftime('%Y-%m-%d'))

    @api.multi
    def startexport(self):
        """ Start the export through the wizard
        """
        for export in self:
            vorlauf = self.env['ecofi'].ecofi_buchungen(
                journal_ids=export.journal_id,
                vorlauf_id=export.vorlauf_id or False,
                date_from=export.date_from if export.export_type == 'date' else False,
                date_to=export.date_to if export.export_type == 'date' else False
            )
        return {
            'name': 'Financial Export Invoices',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': False,
            'res_model': 'ecofi',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'res_id': vorlauf.id if vorlauf else vorlauf,
        }
