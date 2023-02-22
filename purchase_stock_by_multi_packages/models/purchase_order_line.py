# Copyright 2023 Michael Tietz (MT Software) <mtietz@mt-software.de>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def _compute_qty_received(self):
        multi_packages_lines = self.browse()
        for line in self:
            if not line.product_id.is_multi_packages:
                continue
            multi_packages_lines |= line
            moves = line.move_ids.filtered(
                lambda m: m.state == "done" and not m.scrapped
            )
            line.qty_received = moves._compute_multi_packages_qty_delivered(
                outgoing_domain=[("location_id.usage", "=", "supplier")]
            )

        super(PurchaseOrderLine, self - multi_packages_lines)._compute_qty_received()
