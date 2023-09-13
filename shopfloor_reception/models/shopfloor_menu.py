# Copyright 2023 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import api, fields, models

ALLOW_SELECT_DOCUMENT_BY_PRODUCT_HELP = """
If enabled, users will be able to select transfers by product.
"""


class ShopfloorMenu(models.Model):
    _inherit = "shopfloor.menu"

    allow_select_document_by_product = fields.Boolean(
        string="Allow select document by product",
        default=False,
        help=ALLOW_SELECT_DOCUMENT_BY_PRODUCT_HELP,
    )
    allow_select_document_by_product_is_possible = fields.Boolean(
        compute="_compute_pick_pack_same_time_is_possible"
    )

    @api.depends("scenario_id")
    def _compute_pick_pack_same_time_is_possible(self):
        for menu in self:
            menu.allow_select_document_by_product_is_possible = (
                menu.scenario_id.has_option("allow_select_document_by_product")
            )
