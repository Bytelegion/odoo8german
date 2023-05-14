# -*- coding: utf-8 -*-
##############################################################################
#
#    This module uses OpenERP, Open Source Management Solution Framework.
#    Copyright (C) 2014-Today BrowseInfo (<http://www.browseinfo.in>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from openerp.report import report_sxw
from openerp.osv import osv
from datetime import date,time,datetime

class invoice_report_custom(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(invoice_report_custom, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
                                  'get_stock_date' : self.get_stock_date,
                                  })
            
    def get_stock_date(self, obj):
        date_new = False
        if obj.origin:
            piking_id= self.pool.get('stock.picking').search(self.cr,self.uid,[('origin','=',obj.origin)])
            pick_id= self.pool.get('stock.picking').search(self.cr,self.uid,[('name','=',obj.origin)])
            lang_obj = self.pool.get('res.lang')
            if piking_id or pick_id:
                if piking_id:
                    picking_browse = self.pool.get('stock.picking').browse(self.cr,self.uid,piking_id[0])
                    date = picking_browse.date_done
                    print "!!!!!!!!!! Date ",date
                    if date:
                        date1 = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
                        #date1 = datetime.strftime(date1, '%Y-%m-%d')
                        
                        if picking_browse.partner_id.lang:
                            lang_id = lang_obj.search(self.cr,self.uid,[('code','=',picking_browse.partner_id.lang)])
                            print "&&& lang_id &&&",lang_id
                            lang_browse = lang_obj.browse(self.cr,self.uid,lang_id[0])
                            print "@@@@@@ lang_browse",lang_browse.date_format
                            date1 = datetime.strftime(date1, lang_browse.date_format)
                            print "(((((date1 after format)))",date1
                            date_new = date1
                        else:
                            date1 = datetime.strftime(date1, '%Y-%m-%d')
                            date_new=date1
                if pick_id:
                    picking_browse = self.pool.get('stock.picking').browse(self.cr,self.uid,pick_id[0])
                    date = picking_browse.date_done
                    if date:
                        date1 = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
                        #date1 = datetime.strftime(date1, '%Y-%m-%d')
                        #date_new = date1
                        if picking_browse.partner_id.lang:
                            lang_id = lang_obj.search(self.cr,self.uid,[('code','=',picking_browse.partner_id.lang)])
                            print "&&& lang_id &&&",lang_id
                            lang_browse = lang_obj.browse(self.cr,self.uid,lang_id[0])
                            print "@@@@@@ lang_browse",lang_browse.date_format
                            date1 = datetime.strftime(date1, lang_browse.date_format)
                            print "(((((date1 after format)))",date1
                            date_new = date1
                        else:
                            date1 = datetime.strftime(date1, '%Y-%m-%d')
                            date_new=date1
            else:
                date_new = False
        return date_new
        
        
                                  
class report_invoice_custom_demo(osv.AbstractModel):
    _name='report.custom_invoice_report.report_invoice_custom'
    _inherit='report.abstract_report'
    _template='custom_invoice_report.report_invoice_custom'
    _wrapped_report_class=invoice_report_custom
    
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:        
                       

    
