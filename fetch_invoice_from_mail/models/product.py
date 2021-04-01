# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)

class ProductPartnerCode(models.Model):
    _name = 'product.partner.code'

    product_id = fields.Many2one('product.product')
    product_tmpl_id = fields.Many2one('product.template')
    partner_id = fields.Many2one('res.partner', string='Proveedor', index=1, required=1)
    default_code = fields.Char(index=1, string='Código Proveedor')
    name = fields.Char(index=1, string='Nombre Proveedor')

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    partner_code_ids = fields.One2many('product.partner.code', 'product_tmpl_id')