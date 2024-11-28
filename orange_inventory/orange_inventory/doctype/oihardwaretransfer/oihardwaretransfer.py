# Copyright (c) 2024, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class oiHardwareTransfer(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF
        from orange_inventory.orange_inventory.doctype.oihardwaretransfer_table.oihardwaretransfer_table import oiHardwareTransferTable

        amended_from: DF.Link | None
        doc_date: DF.Date | None
        doc_number: DF.Data | None
        from_designation: DF.Link | None
        from_organization: DF.Link | None
        from_user: DF.Link | None
        items: DF.Table[oiHardwareTransferTable]
        skip_transfer: DF.Check
        to_designation: DF.Link | None
        to_organization: DF.Link | None
        to_user: DF.Link | None
        type: DF.Link | None
    # end: auto-generated types

    def on_submit(self):
        if self.skip_transfer:
            return
        for item in self.items:
            frappe.set_value(
                "oiHardware", item.title, "financially_responsible_person", self.to_user
            )
