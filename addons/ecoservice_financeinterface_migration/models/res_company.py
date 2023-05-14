# -*- coding: utf-8 -*-
# Part of Odoo. Developed by ecoservice (Uwe Böttcher und Falk Neubert GbR).
# See COPYRIGHT and LICENSE at the root directory of this module for full copyright and licensing details.

from openerp import api, fields, models, _
from openerp.addons.ecoservice_financeinterface.models.exceptions import FinanceinterfaceException
from datetime import datetime


class ResCompany(models.Model):
    _inherit = 'res.company'

    entries_converted = fields.Boolean(string='Entries converted')
    entries_convert_msg = fields.Text(string='Convert message')

    @api.multi
    def convert_account_moves(self):
        self.ensure_one()
        msg = list()
        account_move_obj = self.env['account.move']
        account_journal_obj = self.env['account.journal']

        journal_ids = account_journal_obj.search([('company_id', '=', self.id)])
        for journal in journal_ids:
            journal_update_posted_pre = journal.update_posted
            if not journal.update_posted:
                journal.update_posted = True
            if journal.update_posted:
                move_ids = account_move_obj.search([
                    ('state', '=', 'posted'),
                    ('company_id', '=', self.id),
                    ('journal_id', '=', journal.id),
                    ('vorlauf_id', '=', False)])
                for move in move_ids:
                    try:
                        move.button_cancel()
                        move.post()
                    except FinanceinterfaceException as E:
                        move.write({'ecofi_to_check': True})
                        msg.append(_(u'Exception: ID {move} --> {exception}\n').format(move=move.id, exception=E))

            if not journal_update_posted_pre:
                journal.update_posted = journal_update_posted_pre

        if msg:
            new_msg = u'{date}\n{msg}\n'.format(date=str(datetime.today().date()), msg='\n'.join(msg))
        else:
            new_msg = u'{date}\nOK!\n'.format(date=str(datetime.today().date()))

        self.write({
            'entries_converted': True,
            'entries_convert_msg': u'{pre}\n{msg}'.format(pre=self.entries_convert_msg or '', msg=new_msg)
        })
