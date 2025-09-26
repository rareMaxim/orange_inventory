# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class oiDonorProject(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		currency: DF.Link | None
		description: DF.TextEditor | None
		end_date: DF.Date | None
		primary_donor: DF.Link | None
		project_budget: DF.Currency
		project_name: DF.Data | None
		project_number: DF.Data | None
		start_date: DF.Date | None
		status: DF.Literal[
			"\u0410\u043a\u0442\u0438\u0432\u043d\u0438\u0439",
			"\u0417\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u0438\u0439",
			"\u0417\u0430\u043f\u043b\u0430\u043d\u043e\u0432\u0430\u043d\u0438\u0439",
		]
	# end: auto-generated types

	pass
