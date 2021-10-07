from odoo import _, models, fields, api

from datetime import datetime, timedelta


class AccountPayment(models.Model):
    _inherit = "account.payment"

    dni_partner = fields.Char(string="Cedula", related='partner_id.vat')
    partner_banks = fields.Many2one('res.partner.bank', string="Cuenta Bancaria")
    banks_name = fields.Char(string="Nombre del Banco", related='partner_banks.bank_id.name')
    abba = fields.Char(string="ABBA", related='partner_banks.bank_id.abba')
    switf = fields.Char(string="SWIFT", related='partner_banks.bank_id.bic')
    destination_bank_name = fields.Char( string="Banco Destino", related='partner_banks.bank_id.destination_bank.name')
    middleware_bank_name = fields.Char(string="Banco Intermediario", related='partner_banks.bank_id.middleware_bank.name')
    street = fields.Char(string="Dirección", related='partner_banks.bank_id.street')
    company_account = fields.Char(string="Cuenta Conectividad", related='journal_id.bank_acc_number')
    company_banks = fields.Char(string="Banco Conectividad", related='journal_id.bank_id.name')

