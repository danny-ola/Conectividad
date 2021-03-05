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
from ..models.emaillib2 import MailBox
from dateutil.parser import parse
import time
import os
import shutil
import base64
import zipfile


from odoo import models, fields, api
import logging
import os
import re
import base64
from lxml import etree as ET
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.parser import parse
from datetime import datetime, timedelta
import imaplib


import logging
_logger = logging.getLogger(__name__)

class LoadZip(models.TransientModel):
    _name = 'load.zip.lines'

    name = fields.Char('Error')

class LoadZip(models.TransientModel):
    _name = 'load.zip'

    archivo = fields.Binary('Carpeta', attachment=True)
    fname_archivo = fields.Char('Nombre')
    errores_ids = fields.Many2many('load.zip.lines', 'Errores')
    company_id = fields.Many2one('res.company', 'Compañia', default=lambda x: x.env.user.company_id.id)


    def send2create(self, contenido, companies_dict, company):
        xml2invoice = self.env['xml.invoice']
        try:
            root = ET.fromstring(
                re.sub(' xmlns=(\'|\")([a-zA-Z]|\:|\/|\.|\d|\-)*(\'|\")', '', contenido.decode('utf-8'), count=1).encode('utf-8'))

            # quita el namespace de los elementos
            if root.tag == 'MensajeHacienda':
                return False
        except Exception as e:
            _logger.error("XML no valido2 %s" % (e,))
            #self.mark_unseen(connection, message.id)
            return False
        invoice_warning = ''
        doc_type = {
            'FacturaElectronica': 'in_invoice',
            'TiqueteElectronico': 'in_invoice',
            'NotaDebitoElectronica': 'in_invoice',
            'NotaCreditoElectronica': 'in_refund',
        }[root.tag]
        if root.tag in ('TiqueteElectronico', 'NotaDebitoElectronica'):
            invoice_warning += '***Cuidado, este documento es un ' + root.tag
        xml_company = root.findall('Receptor')
        if xml_company is not None:
            xml_company = xml_company[0].find('Identificacion')
            if xml_company is not None:
                xml_company = xml_company[1].text
            else:
                xml_company = company.vat

        company2send = companies_dict.get(xml_company, False)

        if not company2send:
            company2send = company.vat
            if invoice_warning != '':
                invoice_warning += '\n'
            invoice_warning += 'La cédula del XML es distinta a la suya'
            # toma el id de la compañia del correo en caso que el del XML no coincida con ninguno de
            # los actuales
        else:
            company2send = xml_company
        result = xml2invoice.load_xml_file(root, [], {
            'company_id': companies_dict[company2send]['id'],
            'journal_id': companies_dict[company2send]['journal_id'].id,
            'type': doc_type,
            'invoice_warning': invoice_warning
        })
        if result and result != 'repetida':
            try:
                invoice_id = self.env['account.move'].sudo().create(result)
                _logger.info('Factura creada de manera exitosa, num: %s id: %s' % (
                    root.find('Clave').text, invoice_id))
            except Exception as e:
                _logger.error('Hubo un error al intentar CREAR la factura, ****ERROR: %s' % ( e, ))
                #self.mark_unseen(connection, message.id)
        else:
            _logger.error('Hubo un error al procesar')

    def _default_journal(self, type, company_id):
        domain = [
            ('type', '=', type),
            '|',
            ('company_id', '=', company_id),
            ('company_id', '=', False),
        ]
        return self.env['account.journal'].search(domain, limit=1)



    def procesar(self):
        attachment = self.env['ir.attachment']
        parent_path = attachment._filestore()

        cr = self.env.cr
        cr.execute("select store_fname from ir_attachment where res_model='%s' and res_id=%s and res_field='archivo';" % ('load.zip', self.id))

        result = cr.dictfetchone()


        full_path = os.path.join(parent_path, result['store_fname'] )
        zfile = zipfile.ZipFile(full_path)

        companies = self.env['res.company'].search([])
        companies_dict = {}
        for c in companies:
            if c.vat:
                companies_dict.update({
                    c.vat: {
                        'id': c.id,
                        'journal_id': self._default_journal('purchase', c.id),
                    }
                })


        for finfo in zfile.infolist():
            filename = finfo.filename
            extension = filename.split('.')[-1:][0].lower()
            if extension == 'xml':
                ifile = zfile.open(finfo)
                content = ifile.read()
                try:
                    try:
                        content = content.decode('utf-8').encode('ASCII', 'ignore')
                    except:
                        content = content.decode('latin-1').encode('ASCII', 'ignore')

                    self.send2create(content, companies_dict, self.company_id)
                except Exception as e:
                    _logger.error('NO SE PUDO %s' % (e,))
            #line_list = ifile.readlines()
        return self.myself()

            #print line_list

    def myself(self):
        self.ensure_one()
        view_id = self.env.ref('fetch_invoice_from_mail.load_zip_form', False)
        return {
            'context': {'active_id': self.id, 'active_ids': [self.id], 'docs': [self.id]},
            'view_mode': 'form',
            'res_model': self._name,
            'res_id': self.id,
            'view_id': view_id and view_id.id or False,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
