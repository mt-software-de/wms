# Copyright 2023 Michael Tietz (MT Software) <mtietz@mt-software.de>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round, groupby


class StockMove(models.Model):
    _inherit = "stock.move"

    is_multi_package = fields.Boolean(
        "Is multi package",
        help="Created by a multi packages move",
        default=False,
        copy=False,
    )
    multi_packages_group_id = fields.Many2one(
        "stock.move.multi_packages.group", "Multi packages group", ondelete="restrict"
    )

    def _prepare_multi_package_vals(self, lot_package, qty, multi_packages_group):
        self.ensure_one()
        lot_package_uom_qty = lot_package.product_id.uom_id._compute_quantity(
            lot_package.qty, self.product_uom
        )
        default_vals = {
            "picking_id": self.picking_id.id if self.picking_id else False,
            "product_id": lot_package.product_id.id,
            "product_uom": self.product_uom.id,
            "product_uom_qty": qty * lot_package_uom_qty,
            "state": "draft",
            "name": self.name,
            "is_multi_package": True,
            "multi_packages_group_id": multi_packages_group.id,
        }
        return self.copy_data(default_vals)[0]

    def _unlink_multi_packages_moves(self):
        self.move_line_ids.unlink()
        self._action_cancel()
        self.unlink()

    @api.model
    def _create_multi_packages_group(self, lot, qty):
        return self.env["stock.move.multi_packages.group"].create(
            {
                "lot_id": lot.id,
                "qty": qty,
            }
        )

    def _explode_multi_packages_by_lot_and_qty(self, lot, qty):
        self.ensure_one()
        multi_packages_group = self._create_multi_packages_group(lot, qty)
        uom_qty = self.product_id.uom_id._compute_quantity(qty, self.product_uom)
        self.product_uom_qty -= min(self.product_uom_qty, uom_qty)
        move_vals = []
        for lot_package in lot.package_ids:
            move_vals.append(
                self._prepare_multi_package_vals(
                    lot_package, uom_qty, multi_packages_group
                )
            )
        return move_vals

    def _action_explode_multi_packages_by_lot_qties(self, lots_qties):
        multi_package_move_vals = []
        moves_to_unlink = self.browse([])
        for move, lot_qties in zip(self, lots_qties):
            lot, qty = lot_qties
            multi_package_move_vals += move._explode_multi_packages_by_lot_and_qty(
                lot, qty
            )
            if (
                float_compare(move.product_uom_qty, 0, move.product_id.uom_id.rounding)
                <= 0
            ):
                moves_to_unlink |= move

        moves_to_unlink._unlink_multi_packages_moves()
        moves_to_confirm = self.create(multi_package_move_vals)
        moves_to_confirm._action_confirm()
        return moves_to_confirm

    def _create_multi_packages_lot(self, package_qties=None, lot_name=None, qty=None):
        self.ensure_one()
        return self.env["stock.production.lot"]._create_multi_packages_lot(
            self.product_id,
            package_qties,
            self.product_uom,
            qty or self.product_qty,
            lot_name,
        )

    def _find_available_lots_by_product(self):
        lots_by_product = {}
        for lot in self.product_id.lot_ids.sorted("id"):
            qty = lot.product_id.with_context(
                lot_id=lot.id, warehouse=self.warehouse_id.id
            ).qty_available
            if not float_compare(qty, 0, lot.product_id.uom_id.rounding) > 0:
                continue

            lots = lots_by_product.setdefault(lot.product_id, {})
            lots[lot] = qty
        return lots_by_product

    def _multi_packages_qty_to_explode(self):
        self.ensure_one()
        return self.product_qty

    def _action_explode_multi_packages(self):
        if not self.exists():
            return self

        lots_by_product = self._find_available_lots_by_product()
        moves_to_explode = self.browse([])
        lot_qties = []
        for move in self:
            lots = lots_by_product.get(move.product_id)
            if not lots:
                continue

            qty_to_explode = move._multi_packages_qty_to_explode()
            for lot, qty in lots.items():
                if float_compare(qty, 0, move.product_id.uom_id.rounding) <= 0:
                    continue
                qty = min(qty_to_explode, qty)
                lots[lot] -= qty
                qty_to_explode -= qty
                moves_to_explode += move
                lot_qties.append(
                    (
                        lot,
                        qty,
                    )
                )
                if not qty_to_explode:
                    break

        return moves_to_explode._action_explode_multi_packages_by_lot_qties(lot_qties)

    @api.model
    def _multi_packages_domain(self):
        return [
            ("product_id.type", "in", ["product", "consu"]),
            ("product_id.is_multi_packages", "=", True),
        ]

    def _filter_multi_packages_moves(self):
        return self.filtered_domain(self._multi_packages_domain())

    def _action_done(self, *args, **kwargs):
        multi_packages_moves = self._filter_multi_packages_moves()
        if multi_packages_moves:
            raise UserError(
                _(
                    "You are not allowed to set a move to done, "
                    "if the product is marked as 'Is Divided Into Several Packages'"
                )
            )

        return super()._action_done(*args, **kwargs)

    def action_explode_multi_packages(self):
        multi_packages_moves = self._filter_multi_packages_moves()
        moves = self.browse([])
        if multi_packages_moves:
            moves = multi_packages_moves._action_explode_multi_packages()
        return multi_packages_moves, moves

    def _explode_multi_packages_on_assign(self):
        self.ensure_one()
        return (
            self.picking_id.picking_type_id.code != "incoming"
            or self.location_id.usage != "supplier"
        )

    def _action_assign(self):
        moves_to_explode = self.filtered(
            lambda m: m._explode_multi_packages_on_assign()
        )
        (
            multi_packages_moves,
            new_moves,
        ) = moves_to_explode.action_explode_multi_packages()
        moves = self - multi_packages_moves + new_moves
        return super(StockMove, moves)._action_assign()

    def _compute_multi_packages_qty_delivered(self, outgoing_domain=None):
        outgoing_domain = outgoing_domain or [
            ("location_dest_id.usage", "=", "customer")
        ]
        qty_delivered = 0
        for multi_packages_group, moves in groupby(
            self, lambda m: m.multi_packages_group_id
        ):
            if not multi_packages_group:
                continue
            moves = self.browse().union(*moves)
            qty_ratios = []
            for package in multi_packages_group.lot_id.package_ids:
                qty_processed = 0
                package_moves = moves.filtered(
                    lambda m: m.product_id == package.product_id
                )
                if not package_moves:
                    qty_ratios.append(qty_processed)
                    continue

                incoming = 0
                outgoing = 0
                for move in package_moves:
                    if move.filtered_domain(outgoing_domain):
                        outgoing += move.product_qty
                    else:
                        incoming += move.product_qty
                qty_processed = outgoing - incoming
                qty_ratios.append(
                    float_round(
                        qty_processed / package.qty,
                        precision_rounding=package.product_id.uom_id.rounding,
                    )
                )

            qty_delivered += min(qty_ratios) // 1
        return qty_delivered
