# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class oiHardwareTransfer(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF
        from orange_inventory.orange_inventory.doctype.oihardware_transfer_item.oihardware_transfer_item import oiHardwareTransferItem

        amended_from: DF.Link | None
        basis_document: DF.Data | None
        from_counterparty: DF.Link
        status: DF.Data | None
        to_counterparty: DF.Link
        transfer_date: DF.Date
        обладнання: DF.Table[oiHardwareTransferItem]
    # end: auto-generated types

    def on_submit(self):
        """
        This function is triggered when the Hardware Transfer document is submitted.
        It iterates through each piece of hardware in the transfer list and
        appends a new record to its movement history.
        """
        for item in self.hardware_list:
            # Load the hardware document that is being transferred
            # <-- ВАЖЛИВО: замініть "oiHardware" на назву вашого DocType обладнання
            hardware_doc = frappe.get_doc("oiHardware", item.hardware)

            # Create a new row in the "movement_history" table
            new_log_entry = hardware_doc.append("movement_history", {})

            # Populate the fields of the new history record
            new_log_entry.movement_date = self.transfer_date
            new_log_entry.from_counterparty = self.from_counterparty
            new_log_entry.to_counterparty = self.to_counterparty
            # You can add more complex logic for the status later
            new_log_entry.status = "Передано"

            # Add a reference back to this Hardware Transfer document
            new_log_entry.reference_document = self.name
            new_log_entry.reference_doctype = self.doctype
            new_log_entry.reference_name = self.name

            # Save the updated hardware document
            hardware_doc.save()

        # Update the status of the Hardware Transfer document itself
        self.db_set("status", "Завершено")
