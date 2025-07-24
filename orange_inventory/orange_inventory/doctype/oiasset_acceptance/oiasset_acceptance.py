# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class oiAssetAcceptance(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF
        from orange_inventory.orange_inventory.doctype.oiasset_acceptance_item.oiasset_acceptance_item import oiAssetAcceptanceItem

        amended_from: DF.Link | None
        asset_owner: DF.Link
        basis_doc_no: DF.Data
        category_totals: DF.TextEditor | None
        counterparty: DF.Link
        items: DF.Table[oiAssetAcceptanceItem]
        posting_date: DF.Date
        total_amount: DF.Currency
    # end: auto-generated types

    def on_submit(self):
        for item in self.items:
            # Обробка товарів, що обліковуються партіями
            if item.is_batched:
                hw = frappe.new_doc('oiHardware')
                hw.title = item.item_name
                hw.item_name = item.item_name
                hw.is_batched = 1
                hw.asset_category = item.asset_category
                hw.unit_cost = item.unit_cost
                hw.quantity = item.quantity
                hw.owner = self.asset_owner
                hw.posting_date = self.posting_date
                hw.acceptance_doc = self.name
                hw.insert()
            else:
                # Обробка серіалізованих товарів
                serial_no_list = []
                if item.serial_numbers:
                    serial_no_list = [
                        s.strip() for s in item.serial_numbers.split('\n') if s.strip()
                    ]

                if not serial_no_list:
                    frappe.throw(
                        f"Для товару '{item.item_name}' не вказано серійні номери.")

                if len(serial_no_list) != item.quantity:
                    frappe.throw(
                        f"Кількість серійних номерів ({len(serial_no_list)}) "
                        f"не відповідає кількості товару ({item.quantity}) "
                        f"для '{item.item_name}'."
                    )

                for serial_no in serial_no_list:
                    hw = frappe.new_doc('oiHardware')
                    hw.title = item.item_name
                    hw.item_name = item.item_name
                    hw.is_batched = 0
                    hw.asset_category = item.asset_category
                    hw.unit_cost = item.unit_cost
                    hw.quantity = 1
                    hw.serial_number = serial_no
                    hw.owner = self.asset_owner
                    hw.posting_date = self.posting_date
                    hw.acceptance_doc = self.name
                    hw.insert()
