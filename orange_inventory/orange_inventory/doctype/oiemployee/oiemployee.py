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

		birthday: DF.Date | None
		department: DF.Data | None
		full_name: DF.Data
		organization: DF.Link | None
		phone: DF.Data | None
		position: DF.Data | None
		status: DF.Literal[
			"\u041f\u0440\u0430\u0446\u044e\u0454", "\u0417\u0432\u0456\u043b\u044c\u043d\u0435\u043d\u043e"
		]
		user: DF.Link | None
	# end: auto-generated types

	pass
