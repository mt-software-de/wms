# Copyright 2023 Michael Tietz (MT Software) <mtietz@mt-software.de>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def open_multi_packages_reception(self):
        self.ensure_one()
        return self.env["stock.picking.multi_packages.reception"].open(self)
