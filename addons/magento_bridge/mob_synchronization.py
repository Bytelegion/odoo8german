 # -*- coding: utf-8 -*-
##############################################################################
#		
#    Odoo, Open Source Management Solution
#    Copyright (C) 2013 webkul
#	 Author :
#				www.webkul.com	
#
##############################################################################

import xmlrpclib
from mob import _unescape
from openerp.osv import fields, osv
from openerp import SUPERUSER_ID, api
from openerp.tools.translate import _

class magento_synchronization(osv.osv):
	_name = "magento.synchronization"
	_description = "Magento Synchronization"

	def open_configuration(self, cr, uid, ids, context=None):
		view_id = False
		setting_ids = self.pool.get('magento.configure').search(cr, uid, [('active','=',True)])
		if  setting_ids:
			view_id = setting_ids[0]
		return {
				'type': 'ir.actions.act_window',
				'name': 'Configure Magento Api',
				'view_type': 'form',
				'view_mode': 'form',
				'res_model': 'magento.configure',
				'res_id': view_id,
				'target': 'current',
				'domain': '[]',
			}

	def sync_attribute_set(self, cr, uid, data, context=None):
		erp_set_id = 0
		set_dic = {}
		res = False
		set_pool = self.pool.get('magento.attribute.set')

		if data.has_key('name') and data.get('name'):
			set_map_ids = set_pool.search(cr, uid, [('name','=',data.get('name'))])
			if not set_map_ids:
				set_dic['name'] = data.get('name')
				if data.has_key('set_id') and data.get('set_id'):
					set_dic['set_id'] = data.get('set_id')
				set_dic['created_by'] = 'Magento'
				set_dic['instance_id'] = context.get('instance_id')
				erp_set_id = set_pool.create(cr, uid, set_dic)
			else:
				erp_set_id = set_map_ids[0]
			if erp_set_id: 
				if data.has_key('set_id') and data.get('set_id'):
					dic = {}
					dic['set_id'] = data.get('set_id')
					if data.has_key('attribute_ids') and data.get('attribute_ids'):
						dic['attribute_ids'] = [(6, 0, data.get('attribute_ids'))]
					else:
						dic['attribute_ids'] = [[5]]
					if context.has_key('instance_id') and context['instance_id']:
						dic['instance_id'] = context.get('instance_id')
					res = set_pool.write(cr, uid, erp_set_id, dic, context)
		return res

	def server_call(self, cr, uid, session, url, method, params=None):		
		if session:
			server = xmlrpclib.Server(url)
			mage_id = 0
			try:
				if params is None:
					mage_id = server.call(session, method)					
				else:
					mage_id = server.call(session, method, params)
			except xmlrpclib.Fault, e:
				name = ""
				return [0,'\nError in create (Code: %s).%s'%(name,str(e))]
			return [1, mage_id]

	#############################################
	## 	 Export Attributes and values          ##
	#############################################
	def export_attributes_and_their_values(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		map_dic = []
		map_dict = {}
		error_message = ''
		attribute_count = 0
		attribute_pool = self.pool.get('product.attribute')
		attribute_value_pool = self.pool.get('product.attribute.value')
		attribute_mapping_pool = self.pool.get('magento.product.attribute')
		value_mapping_pool = self.pool.get('magento.product.attribute.value')
		connection = self.pool.get('magento.configure')._create_connection(cr, uid, context)		
		if connection:
			url = connection[0]
			session = connection[1]
			context['instance_id'] = instance_id = connection[2]
			attribute_map_ids = attribute_mapping_pool.search(cr, uid, [('instance_id','=',instance_id)])
			for attribute_map_id in attribute_map_ids:
				attribute_map_obj = attribute_mapping_pool.browse(cr, uid, attribute_map_id)
				map_dic.append(attribute_map_obj.erp_id)
				map_dict.update({attribute_map_obj.erp_id:attribute_map_obj.mage_id})
			attribute_ids = attribute_pool.search(cr, uid, [], context=context)
			if attribute_ids:
				for attribute_id in attribute_ids:
					attribute_obj = attribute_pool.browse(cr, uid, attribute_id, context)
					if attribute_id not in map_dic:
						name = attribute_obj.name
						label = attribute_obj.name
						attribute_response = self.create_product_attribute(cr, uid, url, session, attribute_id, name, label, context)
					else:
						mage_id = map_dict.get(attribute_id)
						attribute_response = [1, int(mage_id)]
					if attribute_response[0] == 0:
						error_message = error_message + attribute_response[1]
					if attribute_response[0] > 0:
						mage_id = attribute_response[1]
						for value_id in attribute_obj.value_ids:
							if not value_mapping_pool.search(cr,uid,[('erp_id','=',value_id.id),('instance_id','=',instance_id)]):
								value_obj = attribute_value_pool.browse(cr, uid, value_id.id, context)
								name = value_obj.name
								position = value_obj.sequence
								value_response = self.create_attribute_value(cr, uid, url, session, mage_id, value_id.id, name, position, context)
								if value_response[0] == 0:
									error_message = error_message + value_response[1]
						attribute_count += 1
			else:
				error_message = "No Attribute(s) Found To Be Export At Magento!!!"
			if attribute_count:
				error_message += "\n %s Attribute(s) and their value(s) successfully Synchronized To Magento."%(attribute_count)
			partial = self.pool.get('message.wizard').create(cr, uid, {'text':error_message})
			return { 
				'name':_("Message"),
				'view_mode': 'form',
				'view_id': False,
				'view_type': 'form',
				'res_model': 'message.wizard',
				'res_id': partial,
				'type': 'ir.actions.act_window',
				'nodestroy': True,
				'target': 'new',
				'domain': '[]',
			 }

	def create_product_attribute(self, cr, uid, url, session, attribute_id, name, label, context=None):
		if context is None:
			context = {}
		name = name.lower().replace(" ","_").replace("-","_")
		name = name.strip()
		if session:
			attrribute_data = {
					'attribute_code':name,
					'scope':'global',
					'frontend_input':'select',
					'is_configurable':1,
					'is_required':1,
					'frontend_label':[{'store_id':0,'label':label}]
				}
			mage_attribute_id = 0
			mage_id = self.server_call(cr ,uid, session, url, 'product_attribute.create', [attrribute_data])
			if mage_id[0] > 0:
				mage_attribute_id = mage_id[1]
			else:
				attribute_data = self.server_call(cr ,uid, session, url, 'product_attribute.info', [name])
				if attribute_data[0] > 0:
					mage_attribute_id = attribute_data[1]['attribute_id']
				else:
					return mage_id
			erp_map_data = {
					'name':attribute_id, 
					'erp_id':attribute_id, 
					'mage_id':mage_attribute_id,
					'instance_id':context.get('instance_id'),
				}	
			self.pool.get('magento.product.attribute').create(cr, uid, erp_map_data)
			mage_map_data = {
								'name':name, 
								'mage_attribute_id':mage_attribute_id,
								'erp_attribute_id':attribute_id
							}
			self.server_call(cr ,uid, session, url, 'magerpsync.attribute_map', [mage_map_data])
			return mage_id

	def create_attribute_value(self, cr, uid, url, session, mage_attr_id, erp_attr_id, name, position='0', context=None):
		if context is None:
			context = {}
		if session:
			name = name.strip()
			options_data = {
						'label':[{'store_id':0, 'value':name}],
						'order':position,
						'is_default':0
					}
			mage_id = self.server_call(cr ,uid, session, url, 'product_attribute.addOption', [mage_attr_id, options_data])
			if mage_id[0] > 0:
				erp_map_data = {
								'name':erp_attr_id,
								'erp_id':erp_attr_id,
								'mage_id':mage_id[1],
								'instance_id':context.get('instance_id')
								}
				self.pool.get('magento.product.attribute.value').create(cr, uid, erp_map_data, context)
				mage_map_data = {
								'name':name, 
								'mage_attribute_option_id':int(mage_id[1]),
								'erp_attribute_option_id':erp_attr_id
								}				
				self.server_call(cr ,uid, session, url, 'magerpsync.attributeoption_map', [mage_map_data])
				return mage_id
			else:
				return mage_id

	def assign_attribute_Set(self, cr, uid, template_ids, context=None):
		if context is None:
			context = {}
		temp_pool = self.pool.get('product.template')
		connection = self.pool.get('magento.configure')._create_connection(cr, uid, context=context)
		if connection:
			success_ids = []
			for temp_id in template_ids:
				attribute_line_ids = temp_pool.browse(cr, uid, temp_id).attribute_line_ids
				set_id = self.get_default_attribute_set(cr, uid, context=context)
				if attribute_line_ids:
					set_id = self.get_magento_attribute_set(cr, uid, attribute_line_ids, context=context)					
				
				if set_id:
					temp_pool.write(cr, uid, temp_id, {'attribute_set_id':set_id}, context=context)
					success_ids.append(temp_id)
		else:
			raise osv.except_osv(("Connection Error"),("Error in Odoo Connection"))
		return True

	def get_default_attribute_set(self, cr, uid, context=None):
		mage_set_pool = self.pool.get('magento.attribute.set')
		default_search = mage_set_pool.search(cr, uid,[('set_id','=',4),('instance_id','=',context['instance_id'])])
		if default_search:
			return default_search[0]
		else:
			raise osv.except_osv(_('Information'), _("Default Attribute set not Found, please sync all Attribute set from Magento!!!"))

	def get_magento_attribute_set(self, cr, uid, attribute_line_ids, context=None):
		flag = False
		attribute_ids = []
		template_attribute_ids = []
		mage_set_pool = self.pool.get('magento.attribute.set')
		for attr in attribute_line_ids:
			template_attribute_ids.append(attr.attribute_id.id)			
		set_ids = mage_set_pool.search(cr, uid, [('instance_id','=',context['instance_id'])], order="set_id asc")		
		for set_id in set_ids:
			set_attribute_ids = mage_set_pool.browse(cr, uid, set_id, context=context).attribute_ids.ids			
			common_attributes = list(set(set_attribute_ids) & set(template_attribute_ids))
			template_attribute_ids.sort()
			if common_attributes == template_attribute_ids:
				return set_id
						
		return False

	#############################################
	##    	Start Of Category Synchronizations ##
	#############################################


	#############################################
	##    		Export/Update Categories   	   ##
	#############################################
	
	def get_map_category_ids(self, cr, uid, category_ids, context=None):
		if context is None:
			context = {}

		product_category_ids = []		
		mage_cat_pool = self.pool.get('magento.category')
		map_ids = mage_cat_pool.search(cr, uid, [('instance_id','=',context['instance_id'])], context=context)		
		for map_id in map_ids:
			product_category_ids.append(mage_cat_pool.browse(cr, uid, map_id).oe_category_id)
		erp_category_ids = list(set(category_ids) | set(product_category_ids))
		erp_category_ids = list(set(erp_category_ids) ^ set(product_category_ids))
		return erp_category_ids
	
	def get_update_category_ids(self, cr, uid, category_ids, context=None):	
		if context is None:
			context = {}
		map_category_ids = []
		mage_cat_pool = self.pool.get('magento.category')
		map_ids = mage_cat_pool.search(cr, uid, [('need_sync','=','Yes'),('mag_category_id','!=',-1),('instance_id','=',context['instance_id'])], context=context)		
		for map_id in map_ids:
			if mage_cat_pool.browse(cr, uid, map_id).oe_category_id in category_ids:
				map_category_ids.append(map_id)
		return map_category_ids

	def export_categories_check(self, cr, uid, context = None):
		if context is None:
			context = {}
		text = text1 = text2= ''
		up_error_ids = []
		success_ids = []
		success_up_ids = []
		category_ids = []
		connection = self.pool.get('magento.configure')._create_connection(cr, uid, context=context)
		if connection:
			mage_cat_pool = self.pool.get('magento.category')
			mage_sync_history = self.pool.get('magento.sync.history')
			url = connection[0]
			session = connection[1]
			instance_id = context['instance_id'] = connection[2]			
			
			if context.has_key('active_model') and context.get('active_model') == "product.category":
				category_ids = context.get('active_ids')
			else:
				category_ids = self.pool.get('product.category').search(cr, uid, [], context=context)

			if context.has_key('sync_opr') and context['sync_opr'] == 'export':
				erp_category_ids = self.get_map_category_ids(cr, uid, category_ids, context=context)				
				if not erp_category_ids:
					raise osv.except_osv(_('Information'), _("All category(s) has been already exported on magento."))
				for erp_category_id in erp_category_ids:
					categ_id = self.sync_categories(cr, uid, url, session, erp_category_id, context=context)
					if categ_id:
						success_ids.append(categ_id)
						text = "\nThe Listed category ids %s has been created on magento."%(success_ids)
						mage_sync_history.create(cr,uid,{'status':'yes','action_on':'category','action':'b','error_message':text}, context)
			
			if context.has_key('sync_opr') and context['sync_opr'] == 'update':
				update_map_ids = self.get_update_category_ids(cr, uid, category_ids, context=context)			
				if not update_map_ids:
					raise osv.except_osv(_('Information'), _("All category(s) has been already updated on magento."))
				cat_update = self._update_specific_category(cr, uid, update_map_ids, url, session, context=context)
				if cat_update:
					if cat_update[0] != 0:
						success_up_ids.append(cat_update[1])
						text1 = '\nThe Listed category ids %s has been successfully updated to Magento. \n'%success_up_ids
						mage_sync_history.create(cr,uid,{'status':'yes','action_on':'category','action':'c','error_message':text1}, context)
					else:
						up_error_ids.append(cat_update[1])
						text2 = '\nThe Listed category ids %s does not updated on magento.'%up_error_ids
						mage_sync_history.create(cr,uid,{'status':'no','action_on':'category','action':'c','error_message':text2}, context)

			partial = self.pool.get('message.wizard').create(cr, uid, {'text':text+text1+text2})
			return { 'name':_("Information"),
					 'view_mode': 'form',
					 'view_id': False,
					 'view_type': 'form',
					'res_model': 'message.wizard',
					 'res_id': partial,
					 'type': 'ir.actions.act_window',
					 'nodestroy': True,
					 'target': 'new',
					 'domain': '[]',
					}
		########## update specific category ##########
	
	def _update_specific_category(self, cr, uid, update_map_ids, url, session, context=None):
		cat_mv = False
		get_category_data = {}
		category_ids = []
		cat_pool = self.pool.get('magento.category')
		for id in update_map_ids:
			cat_obj = cat_pool.browse(cr, uid, id)
			cat_id = cat_obj.oe_category_id
			mage_id = cat_obj.mag_category_id
			mag_parent_id = 1
			if cat_id and mage_id:
				category_ids.append(cat_id)
				obj_cat = self.pool.get('product.category').browse(cr, uid, cat_id, context=context)
				get_category_data['name'] = obj_cat.name
				get_category_data['available_sort_by'] = 1
				get_category_data['default_sort_by'] = 1
				parent_id = obj_cat.parent_id.id or False
				if parent_id:
					search = cat_pool.search(cr,uid,[('cat_name','=',parent_id),('instance_id','=',context['instance_id'])])
					if search:
						mag_parent_id = cat_pool.browse(cr, uid, search[0], context=context).mag_category_id or 1
					else:
						mag_parent_id = self.sync_categories(cr, uid, url, session, parent_id, context)
				update_data = [mage_id, get_category_data]
				move_data = [mage_id, mag_parent_id]
				self.server_call(cr ,uid, session, url, 'catalog_category.update', update_data)				
				self.server_call(cr ,uid, session, url, 'catalog_category.move', move_data)
				cat_pool.write(cr, uid, id, {'need_sync':'No'}, context)				
		return [1, category_ids]

	def sync_categories(self, cr, uid, url, session, erp_category_id, context=None):
		if context is None:
			context = {}
		map_category_obj = self.pool.get('magento.category')
		instance_id = 0
		if context.has_key('instance_id'):
			instance_id = context['instance_id']
		else:
			connection = self.pool.get('magento.configure')._create_connection(cr, uid, context=context)
			if connection:
				instance_id = connection[2]
		if erp_category_id:
			map_category_ids = map_category_obj.search(cr ,uid, [('cat_name','=',erp_category_id),('instance_id','=',instance_id)])
			if not map_category_ids:
				obj_catg = self.pool.get('product.category').browse(cr, uid, erp_category_id, context=context)
				name = obj_catg.name
				if obj_catg.parent_id.id:
					p_cat_id = self.sync_categories(cr, uid, url, session, obj_catg.parent_id.id, context)
				else:
					p_cat_id = self.create_category(cr, uid, url, session, erp_category_id, 1, name, context)
					if p_cat_id[0] > 0:
						return p_cat_id[1]
					else:
						return False
				category_id = self.create_category(cr, uid, url, session, erp_category_id, p_cat_id, name, context)
				if category_id[0] > 0:
					return category_id[1]
				else:
					False
			else:
				mage_id = map_category_obj.browse(cr, uid, map_category_ids[0]).mag_category_id
				return mage_id
		else:
			return False

	def create_category(self, cr, uid, url, session, catg_id, parent_id, catgname, context=None):
		if context is None:
			context = {}
		if catg_id < 1:
			return False

		catgdetail = dict({
			'name':catgname,
			'is_active':1,
			'available_sort_by':1,
			'default_sort_by' : 1,
			'is_anchor' : 1,
			'include_in_menu' : 1
		})
		updatecatg = [parent_id,catgdetail]	
		mage_cat = self.server_call(cr ,uid, session, url, 'catalog_category.create', updatecatg)		
		if mage_cat[0] > 0:
			##########  Mapping Entry  ###########
			self.pool.get('magento.category').create(cr, uid, {'cat_name':catg_id,'oe_category_id':catg_id,'mag_category_id':mage_cat[1],'created_by':'odoo','instance_id':context.get('instance_id')})
			self.server_call(cr ,uid, session, url, 'magerpsync.category_map', [{'mage_category_id':mage_cat[1],'erp_category_id':catg_id}])
		return mage_cat


	
	#############################################
	##    	End Of Category Synchronizations   ##
##########################################################

##########################################################
	##    	Start Of Product Synchronizations  ##
	#############################################

	#############################################
	##    		export all products		       ##
	#############################################
	
	def get_map_template_ids(self, cr, uid, product_template_ids, context=None):
		if context is None:
			context = {}

		template_ids = []
		update_template_map_ids = []
		mage_product_obj = self.pool.get('magento.product.template')
		if context.has_key('sync_opr') and context['sync_opr'] == 'export':
			map_ids = mage_product_obj.search(cr, uid, [('instance_id','=',context['instance_id'])], context=context)	
			for map_id in map_ids:
				map_obj = mage_product_obj.browse(cr, uid, map_id)
				erp_template_id = map_obj.erp_template_id
				template_ids.append(erp_template_id)
			not_mapped_template_ids = list(set(product_template_ids) | set(template_ids))
			not_mapped_template_ids = list(set(not_mapped_template_ids) ^ set(template_ids))
			return not_mapped_template_ids			
		if context.has_key('sync_opr') and context['sync_opr'] == 'update':
			for product_template_id in product_template_ids:
				map_ids = mage_product_obj.search(cr, uid, [('instance_id','=',context['instance_id']),('need_sync','=','Yes'),('erp_template_id','=',product_template_id)], context=context)
				if map_ids:
					update_template_map_ids.append(map_ids[0])
			return update_template_map_ids
		return False

	#############################################
	##  export bulk/selected products template ##
	#############################################

	def export_product_check(self, cr, uid, context = None):
		if context is None:
			context = {}
		text = text1 = text2= ''
		up_error_ids = []
		success_ids = []
		error_ids = []
		success_exp_ids = []
		success_up_ids = []
		template_ids = []
		not_mapped_template_ids = 0
		update_mapped_template_ids = 0
		connection = self.pool.get('magento.configure')._create_connection(cr, uid, context=context)
		if connection:
			mage_sync_history = self.pool.get('magento.sync.history')
			template_obj = self.pool.get('product.template')
			url = connection[0]
			session = connection[1]
			instance_id = context['instance_id'] = connection[2]			
			pro_dt = len(self.pool.get('product.attribute').search(cr, uid, [], context=context))
			map_dt = len(self.pool.get('magento.product.attribute').search(cr, uid, [('instance_id','=',context['instance_id'])], context=context))
			pro_op = len(self.pool.get('product.attribute.value').search(cr, uid, [], context=context))
			map_op = len(self.pool.get('magento.product.attribute.value').search(cr, uid, [('instance_id','=',context['instance_id'])]))		
			if pro_dt != map_dt or pro_op != map_op:
				raise osv.except_osv(('Warning'),_('Please, first map all ERP Product attributes and it\'s all options'))
			if context.has_key('active_model') and context.get('active_model') == "product.template":
				template_ids = context.get('active_ids')
			else:
				template_ids = template_obj.search(cr, uid, [('type','!=','service')], context=context)
			if not template_ids:
				raise osv.except_osv(_('Information'), _("No new product(s) Template found to be Sync."))
			
			if context.has_key('sync_opr') and context['sync_opr'] == 'export':
				not_mapped_template_ids = self.get_map_template_ids(cr, uid, template_ids, context=context)				
				if not not_mapped_template_ids:
					raise osv.except_osv(_('Information'), _("Listed product(s) has been already exported on magento."))
				for template_id in not_mapped_template_ids:
					prodtype = template_obj.browse(cr, uid, template_id, context=context).type
					if prodtype == 'service':
						error_ids.append(template_id)
						continue
					pro = self._export_specific_template(cr, uid, template_id, url, session, context=context)
					if pro:
						if pro[0] > 0:
							success_exp_ids.append(template_id)
						else:
							error_ids.append(pro[1])
					else:
						continue

			if context.has_key('sync_opr') and context['sync_opr'] == 'update':
				update_mapped_template_ids = self.get_map_template_ids(cr, uid, template_ids, context=context)
				if not update_mapped_template_ids:
					raise osv.except_osv(_('Information'), _("Listed product(s) has been already updated on magento."))
				for template_map_id in update_mapped_template_ids:
					pro_update = self._update_specific_product_template(cr, uid, template_map_id, url, session, context)
					if pro_update:
						if pro_update[0] > 0:
							success_up_ids.append(pro_update[1])
						else:
							up_error_ids.append(pro_update[1])
			if success_exp_ids:
				text = "\nThe Listed product(s) %s successfully created on Magento."%(success_exp_ids)
			if error_ids:
				text += '\nThe Listed Product(s) %s does not synchronized on magento.'%error_ids
			if text:
				mage_sync_history.create(cr, uid, {'status':'yes','action_on':'product','action':'b','error_message':text}, context)
			if success_up_ids:
				text1 = '\nThe Listed Product(s) %s has been successfully updated to Magento. \n'%success_up_ids
				mage_sync_history.create(cr, uid, {'status':'yes','action_on':'product','action':'c','error_message':text1}, context)
			if up_error_ids:
				text2 = '\nThe Listed Product(s) %s does not updated on magento.'%up_error_ids				
				mage_sync_history.create(cr, uid, {'status':'no','action_on':'product','action':'c','error_message':text2}, context)
			partial = self.pool.get('message.wizard').create(cr, uid, {'text':text+text1+text2})
			return { 'name':_("Information"),
					 'view_mode': 'form',
					 'view_id': False,
					 'view_type': 'form',
					'res_model': 'message.wizard',
					 'res_id': partial,
					 'type': 'ir.actions.act_window',
					 'nodestroy': True,
					 'target': 'new',
					 'domain': '[]',
				}

	#############################################
	##    		Specific template sync	       ##
	#############################################
	
	def _export_specific_template(self , cr, uid, template_id, url, session, context=None):
		if context is None:
			context = {}
		if template_id:
			mage_set_id = 0
			get_product_data = {}
			mage_price_changes = {}
			mage_attribute_ids = []
			map_tmpl_pool = self.pool.get('magento.product.template') 
			val_price_pool = self.pool.get('product.attribute.price')
			product_tmp_pool = self.pool.get('product.template')
			obj_pro = product_tmp_pool.browse(cr, uid, template_id, context=context)
			template_sku = obj_pro.default_code or 'Template Ref %s'%template_id
			if not obj_pro.product_variant_ids:
				return [-2, str(template_id)+' No Variant Ids Found!!!']	
			else:
				if not obj_pro.attribute_set_id.id:
					self.assign_attribute_Set(cr, uid, [template_id], context=context)
				set_id = obj_pro.attribute_set_id.id
				set_id = self._check_valid_attribute_set(cr, uid, set_id, template_id, context=context)
				wk_attribute_line_ids = obj_pro.attribute_line_ids
				
				if not wk_attribute_line_ids:
					template_sku = 'single_variant'
					mage_ids = self._sync_template_variants(cr, uid, obj_pro, template_sku, url, session, context=context)
					price = obj_pro.list_price or 0.0
					if mage_ids:
						erp_map_data = {
										'template_name':template_id,
										'erp_template_id':template_id,
										'mage_product_id':mage_ids[0],
										'base_price':price,
										'is_variants':False,
										'instance_id':context.get('instance_id')
										}
						check = map_tmpl_pool.create(cr, uid, erp_map_data)
						return mage_ids
				else:
					check_attribute = self._check_attribute_with_set(cr, uid, set_id, wk_attribute_line_ids)
					if check_attribute and check_attribute[0] == -1:
						return check_attribute
					mage_set_id = obj_pro.attribute_set_id.set_id
					if not mage_set_id:
						return [-3, str(template_id)+' Attribute Set Name not found!!!']
					else:
						for type_obj in wk_attribute_line_ids:
							mage_attr_ids = self._check_attribute_sync(cr, uid, type_obj)
							if not mage_attr_ids:
								return [-1, str(template_id)+' Attribute not syned at magento!!!']
							mage_attribute_ids.append(mage_attr_ids[0])
							get_product_data['configurable_attributes'] = mage_attribute_ids
							attrname = type_obj.attribute_id.name.lower().replace(" ","_").replace("-","_")
							val_dic = self._search_single_values(cr, uid, template_id, type_obj.attribute_id.id, context=context)
							if val_dic:
								context.update(val_dic)
							for value_id in type_obj.value_ids:
								price_extra = 0.0
								##### product template and value extra price ##### 
								price_search = val_price_pool.search(cr, uid, [('product_tmpl_id','=',template_id),('value_id','=',value_id.id)])
								if price_search:
									price_extra = val_price_pool.browse(cr, uid, price_search[0]).price_extra
								valuename = value_id.name
								if mage_price_changes.has_key(attrname):
									mage_price_changes[attrname].update({valuename:price_extra})
								else:
									mage_price_changes[attrname] = {valuename:price_extra}
						mage_ids = self._sync_template_variants(cr, uid, obj_pro, template_sku, url, session, context=context)
						get_product_data['associated_product_ids'] = mage_ids
						get_product_data['price_changes'] = mage_price_changes
						get_product_data['visibility'] = 4
						get_product_data['price'] = obj_pro.list_price or 0.00
						get_product_data = self._get_product_array(cr, uid, url, session, obj_pro, get_product_data, context=context)
						get_product_data['tax_class_id'] = '0'
						template_sku = 'Template sku %s'%template_id
						newprod_data = ['configurable', mage_set_id, template_sku, get_product_data]
						product_tmp_pool.write(cr, uid, template_id, {'prod_type':'configurable'}, context=context)
						mage_product_id = self.server_call(cr ,uid, session, url, 'product.create', newprod_data)						
						if mage_product_id[0] > 0:
							self.server_call(cr ,uid, session, url, 'product_stock.update', [mage_product_id[1],{'manage_stock':1,'is_in_stock':1}])
							map_tmpl_pool.create(cr, uid, {'template_name':template_id, 'erp_template_id':template_id, 'mage_product_id':mage_product_id[1], 'base_price': get_product_data['price'], 'is_variants':True, 'instance_id':context.get('instance_id')})
							self.server_call(cr ,uid, session, url, 'magerpsync.template_map', [{'mage_template_id':mage_product_id[1],'erp_template_id':template_id}])
							self._create_product_attribute_media(cr, uid, url, session, obj_pro, mage_product_id[1] , template_id, context=context)
							return mage_product_id
						else:
							return [0, str(template_id)+"Not Created at magento"]
		else:
			return False


	def get_attribute_price_list(self, cr, uid, wk_attribute_line_ids, template_id, context=None):
		mage_price_changes = []
		val_price_pool = self.pool.get('product.attribute.price')

		for type_obj in wk_attribute_line_ids:
			for value_id in type_obj.value_ids:
				mage_price_changes_data = {}
				price_extra = 0.0
				##### product template and value extra price ##### 
				price_search = val_price_pool.search(cr, uid, [('product_tmpl_id','=',template_id),('value_id','=',value_id.id)])
				mage_value_obj = self.pool.get('magento.product.attribute.value').search(cr, uid, [('name','=',value_id.id)])
				if mage_value_obj:
					mage_value_id = self.pool.get('magento.product.attribute.value').browse(cr, uid, mage_value_obj[0]).mage_id
					mage_price_changes_data['value_id'] = mage_value_id
				if price_search:
					price_extra = val_price_pool.browse(cr, uid, price_search[0]).price_extra
					mage_price_changes_data['price'] = price_extra
				mage_price_changes.append(mage_price_changes_data)
		return mage_price_changes


	def _check_valid_attribute_set(self, cr, uid, set_id, template_id, context=None):
		if context is None:
			context = {}
		if context.has_key('instance_id'):
			instance_id = self.pool.get('magento.attribute.set').browse(cr, uid, set_id).instance_id.id
			if instance_id == context['instance_id']:
				return set_id
			else:
				return False
		else:
			return False

	############# sync template variants ########				
	def _sync_template_variants(self, cr, uid, temp_obj, template_sku, url, session, context=None):
		if context is None:
			context = {}
		mage_variant_ids = []
		map_prod_pool = self.pool.get('magento.product')		
		for obj in temp_obj.product_variant_ids:
			vid = obj.id
			search_ids = map_prod_pool.search(cr, uid, [('oe_product_id','=',vid),('instance_id','=',context.get('instance_id'))])						
			if search_ids:
				map_obj = map_prod_pool.browse(cr, uid, search_ids[0])
				mage_variant_ids.append(map_obj.mag_product_id)
			else:
				mage_ids = self._export_specific_product(cr, uid, vid, template_sku, url, session, context=context)
				if mage_ids and mage_ids[0]>0:
					mage_variant_ids.append(mage_ids[1])
		return mage_variant_ids
	
	############# check single attribute lines ########
	def _search_single_values(self, cr, uid, temp_id, attr_id, context):
		dic = {}
		attr_line_pool = self.pool.get('product.attribute.line')
		search_ids  = attr_line_pool.search(cr, uid, [('product_tmpl_id','=',temp_id),('attribute_id','=',attr_id)], context=context)		
		if search_ids and len(search_ids) == 1:
			att_line_obj = attr_line_pool.browse(cr, uid, search_ids[0], context=context)
			if len(att_line_obj.value_ids) == 1:
				dic[att_line_obj.attribute_id.name] = att_line_obj.value_ids.name
		return dic


	############# check attributes lines and set attributes are same ########
	def _check_attribute_with_set(self, cr, uid, set_id, attribute_line_ids):
		set_attr_ids = self.pool.get('magento.attribute.set').browse(cr, uid, set_id).attribute_ids
		if not set_attr_ids:
			return [-1, str(id)+' Attribute Set Name has no attributes!!!']
		set_attr_list = list(set_attr_ids.ids)
		for attr_id in attribute_line_ids:	
			if attr_id.attribute_id.id not in set_attr_list:
				return [-1, str(id)+' Attribute Set Name not matched with attributes!!!']
		return [1]

	############# check attributes syned return mage attribute ids ########
	def _check_attribute_sync(self, cr, uid, type_obj):
		map_attr_pool = self.pool.get('magento.product.attribute')
		mage_attribute_ids = []
		type_search = map_attr_pool.search(cr, uid, [('name','=',type_obj.attribute_id.id)])
		if type_search:
			map_type_obj = map_attr_pool.browse(cr, uid, type_search[0])
			mage_attr_id = map_type_obj.mage_id
			mage_attribute_ids.append(mage_attr_id)
		return mage_attribute_ids

	############# fetch product details ########
	def _get_product_array(self, cr, uid, url, session, obj_pro, get_product_data, context=None):
		prod_catg = []
		for i in obj_pro.categ_ids:
			mage_categ_id = self.sync_categories(cr, uid, url, session, i.id, context=context)
			prod_catg.append(mage_categ_id)
		if obj_pro.categ_id.id:
			mage_categ_id = self.sync_categories(cr, uid, url, session, obj_pro.categ_id.id, context=context)
			prod_catg.append(mage_categ_id)
		status = 2
		if obj_pro.sale_ok:
			status = 1
		get_product_data['name'] = obj_pro.name
		get_product_data['short_description'] = obj_pro.description_sale or ' '
		get_product_data['description'] = obj_pro.description or ' '
		get_product_data['weight'] = obj_pro.weight_net or 0.00
		get_product_data['categories'] = prod_catg
		get_product_data['ean'] = obj_pro.ean13		
		get_product_data['status'] = status
		if not get_product_data.has_key('websites'):
			get_product_data['websites'] = [1]
		return get_product_data

	############# create product image ########
	def _create_product_attribute_media(self, cr, uid, url, session, obj_pro, mage_product_id, odoo_product_id, context=None):
		if obj_pro.image:			
			image_file = {'content':obj_pro.image,'mime':'image/jpeg'}
			if image_file:
				self.server_call(cr ,uid, session, url, 'magerpsync.update_product_image', [[mage_product_id, image_file, "create"]])
				return True

	############# Update product image ########
	def _update_product_attribute_media(self, cr, uid, url, session, obj_pro, mage_product_id, odoo_product_id, context=None):
		if obj_pro.image:			
			image_file = {'content':obj_pro.image,'mime':'image/jpeg'}
			self.server_call(cr ,uid, session, url, 'magerpsync.update_product_image',[[mage_product_id, image_file, "write", 0]])
			return True
		return False


	#############################################
	##    		Specific product sync	       ##
	#############################################
	def _export_specific_product(self, cr, uid, id, template_sku, url, session, context=None):
		"""
		@param code: product Id.
		@param context: A standard dictionary
		@return: list
		"""
		get_product_data = {}
		if context is None:
			context = {}
		map_variant=[]		
		pro_attr_id = 0
		price_extra = 0
		mag_pro_pool = self.pool.get('magento.product')
		if id:
			obj_pro = self.pool.get('product.product').browse(cr, uid, id)
			if template_sku == "single_variant":
				get_product_data['visibility'] = 4
			else:
				get_product_data['visibility'] = 1
			sku = obj_pro.default_code or 'Ref %s'%id
			# if template_sku == sku:
			# 	sku = 'Variant Ref %s'%id			
			get_product_data['currentsetname'] = ""
			if obj_pro.attribute_value_ids:
				for value_id in obj_pro.attribute_value_ids:
					map_id = self.pool.get('magento.product.attribute.value').search(cr, uid, [('name','=',value_id.id)])
					if not map_id:
						erp_attr_id = value_id.attribute_id.id
						map_attribute_ids = self.pool.get('magento.product.attribute').search(cr, uid, [('name','=',erp_attr_id)])
						if map_attribute_ids:
							map_attribute_obj = self.pool.get('magento.product.attribute').browse(cr, uid, map_attribute_ids[0], context)
							mage_attr_id = map_attribute_obj[0].mage_id
							self.create_attribute_value(cr, uid, url, session, mage_attr_id, value_id.id, value_id.name, position='0', context=context)
					attrname = str(_unescape(value_id.attribute_id.name)).lower().replace(" ","_").replace("-","_")
					valuename = value_id.name
					get_product_data[attrname] = valuename					
					pro_attr_id = value_id.attribute_id.id
					search_price_id = self.pool.get('product.attribute.price').search(cr, uid, [('product_tmpl_id','=',obj_pro.product_tmpl_id.id),('value_id','=',value_id.id)])
					if search_price_id:
						price_extra += self.pool.get('product.attribute.price').browse(cr,uid, search_price_id[0]).price_extra

			get_product_data['currentsetname'] = obj_pro.product_tmpl_id.attribute_set_id.name
			get_product_data['price'] = obj_pro.list_price+price_extra or 0.00
			get_product_data = self._get_product_array(cr, uid, url, session, obj_pro, get_product_data, context=context)			
			get_product_data['tax_class_id'] = '0'
			if obj_pro.type in ['product','consu']:
				prodtype = 'simple'
			else:
				prodtype = 'virtual'	
			self.pool.get('product.product').write(cr, uid, id, {'prod_type':prodtype}, context)
			pro = self.prodcreate(cr, uid, url, session, id, prodtype, sku, get_product_data, context)
			if pro and pro[0] != 0:
				self._create_product_attribute_media(cr, uid, url, session, obj_pro, pro[1], id, context)
			return pro

	#############################################
	##    		single products	create 	       ##
	#############################################
	def prodcreate(self, cr, uid, url, session, pro_id, prodtype, prodsku, put_product_data, context):
		if put_product_data['currentsetname']:
			current_set = put_product_data['currentsetname']
		else:
			currset = self.server_call(cr ,uid, session, url, 'product_attribute_set.list')			
			current_set = ""
			if currset[0] > 0:
				current_set = currset[1].get('set_id')
		newprod = [prodtype, current_set, prodsku, put_product_data]
		pro = self.server_call(cr ,uid, session, url, 'product.create', newprod)
		if pro[0] > 0:
			oe_product_qty = self.pool.get('product.product').browse(cr,uid,pro_id).qty_available
			quantity = oe_product_qty
			self.server_call(cr ,uid, session, url, 'product_stock.update', [pro[1] ,{'manage_stock':1,'qty':oe_product_qty,'is_in_stock':1}])
			erp_map_data = {
							'pro_name':pro_id,
							'oe_product_id':pro_id,
							'mag_product_id':pro[1] ,
							'instance_id':context.get('instance_id')
							}
			check = self.pool.get('magento.product').create(cr, uid, erp_map_data)
			self.server_call(cr ,uid, session, url, 'magerpsync.product_map', [{'mage_product_id':pro[1] ,'erp_product_id':pro_id}])
		return  pro

	#############################################
	##    	update specific product template   ##
	#############################################
	def _update_specific_product_template(self, cr, uid, id, url, session, context=None):
		if context is None:
			context = {}
		get_product_data = {}
		mage_variant_ids=[]
		mage_price_changes = {}
		map_tmpl_pool = self.pool.get('magento.product.template')
		temp_obj = map_tmpl_pool.browse(cr, uid, id)
		temp_id = temp_obj.template_name.id
		mage_id = temp_obj.mage_product_id
		mage_ids = []
		if temp_id and mage_id:
			map_prod_pool = self.pool.get('magento.product')			
			obj_pro = self.pool.get('product.template').browse(cr, uid, temp_id, context)			
			get_product_data['price'] = obj_pro.list_price or 0.00
			get_product_data = self._get_product_array(cr, uid, url, session, obj_pro, get_product_data, context)			
			if obj_pro.product_variant_ids:
				if temp_obj.is_variants == True and obj_pro.is_product_variant == False:
					if obj_pro.attribute_line_ids :
						for obj in obj_pro.product_variant_ids:
							mage_update_ids = []
							vid = obj.id
							search_ids = map_prod_pool.search(cr, uid, [('oe_product_id','=',vid),('instance_id','=',context['instance_id'])])
							if search_ids:
								mage_update_ids = self._update_specific_product(cr, uid, search_ids[0], url, session, context)
							else:
								template_sku = obj_pro.default_code or 'Template Ref %s'%temp_id
								mage_ids = self._sync_template_variants(cr, uid, obj_pro, template_sku, url, session, context=context)
				else:
					for obj in obj_pro.product_variant_ids:
						price = obj_pro.list_price or 0.0
						mage_update_ids = []
						vid = obj.id
						search_ids = map_prod_pool.search(cr, uid, [('oe_product_id','=',vid),('instance_id','=',context['instance_id'])])
						if search_ids:
							mage_update_ids = self._update_specific_product(cr, uid, search_ids[0], url, session, context=context)			
						if mage_update_ids and mage_update_ids[0]>0:
							map_tmpl_pool.write(cr, uid, id, {'need_sync':'No'}, context)
						return mage_update_ids
				if mage_id:
					check = self._update_product_attribute_media(cr, uid, url, session, obj_pro, mage_id, temp_id, context)
				
			else:
				return [-1, str(id)+' No Variant Ids Found!!!']
			attribute_line_ids = temp_obj.template_name.attribute_line_ids
			if mage_ids:
				get_product_data['associated_product_ids'] = mage_ids
			update_data = [mage_id, get_product_data]
			self.server_call(cr ,uid, session, url, 'product.update', update_data)

			attribute_line_data = self.get_attribute_price_list(cr, uid, attribute_line_ids, temp_id, context)
			self.server_call(cr ,uid, session, url, 'magerpsync.product_super_attribute', [mage_id, attribute_line_data])			
			map_tmpl_pool.write(cr, uid, id, {'need_sync':'No'}, context)
			return [1, temp_id]

	#############################################
	##    		update specific product	       ##
	#############################################
	def _update_specific_product(self, cr, uid, id, url, session, context):
		get_product_data = {}
		pro_obj = self.pool.get('magento.product').browse(cr, uid, id)
		pro_id = pro_obj.pro_name.id
		mage_id = pro_obj.mag_product_id
		if pro_id and mage_id:
			quantity = 0
			price_extra=0
			obj_pro = self.pool.get('product.product').browse(cr, uid, pro_id, context)
			if obj_pro.attribute_value_ids:
				for value_id in obj_pro.attribute_value_ids:
					get_product_data[value_id.attribute_id.name] = value_id.name
					pro_attr_id = value_id.attribute_id.id
					search_price_id = self.pool.get('product.attribute.price').search(cr, uid, [('product_tmpl_id','=',obj_pro.product_tmpl_id.id),('value_id','=',value_id.id)])
					if search_price_id:
						price_extra += self.pool.get('product.attribute.price').browse(cr,uid, search_price_id[0]).price_extra
			get_product_data['price'] = obj_pro.list_price+price_extra or 0.00
			get_product_data = self._get_product_array(cr, uid, url, session, obj_pro, get_product_data, context)
			update_data = [mage_id, get_product_data]
			pro = self.server_call(cr ,uid, session, url, 'product.update', update_data)
			if mage_id:
				check = self._update_product_attribute_media(cr, uid, url, session, obj_pro, mage_id, pro_id, context)
			self.pool.get('magento.product').write(cr, uid, id, {'need_sync':'No'}, context)
			if pro[0] > 0 and obj_pro.qty_available>0:
				quantity = obj_pro.qty_available
			con_pool = self.pool.get('magento.configure')
			connection = con_pool.search(cr, uid, [('active','=',True),('inventory_sync','=','enable')], context=context)
			if connection:
				self.server_call(cr ,uid, session, url, 'product_stock.update', [mage_id, {'manage_stock':1, 'qty':quantity,'is_in_stock':1}])				
			return  [1, pro_id]

	def get_mage_region_id(self, cr, uid, url, session, region, country_code, context=None):
		""" 
		@return magneto region id 
		"""
		region_obj = self.pool.get('magento.region')
		map_id = region_obj.search(cr,uid,[('country_code','=',country_code)])
		if not map_id:
			return_id = self.pool.get('region.wizard')._sync_mage_region(cr, uid, url, session, country_code)			
		region_ids = region_obj.search(cr,uid,[('name','=',region),('country_code','=',country_code)])
		if region_ids:
			id = region_obj.browse(cr,uid,region_ids[0]).mag_region_id
			return id
		else:		
			return 0

magento_synchronization()
# END