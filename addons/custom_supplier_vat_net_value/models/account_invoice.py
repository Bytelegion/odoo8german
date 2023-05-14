from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.tools import float_is_zero, float_compare


class Account_Invoice_Line(models.Model):
    _inherit = 'account.invoice.line'

    price_unit_gross = fields.Float(string='Unit Price Gross', digits=dp.get_precision('Product Price'))

    @api.onchange('price_unit_gross','invoice_line_tax_id')
    def _onchange_price_unit_gross(self):
        for line in self:
            amount = 0.0
            tax_amount = 0.0
            if line.price_unit_gross:
                for invoice_tax in line.invoice_line_tax_id:
                    tax_amount += invoice_tax.amount
                amount = tax_amount + 1
                line.price_unit = (line.price_unit_gross / amount)


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.multi
    def invoice_validate(self):
        res_id = super(AccountInvoice, self).invoice_validate()
        for invoice in self:
            for line in invoice.invoice_line:
                line.product_id.standard_price = line.price_unit
        return res_id
