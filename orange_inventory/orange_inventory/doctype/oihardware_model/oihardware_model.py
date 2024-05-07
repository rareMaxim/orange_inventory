# Copyright (c) 2024, Maxim Sysoev and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class oiHardwareModel(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        manufacturer: DF.Link | None
        model: DF.Data | None
        picture: DF.AttachImage | None
        product: DF.Data | None
        title: DF.Data | None
        type: DF.Link | None
    # end: auto-generated types

    # this method will run every time a document is saved {self.model or ""}'
    def before_save(self):
        self.title = f"{self.manufacturer} {self.model}"
        if self.product:
            self.title = f"{self.title} ({self.product})"
