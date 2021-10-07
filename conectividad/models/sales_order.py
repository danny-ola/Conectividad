from odoo import models, api, fields, _
from odoo.tools.misc import formatLang, get_lang


class SaleOrderImport(models.Model):
    _inherit = 'sale.order'

    sale_description = fields.Char(string='Internal references')
    def search_file(self):
        internalReferences = self.sale_description
        if internalReferences!=False:
            internalReferencesList=internalReferences.split()
            new_lines = self.env['sale.order.line']
            for i in internalReferencesList:
                product = self.env['product.product'].search([('default_code', '=', i)], limit=1)
                if product :
                    new_order_line = self.env['sale.order.line'].new({
                        'product_id' : product.id,
                        'name' : product.name,
                        'product_uom_qty' : 1,
                        'price_unit' : product.lst_price,
                        'tax_id' : product.taxes_id,
                        # 'buy_price' : float(product.standard_price),  #No
                        # 'total_buy' : float(self.buy_price * product.standard_price),
                        # # 'operative_porcentage' : ,  #No
                        # 'unit_cost' : self.buy_price+self.sales_margin,  #No
                        # # 'sales_margin' : ,  #No
                        # # 'sales_price' :
                    })
                    new_lines += new_order_line
                else:
                    alert('Error in '+i)
            self.order_line = new_lines


    def manager_approval(self):
        print()


class NewFieldsProducts(models.Model):
    _inherit = 'sale.order.line'

    buy_price = fields.Float(string='Precio compra')
    total_buy = fields.Float(string='Compra total', readonly=True)
    operative_porcentage = fields.Integer(string='% operativo')
    unit_cost = fields.Float(string='Costo unitario')
    sales_margin = fields.Float(string='Margen ventas')
    seller_id = fields.Many2one("product.supplierinfo", string="Proveedores", required=False)
    seller_count = fields.Integer(string="Number of vendor", compute='get_seller_count',
                                  help="Number of vendor prices for this product")

    @api.onchange("buy_price","product_uom_qty")
    def _compute_total_buy(self):
        for record in self:
            record.total_buy = record.buy_price * record.product_uom_qty

    @api.onchange("operative_porcentage")
    def _compute_operative(self):
        for record in self:
            record.unit_cost = ((record.operative_porcentage/100)*record.buy_price)+record.buy_price

    @api.onchange("sales_margin","unit_cost")
    def _compute_sales_margin(self):
        for record in self:
            record.price_unit = ((record.sales_margin/100)*record.unit_cost)+record.unit_cost

    @api.onchange('product_id')
    def onchange_saller_id(self):
        if self.product_id:
            seller = self.env['product.supplierinfo'].search(
                [('product_tmpl_id', '=', self.product_id.product_tmpl_id.id)], order='sequence', limit=1)

            self.seller_id = seller
        else:
            self.seller_id = False

    @api.onchange('product_id')
    def product_id_change(self):
        if not self.product_id:
            return
        valid_values = self.product_id.product_tmpl_id.valid_product_template_attribute_line_ids.product_template_value_ids
        # remove the is_custom values that don't belong to this template
        for pacv in self.product_custom_attribute_value_ids:
            if pacv.custom_product_template_attribute_value_id not in valid_values:
                self.product_custom_attribute_value_ids -= pacv

        # remove the no_variant attributes that don't belong to this template
        for ptav in self.product_no_variant_attribute_value_ids:
            if ptav._origin not in valid_values:
                self.product_no_variant_attribute_value_ids -= ptav

        vals = {}
        if not self.product_uom or (self.product_id.uom_id.id != self.product_uom.id):
            vals['product_uom'] = self.product_id.uom_id
            vals['product_uom_qty'] = self.product_uom_qty or 1.0

        product = self.product_id.with_context(
            lang=get_lang(self.env, self.order_id.partner_id.lang).code,
            partner=self.order_id.partner_id,
            quantity=vals.get('product_uom_qty') or self.product_uom_qty,
            date=self.order_id.date_order,
            pricelist=self.order_id.pricelist_id.id,
            uom=self.product_uom.id
        )

        vals.update(name=self.get_sale_order_line_multiline_description_sale(product))

        self._compute_tax_id()
        # set the selected supplier info as true
        if self.seller_id:
            this_seller = self.env['product.supplierinfo'].search([('id', '=', self.seller_id.id)])
            this_seller.write({'selected': True})
            other_sellers = self.env['product.supplierinfo'].search([('id', '!=', self.seller_id.id)])
            other_sellers.write({'selected': False})
        if self.order_id.pricelist_id and self.order_id.partner_id:
            vals['price_unit'] = self.env['account.tax']._fix_tax_included_price_company(
                self._get_display_price(product), product.taxes_id, self.tax_id, self.company_id)
        self.update(vals)

        title = False
        message = False
        result = {}
        warning = {}
        if product.sale_line_warn != 'no-message':
            title = _("Warning for %s") % product.name
            message = product.sale_line_warn_msg
            warning['title'] = title
            warning['message'] = message
            result = {'warning': warning}
            if product.sale_line_warn == 'block':
                self.product_id = False

        return result

    @api.onchange('seller_id')
    def product_vendor_change(self):
        if self.seller_id:
            this_seller = self.env['product.supplierinfo'].search([('id', '=', self.seller_id.id)])
            this_seller.write({'selected': True})
            other_sellers = self.env['product.supplierinfo'].search([('id', '!=', self.seller_id.id)])
            other_sellers.write({'selected': False})
            self.product_id_change()

    @api.depends('product_id')
    def get_seller_count(self):
        for sale_line in self:
            sale_line.seller_count = len(
                self.env['product.supplierinfo'].search([('product_tmpl_id', '=', sale_line.product_id.product_tmpl_id.id)]))



class SupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'
    selected = fields.Boolean(string="Supplier selected")


    def name_get(self):
        res = []
        for vendor in self:
            code = vendor.product_code and str(vendor.product_code) + ',' or ''
            tt = str(vendor.name.name) + ' [ ' + code + ' ' + str(vendor.price) + ' ]'
            res.append((vendor.id, tt))
        return res
