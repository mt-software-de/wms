# Copyright 2022 Michael Tietz (MT Software) <mtietz@mt-software.de>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from psycopg2.errors import CheckViolation, NotNullViolation

from odoo import tools

from .common import TestStockMultiPackagesFlowCommon


class TestCreateMultiPackagesLot(TestStockMultiPackagesFlowCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.lot = cls.env["stock.production.lot"]

    def test_create_multi_packages_lot(self):
        lot_name = "test-lot"

        packages = [1, 2]
        lot = self.lot._create_multi_packages_lot(
            self.productA, packages, lot_name=lot_name
        )
        self.assertEqual(lot.product_id, self.productA)
        self.assertEqual(lot.name, lot_name)
        self.assertEqual(len(lot.package_ids), len(packages))
        self.assertTrue(all(qty in packages for qty in lot.package_ids.mapped("qty")))
        self.assertEqual(
            len(self.productA.lot_ids.package_ids.product_id.product_tmpl_id),
            len(packages),
        )

        lot2 = self.lot._create_multi_packages_lot(
            self.productA, packages, lot_name=lot_name
        )
        self.assertEqual(lot, lot2)
        self.assertEqual(lot.package_ids, lot2.package_ids)
        self.assertEqual(
            len(self.productA.lot_ids.package_ids.product_id.product_tmpl_id),
            len(packages),
        )

        packages = [1, 2, 3]
        lot3 = self.lot._create_multi_packages_lot(self.productA, packages)
        self.assertTrue(lot != lot3)
        self.assertTrue(
            all(package not in lot.package_ids for package in lot3.package_ids)
        )
        self.assertTrue(
            all(
                p not in lot3.package_ids.product_id for p in lot.package_ids.product_id
            )
        )
        self.assertEqual(
            len(self.productA.lot_ids.package_ids.product_id.product_tmpl_id), 5
        )

        packages = [4, 8, 12]
        factor = 4
        lot = self.lot._create_multi_packages_lot(
            self.productA, packages, factor=factor
        )
        self.assertEqual(
            len(self.productA.lot_ids.package_ids.product_id.product_tmpl_id), 8
        )
        self.assertTrue(len(lot.package_ids), packages)
        self.assertTrue(
            all(qty * factor in packages for qty in lot.package_ids.mapped("qty"))
        )

    def test_create_multi_packages_lot_null_error(self):
        packages = [1, 2]
        lot = self.lot._create_multi_packages_lot(self.productA, packages)
        product = lot.product_id.create({"name": "test package", "type": "product"})

        with self.assertRaises(NotNullViolation), tools.mute_logger("odoo.sql_db"):
            lot.package_ids.create({"product_id": product.id, "parent_id": lot.id})

    def test_create_multi_packages_lot_gt_zero(self):
        packages = [1, 2]
        lot = self.lot._create_multi_packages_lot(self.productA, packages)
        product = lot.product_id.create({"name": "test package", "type": "product"})

        with self.assertRaises(CheckViolation), tools.mute_logger("odoo.sql_db"):
            lot.package_ids.create(
                {"product_id": product.id, "parent_id": lot.id, "qty": 0}
            )
