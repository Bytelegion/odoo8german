# -*- coding: utf-8 -*-
# Part of Odoo. Developed by ecoservice (Uwe Böttcher und Falk Neubert GbR).
# See COPYRIGHT and LICENSE at the top level of this module for full copyright and licensing details.

from openerp import api, fields, models, _
from . import exceptions
import openerp.addons.decimal_precision as dp


class AccountMove(models.Model):
    """ Inherits the account.move class and adds methods and attributes
    """
    _inherit = 'account.move'

    vorlauf_id = fields.Many2one(comodel_name='ecofi', string='Export', readonly=True, copy=False, ondelete='set null')
    ecofi_buchungstext = fields.Char(string='Export Voucher Text', size=60)
    ecofi_manual = fields.Boolean(string='Set Counter accounts manually')
    ecofi_autotax = fields.Boolean(string='Automatic Tax Lines')
    ecofi_to_check = fields.Boolean(string='To Check')
    export_mismatch = fields.Float(string="Rounding mismatch at export", readonly=1)
    export_mismatch_reason = fields.Char(string='Mismatch reason', readonly=1)
    # should be copied but as the model already contains a field with comodel 'account.move.line' and this one is always a subset,
    # it produce an error while copying
    # see as reference:
    # odoo/odoo/models.py > def copy(
    # odoo/odoo/models.py > def copy_data(
    export_mismatch_lines = fields.One2many(comodel_name='account.move.line', inverse_name='move_id', string='Journal Items')  # , copy=True)

    @api.multi
    def unlink(self):
        """Method that prevents that account_moves which have been exported are being deleted
        """
        for thismove in self:
            if self.env.context.get('delete_none', False):
                continue
            if thismove.vorlauf_id:
                raise exceptions.FinanceinterfaceException(_(u'Warning! Account moves which are already in an export can not be deleted!'))
        return super(AccountMove, self).unlink()

    def financeinterface_test_move(self, move):
        """ Test if the move account counterparts are set correct """
        res = ''
        checkdict = {}
        for line in move.line_id:
            if line.account_id and line.ecofi_account_counterpart:
                if line.account_id.id != line.ecofi_account_counterpart.id:
                    if line.ecofi_account_counterpart.id not in checkdict:
                        checkdict[line.ecofi_account_counterpart.id] = {}
                        checkdict[line.ecofi_account_counterpart.id]['check'] = 0
                        checkdict[line.ecofi_account_counterpart.id]['real'] = 0
                    checkdict[line.ecofi_account_counterpart.id]['check'] += line.debit - line.credit
                else:
                    if line.ecofi_account_counterpart.id not in checkdict:
                        checkdict[line.ecofi_account_counterpart.id] = {}
                        checkdict[line.ecofi_account_counterpart.id]['check'] = 0
                        checkdict[line.ecofi_account_counterpart.id]['real'] = 0
                    checkdict[line.ecofi_account_counterpart.id]['real'] += line.debit - line.credit
            else:
                res += _(u'Not all move lines have an account and an account counterpart defined.')
                return res
        for key in checkdict:
            if abs(checkdict[key]['check'] + checkdict[key]['real']) > 10 ** -4:
                res += _(u'The sum of the account lines debit/credit and the account_counterpart lines debit/credit is no Zero!')
                return res
        return False

    def finance_interface_checks(self):
        """Hook Method for different checks which is called if the moves post method is called """
        for move in self:
            if len(move.line_id) == 0:  # There is actually the possibility to post account moves w/o move lines
                continue
            thiserror = ''
            if move.ecofi_manual is False:
                error = self.env['ecofi'].set_main_account(move)
                if error:
                    thiserror += error
                if thiserror != '':
                    raise exceptions.FinanceinterfaceException(_(u'Error! {error}'.format(error=thiserror)))
            error = self.financeinterface_test_move(move)
            if error:
                raise exceptions.FinanceinterfaceException(_(u'Error! {error}'.format(error=error)))
        return True

    @api.multi
    def button_cancel(self):
        """Check if the move has already been exported"""
        res = super(AccountMove, self).button_cancel()
        for move in self:
            if move.vorlauf_id:
                raise exceptions.FinanceinterfaceException(_(u'Error! You cannot modify an already exported move.'))
            if move.ecofi_autotax:
                for line in move.line_id:
                    if line.ecofi_move_line_autotax:
                        line.delete_autotaxline()
        return res

    @api.multi
    def post(self):
        """ If a move is posted to a journal the Datev corresponding checks are being performed.
        """
        self.finance_interface_checks()
        res = super(AccountMove, self).post()
        return res


class AccountMoveLine(models.Model):
    """Inherits the account.move.line class and adds attributes
    """
    _inherit = 'account.move.line'

    @api.multi
    def name_get(self):
        if self.env.context.get('counterpart_name'):
            result = []
            for line in self:
                if line.ref:
                    result.append((line.id, (line.name or '') + ' (' + line.ref + ')'))
                else:
                    result.append((line.id, line.name))
            return result
        return super(AccountMoveLine, self).name_get()

    ecofi_taxid = fields.Many2one(comodel_name='account.tax', string='Move Tax')
    ecofi_brutto_credit = fields.Float(string='Amount Credit Brutto', digits=dp.get_precision('Account'))
    ecofi_brutto_debit = fields.Float(string='Amount Debit Brutto', digits=dp.get_precision('Account'))
    ecofi_account_counterpart = fields.Many2one(comodel_name='account.account', string='Account Counterpart', ondelete='restrict')
    ecofi_move_line_autotax = fields.Many2one(comodel_name='account.move.line', string='Move Counterpart', ondelete='cascade')
    ecofi_manual = fields.Boolean(related='move_id.ecofi_manual', string='Manual', store=True)

    @api.model
    def create(self, vals):
        tax_id = vals.get('account_tax_id', False)
        if tax_id > 0 and not vals.get('ecofi_taxid'):
            vals['ecofi_taxid'] = tax_id
        return super(AccountMoveLine, self).create(vals)

    @api.multi
    def delete_autotaxline(self):
        """ Method that deletes the corresponding auto generated tax moves"""
        for move_line in self:
            move_line_main = move_line.ecofi_move_line_autotax
            update = {
                'debit': move_line_main.ecofi_brutto_debit,
                'credit': move_line_main.ecofi_brutto_credit,
                'tax_amount': 0.00,
            }
            move_line.unlink()
            move_line_main.write(update)
        return True


class AccountInvoice(models.Model):
    """ Inherits the account.invoice class and adds methods and attributes
    """
    _inherit = 'account.invoice'

    ecofi_buchungstext = fields.Char(string='Export Voucher Text', size=60)

    @api.multi
    def action_move_create(self):
        """Extends the original action_move_create so that if
         an invoice is confirmed the finance interface attributes are transfered to the account move
        """
        thisreturn = super(AccountInvoice, self).action_move_create()
        if thisreturn:
            for invoice in self:
                invoice.move_id.write({'ecofi_buchungstext': invoice.ecofi_buchungstext or False})
        return thisreturn

    def inv_line_characteristic_hashcode(self, invoice_line):
        """Transfers the line tax to the hash code
        :param invoice: Invoice Object
        :param invoice_line: Invoice Line Object
        """
        res = super(AccountInvoice, self).inv_line_characteristic_hashcode(invoice_line)
        res += u"-{tax_id}".format(tax_id=invoice_line.get('ecofi_taxid', "False"))
        return res

    @api.model
    def line_get_convert(self, line, part, date):
        """Extends the line_get_convert method that it transfers the tax to the account_move_line
        """
        res = super(AccountInvoice, self).line_get_convert(line, part, date)
        if line.get('tax_ids', False):
            for tax in line.get('tax_ids', False):
                res['ecofi_taxid'] = tax[1]
        return res

    @api.model
    @api.onchange('fiscal_position_id', 'invoice_line_id')
    def onchange_fiscal_position_id(self):
        if self.state != 'draft' and self.fiscal_position_id:
            available_accounts = self.fiscal_position_id.account_ids.mapped('account_dest_id').ids
            account_name_list = self.invoice_line_id.filtered(lambda l: l.account_id.id not in available_accounts).mapped('account_id.name')
            if account_name_list:
                _msg = _(u'The following invoice line accounts does not match the available fiscal position accounts:')
                _msg = u'{msg}\n{join}'.format(
                    msg=_msg,
                    join=u'\n- '.join(account_name_list),
                )
                raise exceptions.FinanceinterfaceException(_msg)


class AccountInvoiceLine(models.Model):
    """ Inherits the account.invoice.line class and adds methods and attributes
    """
    _inherit = 'account.invoice.line'

    @api.model
    def create(self, vals):
        """Prevent that a user places two different taxes in an invoice line
        """
        if vals.get('invoice_line_tax_ids', False):
            if len(vals['invoice_line_tax_ids'][0]) > 1 and len(vals['invoice_line_tax_ids'][0][2]) > 1:
                raise exceptions.FinanceinterfaceException(_(u'Error! There can only be one tax per invoice line'))
        result = super(AccountInvoiceLine, self).create(vals)
        return result

    @api.multi
    def write(self, vals):
        """Prevent that a user places two different taxes in an invoice line
        """
        if vals.get('invoice_line_tax_ids', False):
            if len(vals['invoice_line_tax_ids'][0]) > 1 and len(vals['invoice_line_tax_ids'][0][2]) > 1:
                raise exceptions.FinanceinterfaceException(_(u'Error! There can only be one tax per invoice line'))
        return super(AccountInvoiceLine, self).write(vals)


class AccountTax(models.Model):
    """Inherits the account.tax class and adds attributes
    """
    _inherit = 'account.tax'

    buchungsschluessel = fields.Integer(string='Posting key', required=True, default=-1)
