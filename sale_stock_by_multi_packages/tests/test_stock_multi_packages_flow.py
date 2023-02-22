# Copyright 2022 Michael Tietz (MT Software) <mtietz@mt-software.de>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests import Form, common

from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.addons.stock_by_multi_packages.tests.common import (
    TestStockMultiPackagesFlowCommon,
)


@common.tagged("post_install", "-at_install")
class TestStockMultiPackagesFlow(TestSaleCommon, TestStockMultiPackagesFlowCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        user = cls.env.user
        company = cls.env.ref("base.main_company")
        user.company_ids |= company
        user.company_id = company
        cls.env = cls.env(user=user)
        cls.productA = cls.env["product.product"].create(
            {
                "name": "test",
                "type": "product",
                "is_multi_packages": True,
                "company_id": cls.env.user.company_id.id,
            }
        )

    def test_flow(self):
        move_qty = 10
        packages_len = 3
        packages_qty = 10

        picking_in = self._create_picking_in([(self.productA, move_qty)])
        picking_in.action_confirm()
        self._explode_picking_in(picking_in, move_qty, packages_len, packages_qty)
        picking_in.action_assign()
        self._do_picking(picking_in, packages_qty)

        partner = self.env["res.partner"].create({"name": "My Test Partner"})
        f = Form(self.env["sale.order"])
        f.partner_id = partner
        with f.order_line.new() as line:
            line.product_id = self.productA
            line.product_uom_qty = 2.0

        so = f.save()
        so.action_confirm()
        self._do_picking(so.picking_ids, 1)
        self.assertEqual(so.order_line.qty_delivered, 1)

        for qty_delivered in [1, 1, 2]:
            picking = so.picking_ids.sorted("id")[-1]
            picking.move_lines[-1].move_line_ids.write({"qty_done": 1})
            picking._action_done()
            self.assertEqual(so.order_line.qty_delivered, qty_delivered)

        pickings = so.picking_ids.sorted("id")
        self._do_return(pickings[0])
        self.assertEqual(so.order_line.qty_delivered, 1)

        self._do_return(pickings[1])
        self.assertEqual(so.order_line.qty_delivered, 0)
