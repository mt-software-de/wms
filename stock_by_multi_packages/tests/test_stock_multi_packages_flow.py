# Copyright 2022 Michael Tietz (MT Software) <mtietz@mt-software.de>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from .common import TestStockMultiPackagesFlowCommon


class TestStockMultiPackagesFlow(TestStockMultiPackagesFlowCommon):
    def test_flow(self):
        move_qty = 4
        packages_len = 3
        packages_qty = 8

        picking_in = self._create_picking_in([(self.productA, move_qty)])
        picking_in.action_confirm()
        self._explode_picking_in(picking_in, move_qty, packages_len, packages_qty)
        self._check_picking_moves(picking_in, move_qty, packages_len, packages_qty)

        picking_in.action_assign()
        self._check_picking_moves(picking_in, move_qty, packages_len, packages_qty)

        self._do_picking(picking_in, packages_qty)
        self._check_picking_moves(picking_in, move_qty, packages_len, packages_qty)
        self._check_product_qty_available(picking_in, packages_qty)

        picking_out = self._create_picking_out([(self.productA, move_qty)])
        picking_out.action_confirm()
        self.assertEqual(len(picking_out.move_lines), 1)
        picking_out.action_assign()
        self._check_picking_moves(picking_out, move_qty, packages_len, packages_qty)

        self._do_picking(picking_out, packages_qty)
        self._check_product_qty_available(picking_out, 0)

    def _check_qties(
        self, qty_available=0, free_qty=0, incoming_qty=0, outgoing_qty=0, lot=None
    ):
        product = self.productA
        virtual_available = qty_available + incoming_qty - outgoing_qty
        product.flush()
        product.invalidate_cache()
        if lot:
            product = product.with_context(lot_id=lot.id)
        self.assertEqual(product.qty_available, qty_available)
        self.assertEqual(product.free_qty, free_qty)
        self.assertEqual(product.incoming_qty, incoming_qty)
        self.assertEqual(product.outgoing_qty, outgoing_qty)
        self.assertEqual(product.virtual_available, virtual_available)

    def test_qty_available(self):
        move_qty = 4
        packages_len = 2
        packages_qty = 4

        picking_in1 = self._create_picking_in([(self.productA, move_qty)])
        picking_in1.action_confirm()
        self._check_qties(0, 0, move_qty, 0)
        lot1 = self._explode_picking_in(
            picking_in1, move_qty, packages_len, packages_qty
        )
        self._check_qties(0, 0, move_qty, 0)
        self._check_qties(0, 0, move_qty, 0, lot=lot1)

        picking_in2 = self._create_picking_in([(self.productA, move_qty)])
        picking_in2.action_confirm()
        self._check_qties(0, 0, move_qty * 2, 0)
        lot2 = self._explode_picking_in(
            picking_in2, move_qty, packages_len, packages_qty
        )
        self._check_qties(0, 0, move_qty * 2, 0)

        self._check_qties(0, 0, move_qty, 0, lot=lot1)
        self._check_qties(0, 0, move_qty, 0, lot=lot2)

        picking_in1.action_assign()
        self._check_qties(0, 0, move_qty * 2, 0)
        self._check_qties(0, 0, move_qty, 0, lot=lot1)
        self._check_qties(0, 0, move_qty, 0, lot=lot2)

        self._do_picking(picking_in1, packages_qty)

        self._check_qties(move_qty, move_qty, 0, 0, lot=lot1)
        self._check_qties(move_qty, move_qty, 4, 0)

        picking_in2.action_assign()
        self._do_picking(picking_in2, packages_qty)
        self._check_qties(move_qty, move_qty, 0, 0, lot=lot2)
        self._check_qties(move_qty * 2, move_qty * 2, 0, 0)

        picking_out = self._create_picking_out([(self.productA, move_qty)])
        picking_out.action_confirm()
        self._check_qties(move_qty * 2, move_qty * 2, 0, move_qty)
        picking_out.action_assign()
        picking_out.move_lines.action_explode_multi_packages()
        picking_out.action_assign()

        self._check_qties(move_qty * 2, move_qty, 0, move_qty)
