from odoo import models, fields, api
from datetime import datetime, timedelta


class ResPartnerBankTemplate(models.Model):
    _inherit = 'res.bank'

    abba = fields.Char(string="ABBA")
    destination_bank = fields.Many2one("res.bank", string="Banco Destino")
    middleware_bank = fields.Many2one("res.bank", string="Banco Intermediario")