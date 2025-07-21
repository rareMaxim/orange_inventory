# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class oiHardwareTransferItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		cost: DF.Currency
		hardware: DF.Link
		inventory_number: DF.Data | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		serial_number: DF.Data | None
	# end: auto-generated types

	pass
