# -*- coding: utf-8 -*-
# Part of Odoo. Developed by ecoservice (Uwe Böttcher und Falk Neubert GbR).
# See COPYRIGHT and LICENSE at the top level of this module for full copyright and licensing details.

from openerp import api, fields, models, exceptions, tools
from openerp.tools.translate import _
import base64
import cStringIO
import csv
from decimal import Decimal
from datetime import datetime


class Ecofi(models.Model):
    """
    The class ecofi is the central object to generate a csv file for the selected moves that
    can be used to be imported in the different financial programms
    """
    _name = 'ecofi'
    _description = 'Ecoservice Financial Interface'
    _zahlungsbedingungen = []

    name = fields.Char(string='Exportname', required=True, readonly=True)
    journale = fields.Char(string='Journals', required=True, readonly=True)
    date_from = fields.Date(string='From', required=True, readonly=True)
    date_to = fields.Date(string='To', required=True, readonly=True)
    csv_file = fields.Binary(string='Export CSV', readonly=True)
    csv_file_fname = fields.Char(string='Stored Filename')
    account_moves = fields.One2many(comodel_name='account.move', inverse_name='vorlauf_id', string='Account Moves', readonly=False)
    note = fields.Text(string='Comment')
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.user.company_id)

    def copy(self):
        """ Prevent the copy of the object
        """
        raise exceptions.Warning(_(u'Invalid record set: should be called as model (without records) or on single-record recordset'))

    def is_taxline(self, account_id):
        """Method to check if the selected account is a tax account

        :param account_id: Id of the account to analyse
        """
        self._cr.execute("Select id from account_tax where account_collected_id = %s or account_paid_id = %s" % (account_id, account_id))
        taxids = map(lambda x: x[0], self._cr.fetchall())
        return len(taxids) > 0

    def get_tax(self, account_id):
        """Method to get the tax for the selected account

        :param account_id: Id of the account to analyse
        """
        self._cr.execute("Select id from account_tax where account_collected_id = %s or account_paid_id = %s" % (account_id, account_id))
        taxids = map(lambda x: x[0], self._cr.fetchall())
        return taxids

    def get_line_tax(self, line):
        """returns the tax used in the line

        :param line: move.account.line
        """
        linetax = False
        if line.account_tax_id:
            linetax = line.account_tax_id
        if line.ecofi_taxid:
            linetax = line.ecofi_taxid
        return linetax or self.env['account.tax']

    def calculate_tax(self, line):
        """ Calculates and returns the amount of tax that has to be considered for an account_move_line. The calculation
        always uses the _compute method of the account.tax object wich returns the tax as if it was excluded.

        :param line: account_move_line
        """
        line_tax = self.get_line_tax(line)
        tax_amount = 0.0
        if line_tax:
            if self.env.context.get('currency'):
                amount = line.amount_currency
            else:
                amount = line.debit - line.credit
            return self.calc_tax(line_tax, amount)
        else:
            if self.env.context.get('return_calc'):
                return []
        return tax_amount

    def calc_tax(self, tax_object, amount):
        if not tax_object:
            return 0.0
        if self.env.context.get('odoo_taxation'):
            return sum([tax.get('amount', 0.0) for tax in tax_object.compute_all(amount)['taxes']])
        return self._compute_tax(tax_object, amount)

    @staticmethod
    def _compute_tax(tax, amount):
        """
        Calculates the base tax (tax * amount * 0.01)
        :param tax: The tax record
         :type tax: model('account.tax')
        :param amount: The amount from which the base tax is calculated
         :type amount: float, double
        :return: The calculated base tax
        :rtype: float, double
        """
        if tax.amount_type == 'group':
            if not sum([t.amount for t in tax.children_tax_ids]):
                return 0.0
            return sum([t.amount * amount for t in tax.children_tax_ids])
        return tax.amount * amount

    def set_main_account(self, move):
        """ This methods sets the main account of the corresponding account_move

        :param move: account_move

        How the Mainaccount is calculated (tax lines are ignored):

        1. Analyse the number of debit and credit lines.
        a. 1 debit, n credit lines: Mainaccount is the debitline account
        b. m debit, 1 credit lines: Mainaccount is the creditline account
        c. 1 debit, 1 credit lines: Mainaccount is the firstline account

        If there are m debit and n debitlines:
        a. Test if there is an invoice connected to the move_id and test if the invoice
            account_id is in the move than this is the mainaccount
        """

        sollkonto = list()
        habenkonto = list()
        nullkonto = list()
        error = False
        ecofikonto_no_invoice = move.line_id[0].account_id

        fn_counter_account = self._get_counter_account().get(move.journal_id.type, lambda *a: None)

        ecofikonto = fn_counter_account(move)

        if not ecofikonto:
            for line in move.line_id:
                Umsatz = Decimal(str(line.debit)) - Decimal(str(line.credit))
                if Umsatz < 0:
                    habenkonto.append(line.account_id)
                elif Umsatz > 0:
                    sollkonto.append(line.account_id)
                else:
                    nullkonto.append(line.account_id)
            if len(sollkonto) == 1 and len(habenkonto) == 1:
                ecofikonto = move.line_id[0].account_id
            elif len(sollkonto) == 1 and len(habenkonto) > 1:
                ecofikonto = sollkonto[0]
            elif len(sollkonto) > 1 and len(habenkonto) == 1:
                ecofikonto = habenkonto[0]
            elif len(sollkonto) > 1 and len(habenkonto) > 1:
                if len(sollkonto) > len(habenkonto):
                    habennotax = list()
                    for haben in habenkonto:
                        if not self.is_taxline(haben.id):
                            habennotax.append(haben)
                    if len(habennotax) == 1:
                        ecofikonto = habennotax[0]
                elif len(sollkonto) < len(habenkonto):
                    sollnotax = list()
                    for soll in sollkonto:
                        if not self.is_taxline(soll.id):
                            sollnotax.append(soll)
                    if len(sollnotax) == 1:
                        ecofikonto = sollnotax[0]

        if not ecofikonto:
            if 'invoice' in self.env.context:
                invoice = self.env.context['invoice']
            else:
                invoice = self.env['account.invoice'].search([('move_id', '=', move.id)])
            in_booking = False
            invoice_mainaccount = False
            if len(invoice) == 1:
                invoice_mainaccount = invoice.account_id
                for sk in sollkonto:
                    if sk == invoice_mainaccount:
                        in_booking = True
                        break
                for hk in habenkonto:
                    if hk == invoice_mainaccount:
                        in_booking = True
                        break
            if not in_booking and invoice:
                error = _(u"The main account of the booking could not be resolved, the move has {credit} credit- and {debit} debitlines!\n".format(credit=len(sollkonto), debit=len(habenkonto)))
                ecofikonto = ecofikonto_no_invoice
            else:
                ecofikonto = invoice_mainaccount

        # get account from journal
        if not ecofikonto:
            ecofikonto = move.journal_id.default_debit_account_id

        if ecofikonto:
            move.line_id.write({'ecofi_account_counterpart': ecofikonto.id})

        return error

    @api.model
    def _get_counter_account(self):
        """
        Creates a dictionary of methods which let you extract the counter account for the booking lines
        automatically. The methods referenced by the dict may still return None.

        :return: A dictionary of methods that extract a counter account from a specific journal type.
        :rtype: dict
        """
        return {
            'bank': self.__get_account_from_bank,
            'cash': self.__get_account_from_cash,
            'general': self.__get_account_from_general,
            'purchase': self.__get_account_from_purchase,
            'sale': self.__get_account_from_sale,
        }

    @api.model
    def __get_account_from_bank(self, move):
        """
        Returning the account which can be used as a counter account for an account move
        created in a bank journal.

        :param move: The account move for which the counter account is extracted from the journal.
        :return: The account of the journal if it is set. None otherwise.
        """

        return move.journal_id.default_debit_account_id or None

    @api.model
    def __get_account_from_cash(self, move):
        return None

    @api.model
    def __get_account_from_general(self, move):
        """
        Returning the account which can be used as a counter account for an account move
        created in a general journal.

        Specifically this method only handles the case that the journal is specified in the config as
        the currency exchange rate differences journal. In this case the corresponding default credit
        or debit account is returned.

        :param move: The account move for which the counter account is extracted from the journal.
        :return: The account of the journal if it is set. None otherwise.
        """
        return None

    @api.model
    def __get_account_from_purchase(self, move):
        return None

    @api.model
    def __get_account_from_sale(self, move):
        return None

    def generate_csv_move_lines(self, move, buchungserror, errorcount, thislog, thismovename, exportmethod,
                                partnererror, buchungszeilencount, bookingdict):
        """Method to be implemented for each Interface, generates the corresponding csv entries for each move

        :param move: account_move
        :param buchungserror: list of the account_moves with errors
        :param errorcount: number of errors
        :param thislog: logstring wich contains error descriptions or infos
        :param thismovename: Internal name of the move (for error descriptions)
        :param exportmethod: brutto / netto
        :param partnererror: List of the partners with errors (eg. missing ustid)
        :param buchungszeilencount: total number of lines written
        :param bookingdict: Dictionary that contains generated Bookinglines and Headers
        """
        return buchungserror, errorcount, thislog, partnererror, buchungszeilencount, bookingdict

    def generate_csv(self, ecofi_csv, bookingdict, log):
        """ Method to be implemented for each Interface, generates the corresponding csv entries for each move

        :param cr: the current row, from the database cursor
        :param uid: the current user’s ID for security checks
        :param ecofi_csv: object for the csv file
        :param bookingdict: Dictionary that contains generated Bookinglines and Headers
        :param log: logstring wich contains error descriptions or infos
        :param context: context arguments, like lang, time zone
        """
        return ecofi_csv, log

    def pre_export(self, account_move_ids):
        """ Method to call before the Import starts and the moves to export are going to be browsed

        :param cr: the current row, from the database cursor
        :param uid: the current user’s ID for security checks
        :param ecofi_csv: object for the csv file
        :param bookingdict: Dictionary that contains generated Bookinglines and Headers
        :param log: logstring wich contains error descriptions or infos
        :param context: context arguments, like lang, time zone
        """
        return True

    def ecofi_buchungen(self, journal_ids=None, vorlauf_id=None, date_from=None, date_to=None):
        """ Method that generates the csv export by the given parameters

        :param journal_ids: list of journalsIDS wich should be exported if the value is False all exportable journals will be exported
        :param vorlauf_id: id of the vorlauf if an existing export should be generated again
        :param date_from: date in wich moves should be exported
        :param date_to: date in wich moves should be exported
        .. seealso::
            :class:`ecoservice_financeinterface.wizard.export_ecofi_buchungsaetze.export_ecofi`
        """
        context = self.env.context.copy()
        buf = cStringIO.StringIO()
        ecofi_csv = csv.writer(buf, delimiter=';', quotechar='"', quoting=csv.QUOTE_ALL)
        partnererror = []
        buchungserror = []
        user = self.env.user

        journalname = u','.join(journal_ids.mapped('name'))

        if user.company_id.finance_interface:
            context['export_interface'] = user.company_id.finance_interface
            try:
                exportmethod = user.company_id.exportmethod
            except:
                exportmethod = 'netto'
        else:
            context['export_interface'] = 'datev'
            exportmethod = 'netto'
        if vorlauf_id:
            account_move_searchdomain = [('vorlauf_id', '=', vorlauf_id.id)]
        else:
            account_move_searchdomain = [
                ('journal_id', 'in', journal_ids.ids),
                ('state', '=', 'posted'),
                ('vorlauf_id', '=', False)
            ]
            if date_from and date_to:
                account_move_searchdomain.append(('date', '>=', date_from))
                account_move_searchdomain.append(('date', '<=', date_to))
        account_move_ids = self.env['account.move'].search(account_move_searchdomain)

        if len(account_move_ids) != 0:
            if not vorlauf_id:
                vorlaufname = self.env['ir.sequence'].next_by_code('ecofi.vorlauf')
                vorlauf_id = self.env['ecofi'].create({
                    'name': str(vorlaufname),
                    'date_from': date_from,
                    'date_to': date_to,
                    'journale': journalname
                })
            else:
                vorlaufname = vorlauf_id.name
            thislog = _(u'This export is conducted under the Vorlaufname: {vorlaufname}\n'
                        u'{sign}\n'
                        u'Start export\n').format(vorlaufname=vorlaufname, sign=90 * '-')
            bookingdictcount = 0
            buchungszeilencount = 0
            errorcount = 0
            warncount = 0
            bookingdict = {}
            self.with_context(context).pre_export(account_move_ids)
            for move in account_move_ids:
                bookingdict['move_bookings'] = []
                move.write({'vorlauf_id': vorlauf_id.id})
                thismovename = u"{name}, {ref}: ".format(name=move.name, ref=move.ref)
                bookingdictcount += 1
                buchungserror, errorcount, thislog, partnererror, buchungszeilencount, bookingdict = self.with_context(context).generate_csv_move_lines(
                        move, buchungserror, errorcount, thislog, thismovename, exportmethod,
                        partnererror, buchungszeilencount, bookingdict)

                # Check if our export made some rounding mistakes
                sum_move_lines = str(sum(move.line_id.mapped('credit')))
                sum_export_lines = Decimal('0.00')

                for move_booking in bookingdict['move_bookings']:
                    sum_export_lines += Decimal(move_booking[0].replace(',', '.'))
                    bookingdict['buchungen'].append(move_booking)

                mismatch = Decimal(sum_move_lines) - sum_export_lines

                if mismatch:
                    mistakes = [
                        x for x in bookingdict['move_bookings']
                        if abs(Decimal(x[0].replace(',', '.'))) == abs(mismatch)
                    ]
                    mismatch = 0 if len(mistakes) != 0 else mismatch

                move.export_mismatch = mismatch
                move.export_mismatch_reason = _(u'A rounding mistake occured while calculating the gross values per move line. Please adjust the values manually.')

                if not sum_export_lines:
                    # If in if: User did some grave mistake (i.e. wrong accounts in move lines)
                    move.ecofi_to_check = True
                    move.export_mismatch_reason = _(u'Move lines contain zero values or have a wrong account set')

                wrong_move_lines = move.line_id.filtered(lambda x: x.ecofi_taxid and (x.debit or x.credit))
                for wrong_move_line in wrong_move_lines:
                    if not wrong_move_line.datev_export_value:
                        value = Decimal(str(wrong_move_line.debit or wrong_move_line.credit))
                        wrong_move_line.datev_export_value = round(value * Decimal(1.0 + wrong_move_line.ecofi_taxid.amount), 2) if wrong_move_line.ecofi_taxid.amount else value

            ecofi_csv, thislog = self.with_context(context).generate_csv(ecofi_csv, bookingdict, thislog)
            out = base64.encodestring(buf.getvalue())
            thislog2 = _(u'Export finished\n'
                         u'{sign}\n'
                         u'Edited posting record: {bookingdictcount}\n'
                         u'Edited posting lines: {buchungszeilencount}\n'
                         u'Warnings: {warncount}\n'
                         u'Error: {errorcount}\n').format(sign=90 * '-', bookingdictcount=bookingdictcount, buchungszeilencount=buchungszeilencount, warncount=warncount, errorcount=errorcount)
            log = u'{thislog}{thislog2}'.format(thislog=thislog, thislog2=thislog2)
            vorlauf_id.write({
                'csv_file': out,
                'csv_file_fname': u'{}.csv'.format(vorlaufname),
                'note': log
            })
        else:
            vorlauf_id = False
        return vorlauf_id
