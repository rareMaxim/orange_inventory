# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class oiAssetTransfer(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF
        from orange_inventory.orange_inventory.doctype.oiasset_transfer_item.oiasset_transfer_item import oiAssetTransferItem

        amended_from: DF.Link | None
        document_date: DF.Date
        document_number: DF.Data
        document_type: DF.Literal["\u0420\u0456\u0448\u0435\u043d\u043d\u044f", "\u041d\u0430\u043a\u0430\u0437", "\u0414\u043e\u0433\u043e\u0432\u0456\u0440"]
        hardware_list: DF.Table[oiAssetTransferItem]
        scan: DF.Attach | None
        title: DF.SmallText
        transfer_date: DF.Date | None
    # end: auto-generated types

    def on_submit(self):
        for item in self.hardware_list:
            source_doc = frappe.get_doc("oiHardware", item.hardware)

            if not source_doc.is_batched:
                source_doc.owner = self.to_counterparty
                source_doc.save(ignore_permissions=True)
            else:
                if item.quantity > source_doc.quantity:
                    frappe.throw(
                        f"Недостатньо залишків '{source_doc.name}'. В наявності: {source_doc.quantity}")

                if item.quantity == source_doc.quantity:
                    source_doc.owner = self.to_counterparty
                    source_doc.save(ignore_permissions=True)
                else:
                    new_doc = frappe.copy_doc(source_doc)
                    new_doc.quantity = item.quantity
                    new_doc.owner = self.to_counterparty
                    # Важливо: генеруємо новий інвентарний/внутрішній номер
                    new_doc.name = None
                    new_doc.insert(ignore_permissions=True)

                    source_doc.quantity -= item.quantity
                    source_doc.save(ignore_permissions=True)

        self.db_set("status", "Завершено")
