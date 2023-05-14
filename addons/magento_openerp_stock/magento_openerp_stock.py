# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
#################################################################################


from openerp.osv import fields, osv
from openerp.tools.translate import _
import xmlrpclib

from openerp.addons.magento_bridge.mob import XMLRPC_API

################## .............magento-Odoo stock.............##################

class stock_move(osv.osv):
	_inherit="stock.move"

	def action_confirm(self, cr, uid, ids, context=None):
		""" Confirms stock move or put it in waiting if it's linked to another move.
		"""
		context = dict(context or {})

		mob_stock_action = self.pool.get('ir.values').get_default(cr, uid, 'mob.config.settings', 'mob_stock_action')
		res = super(stock_move, self).action_confirm(cr, uid, ids, context=context)			
		if mob_stock_action == "fq":
			context['mob_stock_action_val'] = mob_stock_action
			self.fetch_stock_warehouse(cr, uid, ids, context)			
		return res

	def action_cancel(self, cr, uid, ids, context=None):
		""" Confirms stock move or put it in waiting if it's linked to another move.
		"""
		context = dict(context or {})
		context['action_cancel'] = True
		mob_stock_action = self.pool.get('ir.values').get_default(cr, uid, 'mob.config.settings', 'mob_stock_action')
		check = False
		for id in ids:
			data = self.browse(cr, uid, id)
			if data.state == "cancel":
				check = True
		res = super(stock_move, self).action_cancel(cr, uid, ids, context=context)			
		# raise osv.except_osv(('Check'),('testing :-- %r'%res))
		if mob_stock_action == "fq" and not check:			
			self.fetch_stock_warehouse(cr, uid, ids, context)			
		return res

	def action_done(self, cr, uid, ids, context=None):
		""" Process completly the moves given as ids and if all moves are done, it will finish the picking.
		"""
		context = dict(context or {})
		mob_stock_action = self.pool.get('ir.values').get_default(cr, uid, 'mob.config.settings', 'mob_stock_action')
		check = False
		for id in ids:
			data = self.browse(cr, uid, id)
			if data.location_id.name == "Inventory loss" or data.location_dest_id.name == "Inventory loss":
				check = True

		res = super(stock_move, self).action_done(cr, uid, ids, context=context)			
		if mob_stock_action == "qoh" or check:
			context['mob_stock_action_val'] = mob_stock_action
			self.fetch_stock_warehouse(cr, uid, ids, context)			
		return res

	def fetch_stock_warehouse(self, cr, uid, ids, context=None):
		context = dict(context or {})
		product_quantity = 0

		if not context.has_key('stock_from'):
			for id in ids:
				data = self.browse(cr, uid, id)
				erp_product_id = data.product_id.id
				context['warehouse'] = data.warehouse_id.id
				product_obj = self.pool['product.product'].browse(cr, uid, erp_product_id, context)
				if context.has_key('mob_stock_action_val') and context['mob_stock_action_val'] == "qoh":
					product_quantity = product_obj.qty_available -product_obj.outgoing_qty
				else:
					product_quantity = product_obj.virtual_available

				flag = 1
				if data.origin and data.origin.startswith('SO'):
					sale_id = self.pool.get('sale.order').search(cr, uid, [('name','=',data.origin)])
					if sale_id:
						get_channel = self.pool.get('sale.order').browse(cr,uid,sale_id[0]).channel
						if get_channel == 'magento' and 'IN' not in data.picking_id.name:
							flag=0
				else:
					flag = 2 # no origin
				warehouse_id = 0
				if flag == 1:					
					warehouse_id = data.warehouse_id.id
				if flag == 2:
					location_id = data.location_dest_id.id
					company_id = data.company_id.id
					check_in = self.pool.get('stock.warehouse').search(cr,uid,[('lot_stock_id','=',location_id),('company_id','=',company_id)],limit=1)
					if not check_in:
						check_in = self.check_warehouse_location(cr, uid, data.location_dest_id.id, data.company_id.id, context=context)						
					if check_in:
						# Getting Goods.
						warehouse_id = check_in[0]						
					check_out = self.pool.get('stock.warehouse').search(cr,uid,[('lot_stock_id','=',data.location_id.id),('company_id','=',data.company_id.id)],limit=1)
					if not check_out:
						check_out = self.check_warehouse_location(cr, uid, data.location_id.id, data.company_id.id, context=context)						
					if check_out:
						# Sending Goods.
						warehouse_id = check_out[0]						
				check = context.copy()
				self.check_warehouse(cr, uid, erp_product_id, warehouse_id, product_quantity, context=check)
		return True

	def check_warehouse_location(self, cr, uid, location_id, company_id, context=None):
		context = dict(context or {})
		flag = True
		check_in = []
		while flag == True and location_id:
			location_id = self.pool.get('stock.location').browse(cr, uid, location_id).location_id.id
			check_in = self.pool.get('stock.warehouse').search(cr,uid,[('lot_stock_id','=',location_id),('company_id','=',company_id)],limit=1)					
			if check_in:
				flag = False
		return check_in

	def check_warehouse(self, cr, uid, erp_product_id, warehouse_id, product_qty, context=None):
		context = dict(context or {})
		mapping_ids = self.pool.get('magento.product').search(cr, uid, [('pro_name','=',erp_product_id)])
		if mapping_ids:
			mapping_obj = self.pool.get('magento.product').browse(cr, uid, mapping_ids[0])
			instance_id = mapping_obj.instance_id.id
			mage_product_id = mapping_obj.mag_product_id
			if mapping_obj.instance_id.warehouse_id.id == warehouse_id:					
				self.synch_quantity(cr, uid, mage_product_id, product_qty, instance_id, context=context)
			

	def synch_quantity(self, cr, uid, mage_product_id, product_qty, instance_id, context=None):
		context = dict(context or {})
		response = self.update_quantity(cr, uid, mage_product_id, product_qty, instance_id, context=context)	
		if response[0]==1:
			return True
		else:
			self.pool.get('magento.sync.history').create(cr,uid,{'status':'no','action_on':'product','action':'c','error_message':response[1]})
		
	def update_quantity(self, cr, uid, mage_product_id, quantity, instance_id, context=None):
		context = dict(context or {})
		qty = 0		
		text = ''
		session = False
		context['instance_id'] = instance_id
		if mage_product_id:
			obj = self.pool.get('magento.configure').browse(cr, uid, instance_id)		
			if not obj.active :
				return [0,' Connection needs one Active Configuration setting.']
			else:
				url = obj.name + XMLRPC_API
				user = obj.user
				pwd = obj.pwd
				try:
					server = xmlrpclib.Server(url)
					session = server.login(user,pwd)
				except xmlrpclib.Fault, e:
					text = 'Error, %s Magento details are Invalid.'%e
				except IOError, e:
					text = 'Error, %s.'%e
				except Exception,e:
					text = 'Error in Magento Connection.'
				if not session:
					return [0,text]
				else:
					try:
						update_data = [mage_product_id,{'manage_stock':1, 'qty':quantity, 'is_in_stock':1}]						
						server.call(session, 'product_stock.update', update_data)
						return [1, '']
					except Exception,e:
						return [0,' Error in Updating Quantity for Magneto Product Id %s'%mage_product_id]
		else:
			return [1, 'Error in Updating Stock, Magento Product Id Not Found!!!']
stock_move()	