# -*- coding: utf-8 -*-
# Part of Odoo. Developed by ecoservice (Uwe Böttcher und Falk Neubert GbR).
# See COPYRIGHT and LICENSE at the top level of this module for full copyright and licensing details.

from decimal import Decimal
from openerp import api, fields, models, _
from . import exceptions


class AccountAccount(models.Model):
    """Inherits the account.account class and adds attributes
    """
    _inherit = 'account.account'

    ustuebergabe = fields.Boolean(string='Datev VAT-ID',
                                  help=_(u'Is required when transferring a sales tax identification number from the account partner (e.g. EU-Invoice)'))
    automatic = fields.Boolean(string='Datev Automatic Account')
    datev_steuer = fields.Many2one(comodel_name='account.tax', string='Datev Tax Account', domain=[('buchungsschluessel', '!=', -1)])
    datev_steuer_erforderlich = fields.Boolean(string='Tax posting required?')

    def cron_update_line_autoaccounts_tax(self):
        """Method for Cronjob that Updates all account.move.lines
        without ecofi_taxid of Accounts where automatic is True and a datev_steuer
        """
        for account in self.search([('automatic', '=', True), ('datev_steuer', '!=', False)]):
            move_line_ids = self.env['account.move.line'].search([('account_id', '=', account.id), ('ecofi_taxid', '=', False)])
            if move_line_ids:
                move_line_ids.write({'ecofi_taxid': account.datev_steuer.id})


class AccountTax(models.Model):
    """Inherits the account.tax class and adds attributes
    """
    _inherit = 'account.tax'

    datev_skonto = fields.Many2one(comodel_name='account.account', string='Datev Cashback Account')


class AccountPaymentTerm(models.Model):
    """Inherits the account.payment.term class and adds attributes
    """
    _inherit = 'account.payment.term'

    zahlsl = fields.Integer(string='Payment key')


class AccountMove(models.Model):
    """ Inherits the account.move class to add checking methods to the original post method
    """
    _inherit = 'account.move'

    enable_datev_checks = fields.Boolean(string='Perform Datev Checks', default=True)

    def datev_account_checks(self, move):
        errors = list()
        self.update_line_autoaccounts_tax(move)
        for linecount, line in enumerate(move.line_id, start=1):
            if line.account_id.id != line.ecofi_account_counterpart.id:
                if not self.env['ecofi'].is_taxline(line.account_id.id) or line.ecofi_bu == 'SD':
                    linetax = self.env['ecofi'].get_line_tax(line)
                    if line.account_id.automatic and not line.account_id.datev_steuer:
                        errors.append(_(u'The account {account} is an Auto-Account but the automatic taxes are not configured!').format(account=line.account_id.code))
                    if line.account_id.datev_steuer_erforderlich and not linetax:
                        errors.append(_(u'The Account requires a tax but the move line {line} has no tax!').format(line=linecount))
                    if line.account_id.automatic and linetax:
                        if not line.account_id.datev_steuer or linetax.id != line.account_id.datev_steuer.id:
                            errors.append(_(
                                u'The account is an Auto-Account but the tax account ({line}) in the move line {tax_line} differs from the configured {tax_datev}!').format(
                                    line=linecount, tax_line=linetax.name, tax_datev=line.account_id.datev_steuer.name))
                    if line.account_id.automatic and not linetax:
                        errors.append(_(u'The account is an Auto-Account but the tax account in the move line {line} is not set!').format(line=linecount))
                    if not line.account_id.automatic and linetax and linetax.buchungsschluessel < 0:
                        errors.append(_(u'The booking key for the tax {tax} is not configured!').format(tax=linetax.name))
        return '\n'.join(errors)

    def update_line_autoaccounts_tax(self, move):
        errors = list()
        for linecount, line in enumerate(move.line_id, start=1):
            if line.account_id.id != line.ecofi_account_counterpart.id:
                if not self.env['ecofi'].is_taxline(line.account_id.id):
                    linetax = self.env['ecofi'].get_line_tax(line)
                    if line.account_id.automatic and not linetax:
                        if line.account_id.datev_steuer:
                            line.write({'ecofi_taxid': line.account_id.datev_steuer.id})
                        else:
                            errors.append(_(u'The Account is an Auto-Account but the move line {line} has no tax!').format(line=linecount))
        return '\n'.join(errors)

    def datev_tax_check(self, move):
        errors = list()
        linecount = 0
        tax_values = dict()
        linecounter = 0
        for line in move.line_id:
            linecount += 1
            if line.account_id.id != line.ecofi_account_counterpart.id:
                if self.env['ecofi'].is_taxline(line.account_id.id) and not line.ecofi_bu == 'SD':
                    if line.account_id.code not in tax_values:
                        tax_values[line.account_id.code] = {
                            'real': 0.0,
                            'datev': 0.0
                        }
                    tax_values[line.account_id.code]['real'] += line.debit - line.credit
                else:
                    linecounter += 1
                    taxcalc_ids = self.env['ecofi'].with_context(return_calc=True).calculate_tax(line)
                    for taxcalc_id in taxcalc_ids:
                        taxaccount = taxcalc_id['account_paid_id'] and taxcalc_id['account_paid_id'] or taxcalc_id['account_collected_id']
                        if taxaccount:
                            # datev_account_code = self.pool.get('account.account').read(cr, uid, taxaccount, context=new_context)['code']
                            datev_account_code = taxaccount.read(taxaccount)['code']
                            if datev_account_code not in tax_values:
                                tax_values[datev_account_code] = {
                                    'real': 0.0,
                                    'datev': 0.0,
                                }
                            if line.ecofi_bu and line.ecofi_bu == '40':
                                continue
                            tax_values[datev_account_code]['datev'] += taxcalc_id['amount']

        sum_real = 0.0
        sum_datev = 0.0
        for value in tax_values.itervalues():
            sum_real += value['real']
            sum_datev += value['datev']
        if Decimal(str(abs(sum_real - sum_datev))) > Decimal(str(10 ** -2 * linecounter)):
            errors.append(_(u'The sums for booked ({real}) and calculated ({datev}) are different!').format(
                real=sum_real, datev=sum_datev))

        return '\n'.join(errors)

    def datev_checks(self, move):
        """Constraint check if export method is 'gross'
        :param move: account_move
        """
        errors = list()
        errors.append(self.update_line_autoaccounts_tax(move))
        errors.append(self.datev_account_checks(move))
        if not errors:
            errors.append(self.datev_tax_check(move))
        return '\n'.join(filter(lambda e: bool(e), errors)) or False

    def finance_interface_checks(self):
        res = True
        if 'invoice' not in self.env.context or self.env.context['invoice'] and self.env.context['invoice'].enable_datev_checks:
            for move in self:
                if move.enable_datev_checks and self.env.user.company_id.enable_datev_checks:
                    res &= super(AccountMove, self).finance_interface_checks()
                    error = self.datev_checks(move)
                    if error:
                        raise exceptions.DatevWarning(error)
        return res

    @api.multi
    def post(self):
        res = super(AccountMove, self).post()
        invoice_line_tax_ids = dict()
        for move in self:
            for account_invoice_id in self.env['account.invoice'].search([('move_id', '=', move.id)]):
                for line in account_invoice_id.invoice_line:
                    invoice_line_tax_ids[line.account_id.id] = line.invoice_line_tax_id

            for line in move.line_id:
                if invoice_line_tax_ids.get(line.account_id.id):
                    line.write({'ecofi_taxid': invoice_line_tax_ids[line.account_id.id].id})
        return res


class AccountMoveLine(models.Model):
    """Inherits the account.move.line class and adds attributes
    """
    _inherit = 'account.move.line'

    datev_export_value = fields.Float(string='Export value')
    ecofi_bu = fields.Selection(
        selection=[
            ('40', '40'),
            ('SD', 'Steuer Direkt')
        ],
        string='Datev BU'
    )


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    @api.multi
    def write(self, values):
        has_new_vat = 'vat_required' in values
        new_account_ids = self.env['account.account'].browse([account_id[2]['account_dest_id'] for account_id in values.get('account_ids', []) if account_id[2]])
        for fiscal_position in self:
            if has_new_vat:
                for account_id in fiscal_position.account_ids:
                    # Note: account_id._name == account.fiscal.position.account
                    account_id.account_dest_id.write({'ustuebergabe': values['vat_required']})
                new_account_ids.write({'ustuebergabe': values['vat_required']})
            else:
                new_account_ids.write({'ustuebergabe': fiscal_position.vat_required})

        return super(AccountFiscalPosition, self).write(values)

    @api.model
    def create(self, values):
        if values.get('vat_required') and self.env['account.account'].browse([account_id[2]['account_dest_id'] for account_id in values.get('account_ids', []) if account_id[2]]):
            for account_id in values.get('account_ids'):
                account_id = self.env['account.account'].browse(account_id[2]['account_dest_id'])
                account_id.write({'ustuebergabe': True})
        return super(AccountFiscalPosition, self).create(values)
