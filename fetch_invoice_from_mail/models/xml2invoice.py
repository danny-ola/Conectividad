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
from odoo import models, fields, api, _
from odoo.exceptions import UserError

from odoo import models, fields, api
import logging
import os
import re
import base64
from lxml import etree as ET
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.parser import parse
from datetime import datetime, timedelta
from odoo.addons.account.models.account_move import AccountMoveLine as AccountInvoiceLine


_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _inherit = 'account.move'

    desde_correo = fields.Boolean('Creada desde el correo 2', default=False)
    invoice_warning = fields.Char('Información FE')
    attachments_ids = fields.Many2many('ir.attachment', string='Archivos de correo')
    tipo_cambio_xml = fields.Float('Tipo de cambio FE')
    confirmar_clave_numerica = fields.Char(size=50)

    @api.model
    def _get_xml_decoders(self):
        result = super(AccountInvoice, self)._get_xml_decoders()
        def curry(new_ids):
            def return_ids(xml):
                return new_ids
            return return_ids

        def check_func(xml, fname):
            return {'flag': True, 'error': False}

        return [(1, check_func, curry(self))]

class AccountInvoiceLineInherit(models.Model):
    _inherit = 'account.move.line'

    desde_correo = fields.Boolean('Creada desde el correo', default=False)
    partner_code = fields.Char()
    partner_name = fields.Char()

    @api.model
    def create(self, vals):
        result = super(AccountInvoiceLineInherit, self).create(vals)
        if 'product_id' in vals and vals['product_id'] and 'desde_correo' in vals and vals['desde_correo'] and self.move_id.partner_id.id:
            product_partner_code_env = self.env['product.partner.code']
            product_tmpl_id = self.env['product.product'].browse(vals['product_id']).product_tmpl_id.id
            product_partner_code_env.create({
                'product_id': vals['product_id'],
                'product_tmpl_id': product_tmpl_id,
                'partner_id': self.move_id.partner_id.id,
                'default_code': vals['partner_code'],
                'name': vals['partner_name'],
            })
        return result


    def write(self, vals):
        result = super(AccountInvoiceLineInherit, self).write(vals)
        if 'product_id' in vals and vals['product_id'] and self.desde_correo and (self.partner_code or self.partner_name) and self.move_id.partner_id.id:
            product_partner_code_env = self.env['product.partner.code']
            product_tmpl_id = self.env['product.product'].browse(vals['product_id']).product_tmpl_id.id
            product_partner_code_env.create({
                'product_id': vals['product_id'],
                'product_tmpl_id': product_tmpl_id,
                'partner_id': self.move_id.partner_id.id,
                'default_code': self.partner_code,
                'name': self.partner_name,
            })
        return result



class ParseXML(models.TransientModel):
    _name = 'xml.invoice'

    def search_data(self, table, data, field='name', company=False):
        """
        :param table: nombre de la tabla en la que se va a buscar
        :param data: valor que se va a busar
        :param field: campo que se quiere buscar, por defecto va ser 'name'
        :param company: condicion para buscar por compañia y además será el valor de la compañia actual
        :return: id del registro encontrado
        """
        query = """select id from %s where %s ilike '%%%s%%' """ % (table, field, data)
        if company:
            query += " and (company_id=%s or company_id is null)" % (company)
        query += " limit 1;"
        self._cr.execute(query)
        val = self._cr.dictfetchone()
        if val:
            return val['id']
        return False

    @api.model
    def _default_account(self):
        if self._context.get('journal_id'):
            journal = self.env['account.journal'].browse(self._context.get('journal_id'))
            if self._context.get('type') in ('out_invoice', 'in_refund'):
                return journal.default_credit_account_id.id
            return journal.default_debit_account_id.id

    def get_partner(self, root, company_id):
        partner_env = self.env['res.partner']
        partner = partner_env.search(
            [('vat', '=', root.findall('Emisor')[0].find('Identificacion')[1].text), ('parent_id','=',False), '|', ('company_id', '=', False),
             ('company_id', '=', company_id)], limit=1)

        correo = root.find('Emisor').find('CorreoElectronico')
        telefono = root.find('Emisor').find('Telefono')
        if telefono is not None:
            telefono = telefono.find('NumTelefono').text
        else:
            telefono = False

        partner_vals = {
            'name': root.find('Emisor').find('Nombre').text,
            'vat': root.find('Emisor').find('Identificacion')[1].text,
            'ref': root.find('Emisor').find('Identificacion')[0].text,
            'email': (correo is not None) and correo.text or '',
            'phone': telefono,
            'company_id': company_id
        }
        if not partner:
            partner = partner_env.sudo().create(partner_vals)
        else:
            partner_env.sudo().write(partner_vals)
        return partner

    def load_xml_file(self, root, files=False, values={}):
        """
        :param root: root XML document
        :return: completa la SaleOrder con los datos enviados en el XML de la empresa
        """
        if True: #try:
            invoice_values = {}
            tipo_cambio = 1
            if root.find('ResumenFactura').find('CodigoTipoMoneda') is not None:
                tipo_cambio = float(root.find('ResumenFactura').find('CodigoTipoMoneda').find('TipoCambio').text)
            elif root.find('ResumenFactura').find('TipoCambio') is not None:
                tipo_cambio = float(root.find('ResumenFactura').find('TipoCambio').text)

            journal_id = values['journal_id']
            company_id = values['company_id']
            partner_found = self.get_partner(root, company_id)
            if partner_found.vat == self.env['res.company'].browse(company_id).vat:
                return False #No create invoice if if same company
            partner_id = partner_found.id

            invoice_values.update({
                'partner_id': partner_id,
                'type': values['type'],
                'journal_id': journal_id,
                'ref': root.find('Clave').text[21:41],
                'tipo_cambio_xml': tipo_cambio
            })

            fecha = parse(root.findall('FechaEmision')[0].text)

            invoice_values.update({'invoice_date': fecha.strftime('%Y-%m-%d')})
            plazo = root.find('PlazoCredito')
            if plazo is not None:
                try:
                    plazo = int((plazo.text or '0').lower().replace('dias', ''))
                except:
                    plazo = 0
                    #en ocasiones el plazo da error xq hacienda permite texto
            else:
                plazo = 0

            date_issuance = fecha.strftime(str(fecha.year) + "-" + str(fecha.month) + "-" + str(fecha.day) + "T%H:%M:%S-06:00")
            invoice_values.update({'invoice_date_due': (fecha + timedelta(days=plazo)).strftime('%Y-%m-%d'),'date_issuance':date_issuance})
            term_line_env = self.env['account.payment.term.line']
            term_line = term_line_env.search([('days', '=', plazo), '|', ('payment_id.company_id', '=', company_id),
                                              ('payment_id.company_id', '=', False)], limit=1)

            if term_line:
                invoice_values.update({'invoice_payment_term_id': term_line.payment_id.id})
            else:
                term_env = self.env['account.payment.term']
                values_term = {}  # term_env.default_get()
                values_term.update({'name': str(plazo), 'note': 'Plazo de pago a ' + str(plazo) + ' días'})

                values_term.update(
                    {'line_ids': [[0, 0, {'value': 'balance', 'days': plazo, 'option': 'day_after_invoice_date'}]]})

                payment_term = term_env.sudo().create(values_term)
                invoice_values.update({'invoice_payment_term_id': payment_term.id})

            lineas_factura = []
            product_env = self.env['product.product']
            product_partner_code_env = self.env['product.partner.code']

            default_account = self.with_context({'type': 'in_invoice', 'journal_id': journal_id}).sudo()._default_account()
            
            for l in root.findall('DetalleServicio')[0].findall('LineaDetalle'):
                codigo = l.find('Codigo')
                if codigo is not None:
                    codigo = l.find('CodigoComercial')
                    if codigo is not None:
                        codigo = codigo.find('Codigo')
                if not codigo  is not None:
                    codigo = False
                else:
                    codigo = codigo.text
                descripcion = l.find('Detalle').text
                condicion = [('name', 'ilike', descripcion)]
                if codigo:
                    condicion = ['|', ('name', 'ilike', descripcion), ('default_code', '=', codigo)]
                product_id = product_env.search(condicion, limit=1)
                if not product_id:
                    condicion.append(('partner_id', '=', partner_id))
                    product_id_result = product_partner_code_env.search(condicion, limit=1)
                    if len(product_id_result.ids):
                        product_id = product_id_result.product_id
                product_qty = float(l.find('Cantidad').text)
                linea = {
                    'product_id': product_id and product_id.id or False,
                    'name': ('[%s] ' % (codigo,) if codigo else '') + descripcion,
                    'quantity': product_qty,
                    'product_uom_id': 1, #self.env['uom.uom'].search([('code', '=', l.find('UnidadMedida').text)], limit=1).id,
                    'price_unit': float(l.find('PrecioUnitario').text),
                    'desde_correo': True,
                    'partner_code': codigo,
                    'display_type': False,
                    'partner_name': descripcion,
                    'account_id': (product_id and product_id.property_account_expense_id) and product_id.property_account_expense_id.id or default_account
                }
                codigo_impuesto = False
                impuesto = l.find('Impuesto')
                if impuesto is not None:
                    tarifa_impuesto = int(float(impuesto.find('Tarifa').text))
                    codigo_tarifa= str(impuesto.find('CodigoTarifa').text)
                    codigo_impuesto = self.env['account.tax'].search([('iva_tax_code','=',codigo_tarifa),('type_tax_use', '=', 'purchase'), ('company_id', '=', company_id)], limit=1).id

                        # self.search_data('account_tax', str(tarifa_impuesto), 'name', company_id)
                    if codigo_impuesto:
                        #linea.update({'invoice_line_tax_ids': [[4, codigo_impuesto]]})
                        linea.update({'tax_ids': [(6, 0, [codigo_impuesto])]})
                    else:
                        codigo_impuesto = self.env['account.tax'].search(
                            [('amount', '>=', tarifa_impuesto - 1),
                             ('amount', '<=', tarifa_impuesto + 1),
                             ('type_tax_use', '=', 'purchase'), ('company_id', '=', company_id)], limit=1)
                        if codigo_impuesto:
                            linea.update({'tax_ids': [(6, 0, [codigo_impuesto.id])]})
                if not codigo_impuesto:
                    codigo_impuesto = self.search_data('account_tax', '0', 'name')
                    if codigo_impuesto:
                        linea.update({'tax_ids': [[4, codigo_impuesto]]})
                #else:
                #    linea.update({'invoice_line_tax_ids': [(6, 0, [codigo_impuesto.id])]})

                descuento = l.find('MontoDescuento')
                if descuento is not None:
                    desc = float(descuento.text)
                    if False: #desc > 0.00:
                        monto_total = linea['quantity'] * linea['price_unit']
                        linea['price_unit'] -= (desc / product_qty)
                        #linea.update({'discount': round((desc / monto_total) * 100, 4)})
                else:
                    descuento = l.find('Descuento')
                    if descuento is not None:
                        descuento = descuento.find('MontoDescuento')
                        if descuento is not None:
                            desc = float(descuento.text)
                            if desc > 0.00:
                                monto_total = linea['quantity'] * linea['price_unit']
                                #linea.update({'discount': round((desc / monto_total) * 100, 4)}) # discount field does not exist

                #_logger.info("linea --> %s" %(linea,))
                lineas_factura.append([0, 0, linea])


            other_expenses = {
                '01': 'Contribución parafiscal',
                '02': 'Timbre de la Cruz Roja',
                '03': 'Timbre de Benemérito Cuerpo de Bomberos de Costa Rica',
                '04': 'Cobro de un tercero',
                '05': 'Costos de Exportación',
                '06': 'Impuesto de Servicio 10%',
                '07': 'Timbre de Colegios Profesionales',
                '99': 'Otros Cargos'
            }
            for l in root.findall('OtrosCargos'):
                prod_ref = False
                price_unit = 0

                type_doc = l.find('TipoDocumento')
                if type_doc is not None:
                    prod_ref = other_expenses.get(type_doc.text, 'Otros cargos')

                detalle = l.find('Detalle')
                if detalle is not None:
                    detalle = detalle.text

                monto = l.find('MontoCargo')
                if monto is not None:
                    price_unit = float(monto.text)

                linea = {
                    'name': ('[%s] ' % (prod_ref,) if prod_ref else '') + (detalle or ''),
                    'quantity': 1,
                    'product_uom_id': 1,
                    'price_unit': price_unit,
                    'desde_correo': True,
                    'display_type': False,
                    'account_id': default_account
                }
                lineas_factura.append([0, 0, linea])

            moneda = 'CRC'
            resumen = root.find('ResumenFactura')
            moneda_resumen = resumen.find('CodigoTipoMoneda')
            if moneda_resumen is not None:
                moneda = moneda_resumen.find('CodigoMoneda').text
            else:
                moneda_resumen = resumen.find('CodigoMoneda')
                if moneda_resumen is not None:
                    moneda = moneda_resumen.text
            clave = root.find('Clave').text
            attachments = []
            for a in files:
                if len(a) < 2:
                    continue
                attachments.append([0, 0, {
                    'name': a[0],
                    'datas_fname': a[0],
                    'res_name': a[0],
                    'type': 'binary',
                    'datas': base64.b64encode( a[1] ),
                }])

            invoice_values.update({
                'invoice_line_ids': lineas_factura,
                'currency_id': self.search_data('res_currency', moneda),
                'xml_supplier_approval': base64.b64encode(ET.tostring(root)),
                'fname_xml_supplier_approval': root.find('Emisor').find('Nombre').text + ' ' + root.find('Clave').text + '.xml',
                'desde_correo': True,
                'tipo_documento': 'CCE',
                'confirmar_clave_numerica': clave,
                'company_id': company_id,
                'invoice_warning': values.get('invoice_warning', ''),
                'attachments_ids': attachments,
                #'branch': 2,
                #'terminal': 2,
                #'payment_method': '04', #root.find('MedioPago').text,
                #'sale_condition': root.find('CondicionVenta').text
            })
            if self.env['account.move'].search_count([('confirmar_clave_numerica', '=', clave)]) > 0:
                _logger.error('Clave: %s REPETIDA1' % (clave,))
                return 'repetida'

            if self.env['account.move'].search_count([ ('partner_id', '=', invoice_values['partner_id']), ('ref', '=', invoice_values['ref']), ('type', '=', invoice_values['type']) ]) > 0:
                _logger.error('Clave: %s REPETIDA2' % (clave,))
                return 'repetida'

            return invoice_values
        if False: #except Exception as e:
            _logger.error('%s' % (e,))
            return False
