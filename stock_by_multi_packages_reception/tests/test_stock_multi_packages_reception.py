# Copyright 2022 Michael Tietz (MT Software) <mtietz@mt-software.de>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests import Form

from odoo.addons.stock_by_multi_packages.tests.common import (
    TestStockMultiPackagesFlowCommon,
)


class TestStockMultiPackagesReception(TestStockMultiPackagesFlowCommon):
    def test_multi_packages_reception(self):
        move_qty = 4
        packages_len = 3
        packages_qty = 8

        picking_in = self._create_picking_in([(self.productA, move_qty)])
        picking_in.action_confirm()

        action = picking_in.open_multi_packages_reception()
        reception = self.env["stock.picking.multi_packages.reception"].browse(
            action["res_id"]
        )
        self.assertEqual(reception.line_ids.move_id, picking_in.move_lines)
        self.assertEqual(reception.line_ids.qty, picking_in.move_lines.product_uom_qty)
        self.assertEqual(
            reception.line_ids.product_id, picking_in.move_lines.product_id
        )
        self.assertFalse(reception.line_ids.packages)

        packages = ", ".join(str(packages_qty) for i in range(packages_len))
        reception.line_ids.packages = packages
        reception.action_confirm()

        self._check_picking_moves(picking_in, move_qty, packages_len, packages_qty)

        picking_in.action_assign()
        self._check_picking_moves(picking_in, move_qty, packages_len, packages_qty)

        self._do_picking(picking_in, packages_qty)
        self._check_picking_moves(picking_in, move_qty, packages_len, packages_qty)
        self._check_product_qty_available(picking_in, packages_qty)

        picking_in = self._create_picking_in([(self.productA, move_qty)])
        picking_in.action_confirm()

        action = picking_in.open_multi_packages_reception()
        reception = self.env["stock.picking.multi_packages.reception"].browse(
            action["res_id"]
        )
        self.assertFalse(reception.line_ids.packages)

        line_qty = 2
        packages_qty = int(packages_qty / line_qty)
        packages = ", ".join(str(packages_qty) for i in range(packages_len))

        reception_form = Form(reception)
        line = reception_form.line_ids.edit(0)
        line.qty = line_qty
        line.packages_amount = 3
        new_packages = [1.0 * line_qty] * line.packages_amount
        new_packages = self.env[
            "stock.picking.multi_packages.reception.line"
        ]._packages_to_str(new_packages)
        self.assertEqual(line.packages, new_packages)
        line.packages = packages
        line.save()
        reception = reception_form.save()
        reception.action_confirm()

        self.assertEqual(len(picking_in.move_lines), 1 + packages_len)
        move_multi_packages = picking_in.move_lines.filtered(
            lambda m: m.product_id.is_multi_packages
        )
        self.assertEqual(move_multi_packages.product_qty, line_qty)
        self.assertEqual(
            sum((picking_in.move_lines - move_multi_packages).mapped("product_qty")),
            packages_qty * packages_len,
        )

        action = picking_in.open_multi_packages_reception()
        reception = self.env["stock.picking.multi_packages.reception"].browse(
            action["res_id"]
        )

        reception_form = Form(reception)
        line = reception_form.line_ids.edit(0)
        line.qty = line_qty
        line.packages = packages
        line.save()
        reception = reception_form.save()
        reception.action_confirm()

        self.assertEqual(len(picking_in.move_lines), packages_len * line_qty)
        move_multi_packages = picking_in.move_lines.filtered(
            lambda m: m.product_id.is_multi_packages
        )
        self.assertFalse(move_multi_packages)
        self.assertEqual(
            sum(picking_in.move_lines.mapped("product_qty")),
            packages_qty * packages_len * line_qty,
        )

        picking_in.action_assign()
        self._do_picking(picking_in, packages_qty)
