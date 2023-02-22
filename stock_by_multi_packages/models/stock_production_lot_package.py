# Copyright 2023 Michael Tietz (MT Software) <mtietz@mt-software.de>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class StockProductionLotPackage(models.Model):
    _name = "stock.production.lot.package"
    _rec_name = "product_id"
    _description = "Lot - Package"

    parent_id = fields.Many2one(
        "stock.production.lot", "Parent lot", required=True, ondelete="cascade"
    )
    product_id = fields.Many2one("product.product", "Product", required=True)
    qty = fields.Integer("Qty", required=True)

    _sql_constraints = [
        ("check_qty", "CHECK (qty > 0)", "A package qty must be greater than 0")
    ]
