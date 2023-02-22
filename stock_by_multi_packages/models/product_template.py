# Copyright 2023 Michael Tietz (MT Software) <mtietz@mt-software.de>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_multi_packages = fields.Boolean(
        "Is Divided Into Several Packages",
        help="A single unit is split into multiple packages. "
        "The product must be tracked by lot "
        "and each package will be a distinct sub-product lot. "
        "The lot will contain the list of sub-products",
    )
