# Copyright (c) 2024, Maxim Sysoev and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class oiDecommissioning(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        date: DF.Date | None
        doc_name: DF.Data | None
        number: DF.Data | None
        title: DF.Data | None
    # end: auto-generated types

    def before_save(self):
        self.title = f"{self.doc_name} №{self.number} {self.date}"
