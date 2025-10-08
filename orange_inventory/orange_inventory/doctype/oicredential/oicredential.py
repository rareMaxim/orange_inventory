# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class oiCredential(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		credential_type: DF.Literal["Website", "Email", "OS Account", "SNMP", "SSH Key", "Other"]
		domain: DF.Data | None
		linked_asset: DF.Link | None
		notes: DF.SmallText | None
		secret: DF.Password | None
		title: DF.Data | None
		username: DF.Data | None
	# end: auto-generated types

	pass
