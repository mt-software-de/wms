# Copyright 2023 Michael Tietz (MT Software) <mtietz@mt-software.de>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, groupby
from odoo.tools.safe_eval import safe_eval


class StockPickingMultiPackagesReceptionLine(models.TransientModel):
    _name = "stock.picking.multi_packages.reception.line"
    _description = "Stock Picking Multi Packages Reception Line"

    qty = fields.Float("Qty")
    reception_id = fields.Many2one(
        "stock.picking.multi_packages.reception",
        "Reception",
        required=True,
        ondelete="cascade",
    )
    move_id = fields.Many2one(
        "stock.move",
        "Move",
        required=True,
        domain="[('picking_id', 'in', parent.picking_ids), ('is_multi_package', '=', False)]",
        ondelete="cascade",
    )
    product_id = fields.Many2one(
        "product.product", "Product", related="move_id.product_id", readonly=True
    )
    packages_amount = fields.Integer("Amount of Packages", default=0)
    packages = fields.Char(
        "Packages qty",
        help="1, 1, 1 - the amount of numbers is representing the amount of packages "
        "and the number it self defines the quantity of each new package move",
    )
    show_detailed = fields.Boolean()

    @api.constrains("packages")
    def _check_packages(self):
        for line in self:
            line._get_packages()

    def _get_packages(self):
        self.ensure_one()
        try:
            packages = safe_eval(f"[{self.packages}]")
            return packages
        except Exception:
            raise UserError(
                _("The format of your packages string '{}' is wrong").format(
                    self.packages
                )
            )

    @api.model
    def _packages_to_str(self, packages=None):
        packages = packages or []
        return str(packages).replace("[", "").replace("]", "").strip()

    @api.model
    def _prepare_vals(self, move):
        move.ensure_one()
        return {
            "move_id": move.id,
            "product_id": move.product_id.id,
            "qty": move.product_uom_qty,
        }

    @api.onchange("packages_amount", "qty")
    def _onchange_packages_amount(self):
        packages = []
        if self.packages_amount and self.qty:
            packages = [1 * self.qty] * self.packages_amount
        self.packages = self._packages_to_str(packages)

    @api.onchange("move_id")
    def _onchange_move_id(self):
        if not self.move_id:
            self.qty = 0
            self.packages = ""
            return

        qty = self.move_id.product_uom_qty
        for line in self.reception_id.line_ids:
            if line == self or line.move_id != self.move_id:
                continue
            qty -= line.qty
        self.qty = max(0, qty)


class StockPickingMultiPackagesReception(models.TransientModel):
    _name = "stock.picking.multi_packages.reception"
    _description = "Stock Picking Multi Packages Reception"

    picking_ids = fields.Many2many("stock.picking", string="Picking")
    line_ids = fields.One2many(
        "stock.picking.multi_packages.reception.line", "reception_id", "Lines"
    )

    def action_confirm(self):
        moves = self.line_ids.move_id.browse()
        lot_qties = []
        for move, lines in groupby(self.line_ids, lambda l: l.move_id):
            lines = lines[0].browse().union(*lines)
            remaining_qty = move.product_uom_qty
            to_split_qty = sum(lines.mapped("qty"))

            if (
                float_compare(to_split_qty, remaining_qty, move.product_uom.rounding)
                > 0
            ):
                raise UserError(_("You are trying to split more than is remaining"))

            for line in lines:
                if float_compare(line.qty, 0, line.move_id.product_uom.rounding) <= 0:
                    continue
                packages_qties = line._get_packages()
                if not packages_qties:
                    continue
                qty = line.move_id.product_uom._compute_quantity(
                    line.qty, line.move_id.product_id.uom_id
                )
                lot = line.move_id._create_multi_packages_lot(packages_qties, qty=qty)
                lot_qties.append((lot, qty))
                moves += line.move_id
        moves._action_explode_multi_packages_by_lot_qties(lot_qties)
        self.unlink()
        return {"type": "ir.actions.act_window_close"}

    def _prepare_line_ids_vals(self, moves):
        lines = []
        for move in moves:
            lines.append((0, 0, self.line_ids._prepare_vals(move)))
        return lines

    def _prepare_vals(self, moves):
        return {
            "line_ids": self._prepare_line_ids_vals(moves),
            "picking_ids": [(6, 0, moves.picking_id.ids)],
        }

    def open(self, picking):
        moves = picking.move_lines._filter_multi_packages_moves()
        if not moves:
            raise UserError(
                _("There are no moves which should split into several packages")
            )

        reception = self.create(self._prepare_vals(moves))
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "stock_by_multi_packages_reception.stock_picking_multi_packages_reception_action"
        )
        action["res_id"] = reception.id
        return action
