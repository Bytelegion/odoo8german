# -*- coding: utf-8 -*-

from openerp.osv import fields, osv
from openerp.tools import ustr
from openerp.tools.translate import _
from openerp import addons
from mako.template import Template as MakoTemplate


class ecofi_datev_formate(osv.osv):
    _inherit = 'ecofi.datev.formate'

    def _get_export_type(self, cr, uid, context={}):
        """Method that can be used by other Modules to add their interface to the selection of possible export formats"""
        res = super(ecofi_datev_formate, self)._get_export_type(cr, uid, context=context)
        res.append(('pterm', _('Paymentterms')))
        return res

    _columns = {
        'datev_type': fields.selection(_get_export_type, 'Exporttype'),
    }

    def getfields_defaults(self, cr, thisimport, context=None):
        """Return the Defaults MakeHelp and CSV Template File"""
        if context is None:
            context = {}
        res = super(ecofi_datev_formate, self).getfields_defaults(cr, thisimport, context=context)
        if thisimport.datev_type == 'pterm':
            res['module'] = 'ecoservice_financeinterface_datev_export'
            res['csv_template'] = 'csv_templates/datev_payment_terms.csv'
            res['mako_help'] = _("""Possible Mako Object paymentterm
            Paymentterm Values:
               'number'
               'name'
               'typ'
               'netdays'
               'skonto1days'
               'skonto1percent'
               'skonto2days'
               'skonto2percent'
               'error'
               'log'
            """)
        return res

    def generate_payment_terms(self, cr, uid, paymentterm, context=None):
        """ Generate Payment Term for Mako"""
        if context is None:
            context = {}
        res = {
               'number': paymentterm.id,
               'name': paymentterm.name,
               'typ': 1,
               'netdays': False,
               'skonto1days': '',
               'skonto1percent': '',
               'skonto2days': '',
               'skonto2percent': '',
               'error': False,
               'log': ''
               }
        skontocount = 0
        for line in paymentterm.line_id:
            if line.value == 'balance':
                res['netdays'] = line.days
            elif line.value == 'procent':
                if skontocount == 0:
                    res['skonto1days'] = line.days 
                    res['skonto1percent'] = line.value_amount * 100
                elif skontocount == 1:
                    res['skonto2days'] = line.days
                    res['skonto2percent'] = line.value_amount * 100
                skontocount += 1
        if res['netdays'] is False:
            res['error'] = True
            res['log'] = _('Paymentterm %s has no balance line' % (paymentterm.name))
        if skontocount > 1:
            res['error'] = True
            res['log'] = _('Paymentterm %s has more than 2 percent lines' % (paymentterm.name))
        return res

    def generate_export_csv(self, cr, uid, export, ecofi_csv, context=None):
        """Funktion that fills the CSV Export"""
        if context is None:
            context = {}
        res = super(ecofi_datev_formate, self).generate_export_csv(cr, uid, export, ecofi_csv, context=context)
        if export.datev_type == 'pterm':
            try:
                domain = eval(export.datev_domain)
            except:
                domain = []
            paymentterm_ids = self.pool.get('account.payment.term').search(cr, uid, domain, order='id asc', context=context)
            thisline = []
            for spalte in export.csv_spalten:
                if spalte.mako or 'export_all' in context:
                    thisline.append(ustr(spalte.feldname).encode('encoding' in context and context['encoding'] or 'iso-8859-1'))
            ecofi_csv.writerow(thisline)
            log = ''
            for paymentterm in self.pool.get('account.payment.term').browse(cr, uid, paymentterm_ids, context=context):
                thisline = []
                writeline = True
                for spalte in export.csv_spalten:
                    if spalte.mako or 'export_all' in context:
                        try:
                            thispaymentterm = self.generate_payment_terms(cr, uid, paymentterm, context=context)
                            if thispaymentterm['error'] is False:
                                reply = MakoTemplate(spalte.mako).render_unicode(paymentterm=thispaymentterm)
                                if reply == 'False':
                                    reply = ''
                                if reply != '':
                                    convertet_value = self.pool.get('ecofi.datev.formate').convert_value(spalte.typ, reply, context=context)
                                    if convertet_value['value'] is not False:
                                        thisline.append(convertet_value['value'])
                                    else:
                                        log += _("Paymentterm: %s could not be exported!\n" % (paymentterm.name))
                                        log += "\t %s\n" % (convertet_value['log'])
                                        writeline = False
                                        break
                                else:
                                    thisline.append('')
                            else:
                                log += _("Paymentterm: %s could not be exported!\n" % (paymentterm.name))
                                log += "\t %s\n" % (thispaymentterm['log'])
                                writeline = False
                                break
                        except:
                            thisline.append('')
                if writeline:
                    ecofi_csv.writerow(thisline)
            res['log'] += log
        return res
ecofi_datev_formate()
