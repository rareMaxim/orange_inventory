# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class oiEmployee(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		department: DF.Data | None
		full_name: DF.Data
		is_active: DF.Check
		organization: DF.Link | None
		position: DF.Data | None
		user: DF.Link | None
	# end: auto-generated types

	pass
