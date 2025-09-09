# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class oiServiceRequestActivity(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		activity_date: DF.Datetime | None
		activity_type: DF.Literal[
			"\u0421\u0442\u0432\u043e\u0440\u0435\u043d\u043e",
			"\u041e\u043d\u043e\u0432\u043b\u0435\u043d\u043e",
			"\u041f\u0440\u0438\u0437\u043d\u0430\u0447\u0435\u043d\u043e",
			"\u041a\u043e\u043c\u0435\u043d\u0442\u0430\u0440",
			"\u0417\u043c\u0456\u043d\u0430 \u0441\u0442\u0430\u0442\u0443\u0441\u0443",
			"\u041f\u0440\u0438\u043a\u0440\u0456\u043f\u043b\u0435\u043d\u0438\u0439 \u0444\u0430\u0439\u043b",
			"\u0412\u0438\u043a\u043e\u043d\u0430\u043d\u043e",
		]
		description: DF.SmallText | None
		new_value: DF.Data | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		previous_value: DF.Data | None
		user: DF.Link | None
	# end: auto-generated types

	pass
