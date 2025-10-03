# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class oiLocation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		building: DF.Data
		floor: DF.Data | None
		note: DF.SmallText | None
		responsible_name: DF.Data | None
		responsible_phone: DF.Data | None
		responsible_user: DF.Link | None
		room: DF.Data
	# end: auto-generated types

	pass
