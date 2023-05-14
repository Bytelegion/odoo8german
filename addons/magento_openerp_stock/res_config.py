from openerp.osv import fields, osv
from openerp.tools.translate import _

class mob_config_settings(osv.osv_memory):
    _inherit = 'mob.config.settings'

    _columns = {
        'mob_stock_action': fields.selection([('qoh', 'Quantity on hand'),('fq', 'Forecast Quantity')], 'Stock Management',help="Manage Stock"),
    }

    def set_default_stock_fields(self, cr, uid, ids, context=None):
        ir_values = self.pool.get('ir.values')
        config = self.browse(cr, uid, ids[0], context)
        ir_values.set_default(cr, uid, 'mob.config.settings', 'mob_stock_action',
            config.mob_stock_action or False)
        return True
    
    def get_default_stock_fields(self, cr, uid, ids, context=None):
        values = {}
        ir_values = self.pool.get('ir.values')
        config = self.browse(cr, uid, ids[0], context)
        mob_stock_action = ir_values.get_default(cr, uid, 'mob.config.settings', 'mob_stock_action')
        return {'mob_stock_action':mob_stock_action}
mob_config_settings()