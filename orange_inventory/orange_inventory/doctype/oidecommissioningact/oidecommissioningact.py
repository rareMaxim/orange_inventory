# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class oiDecommissioningAct(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF
        from orange_inventory.orange_inventory.doctype.oidecommissioningitem.oidecommissioningitem import oiDecommissioningItem

        decision: DF.Link | None
        decommission_date: DF.Date
        items: DF.Table[oiDecommissioningItem]
    # end: auto-generated types

    def on_submit(self):
        """
        При затвердженні 'Акту списання' оновлює статус активів.
        """
        for item in self.items:
            # Завантажуємо документ 'oiAsset' за посиланням з рядка
            asset_doc = frappe.get_doc("oiAsset", item.asset)

            # Оновлюємо статус та обнуляємо кількість
            asset_doc.status = "Списано"
            asset_doc.quantity = 0

            # Додаємо запис в історію руху
            asset_doc.append("movement_history", {
                "date": self.decommission_date,
                "movement_type": "Списання",
                # При списанні актив "іде в нікуди", тому поля from/to пусті
                "reference_appendix": self.decision
            })

            # Зберігаємо зміни в документі активу
            asset_doc.save()
