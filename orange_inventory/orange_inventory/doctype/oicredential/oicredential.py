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
		status: DF.Literal[
			"\u0410\u043a\u0442\u0443\u0430\u043b\u044c\u043d\u0438\u0439",
			"\u041d\u0435 \u043f\u0440\u0430\u0446\u044e\u0454",
			"\u041f\u0435\u0440\u0435\u0432\u0456\u0440\u0438\u0442\u0438",
		]
		title: DF.Data | None
		username: DF.Data | None
	# end: auto-generated types

	pass
