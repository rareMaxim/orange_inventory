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
			"\u041f\u0440\u0430\u0446\u044e\u0454 \u043e\u0447\u043d\u043e",
			"\u041f\u0440\u0430\u0446\u044e\u0454 \u0432\u0456\u0434\u0434\u0430\u043b\u0435\u043d\u043e",
			"\u0417\u0432\u0456\u043b\u044c\u043d\u0435\u043d\u043e",
			"\u0421\u043b\u0443\u0436\u0438\u0442\u044c",
			"\u041f\u0440\u043e\u0441\u0442\u043e\u0439",
			"\u0414\u0435\u043a\u0440\u0435\u0442",
			"\u041d\u0435 \u0434\u043e\u0441\u0442\u0443\u043f\u043d\u0438\u0439/\u043d\u0435 \u043f\u0440\u0430\u0446\u044e\u0454",
		]
		user: DF.Link | None
	# end: auto-generated types

	pass
