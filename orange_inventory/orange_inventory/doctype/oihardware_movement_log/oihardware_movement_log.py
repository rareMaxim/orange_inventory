# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class oiHardwareMovementLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from_counterparty: DF.Link
		movement_date: DF.Date
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		reference_doctype: DF.Data | None
		reference_document: DF.Data | None
		reference_name: DF.Data | None
		status: DF.Data | None
		to_counterparty: DF.Link
	# end: auto-generated types

	pass
