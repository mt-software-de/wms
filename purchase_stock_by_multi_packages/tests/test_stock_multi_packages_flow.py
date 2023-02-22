# Copyright 2022 Michael Tietz (MT Software) <mtietz@mt-software.de>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests import Form

from odoo.addons.stock_by_multi_packages.tests.common import (
    TestStockMultiPackagesFlowCommon,
)


class TestStockMultiPackagesFlow(TestStockMultiPackagesFlowCommon):
    @classmethod
    def setUpClasss(cls):
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
        move_qty = 2
        packages_len = 3
        packages_qty = 2

        partner = self.env["res.partner"].create({"name": "My Test Partner"})
        f = Form(self.env["purchase.order"])
        f.partner_id = partner
        with f.order_line.new() as line:
            line.product_id = self.productA
            line.product_qty = move_qty

        po = f.save()
        po.button_confirm()

        picking = po.picking_ids
        picking.action_confirm()
        self._explode_picking_in(picking, move_qty, packages_len, packages_qty)
        picking.action_assign()
        self._do_picking(picking, 1)
        self.assertEqual(po.order_line.qty_received, 1)

        for qty_received in [1, 1, 2]:
            picking = po.picking_ids.sorted("id")[-1]
            picking.move_lines[-1].move_line_ids.write({"qty_done": 1})
            picking._action_done()
            self.assertEqual(po.order_line.qty_received, qty_received)

        pickings = po.picking_ids.sorted("id")
        self._do_return(pickings[0])
        self.assertEqual(po.order_line.qty_received, 1)

        self._do_return(pickings[1])
        self.assertEqual(po.order_line.qty_received, 0)
