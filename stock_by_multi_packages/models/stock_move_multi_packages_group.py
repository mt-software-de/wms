# Copyright 2023 Michael Tietz (MT Software) <mtietz@mt-software.de>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class StockMoveMultiPackagesGroup(models.Model):
    _name = "stock.move.multi_packages.group"
    _description = "Stock move multi packages group"

    lot_id = fields.Many2one("stock.production.lot", required=True, ondelete="cascade")
    move_ids = fields.One2many("stock.move", "multi_packages_group_id", "Moves")
    qty = fields.Integer("Qty")
