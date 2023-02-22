# Copyright 2023 Michael Tietz (MT Software) <mtietz@mt-software.de>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockProductionLot(models.Model):
    _inherit = "stock.production.lot"

    is_multi_packages = fields.Boolean(related="product_id.is_multi_packages")
    package_ids = fields.One2many(
        "stock.production.lot.package", "parent_id", "Packages"
    )

    @api.constrains("package_ids")
    def _check_package_ids(self):
        for lot in self:
            if lot.package_ids and not lot.product_id.is_multi_packages:
                raise UserError(
                    _(
                        "You cannot create lot.package for products "
                        'which are not marked as "Is Divided Into Several Packages"'
                    )
                )

    def _prepare_package_lot_vals(self, product, name=None):
        vals = {
            "product_id": product.id,
            "company_id": self.env.user.company_id.id,
        }
        if name:
            vals["name"] = name
        return vals

    def _package_suffix(self, packages_amount, package_number):
        return f"{self.name}-{package_number}/{packages_amount}"

    def _prepare_package_product_name(self, packages_amount, package_number):
        name_suffix = self._package_suffix(packages_amount, package_number)
        return f"{self.product_id.name} - {name_suffix}"

    def _prepare_package_product_barcode(self, packages_amount, package_number):
        barcode_suffix = self._package_suffix(packages_amount, package_number)
        return f"{self.product_id.default_code}-{barcode_suffix}"

    def _prepare_package_product_vals(self, packages_amount, package_number):
        self.ensure_one()
        return {
            "name": self._prepare_package_product_name(packages_amount, package_number),
            "barcode": self._prepare_package_product_barcode(
                packages_amount, package_number
            ),
            "type": "product",
            "sale_ok": False,
            "purchase_ok": False,
            "uom_id": self.product_id.uom_id.id,
        }

    def _prepare_package_vals(self, product, qty, factor=1):
        return {
            "parent_id": self.id,
            "qty": qty / factor,
            "product_id": product.id,
        }

    def _generate_package_products(self, package_qties):
        vals_list = []
        products = self.env["product.product"]
        packages_amount = len(package_qties)
        for package_number in range(1, packages_amount + 1):
            vals_list.append(
                self._prepare_package_product_vals(packages_amount, package_number)
            )
        if vals_list:
            products |= self.env["product.product"].create(vals_list)
        return products

    def _generate_packages(self, package_qties, uom=None, factor=1):
        self.ensure_one()
        products = self._generate_package_products(package_qties)
        products = products and dict(enumerate(products)) or {}
        vals_list = []
        for i, package_qty in enumerate(package_qties):
            package_qty = (
                uom
                and uom._compute_quantity(package_qty, self.product_id.uom_id)
                or package_qty
            )
            product = products.get(i)
            vals_list.append(self._prepare_package_vals(product, package_qty, factor))
        return self.env["stock.production.lot.package"].create(vals_list)

    def _get_existing_lot(self, product, name=None):
        return name and self.search(
            [("product_id", "=", product.id), ("name", "=", name)]
        )

    def _get_or_create_existing_lot(self, product, name=None):
        lot = self._get_existing_lot(product, name)
        if lot:
            return lot
        return self.create(self._prepare_package_lot_vals(product, name))

    @api.model
    def _create_multi_packages_lot(
        self, product, package_qties=None, uom=None, factor=1, lot_name=None
    ):
        product.ensure_one()
        lot = self._get_or_create_existing_lot(product, lot_name)
        if lot.package_ids:
            return lot

        lot._generate_packages(package_qties, uom, factor)
        return lot
