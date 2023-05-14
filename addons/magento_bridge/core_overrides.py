# -*- coding: utf-8 -*-
##########################################################################
#
#    Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
##########################################################################

import re
import xmlrpclib
from mob import _unescape
from mob import XMLRPC_API
from openerp import workflow
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import SUPERUSER_ID, api


class product_attribute_line(osv.osv):
    _inherit = "product.attribute.line"

    def onchange_attribute_set_id(self, cr, uid, ids, set_id, context=None):
        result = {}
        if set_id:
            obj = self.pool.get(
                "magento.attribute.set").browse(cr, uid, set_id)
            attribute_ids = [x.id for x in obj.attribute_ids]
            result['domain'] = {'attribute_id': [('id', 'in', attribute_ids)]}
        return result

    def create(self, cr, uid, vals, context=None):
        if vals.has_key("product_tmpl_id") and not context.has_key('magento'):
            product_map_ids = self.pool.get('magento.product.template').search(cr, uid, [('template_name','=', vals['product_tmpl_id'])])
            if product_map_ids:
                raise osv.except_osv(('Error'),("You can't introduce new attribute because this product is already synced at Magento. This error is coming because Magento never allow to add new attribute inside configurable products."))
            
        return super(product_attribute_line, self).create(cr, uid, vals, context=context)

class product_attribute(osv.osv):
    _inherit = 'product.attribute'

    def _check_unique_insesitive(self, cr, uid, ids, context=None):
        sr_ids = self.search(cr, uid, [], context=context)
        if sr_ids:
            lst = [x.name.lower() for x in self.browse(
                cr, uid, sr_ids, context=context) if x.name and x.id not in ids]
            for self_obj in self.browse(cr, uid, ids, context=context):
                if self_obj.name and self_obj.name.lower() in lst:
                    return False
                return True
        return False

    def _check_valid_attribute(self, cr, uid, ids, context=None):
        self_obj = self.browse(cr, uid, ids, context=context)
        check_valid = re.search(r"^[a-z][a-z_0-9]{1,30}$", self_obj.name)
        if check_valid:
            return True
        else:
            return False
    _constraints = [(_check_unique_insesitive, 'Attribute name already exists', ['name']),
                    (_check_valid_attribute,
                     'Must be unique and in lowercase with no spaces. Maximum length of attribute code must be less then 30 symbols', ['name'])
                    ]

    def check_attribute(self, cr, uid, vals, context=None):
        attribute_ids = self.search(cr, uid, [])
        for attribute_id in attribute_ids:
            if self.browse(cr, uid, attribute_id).name.lower() == vals['name']:
                return attribute_id
        return False

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        attribute_id = self.check_attribute(cr, uid, vals, context)
        if attribute_id and context.has_key('magento'):
            return attribute_id
        else:
            return super(product_attribute, self).create(cr, uid, vals, context=context)

product_attribute()


class product_attribute_value(osv.osv):
    _inherit = 'product.attribute.value'

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}

        attribute_value_ids = self.search(cr, uid, [('name', '=', vals.get(
            'name')), ('attribute_id', '=', vals.get('attribute_id'))])
        if attribute_value_ids and context.has_key('magento'):
            return attribute_value_ids[0]
        else:
            return super(product_attribute_value, self).create(cr, uid, vals, context=context)


class product_template(osv.osv):
    _inherit = "product.template"

    def _inactive_default_variant(self, cr, uid, product_template_id, context):
        varinat_ids = self.pool.get('product.template').browse(
            cr, uid, product_template_id).product_variant_ids
        for vid in varinat_ids:
            product_pool = self.pool.get('product.product')
            att_line_ids = product_pool.browse(
                cr, uid, vid.id).attribute_line_ids
            if not att_line_ids:
                product_pool.write(cr, uid, [vid.id], {
                                   'active': False}, context)
        return True

    _columns = {
        'prod_type': fields.char('Magento Type'),

        'categ_ids': fields.many2many('product.category', 'product_categ_rel', 'product_id', 'categ_id', 'Product Categories'),

        'attribute_set_id': fields.many2one('magento.attribute.set', 'Magento Attribute Set', help="Magento Attribute Set, Used during configurable product generation at Magento."),
    }

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        mage_id = 0
        if context.has_key('magento'):
            if vals.has_key('name'):
                vals['name'] = _unescape(vals['name'])
            if vals.has_key('description'):
                vals['description'] = _unescape(vals['description'])
            if vals.has_key('description_sale'):
                vals['description_sale'] = _unescape(vals['description_sale'])
            if vals.has_key('category_ids') and vals.get('category_ids'):
                categ_ids = list(set(vals.get('category_ids')))
                default_category = self.pool.get("magento.configure").browse(cr, uid, context['instance_id']).category
                if default_category:
                    vals['categ_id'] = default_category.id
                vals['categ_ids'] = [(6, 0, categ_ids)]
                vals.pop('category_ids')
            if vals.has_key('mage_id'):
                mage_id = vals.get('mage_id')
                vals.pop('mage_id')
        template_id = super(product_template, self).create(
            cr, uid, vals, context=context)
        if context.has_key('magento') and context.has_key('configurable'):
            mapping_pool = self.pool.get('magento.product.template')
            mapping_data = {
                'template_name': template_id,
                'erp_template_id': template_id,
                'mage_product_id': mage_id,
                'base_price': vals['list_price'],
                'is_variants': True,
                'instance_id': context.get('instance_id'),
                'created_by': 'Magento'
            }
            mapping_pool.create(cr, uid, mapping_data)
            self._inactive_default_variant(cr, uid, template_id, context)
        return template_id

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        if context.has_key('magento'):
            if vals.has_key('name'):
                vals['name'] = _unescape(vals['name'])
            if vals.has_key('description'):
                vals['description'] = _unescape(vals['description'])
            if vals.has_key('description_sale'):
                vals['description_sale'] = _unescape(vals['description_sale'])
            if vals.has_key('category_ids') and vals.get('category_ids'):
                categ_ids = list(set(vals.get('category_ids')))
                default_category = self.pool.get("magento.configure").browse(cr, uid, context['instance_id']).category
                if default_category:
                    vals['categ_id'] = default_category.id
                vals['categ_ids'] = [(6, 0, categ_ids)]
            if vals.has_key('mage_id'):
                vals.pop('mage_id')

        map_obj = self.pool.get('magento.product.template')
        for temp_id in ids:
            temp_map_ids = map_obj.search(
                cr, uid, [('template_name', '=', temp_id)])
            if temp_map_ids:
                if not context.has_key('magento'):
                    for temp_map_id in temp_map_ids:
                        map_obj.write(cr, uid, temp_map_id, {
                                      'need_sync': 'Yes'}, context)
                elif context.has_key('magento'):
                    map_obj.write(cr, uid, temp_map_ids[0], {
                                  'need_sync': 'No'}, context)
        return super(product_template, self).write(cr, uid, ids, vals, context)

    def unlink(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        connection_ids = self.pool.get('magento.configure').search(cr, uid, [])
        for template_id in ids:
            for connection_id in connection_ids:
                context['instance_id'] = connection_id
                connection = self.pool.get('magento.configure')._create_connection(
                    cr, uid, context=context)
                product_map_id = self.pool.get('magento.product.template').search(cr, uid, [(
                    'erp_template_id', '=', template_id), ('instance_id', '=', connection_id)])
                if product_map_id:
                    self.pool.get('magento.product.template').unlink(
                        cr, uid, product_map_id[0], context)
                    prod_obj = self.browse(cr, uid, template_id, context)
                    for product_id in prod_obj.product_variant_ids.ids:
                        product_map_id = self.pool.get('magento.product').search(
                            cr, uid, [('oe_product_id', '=', product_id), ('instance_id', '=', connection_id)])
                        if product_map_id:
                            self.pool.get('magento.product').unlink(
                                cr, uid, product_map_id[0], context)
                            if connection:
                                url = connection[0]
                                session = connection[1]
                                server = xmlrpclib.Server(url)
                                try:
                                    server.call(
                                        session, 'magerpsync.product_map_delete', [product_id])
                                except Exception, e:
                                    pass
                    if prod_obj.prod_type == "configurable":
                        if connection:
                            url = connection[0]
                            session = connection[1]
                            server = xmlrpclib.Server(url)
                            try:
                                server.call(
                                    session, 'magerpsync.template_map_delete', [template_id])
                            except Exception, e:
                                pass

        return super(product_template, self).unlink(cr, uid, ids, context=context)

product_template()

class product_product(osv.osv):
    _inherit = 'product.product'

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        mage_id = 0
        attr_val_ids = []
        if context.has_key('magento'):
            if vals.has_key('default_code'):
                vals['default_code'] = _unescape(vals['default_code'])
            if vals.has_key('category_ids') and vals.get('category_ids'):
                categ_ids = list(set(vals.get('category_ids')))
                default_category = self.pool.get("magento.configure").browse(cr, uid, context['instance_id']).category
                if default_category:
                    vals['categ_id'] = default_category.id
                vals['categ_ids'] = [(6, 0, categ_ids)]
                vals.pop('category_ids')
            if vals.has_key('value_ids'):
                attr_val_ids = vals.get('value_ids')
                vals['attribute_value_ids'] = [(6, 0, attr_val_ids)]
            if vals.has_key('mage_id'):
                mage_id = vals.get('mage_id')
                vals.pop('mage_id')
        product_id = super(product_product, self).create(
            cr, uid, vals, context=context)
        if context.has_key('magento'):
            mapping_pool = self.pool.get('magento.product')
            mage_temp_pool = self.pool.get('magento.product.template')
            attribute_val_pool = self.pool.get('product.attribute.value')
            attribute_line_pool = self.pool.get('product.attribute.line')
            template_id = self.browse(cr, uid, product_id).product_tmpl_id.id
            if template_id:
                if attr_val_ids:
                    for attr_val_id in attr_val_ids:
                        attr_id = attribute_val_pool.browse(
                            cr, uid, attr_val_id).attribute_id.id
                        search_ids = attribute_line_pool.search(
                            cr, uid, [('product_tmpl_id', '=', template_id), ('attribute_id', '=', attr_id)])
                        if search_ids:
                            attribute_line_pool.write(cr, uid, search_ids, {
                                                      'value_ids': [(4, attr_val_id)]}, context)
                if mage_id:
                    search_ids = mage_temp_pool.search(
                        cr, uid, [('erp_template_id', '=', template_id)])
                    if not search_ids:
                        price = 0
                        if vals.has_key('list_price'):
                            price = vals['list_price']
                        mage_temp_pool.create(cr, uid, {
                            'template_name': template_id,
                            'erp_template_id': template_id,
                            'mage_product_id': mage_id,
                            'base_price': price,
                            'instance_id': context.get('instance_id'),
                            'created_by': 'Magento'
                        })
                    else:
                        mage_temp_pool.write(cr, uid, search_ids[0], {
                                             'need_sync': 'No'}, context)
                    mapping_pool.create(cr, uid, {'pro_name': product_id, 'oe_product_id': product_id,
                                                  'mag_product_id': mage_id, 'instance_id': context.get('instance_id'), 'created_by': 'Magento'})

        return product_id

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]

        if context.has_key('magento'):
            if vals.has_key('default_code'):
                vals['default_code'] = _unescape(vals['default_code'])
            if vals.has_key('category_ids') and vals.get('category_ids'):
                categ_ids = list(set(vals.get('category_ids')))
                default_category = self.pool.get("magento.configure").browse(cr, uid, context['instance_id']).category
                if default_category:
                    vals['categ_id'] = default_category.id
                vals['categ_ids'] = [(6, 0, categ_ids)]
                vals.pop('category_ids')
            if vals.has_key('mage_id'):
                vals.pop('mage_id')
        product_map_pool = self.pool.get('magento.product')
        template_map_pool = self.pool.get('magento.product.template')
        for pro_id in ids:
            map_ids = []
            if context.has_key('instance_id'):
                map_ids = product_map_pool.search(
                    cr, uid, [('pro_name', '=', pro_id), ('instance_id', '=', context['instance_id'])])
            else:
                map_ids = product_map_pool.search(
                    cr, uid, [('pro_name', '=', pro_id)])
            if map_ids:
                if not context.has_key('magento'):
                    product_map_pool.write(cr, uid, map_ids[0], {
                                           'need_sync': 'Yes'}, context)
                elif context.has_key('magento'):
                    ress = product_map_pool.write(
                        cr, uid, map_ids[0], {'need_sync': 'No'}, context)
            template_id = self.browse(cr, uid, pro_id).product_tmpl_id.id
            temp_map_ids = template_map_pool.search(
                cr, uid, [('template_name', '=', template_id)])
            for temp_map_id in temp_map_ids:
                if not context.has_key('magento'):
                    template_map_pool.write(cr, uid, temp_map_id, {
                                            'need_sync': 'Yes'}, context)
                elif context.has_key('magento'):
                    template_map_pool.write(cr, uid, temp_map_id, {
                                            'need_sync': 'No'}, context)
        return super(product_product, self).write(cr, uid, ids, vals, context=context)

product_product()


class product_category(osv.osv):
    _inherit = 'product.category'

    def check_category(self, cr, uid, vals, context=None):
        category_ids = self.search(cr, uid, [])
        for category_id in category_ids:
            if self.browse(cr, uid, category_id).name.lower() == vals['name'].lower():
                return category_id
        return False

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        if context.has_key('magento'):
            category_id = self.check_category(cr, uid, vals, context)
            if category_id:
                return category_id
        return super(product_category, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        if context.has_key('magento'):
            if vals.has_key('name'):
                vals['name'] = _unescape(vals['name'])

        if not context.has_key('magento'):
            category_map_pool = self.pool.get('magento.category')
            for id in ids:
                map_ids = category_map_pool.search(
                    cr, uid, [('oe_category_id', '=', id)])
                if map_ids:
                    category_map_pool.write(cr, uid, map_ids[0], {
                                            'need_sync': 'Yes'}, context)
        return super(product_category, self).write(cr, uid, ids, vals, context=context)

product_category()

class delivery_carrier(osv.osv):
    _inherit = 'delivery.carrier'

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        if context.has_key('magento'):
            vals['name'] = _unescape(vals['name'])
            vals['partner_id'] = self.pool.get('res.users').browse(
                cr, uid, uid).company_id.partner_id.id
            vals['product_id'] = self.pool.get(
                'bridge.backbone')._get_virtual_product_id(cr, uid, {'name': 'Shipping'})
        return super(delivery_carrier, self).create(cr, uid, vals, context=context)

delivery_carrier()

class account_invoice(osv.osv):
    _inherit = 'account.invoice'

    def mage_invoice_trigger(self, cr, uid, ids, context=None):
        sale_obj = self.pool.get('sale.order')
        for inv_id in ids:
            invoices = self.read(cr, uid, inv_id, ['origin', 'state'])
            if invoices['origin']:
                sale_ids = sale_obj.search(cr, uid, [('invoice_ids','in', ids)])
                for sale_id in sale_ids:
                    order_id = self.pool.get('magento.orders').search(
                        cr, uid, [('order_ref', '=', sale_id)])
                    if order_id:
                        map_obj = self.pool.get('magento.orders').browse(
                            cr, uid, order_id[0])
                        order_name = map_obj.order_ref.name
                        instance_id = map_obj.instance_id.id
                        increment_id = map_obj.mage_increment_id
                        # manual_magento_invoice method is used to create an
                        # invoice on magento end ##
                        mage_invoice = self.manual_magento_invoice(
                            cr, uid, order_name, increment_id, instance_id, context)
        return True

    def manual_magento_invoice(self, cr, uid, order_name, increment_id, instance_id, context=None):
        text = ''
        status = 'no'
        session = 0
        mage_invoice = False
        obj = self.pool.get('magento.configure').browse(cr, uid, instance_id)
        if obj.state != 'enable':
            text = 'Please create the configuration part for connection!!!'
        elif obj.auto_invoice:
            url = obj.name + XMLRPC_API
            user = obj.user
            pwd = obj.pwd
            email = obj.notify
            try:
                server = xmlrpclib.Server(url)
                session = server.login(user, pwd)
            except xmlrpclib.Fault, e:
                text = 'Invoice on magento cannot be done, Error %s Magento details are Invalid.' % e
            except IOError, e:
                text = 'Invoice on magento cannot be done, due to error, %s.' % e
            except Exception, e:
                text = 'Invoice on magento cannot be done, due to error in Magento Connection.'
            if session:
                try:
                    mage_invoice = server.call(session, 'magerpsync.order_invoice', [
                                               increment_id, "Invoiced From Odoo", email])
                    text = 'Invoice of order %s has been sucessfully updated on magento.' % order_name
                    status = 'yes'
                except Exception, e:
                    text = 'Magento Invoicing Error For Order %s , Error %s.' % (
                        order_name, e)
        cr.commit()
        # workflow.trg_validate(uid, 'sale.order',ids[0], 'invoice_end', cr)
        self.pool.get('magento.sync.history').create(cr, uid, {
            'status': status, 'action_on': 'order', 'action': 'b', 'error_message': text})
        return mage_invoice

account_invoice()
################## .............sale order inherit.............###########

class sale_order(osv.osv):
    _inherit = "sale.order"

    _columns = {
        'channel': fields.selection((('odoo', 'Odoo'), ('magento', 'Magento')), 'Channel name'),
    }
    _defaults = {
        'channel': 'odoo',
    }

    def manual_magento_order_cancel(self, cr, uid, order_name, increment_id, instance_id, context=None):
        text = ''
        status = 'no'
        session = 0
        obj = self.pool.get('magento.configure').browse(cr, uid, instance_id)
        if obj.state != 'enable':
            text = 'Please create the configuration part for connection!!!'
        else:
            url = obj.name + XMLRPC_API
            user = obj.user
            pwd = obj.pwd
            try:
                server = xmlrpclib.Server(url)
                session = server.login(user, pwd)
            except xmlrpclib.Fault, e:
                text = 'Error, %s Magento details are Invalid.' % e
            except IOError, e:
                text = 'Error, %s.' % e
            except Exception, e:
                text = 'Error in Magento Connection.'
            if session:
                self.pool.get('bridge.backbone').release_mage_order_from_hold(
                    cr, uid, increment_id,  url, session)
                try:
                    server.call(session, 'sales_order.cancel', [increment_id])
                    text = 'sales order %s has been sucessfully canceled from magento.' % order_name
                    status = 'yes'
                except Exception, e:
                    text = 'Order %s cannot be canceled from magento, Because Magento order %s is in different state.' % (
                        order_name, increment_id)
            cr.commit()
            self.pool.get('magento.sync.history').create(cr, uid, {
                'status': status, 'action_on': 'order', 'action': 'b', 'error_message': text})
        return True

    def action_cancel(self, cr, uid, ids, context=None):
        super(sale_order, self).action_cancel(cr, uid, ids, context)

        # manual_magento_order_cancel method is used to cancel an order
        for order_id in ids:
            order_ids = self.pool.get('magento.orders').search(
                cr, uid, [('order_ref', '=', order_id)])
            if order_ids:
                map_obj = self.pool.get('magento.orders').browse(
                    cr, uid, order_ids[0])
                order_name = map_obj.order_ref.name
                instance_id = map_obj.instance_id.id
                increment_id = map_obj.mage_increment_id
                self.manual_magento_order_cancel(
                    cr, uid, order_name, increment_id, instance_id, context)
                return True
sale_order()

Carrier_Code = [('custom', 'Custom Value'),
                ('dhl', 'DHL (Deprecated)'),
                ('fedex', 'Federal Express'),
                ('ups', 'United Parcel Service'),
                ('usps', 'United States Postal Service'),
                ('dhlint', 'DHL')
                ]


class stock_picking(osv.osv):
    _inherit = "stock.picking"
    _columns = {
        'carrier_code': fields.selection(Carrier_Code, 'Magento Carrier', help="Magento Carrier"),
        'magento_shipment': fields.char('Magento Shipment', help="Contains Magento Order Shipment Number (eg. 300000008)"),
    }

    _defaults = {
        'carrier_code': 'custom',
    }

    @api.cr_uid_ids_context
    def do_transfer(self, cr, uid, picking_ids, context=None):
        if isinstance(picking_ids, (int, long)):
            picking_ids = [picking_ids]
        super(stock_picking, self).do_transfer(cr, uid, picking_ids, context)
        if not context.has_key('magento'):
            for picking_id in picking_ids:
                picking = self.read(cr, uid, picking_id, ['sale_id','origin'])
                if picking['sale_id']:
                    sale_id = picking['sale_id'][0]
                    order_name = picking['sale_id'][1]
                    origin = picking['origin']
                    if order_name == origin:
                        mapping_ids = self.pool.get('magento.orders').search(
                            cr, uid, [('order_ref', '=', sale_id)])
                        if mapping_ids:
                            map_obj = self.pool.get('magento.orders').browse(
                                cr, uid, mapping_ids[0])
                            instance_id = map_obj.instance_id.id
                            increment_id = map_obj.mage_increment_id
                            if order_name and picking_id:
                                magento_shipment = self.manual_magento_shipment(
                                    cr, uid, picking_id, increment_id, order_name, instance_id, context)
                                self.pool.get('stock.picking').write(cr, uid, picking_id, {
                                    'magento_shipment': magento_shipment}, context)
        return True

    def manual_magento_shipment(self, cr, uid, picking_id, increment_id, order_name, instance_id, context=None):
        if context is None:
            context = {}
        text = ''
        status = 'no'
        session = False
        mage_shipment = False
        obj = self.pool.get('magento.configure').browse(cr, uid, instance_id)
        if obj.state != 'enable':
            text = 'Please create the configuration part for connection!!!'
        elif obj.auto_ship:
            url = obj.name + XMLRPC_API
            user = obj.user
            pwd = obj.pwd
            email = obj.notify
            try:
                server = xmlrpclib.Server(url)
                session = server.login(user, pwd)
            except xmlrpclib.Fault, e:
                text = 'Error, %s Magento details are Invalid.' % e
            except IOError, e:
                text = 'Error, %s.' % e
            except Exception, e:
                text = 'Error in Magento Connection.'
            if session and increment_id:
                item_data = {}
                picking = self.browse(cr, uid, picking_id, context)
                for move_line in picking.move_lines:
                    product_id = move_line.product_id.id
                    quantity = move_line.product_uom_qty
                    search_ids = self.pool.get('magento.product').search(
                        cr, uid, [('pro_name', '=', product_id)])
                    if search_ids:
                        mapping = self.pool.get('magento.product').browse(
                            cr, uid, search_ids[0])
                        magento_id = str(mapping.mag_product_id)
                        #### prepare item data #####
                        item_data[magento_id] = int(quantity)
                try:
                    ship_array = [increment_id,
                                  'Shipped From Odoo', email, item_data]
                    mage_shipment = server.call(
                        session, 'magerpsync.order_shippment', ship_array)
                    if mage_shipment:
                        carrier_code = picking.carrier_code
                        carrier_tracking_no = picking.carrier_tracking_ref
                        carrier_title = dict(Carrier_Code)[carrier_code]
                        track_array = [mage_shipment, carrier_code, carrier_title, carrier_tracking_no]
                        mage_track = server.call(session, 'sales_order_shipment.addTrack', track_array)
                    text = 'shipment of order %s has been successfully updated on magento.' % order_name
                    status = 'yes'
                except xmlrpclib.Fault, e:
                    text = 'Magento shipment Error For Order %s , Error %s.' % (
                        order_name, e)
                    status = 'yes'
        cr.commit()
        self.pool.get('magento.sync.history').create(cr, uid, {
            'status': status, 'action_on': 'order', 'action': 'b', 'error_message': text})
        return mage_shipment

    def action_sync_tracking_no(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        text = ''
        for id in ids:
            stock_obj = self.browse(cr, uid, id, context)
            sale_id = stock_obj.sale_id.id
            magento_shipment = stock_obj.magento_shipment
            carrier_code = stock_obj.carrier_code
            carrier_tracking_no = stock_obj.carrier_tracking_ref
            if not carrier_tracking_no:
                raise osv.except_osv(_('Warning!'), _(
                    'Sorry No Carrier Tracking No. Found!!!'))
            elif not carrier_code:
                raise osv.except_osv(_('Warning!'), _(
                    'Please Select Magento Carrier!!!'))
            carrier_title = dict(Carrier_Code)[carrier_code]
            map_ids = self.pool.get('magento.orders').search(
                cr, uid, [('oe_order_id', '=', sale_id)])
            if map_ids:
                instance_id = self.pool.get('magento.orders').browse(
                    cr, uid, map_ids[0]).instance_id.id
                obj = self.pool.get('magento.configure').browse(
                    cr, uid, instance_id)
                url = obj.name + XMLRPC_API
                user = obj.user
                pwd = obj.pwd
                email = obj.notify
                try:
                    server = xmlrpclib.Server(url)
                    session = server.login(user, pwd)
                except xmlrpclib.Fault, e:
                    text = 'Error, %s Magento details are Invalid.' % e
                except IOError, e:
                    text = 'Error, %s.' % e
                except Exception, e:
                    text = 'Error in Magento Connection.'
                if session:
                    track_array = [magento_shipment, carrier_code,
                                   carrier_title, carrier_tracking_no]
                    try:
                        mage_track = server.call(
                            session, 'sales_order_shipment.addTrack', track_array)
                        text = 'Tracking number successfully added.'
                    except xmlrpclib.Fault, e:
                        text = "Error While Syncing Tracking Info At Magento. %s" % e
                partial = self.pool.get('message.wizard').create(
                    cr, uid, {'text': text})
                return {
                    'name': _("Message"),
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

stock_picking()

class res_partner(osv.osv):
    _inherit = 'res.partner'

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        if context.has_key('magento'):
            vals = self.customer_array(cr, uid, vals, context=context)
        customer_id = super(res_partner, self).create(
            cr, uid, vals, context=context)

        return customer_id

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        if context.has_key('magento'):
            vals = self.customer_array(cr, uid, vals, context=context)
        return super(res_partner, self).write(cr, uid, ids, vals, context=context)

    def customer_array(self, cr, uid, data, context=None):

        dic = {}
        if data.has_key('country_code'):
            country_ids = self.pool.get('res.country').search(
                cr, uid, [('code', '=', data.get('country_code'))])
            data.pop('country_code')
            if country_ids:
                data['country_id'] = country_ids[0]
                if data.has_key('region') and data['region']:
                    region = _unescape(data.get('region'))
                    state_ids = self.pool.get('res.country.state').search(
                        cr, uid, [('name', '=', region)])
                    if state_ids:
                        data['state_id'] = state_ids[0]
                    else:
                        dic['name'] = region
                        dic['country_id'] = country_ids[0]
                        dic['code'] = region[:2].upper()
                        state_id = self.pool.get(
                            'res.country.state').create(cr, uid, dic)
                        data['state_id'] = state_id
                data.pop('region')
        if data.has_key('tag') and data["tag"]:
            tag = _unescape(data.get('tag'))
            tag_ids = self.pool.get('res.partner.category').search(
                cr, uid, [('name', '=', tag)], limit=1)
            if not tag_ids:
                tag_id = self.pool.get('res.partner.category').create(
                    cr, uid, {'name': tag})
            else:
                tag_id = tag_ids[0]
            data['category_id'] = [(6, 0, [tag_id])]
            data.pop('tag')
        if data.has_key('wk_company'):
            data['wk_company'] = _unescape(data['wk_company'])
        if data.has_key('name') and data['name']:
            data['name'] = _unescape(data['name'])
        if data.has_key('email') and data['email']:
            data['email'] = _unescape(data['email'])
        if data.has_key('street') and data['street']:
            data['street'] = _unescape(data['street'])
        if data.has_key('street2') and data['street2']:
            data['street2'] = _unescape(data['street2'])
        if data.has_key('city') and data['city']:
            data['city'] = _unescape(data['city'])
        return data

# END