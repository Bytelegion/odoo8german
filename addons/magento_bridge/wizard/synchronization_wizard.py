# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
#################################################################################

from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp import netsvc


class synchronization_wizard(osv.osv_memory):
	_name = 'synchronization.wizard'

	_columns = {
		'action': fields.selection([('export','Export'),('update','Update')],'Action',required=True, help="""Export: Export all Odoo Category/Products at Magento. Update: Update all synced products/categories at magento, which requires to be update at magento"""),
	}

	_defaults={
		'action': 'export',
	}
	def start_category_synchronization(self, cr, uid, ids, context=None):		
		if context is None:
			context = {}
		sync_opr = ''
		for i in ids:
			sync_obj = self.browse(cr, uid, i)
			sync_opr = sync_obj.action
		context['sync_opr'] = sync_opr	
		message = self.pool.get('magento.synchronization').export_categories_check(cr, uid, context)
		return message

	def start_product_synchronization(self, cr, uid, ids, context=None):		
		if context is None:
			context = {}
		sync_opr = ''
		for i in ids:
			sync_obj = self.browse(cr, uid, i)
			sync_opr = sync_obj.action
		context['sync_opr'] = sync_opr	
		message = self.pool.get('magento.synchronization').export_product_check(cr, uid, context)		
		return message

	def start_bulk_product_synchronization(self, cr, uid, context=None):
		partial = self.create(cr, uid, {}, context)
		
		context['check'] = False
		return { 'name':_("Synchronization Bulk Product"),
				 'view_mode': 'form',
				 'view_id': False,
				 'view_type': 'form',
				'res_model': 'synchronization.wizard',
				 'res_id': partial,
				 'type': 'ir.actions.act_window',
				 'nodestroy': True,
				 'target': 'new',
				 'context': context,
				 'domain': '[]',
			}

	def start_bulk_category_synchronization(self, cr, uid, context=None):		
		partial = self.create(cr, uid, {}, context)

		context['All'] = True
		return { 'name':_("Synchronization Bulk Category"),
				 'view_mode': 'form',
				 'view_id': False,
				 'view_type': 'form',
				'res_model': 'synchronization.wizard',
				 'res_id': partial,
				 'type': 'ir.actions.act_window',
				 'nodestroy': True,
				 'target': 'new',
				 'context':context,
				 'domain': '[]',
			}

synchronization_wizard()