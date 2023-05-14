# -*- coding: utf-8 -*-

import base64
import io
import time

import zipfile
from datetime import datetime


from openerp import api, fields, models
from openerp.tools.safe_eval import safe_eval
from openerp import report as odoo_report


class ExportInvoicePdfZip(models.TransientModel):
    _name = 'export.invoice.pdf.zip'
    _description = 'Export Invoice PDFs as Zip'

    zip_data = fields.Binary("Zip File")


    @api.multi
    def action_export_pdf_zip(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []

        report = self.env.ref("account.account_invoices")

        fp = io.BytesIO()
        zf = zipfile.ZipFile(fp, mode="w")
        ctx = self._context.copy() or {}
        ctx.update({'invoice_pdf_export_zip':True})
        datas, format = odoo_report.render_report(self._cr, self._uid, active_ids, report.report_name,{'model': 'account.invoice'},ctx)
        for index, invoice in enumerate(self.env['account.invoice'].browse(active_ids)):
            #data, format = odoo_report.render_report(self._cr, self._uid, [invoice.id], report.report_name,{'model': invoice._model},self._context)
            # data = datas
            data = datas[index]
            #report_name = safe_eval(invoice.display_name, {'object': invoice, 'time': time})
            report_name = str(invoice.display_name)
            if invoice.state in ['draft', 'cancel']:
                report_name = '%s/%s_%s' % (report_name, report_name, invoice.id)
            if invoice.date_invoice:
                report_name = report_name[:report_name.rfind('/')] + '/' + str(datetime.strptime(invoice.date_invoice, "%Y-%m-%d").month) + report_name[
                                                                                                         report_name.rfind(
                                                                                                             '/'):]
            file_name = "%s.%s" % (report_name, format)
            zf.writestr(file_name, data)

        zf.close()
        record = self.env['export.invoice.pdf.zip'].create({'zip_data': base64.b64encode(fp.getvalue())})
        file_name = 'Invoices_' + datetime.now().strftime('%Y%m%d%H%S') + '.zip'

        action = {
        'name': 'Export Invoices Zip',
        'type': 'ir.actions.act_url',
        'url': "/web/binary/saveas/?model="+record._name+"&id=" + str(record.id) + "&field=zip_data&download=true&filename="+file_name,
        'target': 'self',
        }
        return action