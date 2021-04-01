# -*- coding: utf-8 -*-
##############################################################################
#    Copyright 2018 Bryan
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

{
    "name": "Módulo para descargar comprobantes electronicos XML al sistema",
    'version': '1.0',
    'category': 'Base',
    'description': """
    """,
    'author': 'bryanjs@outlook.es',
    'website': 'https://www.facebook.com/VinnyJS',
    'license': 'AGPL-3',
    'depends': ['base', 'web', 'account'],
    'data': [
        "views/base_res.xml",
        "views/invoice.xml",
        #"views/sale.xml",
        #"views/sale_order_stages.xml",
        "data/data.xml",
        "wizard/fetch_mail.xml",
        "wizard/load_zip.xml",
        "security/ir.model.access.csv",
    ],
    'external_dependencies': {
        'python': [],
    },
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
