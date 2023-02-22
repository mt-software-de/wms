# Copyright 2023 Michael Tietz (MT Software) <mtietz@mt-software.de>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _compute_qty_delivered_multi_packages(self):
        for line in self:
            moves = line.move_ids.filtered(
                lambda m: m.state == "done" and not m.scrapped
            )
            line.qty_delivered = moves._compute_multi_packages_qty_delivered()

    def _compute_qty_delivered(self):
        multi_packages_lines = self.browse()
        for line in self:
            if not line.product_id.is_multi_packages:
                continue
            multi_packages_lines |= line
            line._compute_qty_delivered_multi_packages()
        super(SaleOrderLine, self - multi_packages_lines)._compute_qty_delivered()
