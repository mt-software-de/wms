# Copyright 2022 Michael Tietz (MT Software) <mtietz@mt-software.de>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests import Form

from odoo.addons.stock.tests.common import TestStockCommon


class TestStockMultiPackagesFlowCommon(TestStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.productA.is_multi_packages = True

    def _check_picking_moves(self, picking, move_qty, packages_len, packages_qty):
        picking.flush()
        self.assertEqual(len(picking.move_lines), packages_len)
        self.assertEqual(len(picking.move_lines.move_line_ids), packages_len)

        for move in picking.move_lines:
            package = move.product_id.package_ids
            self.assertEqual(move.product_id, package.product_id)
            self.assertEqual(packages_qty / move_qty, package.qty)
            self.assertEqual(move.product_uom_qty, packages_qty)

    def _check_product_qty_available(self, picking, qty):
        for move_line in picking.move_lines.move_line_ids:
            product = move_line.product_id
            product.flush()
            self.assertEqual(product.qty_available, qty)

    def _do_picking(self, picking, qty):
        picking.move_lines.move_line_ids.write({"qty_done": qty})
        picking._action_done()

    def _create_picking_in(self, products_qty):
        return self._create_picking(
            self.picking_type_in,
            self.supplier_location,
            self.stock_location,
            products_qty,
        )

    def _create_picking_out(self, products_qty):
        return self._create_picking(
            self.picking_type_out,
            self.stock_location,
            self.customer_location,
            products_qty,
        )

    def _create_picking(
        self, picking_type, location_id, location_dest_id, products_qty
    ):
        picking = self.PickingObj.create(
            {
                "picking_type_id": picking_type,
                "location_id": location_id,
                "location_dest_id": location_dest_id,
                "company_id": self.env.user.company_id.id,
            }
        )
        for product, qty in products_qty:
            self.MoveObj.create(
                {
                    "name": product.name,
                    "product_id": product.id,
                    "product_uom_qty": qty,
                    "product_uom": product.uom_id.id,
                    "picking_id": picking.id,
                    "location_id": picking.location_id.id,
                    "location_dest_id": picking.location_dest_id.id,
                    "picking_type_id": picking.picking_type_id.id,
                }
            )
        return picking

    def _explode_picking_in(self, picking, move_qty, packages_len, packages_qty):
        packages_qties = [packages_qty] * packages_len

        lot = self.env["stock.production.lot"]._create_multi_packages_lot(
            self.productA,
            packages_qties,
            factor=move_qty,
        )
        picking.move_lines._action_explode_multi_packages_by_lot_qties(
            [(lot, move_qty)]
        )
        return lot

    def _do_return(self, picking, qty=None):
        stock_return_picking_form = Form(
            self.env["stock.return.picking"].with_context(
                active_ids=picking.ids,
                active_id=picking.id,
                active_model="stock.picking",
            )
        )
        return_wiz = stock_return_picking_form.save()
        for return_line in return_wiz.product_return_moves:
            return_line.write(
                {"quantity": qty or return_line.move_id.product_qty, "to_refund": True}
            )
        res = return_wiz.create_returns()
        return_pick = self.env["stock.picking"].browse(res["res_id"])

        # Process all components and validate the picking
        wiz_act = return_pick.button_validate()
        wiz = Form(
            self.env[wiz_act["res_model"]].with_context(wiz_act["context"])
        ).save()
        wiz.process()
