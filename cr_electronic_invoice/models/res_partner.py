# -*- coding: utf-8 -*-
import re
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import phonenumbers
import logging
from . import api_facturae

_logger = logging.getLogger(__name__)


class PartnerCorreos(models.Model):
    _name = "res.partner.correos"

    name = fields.Char('Correo', required=1)

    @api.onchange('name')
    def _onchange_email(self):
        if self.name:
            if not re.match(r'^(\s?[^\s,]+@[^\s,]+\.[^\s,]+\s?,)*(\s?[^\s,]+@[^\s,]+\.[^\s,]+)$', self.name.lower()):
                vals = {'name': False}
                alerta = {
                    'title': 'Atención',
                    'message': 'El correo electrónico no cumple con una estructura válida. ' + str(self.name)
                }
                return {'value': vals, 'warning': alerta}


class PartnerElectronic(models.Model):
    _inherit = "res.partner"

    commercial_name = fields.Char(string="Commercial Name", required=False, )
    identification_id = fields.Many2one("identification.type", string="Id Type",required=False, )
    payment_methods_id = fields.Many2one("payment.methods", string="Payment Method", required=False, )
    has_exoneration = fields.Boolean(string="Tiene exoneración?", required=False)
    type_exoneration = fields.Many2one("aut.ex", string="Tipo de Exoneración", required=False, )
    exoneration_number = fields.Char(string="Número de exoneración", required=False, )
    institution_name = fields.Char(string="Nombre de institución", required=False, )
    date_issue = fields.Date(string="Fecha del documento", required=False, )
    date_expiration = fields.Date(string="Fecha de expiración", required=False, )
    activity_id = fields.Many2one("economic.activity", string="Default Economic Activity", required=False, context={'active_test': False} )
    economic_activities_ids = fields.Many2many('economic.activity', string=u'Economic Activities', context={'active_test': False})
    export = fields.Boolean(string="Cliente de exportación", default=False)
    correos_ids = fields.Many2many('res.partner.correos', string='Correos Adicionales')

    @api.onchange('phone')
    def _onchange_phone(self):
        if self.phone:
            phone = phonenumbers.parse(self.phone, self.country_id and self.country_id.code or 'CR')
            valid = phonenumbers.is_valid_number(phone)
            if not valid:
                alert = {
                    'title': 'Atención',
                    'message': _('Número de teléfono inválido')
                }
                return {'value': {'phone': ''}, 'warning': alert}

    def formatear_direccion(self):
        if not self.street and not self.street2 and not self.state_id and not self.country_id:
            return False
        return ', '.join(filter(lambda val: val, [(self.street and self.street + ',' or False), (self.street2 and self.street2 + ',' or False),
                                (self.state_id and self.state_id.name + ',' or False), (self.country_id and self.country_id.name or False)]))

    @api.onchange('mobile')
    def _onchange_mobile(self):
        if self.mobile:
            mobile = phonenumbers.parse(self.mobile, self.country_id and self.country_id.code or 'CR')
            valid = phonenumbers.is_valid_number(mobile)
            if not valid:
                alert = {
                    'title': 'Atención',
                    'message': 'Número de teléfono inválido'
                }
                return {'value': {'mobile': ''}, 'warning': alert}

    @api.onchange('email')
    def _onchange_email(self):
        if self.email:
            if not re.match(r'^(\s?[^\s,]+@[^\s,]+\.[^\s,]+\s?,)*(\s?[^\s,]+@[^\s,]+\.[^\s,]+)$', self.email.lower()):
                vals = {'email': False}
                alerta = {
                    'title': 'Atención',
                    'message': 'El correo electrónico no cumple con una estructura válida. ' + str(self.email)
                }
                return {'value': vals, 'warning': alerta}

    @api.onchange('vat')
    def _onchange_vat(self):
        if self.identification_id and self.vat:
            if self.identification_id.code == '05':
                if len(self.vat) == 0 or len(self.vat) > 20:
                    raise UserError(
                        'La identificación debe tener menos de 20 carateres.')
            else:
                # Remove leters, dashes, dots or any other special character.
                self.vat = re.sub(r"[^0-9]+", "", self.vat)
                if self.identification_id.code == '01':
                    if self.vat.isdigit() and len(self.vat) != 9:
                        raise UserError(
                            'La identificación tipo Cédula física debe de contener 9 dígitos, sin cero al inicio y sin guiones.')
                elif self.identification_id.code == '02':
                    if self.vat.isdigit() and len(self.vat) != 10:
                        raise UserError(
                            'La identificación tipo Cédula jurídica debe contener 10 dígitos, sin cero al inicio y sin guiones.')
                elif self.identification_id.code == '03' and self.vat.isdigit():
                    if self.vat.isdigit() and len(self.vat) < 11 or len(self.vat) > 12:
                        raise UserError(
                            'La identificación tipo DIMEX debe contener 11 o 12 dígitos, sin ceros al inicio y sin guiones.')
                elif self.identification_id.code == '04' and self.vat.isdigit():
                    if self.vat.isdigit() and len(self.vat) != 9:
                        raise UserError(
                            'La identificación tipo NITE debe contener 10 dígitos, sin ceros al inicio y sin guiones.')

    def action_get_economic_activities(self):
        if self.vat:
            json_response = api_facturae.get_economic_activities(self)
            _logger.debug('E-INV CR  - Economic Activities: %s', json_response)
            if json_response["status"] == 200:
                activities = json_response["activities"]
                activities_codes = list()
                for activity in activities:
                    if activity["estado"] == "A":
                        activities_codes.append(activity["codigo"])
                economic_activities = self.env['economic.activity'].with_context(active_test=False).search([('code', 'in', activities_codes)])

                self.economic_activities_ids = economic_activities
                self.name = json_response["name"]

                if len(activities_codes) >= 1:
                    self.activity_id = economic_activities[0]
            else:
                alert = {
                    'title': json_response["status"],
                    'message': json_response["text"]
                }
                return {'value': {'vat': ''}, 'warning': alert}
        else:
            alert = {
                'title': 'Atención',
                'message': _('Company VAT is invalid')
            }
            return {'value': {'vat': ''}, 'warning': alert}

    def _get_emails(self):
        emails = self.email
        for email in self.correos_ids:
            if email.name:
                emails = emails + ',' + email.name
        return emails
