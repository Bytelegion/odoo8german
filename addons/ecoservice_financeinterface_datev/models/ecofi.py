# -*- coding: utf-8 -*-
# Part of Odoo. Developed by ecoservice (Uwe Böttcher und Falk Neubert GbR).
# See COPYRIGHT and LICENSE at the top level of this module for full copyright and licensing details.

from . import ecofi_export_columns
import logging
import re
from decimal import Decimal
from openerp import _, models

_logger = logging.getLogger(__name__)


class Ecofi(models.Model):
    """Inherits the ecofi class and adds methods and attributes
    """
    _name = 'ecofi'
    _inherit = ['ecofi', 'ecofi.export.columns']

    def migrate_datev(self):
        """ Function to migrate old moves to the new interface
        """
        _logger.info(_(u'Starting Move Migration'))
        invoice_ids = self.env['account.invoice'].search([])
        counter = 0
        for invoice in invoice_ids:
            counter += 1
            _logger.info(_(u'Migrate Move {counter} / {len}'.format(counter=counter, len=len(invoice_ids))))
            if invoice.move_id:
                invoice.move_id.write({'ecofi_buchungstext': invoice.ecofi_buchungstext or False})
                for invoice_line in invoice.invoice_line_ids:
                    if invoice_line.invoice_line_tax_ids:
                        for move_line in invoice.move_id.line_id:
                            if move_line.account_id.id == invoice_line.account_id.id:
                                if move_line.debit + move_line.credit == abs(invoice_line.price_subtotal):
                                    move_line.write({'ecofi_taxid': invoice_line.invoice_line_tax_ids[0].id})
        _logger.info(_(u'Move Migration Finished'))
        return True

    def field_config(self, move, line, errorcount, partnererror, thislog, thismovename, faelligkeit, datevdict):
        """ Method that generates gets the values for the different Datev columns.
        :param move: account_move
        :param line: account_move_line
        :param errorcount: Errorcount
        :param partnererror: Partnererror
        :param thislog: Log
        :param thismovename: Movename
        :param faelligkeit: Fälligkeit
        """
        thisdate = move.date
        datevdict['Datum'] = u'{d1}{d2}'.format(d1=thisdate[8:10], d2=thisdate[5:7])
        if move.name:
            datevdict['Beleg1'] = u'{name}'.format(name=move.name)
        if move.journal_id.type == 'purchase' and move.ref:
            datevdict['Beleg1'] = u'{beleg1}'.format(beleg1=move.ref)
        if faelligkeit:
            datevdict['Beleg2'] = faelligkeit
        datevdict['Waehrung'], datevdict['Kurs'] = self.with_context(lang='de_DE', date=thisdate).format_waehrung(line)
        if line.move_id.ecofi_buchungstext:
            datevdict['Buchungstext'] = u'{ecofi_buchungstext}'.format(ecofi_buchungstext=line.move_id.ecofi_buchungstext)
        if line.account_id.ustuebergabe:
            if move.partner_id:
                if move.partner_id.vat:
                    datevdict['EulandUSTID'] = u'{vat}'.format(vat=move.partner_id.vat)
            if datevdict['EulandUSTID'] == '':
                errorcount += 1
                partnererror.append(move.partner_id.id)
                thislog = u'{log} {name} {text} \n'.format(log=thislog, name=thismovename, text=_(u'Error! No sales tax identification number stored in the partner!'))
        return errorcount, partnererror, thislog, thismovename, datevdict

    def format_umsatz(self, lineumsatz):
        """
        Returns the formatted amount
        :param lineumsatz: amountC
        """
        soll_haben = 's' if lineumsatz <= 0 else 'h'
        umsatz = str(abs(lineumsatz)).replace('.', ',')
        return umsatz, soll_haben

    def format_waehrung(self, line):
        """
        Formats the currency for the export
        :param line: account_move_line
        """
        factor = ''
        company = self.env.user.company_id or self.env['res.company'].search([('parent_id', '=', False)], limit=1)
        currency = self.env['res.currency']

        if line.currency_id and not self.env.context.get('datev_ignore_currency'):
            if line.currency_id.name != company.currency_id.name:
                currency = line.currency_id
                factor = u'{rate}'.format(rate=str(currency.rate).replace('.', ','))

        return currency.name or '', factor

    def generate_csv(self, ecofi_csv, bookingdict, log):
        """ Implements the generate_csv method for the datev interface
        """
        if self.env.context.get('export_interface', '') == 'datev':
            ecofi_csv.writerow(bookingdict[u'datevheader'])
            ecofi_csv.writerow(bookingdict[u'buchungsheader'])
            for buchungsatz in bookingdict[u'buchungen']:
                ecofi_csv.writerow(buchungsatz)
        return super(Ecofi, self).generate_csv(ecofi_csv, bookingdict, log)

    def generate_csv_move_lines(self, move, buchungserror, errorcount, thislog, thismovename, exportmethod,
                                partnererror, buchungszeilencount, bookingdict):
        """
        Implements the generate_csv_move_lines method for the datev interface
        """
        if self.env.context.get('export_interface', '') == 'datev':
            if 'buchungen' not in bookingdict:
                bookingdict['buchungen'] = list()
            if 'buchungsheader' not in bookingdict:
                bookingdict['buchungsheader'] = ecofi_export_columns.EcofiExportColumns.get_datev_column_headings()
            if 'datevheader' not in bookingdict:
                bookingdict['datevheader'] = self.get_legal_datev_header(move.vorlauf_id)

            faelligkeit = False
            for line in move.line_id:
                if line.debit == 0 and line.credit == 0:
                    continue
                datevkonto = line.ecofi_account_counterpart.code
                datevgegenkonto = u'{code}'.format(code=line.account_id.code)
                if datevgegenkonto == datevkonto:
                    if line.date_maturity:
                        faelligkeit = u'{d1}{d2}{d3}'.format(d1=line.date[8:10], d2=line.date[5:7], d3=line.date[2:4])
                    continue
                currency = not self.env.context.get('datev_ignore_currency') and bool(line.amount_currency)
                line_total = Decimal(str(line.amount_currency)) if currency else Decimal(str(line.debit)) - Decimal(str(line.credit))
                buschluessel = ''
                if exportmethod == 'brutto':
                    if self.env['ecofi'].is_taxline(line.account_id.id) and not line.ecofi_bu == 'SD':
                        continue
                    if line.ecofi_bu and line.ecofi_bu == '40':
                        buschluessel = '40'
                    else:
                        linetax = self.get_line_tax(line)
                        gross_value = round(line_total * Decimal(1.0 + linetax.amount), 2) if linetax else line_total
                        line_total = Decimal(str(gross_value))

                        if not line.account_id.automatic and linetax:
                            buschluessel = str(linetax.buchungsschluessel)

                umsatz, sollhaben = self.format_umsatz(line_total)
                umsatz = str(line.datev_export_value) if line.datev_export_value else umsatz

                datevdict = {
                    'Sollhaben': sollhaben,
                    'Umsatz': umsatz.replace('.', ','),
                    'Gegenkonto': datevgegenkonto,
                    'Datum': '',
                    'Konto': datevkonto or '',
                    'Beleg1': '',
                    'Beleg2': '',
                    'Waehrung': '',
                    'Buschluessel': buschluessel,
                    'Kost1': '',
                    'Kost2': '',
                    'Kostmenge': '',
                    'Skonto': '',
                    'Buchungstext': '',
                    'EulandUSTID': '',
                    'EUSteuer': '',
                    'Basiswaehrungsbetrag': '',
                    'Basiswaehrungskennung': '',
                    'Kurs': '',
                    'Movename': u'{name}'.format(name=move.name)
                }
                (errorcount, partnererror, thislog, thismovename, datevdict) = self.field_config(move, line, errorcount, partnererror, thislog, thismovename, faelligkeit, datevdict)
                bookingdict['move_bookings'].append(self.buchungenCreateDatev(datevdict))
                buchungszeilencount += 1
        return buchungserror, errorcount, thislog, partnererror, buchungszeilencount, bookingdict

    @staticmethod
    def buchungenCreateDatev(datev_dict):
        """Method that creates the datev csv move line
        """
        datev_dict = Ecofi._preprocess_export_line(datev_dict)
        return ecofi_export_columns.EcofiExportColumns.get_datev_export_line(datev_dict)

    def ecofi_buchungen(self, journal_ids=None, vorlauf_id=False, date_from=False, date_to=False):
        return super(Ecofi, self.with_context(datev_ignore_currency=self.env.user.company_id.datev_ignore_currency)).ecofi_buchungen(journal_ids=journal_ids, vorlauf_id=vorlauf_id, date_from=date_from, date_to=date_to)

    @staticmethod
    def _preprocess_export_line(datev_dict):
        if datev_dict.get('Buschluessel') == '0':
            datev_dict['Buschluessel'] = ''

        if datev_dict.get('Buchungstext'):
            datev_dict['Buchungstext'] = u'{:.60}'.format(datev_dict['Buchungstext'])

        if datev_dict.get('Beleg1'):
            datev_dict['Beleg1'] = u'{:.12}'.format(re.sub(u'[^{}]'.format(Ecofi._get_valid_chars()), u'', datev_dict['Beleg1']))

        if datev_dict.get('Beleg2'):
            datev_dict['Beleg2'] = u'{:.12}'.format(re.sub(u'[^{}]'.format(Ecofi._get_valid_chars()), u'', datev_dict['Beleg2']))

        return datev_dict

    @staticmethod
    def _get_valid_chars(additional_chars=None):
        """
        Returns a string containing the valid chars for Belegfeld 1 and Belegfeld 2
        which can be used e.g. in a RegEx

        :param str additional_chars:
        :return: a string containing valid chars
        :rtype: str
        """
        chars = 'a-zA-Z0-9$%&*+\-/'

        if additional_chars and isinstance(additional_chars, str):
            chars += additional_chars

        return chars
