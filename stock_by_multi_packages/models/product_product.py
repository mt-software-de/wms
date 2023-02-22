# Copyright 2023 Michael Tietz (MT Software) <mtietz@mt-software.de>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models
from odoo.tools.float_utils import float_round


class ProductProduct(models.Model):
    _inherit = "product.product"

    lot_ids = fields.One2many("stock.production.lot", "product_id", "Lots")
    package_ids = fields.One2many(
        "stock.production.lot.package", "product_id", "Used in packages"
    )

    def _get_last_lot(self):
        lot = self.lot_ids.sorted("create_date", reverse=True)
        return lot and lot[0] or lot

    def _get_last_lot_packages(self, factor=1):
        self.ensure_one()
        last_lot = self._get_last_lot()
        return [int(package.qty * factor) for package in last_lot.package_ids]

    def _compute_quantities_dict(
        self, lot_id, owner_id, package_id, from_date=False, to_date=False
    ):
        res = super()._compute_quantities_dict(
            lot_id, owner_id, package_id, from_date, to_date
        )

        all_measures = [
            "free_qty",
            "qty_available",
            "incoming_qty",
            "outgoing_qty",
        ]

        for product in self:
            if not product.is_multi_packages:
                continue
            product_qties = res[product.id]
            product_qties.update(
                {
                    "qty_available": 0.0,
                    "free_qty": 0.0,
                }
            )
            if lot_id:
                product_qties.update(
                    {
                        "outgoing_qty": 0.0,
                        "incoming_qty": 0.0,
                    }
                )

            for lot in product.lot_ids:
                if lot_id and lot_id != lot.id or not lot.package_ids:
                    continue

                lot_ratios = {
                    "qty_available": [],
                    "free_qty": [],
                    "incoming_qty": [],
                    "outgoing_qty": [],
                }
                for package in lot.package_ids.with_context(lot_id=None):
                    if not package.qty:
                        continue
                    for measure in all_measures:
                        lot_ratios[measure].append(
                            package.product_id[measure] / package.qty
                        )

                for measure, ratios in lot_ratios.items():
                    qty = min(ratios) // 1
                    product_qties[measure] += qty

            product_qties["virtual_available"] = float_round(
                product_qties["qty_available"]
                + product_qties["incoming_qty"]
                - product_qties["outgoing_qty"],
                precision_rounding=product.uom_id.rounding,
            )
        return res
