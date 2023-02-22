# Copyright 2023 Michael Tietz (MT Software) <mtietz@mt-software.de>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "stock_by_multi_packages",
    "summary": "",
    "author": "MT Software, Odoo Community Association (OCA)",
    "category": "Inventory",
    "website": "https://github.com/OCA/wms",
    "data": [
        "security/ir.model.access.csv",
        "views/product_product_views.xml",
        "views/stock_production_lot_views.xml",
    ],
    "depends": [
        "stock_restrict_lot",
    ],
    "version": "14.0.1.0.0",
}
