# Copyright 2023 Michael Tietz (MT Software) <mtietz@mt-software.de>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models
from odoo.tools import float_round


class StockMove(models.Model):
    _inherit = "stock.move"

    def _explode_multi_packages_on_assign(self):
        res = super()._explode_multi_packages_on_assign()
        if not res:
            return res
        return not self.rule_id.route_id.available_to_promise_defer_pull

    def _compute_ordered_available_to_promise(self):
        multi_packages_moves = self._filter_multi_packages_moves()
        super(
            StockMove, self - multi_packages_moves
        )._compute_ordered_available_to_promise()
        locations = multi_packages_moves._ordered_available_to_promise_locations()
        moves = multi_packages_moves.with_context(location=locations.ids)
        for move in moves:
            product_uom = move.product_id.uom_id
            previous_promised_qty = move.previous_promised_qty

            rounding = product_uom.rounding
            available_qty = float_round(
                move.product_id.qty_available,
                precision_rounding=rounding,
            )

            real_promised = available_qty - previous_promised_qty
            uom_promised = product_uom._compute_quantity(
                real_promised,
                move.product_uom,
                rounding_method="HALF-UP",
            )

            move.ordered_available_to_promise_uom_qty = max(
                min(uom_promised, move.product_uom_qty),
                0.0,
            )
            move.ordered_available_to_promise_qty = max(
                min(real_promised, move.product_qty),
                0.0,
            )

    def _multi_packages_qty_to_explode(self):
        if self.rule_id.route_id.available_to_promise_defer_pull:
            return self.ordered_available_to_promise_qty
        return super()._multi_packages_qty_to_explode()

    def _run_stock_rule(self):
        multi_packages_moves = self._filter_multi_packages_moves()
        moves = self - multi_packages_moves
        moves_to_explode = multi_packages_moves.filtered(lambda m: m._is_releasable())
        moves |= moves_to_explode._action_explode_multi_packages()
        return super(StockMove, moves)._run_stock_rule()
