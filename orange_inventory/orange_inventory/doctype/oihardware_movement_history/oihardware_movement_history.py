# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class oiHardwareMovementHistory(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		date: DF.Date | None
		document_name: DF.DynamicLink | None
		document_type: DF.Link | None
		from_party: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		to_party: DF.Link | None
	# end: auto-generated types

	pass
