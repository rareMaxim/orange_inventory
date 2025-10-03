# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class oiCredentialAccessLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		credential: DF.Link
		ip_address: DF.Data | None
		reason: DF.SmallText | None
		timestamp: DF.Datetime | None
		user: DF.Link
		user_agent: DF.SmallText | None
	# end: auto-generated types

	pass
