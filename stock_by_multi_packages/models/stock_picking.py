# Copyright 2023 Michael Tietz (MT Software) <mtietz@mt-software.de>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    needs_multi_packages_split = fields.Boolean(
        "Needs multi packages split",
        compute="_compute_needs_multi_packages_split",
        help="Show if this picking contains moves, "
        "which should split into several packages",
    )

    @api.depends("move_lines", "move_lines.product_id")
    def _compute_needs_multi_packages_split(self):
        for picking in self:
            picking.needs_multi_packages_split = (
                picking.move_lines._filter_multi_packages_moves().exists()
                and True
                or False
            )
