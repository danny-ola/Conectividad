from odoo import _, models, fields, api

from datetime import datetime, timedelta


class AccountPayment(models.Model):
    _inherit = "account.payment"

    dni_partner = fields.Char(string="Cedula", related='partner_id.vat')
    partner_banks = fields.Many2one('res.partner.bank', string="Cuenta Bancaria")
