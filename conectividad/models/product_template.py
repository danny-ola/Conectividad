from odoo import models, fields, api
from datetime import datetime, timedelta


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def create(self, vals):
        category =  self.env['product.category'].browse(vals.get('categ_id')).name
        if category == 'Servicios':
            vals['default_code'] = self.env['ir.sequence'].next_by_code('product.servicios') or '/'
        elif category == 'Licencias o Software':
            vals['default_code'] = self.env['ir.sequence'].next_by_code('product.licencias') or '/'
        else :
            vals['default_code'] = self.env['ir.sequence'].next_by_code('product.conectividad') or '/'

        return super(ProductTemplate, self).create(vals)
