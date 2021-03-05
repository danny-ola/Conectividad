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

import logging
_logger = logging.getLogger(__name__)

class fetchMail(models.TransientModel):
    _name = 'fetch.mail.zip'

    host_imap_server_fe = fields.Char('Servidor IMAP', required=1, default='mail.biopharmacr.com')
    port_imap_server_fe = fields.Integer('Puerto IMAP', required=1, default='993')
    user_imap_server_fe = fields.Char('Usuario IMAP', required=1, default='facturacionelectronica@biopharmacr.com')
    pass_imap_server_fe = fields.Char('Contraseña IMAP', required=1, default='F4ctur4c10n!2019.')

    filter_by = fields.Selection([('date', 'Fecha'), ('unseen', 'No leidos')], 'Filtrar por', default='unseen', required=1)
    date_from = fields.Date('Fecha Inicio')
    date_to = fields.Date('Fecha Final')
    archivo = fields.Binary('Carpeta')
    fname_archivo = fields.Char('Nombre')

    def open_connection(self):
        mailbox = MailBox(self.host_imap_server_fe, self.port_imap_server_fe)
        try:
            mailbox.login(self.user_imap_server_fe, self.pass_imap_server_fe)
        except Exception as e:
            raise UserError('No se ha podido conectar con el servidor')
        return mailbox


    def generate_zip(self):
        num2month = {
            1: 'Jan',
            2: 'Feb',
            3: 'Mar',
            4: 'Apr',
            5: 'May',
            6: 'Jun',
            7: 'Jul',
            8: 'Aug',
            9: 'Sep',
            10: 'Oct',
            11: 'Nov',
            12: 'Dec'
        }
        mailbox = self.open_connection()
        try:
            bandejas = [c for c in
                        filter(lambda f: "INBOX" in f, [i.decode().split(' "/" ')[1] for i in mailbox.box.list()[1]])]
        except:
            bandejas = [c for c in
                        filter(lambda f: "INBOX" in f, [i.decode().split(' "." ')[1] for i in mailbox.box.list()[1]])]



        epoch = str(time.time())
        folder_path = '/tmp/' + epoch
        os.mkdir(folder_path, 0o755)

        for bandeja in bandejas:
            mailbox.box.select(bandeja)
            _logger.info("Buscando en carpeta %s" % (bandeja,))
            if self.filter_by == 'date':
                fecha = self.date_from
                fecha2str = fecha.strftime("%d-") + num2month[int(fecha.strftime("%m"))] + fecha.strftime("-%Y")
                correos_nuevos = mailbox.fetch('(SINCE "%s")' % (fecha2str.upper(),))
            else:
                correos_nuevos = mailbox.fetch('(UNSEEN)')

            cant_correos = 0

            for message in correos_nuevos:
                fecha_correo = parse(message.date)
                if self.date_to:
                    if fecha_correo.date() > self.date_to:
                        break
                attachments = list(message.get_attachments())

                for filename, payload in attachments:
                    extension = filename.split('.')[-1:][0].lower()
                    if extension == "xml":
                        for f, p in attachments:
                            f_ext = f.split('.')[-1:][0].lower()
                            if f_ext in ('pdf', 'xml'):
                                f = f.replace('/', '-')
                                newfile = open(folder_path + '/' + f, 'wb')
                                newfile.write(p)
                                newfile.close()

                cant_correos += 1
                _logger.info('Leyendo correo num %s' % (cant_correos,))

        shutil.make_archive(folder_path, 'zip', folder_path, base_dir=None)  # crea el archivo
        zipFile = open(folder_path + '.zip', "rb").read()  # lee el archivo
        #shutil.rmtree(folder_path, ignore_errors=True)
        #os.remove(folder_path + '.zip')
        self.write({'archivo': base64.b64encode(zipFile), 'fname_archivo': 'Carpeta-' + epoch + '.zip'})

        return self.myself()



    def myself(self):
        self.ensure_one()
        view_id = self.env.ref('fetch_invoice_from_mail.fetch_mail_zip_form', False)
        return {
            'context': {'active_id': self.id, 'active_ids': [self.id], 'docs': [self.id]},
            'view_mode': 'form',
            'res_model': self._name,
            'res_id': self.id,
            'view_id': view_id and view_id.id or False,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
fetchMail()
"""
class fetchMail(models.TransientModel):
    _name = 'fetch.mail.zip'

    host_imap_server_fe = fields.Char('Servidor IMAP', required=1, default='server.cloudcone.email')
    port_imap_server_fe = fields.Integer('Puerto IMAP', required=1, default='993')
    user_imap_server_fe = fields.Char('Usuario IMAP', required=1, default='fe@soinccr.com')
    pass_imap_server_fe = fields.Char('Contraseña IMAP', required=1, default='S0p0rt3!2011.')

    filter_by = fields.Selection([('date', 'Fecha'), ('unseen', 'No leidos')], 'Filtrar por', default='unseen', required=1)
    date_from = fields.Date('Fecha Inicio')
    date_to = fields.Date('Fecha Final')
    archivo = fields.Binary('Carpeta')
    fname_archivo = fields.Char('Nombre')

    def open_connection(self):
        mailbox = MailBox(self.host_imap_server_fe, self.port_imap_server_fe)
        try:
            mailbox.login(self.user_imap_server_fe, self.pass_imap_server_fe)
        except Exception as e:
            raise UserError('No se ha podido conectar con el servidor')
        return mailbox

    
    def generate_zip(self):
        num2month = {
            1: 'Jan',
            2: 'Feb',
            3: 'Mar',
            4: 'Apr',
            5: 'May',
            6: 'Jun',
            7: 'Jul',
            8: 'Aug',
            9: 'Sep',
            10: 'Oct',
            11: 'Nov',
            12: 'Dec'
        }
        mailbox = self.open_connection()
        if self.filter_by == 'date':
            fecha = parse(self.date_from)
            fecha2str = fecha.strftime("%d-") + num2month[int(fecha.strftime("%m"))] + fecha.strftime("-%Y")
            correos_nuevos = mailbox.fetch('(SINCE "%s")' % (fecha2str.upper(),))
        else:
            correos_nuevos = mailbox.fetch('(UNSEEN)')

        cant_correos = 0

        epoch = str(time.time())
        folder_path = '/tmp/' + epoch
        os.mkdir(folder_path, 0755)

        for message in correos_nuevos:
            fecha_correo = parse(message.date)
            if self.date_to:
                if fecha_correo.date() > parse(self.date_to).date():
                    break
            attachments = list(message.get_attachments())

            for filename, payload in attachments:
                extension = filename.split('.')[-1:][0].lower()
                if extension == "xml":
                    for f, p in attachments:
                        f_ext = f.split('.')[-1:][0].lower()
                        if f_ext in ('pdf', 'xml'):
                            newfile = open(folder_path + '/' + f, 'wb')
                            newfile.write(p)
                            newfile.close()

            cant_correos += 1
            _logger.info('Leyendo correo num %s' % (cant_correos,))

        shutil.make_archive(folder_path, 'zip', folder_path, base_dir=None)  # crea el archivo
        zipFile = open(folder_path + '.zip', "rb").read()  # lee el archivo
        shutil.rmtree(folder_path, ignore_errors=True)
        os.remove(folder_path + '.zip')
        self.write({'archivo': base64.b64encode(zipFile), 'fname_archivo': 'Carpeta-' + epoch + '.zip'})

        return self.myself()



    def myself(self):
        self.ensure_one()
        view_id = self.env.ref('fetch_invoice_from_mail.fetch_mail_zip_form', False)
        return {
            'context': {'active_id': self.id, 'active_ids': [self.id], 'docs': [self.id]},
            'view_mode': 'form',
            'res_model': self._name,
            'res_id': self.id,
            'view_id': view_id and view_id.id or False,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
fetchMail()
"""
